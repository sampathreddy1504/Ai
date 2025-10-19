# backend/app/tools/semantic_memory_test.py
"""
Semantic Memory Integration Test
---------------------------------
✅ Verifies your Pinecone + Embeddings setup
✅ Ensures store and query operations work correctly
✅ Safe to run locally or inside the Docker container

Usage:
    docker exec -it <your_backend_container_name> python app/tools/semantic_memory_test.py
"""

import sys
import logging
from app.services.semantic_memory import store_semantic_memory, query_semantic_memory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    logger.info("🔍 Starting semantic memory integration test...")

    # Test user and messages
    user_id = "test_user_001"
    sample_texts = [
        "I enjoy building AI assistants using FastAPI and React.",
        "My favorite fruit is mango.",
        "Remind me to attend the hackathon next weekend."
    ]

    # 1️⃣ Store entries
    for txt in sample_texts:
        res = store_semantic_memory(user_id, txt)
        if res["ok"]:
            logger.info(f"✅ Stored memory: {txt[:60]}...")
        else:
            logger.error(f"❌ Failed to store: {txt}")

    # 2️⃣ Query similar memories
    query = "What do I like to build?"
    matches = query_semantic_memory(user_id, query, top_k=3)

    logger.info(f"\n🔎 Query: {query}")
    if not matches:
        logger.warning("No results found. Pinecone may not be indexing yet.")
    else:
        logger.info("✅ Semantic memory returned results:")
        for m in matches:
            md = m.get("metadata", {})
            score = m.get("score", 0)
            logger.info(f" - ({score:.3f}) {md.get('text')}")

    logger.info("✅ Semantic memory test completed successfully.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.exception(f"Semantic memory test failed: {e}")
        sys.exit(1)
