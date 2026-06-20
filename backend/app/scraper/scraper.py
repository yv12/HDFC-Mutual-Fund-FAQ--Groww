"""
Web scraping module — fetches and extracts mutual fund data from Groww URLs.

Uses Playwright (async) for headless browsing to handle Groww's Next.js
client-side rendered content.  Extracts structured fields and returns
them as `ScrapedFund` dataclass instances with full source metadata.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

# pyrefly: ignore [missing-import]
from playwright.async_api import async_playwright, Page, TimeoutError as PwTimeout

from app.config import settings
from app.scraper.urls import APPROVED_URLS

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------
from app.scraper.models import FundManager, ScrapedFund


# ---------------------------------------------------------------------------
# Extraction helpers  (each receives a Playwright Page)
# ---------------------------------------------------------------------------

async def _extract_text(page: Page, selector: str, default: str = "") -> str:
    """Return trimmed inner text of the *first* element matching selector."""
    try:
        el = page.locator(selector).first
        if await el.count():
            return (await el.inner_text()).strip()
    except Exception:
        pass
    return default


async def _extract_all_text(page: Page, selector: str) -> list[str]:
    """Return trimmed inner texts for *all* elements matching selector."""
    try:
        els = page.locator(selector)
        count = await els.count()
        results = []
        for i in range(count):
            results.append((await els.nth(i).inner_text()).strip())
        return results
    except Exception:
        return []


async def _extract_header(page: Page, fund: ScrapedFund) -> None:
    """Extract data from the header card: name, category, risk, NAV, etc."""

    # Scheme name (h1)
    fund.scheme_name = await _extract_text(page, "h1") or fund.scheme_name

    # Category pills  (e.g.  Equity | Mid Cap | Very High Risk)
    pills = await _extract_all_text(page, "[class*='pills_container'] span")
    if len(pills) >= 1:
        fund.category = pills[0]
    if len(pills) >= 2:
        fund.sub_category = pills[1]
    if len(pills) >= 3:
        fund.risk_level = pills[2]

    # Fund-details grid  (NAV, Min SIP, AUM, Expense ratio, Rating)
    details_container = page.locator("[class*='fundDetails_fundDetailsContainer']")
    if await details_container.count():
        items = details_container.locator("xpath=./div")
        item_count = await items.count()
        for i in range(item_count):
            item = items.nth(i)
            label = (await item.locator("[class*='contentTertiary']").first.inner_text()).strip()
            value = (await item.locator("[class*='contentPrimary']").first.inner_text()).strip()
            label_lower = label.lower()

            if "nav" in label_lower:
                fund.nav = value
                # Try extracting the date portion (e.g. "02 Jun '26")
                date_match = re.search(r"NAV:\s*(.+)", label, re.IGNORECASE)
                if date_match:
                    fund.nav_date = date_match.group(1).strip()
            elif "sip" in label_lower:
                fund.min_sip = value
            elif "fund size" in label_lower or "aum" in label_lower:
                fund.aum = value
            elif "expense" in label_lower:
                fund.expense_ratio = value
            elif "rating" in label_lower:
                # Value might contain star icon text; grab the number
                rating_match = re.search(r"(\d+\.?\d*)", value)
                fund.rating = rating_match.group(1) if rating_match else value


async def _extract_returns(page: Page, fund: ScrapedFund) -> None:
    """Extract annualised returns from the return calculator table."""
    try:
        rows = page.locator("[class*='returnCalculator'] table tbody tr")
        count = await rows.count()
        for i in range(count):
            row = rows.nth(i)
            cells = row.locator("td")
            if await cells.count() < 2:
                continue
            period = (await cells.first.inner_text()).strip().lower()
            # Last cell holds the return percentage
            ret_val = (await cells.last.inner_text()).strip()
            if "1 year" in period or "1y" in period:
                fund.returns_1y = ret_val
            elif "3 year" in period or "3y" in period:
                fund.returns_3y = ret_val
            elif "5 year" in period or "5y" in period:
                fund.returns_5y = ret_val
    except Exception as exc:
        logger.debug("Could not extract returns: %s", exc)


async def _extract_exit_load_and_tax(page: Page, fund: ScrapedFund) -> None:
    """Extract exit-load, stamp-duty, and tax info section."""
    try:
        # Look for section heading containing "Exit load" or "exit"
        headings = page.locator("h3, h2")
        count = await headings.count()
        for i in range(count):
            heading = headings.nth(i)
            text = (await heading.inner_text()).strip().lower()
            if "exit load" in text or "stamp duty" in text:
                # The section content typically follows the heading
                section = heading.locator("xpath=..")
                section_text = (await section.inner_text()).strip()
                fund.sections["Exit Load & Tax"] = section_text

                # Parse exit load value
                exit_match = re.search(
                    r"exit\s*load[:\s]*(.*?)(?:\n|stamp|$)",
                    section_text, re.IGNORECASE | re.DOTALL,
                )
                if exit_match:
                    fund.exit_load = exit_match.group(1).strip()

                # Parse stamp duty
                stamp_match = re.search(
                    r"stamp\s*duty[:\s]*([\d.]+%)",
                    section_text, re.IGNORECASE,
                )
                if stamp_match:
                    fund.stamp_duty = stamp_match.group(1).strip()
                break

        # Fallback: try extracting exit load from a table or key-value layout
        if not fund.exit_load:
            el_container = page.locator("text=/exit load/i").first
            if await el_container.count():
                parent = el_container.locator("xpath=ancestor::div[contains(@class,'container') or contains(@class,'section')]").first
                if await parent.count():
                    full_text = (await parent.inner_text()).strip()
                    # e.g. "Exit Load 1% if redeemed within 1 year"
                    m = re.search(r"exit\s*load\s*(.*?)(?:\n|$)", full_text, re.IGNORECASE)
                    if m:
                        fund.exit_load = m.group(1).strip()
    except Exception as exc:
        logger.debug("Could not extract exit load/tax: %s", exc)


async def _extract_fund_managers(page: Page, fund: ScrapedFund) -> None:
    """Extract fund-manager names and tenure."""
    try:
        # Look for the "Fund management" or "Fund Manager" section
        fm_heading = page.locator("text=/fund manage/i").first
        if not await fm_heading.count():
            return

        # Navigate to the section container
        section = fm_heading.locator("xpath=ancestor::section | ancestor::div[contains(@class,'Manager') or contains(@class,'fundManage')]").first
        if not await section.count():
            # Fallback: grab parent div
            section = fm_heading.locator("xpath=../..").first

        section_text = (await section.inner_text()).strip()
        fund.sections["Fund Managers"] = section_text

        # Parse manager names — pattern: "Name\nManaging since Mon YYYY"
        manager_blocks = re.findall(
            r"([A-Z][a-z]+(?:\s[A-Z][a-z]+)+)\s*(?:Managing\s+since|Since)\s+([A-Za-z]+\s+\d{4})",
            section_text,
            re.IGNORECASE,
        )
        for name, since in manager_blocks:
            fund.fund_managers.append(FundManager(name=name.strip(), since=since.strip()))

        # If regex didn't capture, try a simpler approach with name-like patterns
        if not fund.fund_managers:
            # Look for names in anchor tags or bold elements within the section
            name_els = section.locator("a, [class*='Heavy'], [class*='heavy']")
            for j in range(await name_els.count()):
                el_text = (await name_els.nth(j).inner_text()).strip()
                # Basic heuristic: a name is 2+ capitalised words, no numbers
                if re.match(r"^[A-Z][a-z]+(\s+[A-Z][a-z]+)+$", el_text):
                    fund.fund_managers.append(FundManager(name=el_text))
    except Exception as exc:
        logger.debug("Could not extract fund managers: %s", exc)


async def _extract_about(page: Page, fund: ScrapedFund) -> None:
    """Extract 'About the scheme', investment objective, and benchmark."""
    try:
        # Click any "Read more" buttons to expand hidden text
        read_more_buttons = page.locator("text=/read more/i")
        for i in range(await read_more_buttons.count()):
            try:
                await read_more_buttons.nth(i).click(timeout=2000)
                await asyncio.sleep(0.3)
            except Exception:
                pass

        # Look for the "About" section heading
        about_heading = page.locator("text=/about.*scheme|about.*fund/i").first
        if await about_heading.count():
            section = about_heading.locator("xpath=ancestor::section | xpath=ancestor::div[contains(@class,'about') or contains(@class,'About')]").first
            if not await section.count():
                section = about_heading.locator("xpath=../..").first
            section_text = (await section.inner_text()).strip()
            fund.sections["About"] = section_text

            # Parse "About" paragraph
            about_match = re.search(
                r"(?:about.*?(?:scheme|fund))\s*\n+(.*?)(?:\n\s*investment objective|\n\s*benchmark|\Z)",
                section_text, re.IGNORECASE | re.DOTALL,
            )
            if about_match:
                fund.about = about_match.group(1).strip()

            # Investment objective
            obj_match = re.search(
                r"investment\s*objective\s*\n+(.*?)(?:\n\s*benchmark|\n\s*scheme|\Z)",
                section_text, re.IGNORECASE | re.DOTALL,
            )
            if obj_match:
                fund.investment_objective = obj_match.group(1).strip()

            # Benchmark
            bench_match = re.search(
                r"benchmark\s*(?:index)?\s*\n*\s*(.+)",
                section_text, re.IGNORECASE,
            )
            if bench_match:
                fund.benchmark = bench_match.group(1).strip()

    except Exception as exc:
        logger.debug("Could not extract about section: %s", exc)


async def _extract_fund_house(page: Page, fund: ScrapedFund) -> None:
    """Extract fund-house (AMC) details and launch date."""
    try:
        fh_heading = page.locator("text=/fund house|AMC/i").first
        if not await fh_heading.count():
            return
        section = fh_heading.locator("xpath=ancestor::section | xpath=ancestor::div[3]").first
        if await section.count():
            section_text = (await section.inner_text()).strip()
            fund.sections["Fund House"] = section_text

            # Fund house name
            name_match = re.search(r"([\w\s]+mutual\s*fund)", section_text, re.IGNORECASE)
            if name_match:
                fund.fund_house = name_match.group(1).strip()

    except Exception as exc:
        logger.debug("Could not extract fund house: %s", exc)


async def _extract_minimum_investments(page: Page, fund: ScrapedFund) -> None:
    """Extract minimum investment amounts section."""
    try:
        heading = page.locator("text=/minimum.*invest/i").first
        if not await heading.count():
            return
        section = heading.locator("xpath=ancestor::section | xpath=ancestor::div[3]").first
        if await section.count():
            section_text = (await section.inner_text()).strip()
            fund.sections["Minimum Investments"] = section_text

            # Min lumpsum
            lump_match = re.search(r"(?:1st|first|initial)\s+(?:invest\w*)\s*[:\n]*\s*(₹[\d,]+)", section_text, re.IGNORECASE)
            if lump_match:
                fund.min_lumpsum = lump_match.group(1).strip()

    except Exception as exc:
        logger.debug("Could not extract minimum investments: %s", exc)


async def _extract_launch_date(page: Page, fund: ScrapedFund) -> None:
    """Try to find the scheme launch / inception date from the page text."""
    try:
        full_text = await page.inner_text("body")
        # Patterns like "Launch Date\n01 Jan 2013" or "Inception Date 10 Dec 1999"
        match = re.search(
            r"(?:launch|inception)\s*date\s*[:\n]*\s*(\d{1,2}\s+\w+\s+\d{4})",
            full_text, re.IGNORECASE,
        )
        if match:
            fund.launch_date = match.group(1).strip()
    except Exception as exc:
        logger.debug("Could not extract launch date: %s", exc)


async def _extract_from_json(page: Page, fund: ScrapedFund) -> bool:
    """
    Extract fund details from the Next.js __NEXT_DATA__ JSON payload.
    Returns True if successful, False otherwise.
    """
    try:
        script = page.locator("script#__NEXT_DATA__").first
        if not await script.count():
            return False
        content = await script.inner_text()
        if not content:
            return False
            
        data = json.loads(content)
        mf_data = data.get("props", {}).get("pageProps", {}).get("mfServerSideData", {})
        if not mf_data:
            return False
            
        # 1. Identity
        fund.scheme_name = mf_data.get("scheme_name", fund.scheme_name)
        fund.category = mf_data.get("category", fund.category)
        fund.sub_category = mf_data.get("sub_category", fund.sub_category)
        
        # Risk level
        ret_stats = mf_data.get("return_stats", [])
        risk_val = ""
        if ret_stats and isinstance(ret_stats, list):
            risk_val = ret_stats[0].get("risk", "")
        if not risk_val:
            risk_val = mf_data.get("nfo_risk", "")
        if risk_val:
            if not risk_val.lower().endswith("risk"):
                risk_val = f"{risk_val} Risk"
            fund.risk_level = risk_val
            
        # 2. NAV
        nav_val = mf_data.get("nav")
        if nav_val is not None:
            fund.nav = f"₹{nav_val}"
        fund.nav_date = mf_data.get("nav_date", fund.nav_date)
        
        # 3. Key stats
        min_sip = mf_data.get("min_sip_investment")
        if min_sip is not None:
            fund.min_sip = f"₹{min_sip}"
        min_lump = mf_data.get("min_investment_amount")
        if min_lump is not None:
            fund.min_lumpsum = f"₹{min_lump}"
            
        aum_val = mf_data.get("aum")
        if aum_val is not None:
            fund.aum = f"₹{aum_val:,.2f} Cr"
            
        exp_ratio = mf_data.get("expense_ratio")
        if exp_ratio is not None:
            try:
                exp_ratio_float = float(exp_ratio)
                fund.expense_ratio = f"{exp_ratio_float}%"
            except ValueError:
                fund.expense_ratio = f"{exp_ratio}%"
                
        rating_val = mf_data.get("groww_rating")
        if rating_val is not None:
            fund.rating = str(rating_val)
            
        # 4. Exit load & lock-in
        fund.exit_load = mf_data.get("exit_load", fund.exit_load)
        fund.stamp_duty = mf_data.get("stamp_duty", fund.stamp_duty)
        
        lock_in_dict = mf_data.get("lock_in")
        if lock_in_dict and isinstance(lock_in_dict, dict):
            parts = []
            if lock_in_dict.get("years"):
                parts.append(f"{lock_in_dict['years']} year" + ("s" if lock_in_dict['years'] > 1 else ""))
            if lock_in_dict.get("months"):
                parts.append(f"{lock_in_dict['months']} month" + ("s" if lock_in_dict['months'] > 1 else ""))
            if lock_in_dict.get("days"):
                parts.append(f"{lock_in_dict['days']} day" + ("s" if lock_in_dict['days'] > 1 else ""))
            fund.lock_in_period = ", ".join(parts) if parts else "No lock-in"
        else:
            fund.lock_in_period = "No lock-in"
            
        # 5. Benchmark & fund house
        fund.benchmark = mf_data.get("benchmark", fund.benchmark)
        fund.fund_house = mf_data.get("fund_house", fund.fund_house)
        fund.launch_date = mf_data.get("launch_date", fund.launch_date)
        
        # 6. Description/about
        fund.about = mf_data.get("description", fund.about)
        fund.investment_objective = mf_data.get("description", fund.investment_objective)
        
        # 7. Fund managers
        managers = mf_data.get("fund_manager_details", [])
        fund.fund_managers = []
        for mgr in managers:
            name = mgr.get("person_name", "")
            date_from = mgr.get("date_from", "")
            since_val = ""
            if date_from:
                try:
                    dt = datetime.fromisoformat(date_from.replace("Z", "+00:00"))
                    since_val = dt.strftime("%b %Y")
                except Exception:
                    since_val = date_from
            fund.fund_managers.append(
                FundManager(
                    name=name,
                    since=since_val,
                    qualification=mgr.get("education", ""),
                    experience=mgr.get("experience", "")
                )
            )
            
        # 8. Returns
        stats_list = mf_data.get("stats", [])
        for stat in stats_list:
            if stat.get("type") == "FUND_RETURN":
                if stat.get("stat_1y") is not None:
                    fund.returns_1y = f"{stat['stat_1y']}%"
                if stat.get("stat_3y") is not None:
                    fund.returns_3y = f"{stat['stat_3y']}%"
                if stat.get("stat_5y") is not None:
                    fund.returns_5y = f"{stat['stat_5y']}%"
                break
                
        # 9. Sections dictionary (for matching with test cases / chunker fallback)
        exit_prose = f"Exit load: {fund.exit_load}\nLock-in period: {fund.lock_in_period}\nStamp duty: {fund.stamp_duty}"
        fund.sections["Exit Load & Tax"] = exit_prose
        
        if fund.fund_managers:
            fm_parts = []
            for fm in fund.fund_managers:
                line = f"- {fm.name}"
                if fm.since:
                    line += f" (managing since {fm.since})"
                if fm.qualification:
                    line += f", {fm.qualification}"
                if fm.experience:
                    line += f", {fm.experience}"
                fm_parts.append(line)
            fund.sections["Fund Managers"] = "\n".join(fm_parts)
            
        if fund.about:
            fund.sections["About"] = fund.about
            
        if fund.fund_house:
            fund.sections["Fund House"] = fund.fund_house
            
        min_prose = f"Minimum SIP Investment: {fund.min_sip}\nMinimum Lumpsum Investment: {fund.min_lumpsum}"
        fund.sections["Minimum Investments"] = min_prose
        
        return True
    except Exception as exc:
        logger.warning("Error parsing NEXT_DATA JSON: %s", exc)
        return False


# ---------------------------------------------------------------------------
# Main scraper
# ---------------------------------------------------------------------------

async def scrape_single_url(
    page: Page,
    url: str,
    scheme_name: str,
    *,
    timeout_ms: int = 30_000,
    max_retries: int = 3,
) -> Optional[ScrapedFund]:
    """
    Navigate to *url* using *page*, extract all structured fields, and return
    a populated `ScrapedFund`.  Retries on transient failures.
    """
    last_error: Optional[Exception] = None
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(
                "Scraping %s (attempt %d/%d) …", scheme_name, attempt, max_retries,
            )
            await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)

            # Wait for the fund details container to appear (JS hydration)
            try:
                await page.wait_for_selector(
                    "[class*='fundDetails_fundDetailsContainer'], h1",
                    timeout=15_000,
                )
            except PwTimeout:
                logger.warning("Fund details container did not appear; continuing anyway")

            # Small extra wait for remaining hydration
            await asyncio.sleep(2)

            fund = ScrapedFund(
                scheme_name=scheme_name,
                source_url=url,
                scraped_at=datetime.now(timezone.utc).isoformat(),
            )

            # Try to extract via JSON first (highly robust)
            if await _extract_from_json(page, fund):
                logger.info("✓ Scraped %s via JSON — NAV=%s, AUM=%s", scheme_name, fund.nav, fund.aum)
                return fund

            # Fallback to DOM extractors if JSON extraction fails
            logger.warning("NEXT_DATA JSON extraction failed, falling back to DOM extraction...")
            await _extract_header(page, fund)
            await _extract_returns(page, fund)

            # Scroll to the bottom to trigger lazy-loaded sections
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(1.5)

            await _extract_exit_load_and_tax(page, fund)
            await _extract_fund_managers(page, fund)
            await _extract_about(page, fund)
            await _extract_fund_house(page, fund)
            await _extract_minimum_investments(page, fund)
            await _extract_launch_date(page, fund)

            logger.info("✓ Scraped %s (DOM Fallback) — NAV=%s, AUM=%s", scheme_name, fund.nav, fund.aum)
            return fund

        except PwTimeout as exc:
            last_error = exc
            wait = 2 ** attempt
            logger.warning(
                "Timeout scraping %s (attempt %d/%d). Retrying in %ds …",
                scheme_name, attempt, max_retries, wait,
            )
            await asyncio.sleep(wait)

        except Exception as exc:
            last_error = exc
            wait = 2 ** attempt
            logger.error(
                "Error scraping %s (attempt %d/%d): %s. Retrying in %ds …",
                scheme_name, attempt, max_retries, exc, wait,
            )
            await asyncio.sleep(wait)

    logger.error("✗ Failed to scrape %s after %d attempts: %s", scheme_name, max_retries, last_error)
    return None


async def scrape_all_urls(
    *,
    timeout_ms: int | None = None,
    max_retries: int | None = None,
) -> list[ScrapedFund]:
    """
    Scrape all pre-approved URLs and return a list of `ScrapedFund` objects.

    Uses a single browser instance with one page (sequential) to avoid
    overloading the target site.
    """
    _timeout = timeout_ms or settings.scrape_timeout_ms
    _retries = max_retries or settings.scrape_max_retries

    results: list[ScrapedFund] = []

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
        )
        page = await context.new_page()

        for entry in APPROVED_URLS:
            fund = await scrape_single_url(
                page,
                entry["url"],
                entry["scheme_name"],
                timeout_ms=_timeout,
                max_retries=_retries,
            )
            if fund is not None:
                results.append(fund)

        await browser.close()

    logger.info(
        "Scraping complete: %d / %d URLs succeeded.",
        len(results), len(APPROVED_URLS),
    )
    return results
