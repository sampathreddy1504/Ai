# backend/app/db/neo4j_utils.py
import logging
from neo4j import GraphDatabase
from app.config import settings

logger = logging.getLogger(__name__)

# ======================================================
# 🔹 Neo4j Connection
# ======================================================
def get_driver():
    try:
        driver = GraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
        )
        return driver
    except Exception as e:
        logger.error(f"Failed to connect to Neo4j: {e}")
        raise


# ======================================================
# 🔹 FACT STORAGE
# ======================================================
def save_fact_neo4j(key: str, value: str):
    """
    Save or update a general fact (not tied to user).
    """
    query = """
    MERGE (f:Fact {key: $key})
    SET f.value = $value,
        f.updated_at = timestamp()
    RETURN f
    """
    try:
        driver = get_driver()
        with driver.session() as session:
            session.run(query, key=key, value=value)
        driver.close()
        logger.info(f"✅ Saved fact: {key} → {value}")
    except Exception as e:
        logger.error(f"❌ Failed to save fact in Neo4j: {e}")


def get_fact_neo4j(key: str):
    """
    Retrieve a fact by key.
    """
    query = "MATCH (f:Fact {key: $key}) RETURN f.value AS value"
    try:
        driver = get_driver()
        with driver.session() as session:
            result = session.run(query, key=key)
            record = result.single()
            driver.close()
            if record:
                return record["value"]
            return None
    except Exception as e:
        logger.error(f"❌ Failed to fetch fact from Neo4j: {e}")
        return None


# ======================================================
# 🔹 USER FACTS (Personalization)
# ======================================================
def save_user_fact_neo4j(user_id: str, key: str, value: str):
    """
    Save a personalized user fact (e.g., name, preferences).
    Creates (User)-[:OWNS]->(Fact) relationship.
    """
    query = """
    MERGE (u:User {id: $user_id})
    MERGE (f:Fact {key: $key})
    SET f.value = $value,
        f.updated_at = timestamp()
    MERGE (u)-[:OWNS]->(f)
    RETURN f
    """
    try:
        driver = get_driver()
        with driver.session() as session:
            session.run(query, user_id=user_id, key=key, value=value)
        driver.close()
        logger.info(f"✅ Saved user fact: {user_id} → {key}: {value}")
    except Exception as e:
        logger.error(f"❌ Failed to save user fact in Neo4j: {e}")


def get_user_fact_neo4j(user_id: str, key: str):
    """
    Retrieve a specific fact for a user.
    """
    query = """
    MATCH (u:User {id: $user_id})-[:OWNS]->(f:Fact {key: $key})
    RETURN f.value AS value
    """
    try:
        driver = get_driver()
        with driver.session() as session:
            result = session.run(query, user_id=user_id, key=key)
            record = result.single()
            driver.close()
            if record:
                return record["value"]
            return None
    except Exception as e:
        logger.error(f"❌ Failed to get user fact: {e}")
        return None


def get_all_facts_for_user(user_id: str):
    """
    Retrieve all facts linked to a user.
    """
    query = """
    MATCH (u:User {id: $user_id})-[:OWNS]->(f:Fact)
    RETURN f.key AS key, f.value AS value
    """
    try:
        driver = get_driver()
        with driver.session() as session:
            results = session.run(query, user_id=user_id)
            facts = {r["key"]: r["value"] for r in results}
        driver.close()
        return facts
    except Exception as e:
        logger.error(f"❌ Failed to fetch all facts for user: {e}")
        return {}


# ======================================================
# 🔹 INITIALIZATION UTILITIES
# ======================================================
def ensure_constraints():
    """
    Ensures Neo4j constraints for clean schema setup.
    """
    queries = [
        "CREATE CONSTRAINT user_id_unique IF NOT EXISTS FOR (u:User) REQUIRE u.id IS UNIQUE",
        "CREATE CONSTRAINT fact_key_unique IF NOT EXISTS FOR (f:Fact) REQUIRE f.key IS UNIQUE"
    ]
    try:
        driver = get_driver()
        with driver.session() as session:
            for q in queries:
                session.run(q)
        driver.close()
        logger.info("✅ Neo4j constraints ensured (User.id, Fact.key)")
    except Exception as e:
        logger.error(f"❌ Failed to ensure Neo4j constraints: {e}")


# ======================================================
# 🔹 BACKWARD COMPATIBILITY ALIAS
# ======================================================
def get_facts_neo4j(user_id: str):
    """
    Alias for old code expecting get_facts_neo4j().
    """
    return get_all_facts_for_user(user_id)
