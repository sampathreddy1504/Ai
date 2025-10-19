# backend/app/tools/semantic_inspect.py
"""
Semantic Memory Inspector
-------------------------
Allows manual querying of Pinecone memory for any user.

Usage:
    docker exec -it <backend_container> python app/tools/semantic_inspect.py <user_id> "<query>"
Example:
    docker exec -it backend python app/tools/semantic_inspect.py user123 "hackathon"
"""

import sys
import logging
from app.services.semantic_memory import query_semantic_memory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    if len(sys.argv) < 3:
        print("Usage: python app/tools/semantic_inspect.py <user_id> \"<query>\"")
        sys.exit(1)

    user_id = sys.argv[1]
    query = sys.argv[2]

    logger.info(f"🔍 Searching semantic memory for user '{user_id}' with query: '{query}'")
    matches = query_semantic_memory(user_id, query, top_k=5)

    if not matches:
        logger.warning("❌ No semantic results found.")
    else:
        logger.info("✅ Top semantic matches:")
        for m in matches:
            md = m.get("metadata", {})
            score = m.get("score", 0)
            logger.info(f" - ({score:.3f}) {md.get('text')}")

if __name__ == "__main__":
    main()
