import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from scripts.ingest import run_pipeline
import pytz

logger = logging.getLogger(__name__)

# Initialize the scheduler
scheduler = AsyncIOScheduler(timezone=pytz.timezone("Asia/Kolkata"))

# Global flag to track if ingestion is currently running
IS_SYNCING = False

import asyncio

def _run_sync_in_thread():
    """Runs the sync pipeline in a completely fresh event loop."""
    asyncio.run(run_pipeline(dry_run=False, inspect=False))

async def scheduled_ingestion():
    """Wrapper for the ingestion pipeline to be called by the scheduler."""
    global IS_SYNCING
    logger.info("Starting scheduled knowledge base ingestion...")
    IS_SYNCING = True
    try:
        # Run the entire pipeline in a background thread to prevent Playwright EventLoop
        # conflicts on Windows and to stop ChromaDB/Embedding from freezing FastAPI.
        await asyncio.to_thread(_run_sync_in_thread)
        logger.info("Scheduled ingestion completed successfully.")
    except Exception as e:
        logger.error(f"Scheduled ingestion failed: {e}")
    finally:
        IS_SYNCING = False

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
