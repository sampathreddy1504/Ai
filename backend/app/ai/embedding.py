# backend/app/ai/embedding.py
from typing import List
import hashlib
import random

def get_embedding(text: str) -> List[float]:
    """
    Returns a deterministic pseudo-embedding for a given text.
    Replace this with your real embedding model later.
    """
    # Simple deterministic random vector based on hash
    seed = int(hashlib.sha256(text.encode()).hexdigest(), 16) % (2**32)
    random.seed(seed)
    return [random.random() for _ in range(1536)]  # match your EMBEDDING_DIM

