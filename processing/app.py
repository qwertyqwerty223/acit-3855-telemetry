import os
import json
import logging
import logging.config
import yaml
from datetime import datetime, UTC
from contextlib import asynccontextmanager
import redis
import connexion
from connexion import request
import uvicorn

# Load logging configuration
with open('log_conf.yml', 'r') as f:
    log_config = yaml.safe_load(f.read())
    logging.config.dictConfig(log_config)

logger = logging.getLogger('processing-api')

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")

@asynccontextmanager
async def lifespan(app):
    """Manage persistent Redis connection lifecycle."""
    logger.info(f"Connecting to Redis at {REDIS_URL}...")
    client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
    try:
        client.ping()
        logger.info("Successfully connected to Redis.")
    except Exception as e:
        logger.warning(f"Initial Redis ping failed: {e}. API will attempt query on request.")
    try:
        yield {"redis": client}
    finally:
        logger.info("Closing Redis connection...")
        client.close()

def get_stats():
    """Retrieve aggregate security telemetry statistics from Redis."""
    default_stats = {
        "total_login_events": 0,
        "total_access_checks": 0,
        "max_failed_attempts": 0,
        "max_privilege_level": 0,
        "latest_login_timestamp": None,
        "latest_access_check_timestamp": None,
        "last_login_id": 0,
        "last_access_check_id": 0,
        "last_updated": datetime.now(UTC).isoformat()
    }

    try:
        redis_client = request.state.redis
        data = redis_client.get("stats")
    except Exception as e:
        logger.error(f"Error reading statistics from Redis: {e}")
        return default_stats, 200

    if not data:
        logger.info("No statistics found in Redis yet. Returning initial defaults.")
        return default_stats, 200

    stats = json.loads(data)
    logger.debug(f"Serving statistics: {stats}")
    return stats, 200

app = connexion.AsyncApp(__name__, specification_dir='', lifespan=lifespan)
app.add_api("processing.yaml", strict_validation=True, validate_responses=True)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8100)