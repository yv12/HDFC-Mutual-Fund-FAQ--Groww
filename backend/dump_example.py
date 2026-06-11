import asyncio
from dataclasses import asdict
from playwright.async_api import async_playwright
from app.scraper.scraper import scrape_single_url
from app.ingestion.chunker import chunk_fund
from app.scraper.urls import APPROVED_URLS
import json

async def main():
    target = APPROVED_URLS[0]
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        fund = await scrape_single_url(page, target["url"], target["scheme_name"])
        await browser.close()
        
    if not fund:
        print("Failed to scrape")
        return
        
    chunks = chunk_fund(fund)
    
    with open("../example_scrape_and_chunk.txt", "w", encoding="utf-8") as f:
        f.write("================== RAW SCRAPED DATA ==================\n")
        f.write(json.dumps(asdict(fund), indent=2))
        f.write("\n\n================== AFTER CHUNKING ==================\n")
        for i, c in enumerate(chunks):
            f.write(f"--- CHUNK {i+1} (Section: {c.section}) ---\n")
            f.write(c.text)
            f.write("\n\n")
    print("Done. Saved to ../example_scrape_and_chunk.txt")

if __name__ == "__main__":
    asyncio.run(main())
