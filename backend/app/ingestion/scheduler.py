"""
Ingestion scheduler — conditional cron + manual sync support.

When ENABLE_SCHEDULER=true (local dev): Runs APScheduler with a daily
cron job at 9:15 AM and supports manual sync via API.

When ENABLE_SCHEDULER=false (Railway): No cron job. Manual sync endpoint
still works but scraping requires Playwright (not available on Railway).
"""

import logging
import asyncio

from app.config import settings

logger = logging.getLogger(__name__)

# Global flag to track if ingestion is currently running
IS_SYNCING = False


def _run_sync_in_thread():
    """Runs the sync pipeline in a completely fresh event loop."""
    from scripts.ingest import run_pipeline
    asyncio.run(run_pipeline(dry_run=False, inspect=False))


async def scheduled_ingestion():
    """Wrapper for the ingestion pipeline to be called by the scheduler or manual trigger."""
    global IS_SYNCING
    logger.info("Starting knowledge base ingestion...")
    IS_SYNCING = True
    try:
        # Run the entire pipeline in a background thread to prevent Playwright EventLoop
        # conflicts on Windows and to stop ChromaDB/Embedding from freezing FastAPI.
        await asyncio.to_thread(_run_sync_in_thread)
        logger.info("Ingestion completed successfully.")
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
    finally:
        IS_SYNCING = False


# ── Scheduler (conditional) ──────────────────────────────────────
_scheduler = None


def start_scheduler():
    """Start the background scheduler for daily ingestion (if enabled)."""
    global _scheduler
    if not settings.enable_scheduler:
        logger.info("Scheduler disabled (ENABLE_SCHEDULER=false). Cron job will not run.")
        return

    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from apscheduler.triggers.cron import CronTrigger
        import pytz

        _scheduler = AsyncIOScheduler(timezone=pytz.timezone("Asia/Kolkata"))
        _scheduler.add_job(
            scheduled_ingestion,
            trigger=CronTrigger(hour=9, minute=15),
            id="daily_ingestion_job",
            name="Daily Knowledge Base Ingestion",
            replace_existing=True,
        )
        _scheduler.start()
        logger.info("Hybrid ingestion scheduler started (Next run at 09:15 AM).")
    except ImportError:
        logger.warning("APScheduler not installed. Cron job will not run (expected on Railway).")
    except Exception as exc:
        logger.error("Failed to start scheduler: %s", exc)


def stop_scheduler():
    """Stop the background scheduler (if running)."""
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        _scheduler.shutdown()
        logger.info("Hybrid ingestion scheduler stopped.")
