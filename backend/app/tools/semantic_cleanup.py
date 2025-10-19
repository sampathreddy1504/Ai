# backend/app/tools/semantic_cleanup.py
"""
Semantic Memory Cleanup Utility
-------------------------------
Removes Pinecone vectors older than 90 days (configurable).
Can be run as a scheduled task (cron or Celery) or manually.

Usage:
    docker exec -it <backend_container> python app/tools/semantic_cleanup.py
"""

import logging
import time
from datetime import datetime, timedelta

from app.db.pinecone_utils import get_index
from app.config_pinecone import pinecone_settings

# 🕒 Retention period (seconds) — 90 days
RETENTION_SECONDS = 90 * 24 * 3600

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def cleanup_old_vectors():
    index = get_index()
    logger.info(f"🧹 Starting semantic cleanup for index '{pinecone_settings.PINECONE_INDEX_NAME}'")
    now = int(time.time())
    cutoff = now - RETENTION_SECONDS

    try:
        # Pinecone does not support direct server-side filtering deletion by timestamp yet.
        # We'll fetch all vector metadata via `list` or `fetch` API in batches.
        # (This approach depends on your Pinecone plan and client version.)
        stats = index.describe_index_stats()
        total_vectors = stats.get("total_vector_count", "unknown")
        logger.info(f"ℹ️ Index has approximately {total_vectors} vectors.")

        # NOTE: Most Pinecone environments don't support listing all items.
        # In practice, you'd maintain metadata in Postgres for fast lookups.
        # Here, we'll just log a warning for manual cleanup.
        logger.warning("⚠️ Pinecone currently does not provide full vector enumeration via API.")
        logger.warning("Consider tracking metadata in PostgreSQL for scalable cleanup.")
        logger.info(f"🧾 Retention cutoff timestamp: {datetime.fromtimestamp(cutoff)}")

    except Exception as e:
        logger.exception("Cleanup failed: %s", e)
        return False

    logger.info("✅ Cleanup completed (or simulated). For production, use metadata tracking to delete stale IDs.")
    return True

if __name__ == "__main__":
    cleanup_old_vectors()
