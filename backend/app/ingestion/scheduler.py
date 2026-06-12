import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from scripts.ingest import run_pipeline
import pytz
import time

logger = logging.getLogger(__name__)

# Initialize the scheduler
scheduler = AsyncIOScheduler(timezone=pytz.timezone("Asia/Kolkata"))

# Sync tracking with auto-expiry to prevent stuck flags
_sync_start_time: float | None = None
_SYNC_TIMEOUT_SECONDS = 600  # 10 minutes max




def get_is_syncing() -> bool:
    """Check if sync is running, with auto-expiry after 10 minutes."""
    global _sync_start_time
    if _sync_start_time is None:
        return False
    elapsed = time.time() - _sync_start_time
    if elapsed > _SYNC_TIMEOUT_SECONDS:
        logger.warning(
            "IS_SYNCING was stuck for %.0f seconds — auto-resetting to False.",
            elapsed,
        )
        _sync_start_time = None
        return False
    return True

# Keep IS_SYNCING as a property-like getter for backward compat
IS_SYNCING = False  # Will be updated dynamically

import asyncio

def _run_sync_in_thread():
    """Runs the sync pipeline in a completely fresh event loop."""
    asyncio.run(run_pipeline(dry_run=False, inspect=False))

async def scheduled_ingestion():
    """Wrapper for the ingestion pipeline to be called by the scheduler."""
    global _sync_start_time, IS_SYNCING
    logger.info("Starting scheduled knowledge base ingestion...")
    _sync_start_time = time.time()
    IS_SYNCING = True
    try:
        # Run the entire pipeline in a background thread to prevent Playwright EventLoop
        # conflicts on Windows and to stop ChromaDB/Embedding from freezing FastAPI.
        await asyncio.to_thread(_run_sync_in_thread)
        logger.info("Scheduled ingestion completed successfully.")
    except Exception as e:
        logger.error(f"Scheduled ingestion failed: {e}")
    finally:
        _sync_start_time = None
        IS_SYNCING = False
        logger.info("IS_SYNCING reset to False.")

def start_scheduler():
    """Start the background scheduler for daily ingestion."""
    # Run every day at 09:15 AM
    scheduler.add_job(
        scheduled_ingestion,
        trigger=CronTrigger(hour=9, minute=15),
        id="daily_ingestion_job",
        name="Daily Knowledge Base Ingestion",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Hybrid ingestion scheduler started (Next run at 09:15 AM).")

def stop_scheduler():
    """Stop the background scheduler."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Hybrid ingestion scheduler stopped.")
