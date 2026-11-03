import os
import time
import json
import logging
import logging.config
import yaml
from datetime import datetime, UTC
import requests
import redis

# Load logging configuration
with open("log_conf.yml", 'r') as f:
    log_config = yaml.safe_load(f.read())
    logging.config.dictConfig(log_config)

logger = logging.getLogger("processing-worker")

STORAGE_SERVICE_URL = os.getenv("STORAGE_SERVICE_URL", "http://storage:8090")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "5"))

DEFAULT_STATS = {
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

def get_redis_client():
    return redis.Redis.from_url(REDIS_URL, decode_responses=True)

def init_stats(client):
    """Ensure statistics exist in Redis."""
    try:
        data = client.get("stats")
        if not data:
            logger.info("Initializing default statistics in Redis ... ")
            client.set("stats", json.dumps(DEFAULT_STATS))
    except redis.exceptions.RedisError as e:
        logger.warning(f"Could not connect to Redis on initialization: {e}")

def fetch_events(endpoint, after_timestamp, last_id=0):
    """Query storage service for events after a specific timestamp (with ID tie-breaker)."""
    url = f"{STORAGE_SERVICE_URL}{endpoint}"
    params = {}
    if after_timestamp:
        params["after"] = after_timestamp
        params["last_id"] = last_id
    response = requests.get(url, params=params, timeout=5)
    response.raise_for_status()
    return response.json()

def process_events():
    """Main worker loop."""
    logger.info(f"Connecting to Redis at {REDIS_URL} ... ")
    client = get_redis_client()
    init_stats(client)

    logger.info(f"Worker started. Polling {STORAGE_SERVICE_URL} every {POLL_INTERVAL} seconds ... ")

    while True:
        cycle_start = time.time()
        logger.info("Starting processing loop cycle...")

        try:
            # 1. Fetch current statistics from Redis
            raw_stats = client.get("stats")
            stats = json.loads(raw_stats) if raw_stats else DEFAULT_STATS.copy()
            last_login_ts = stats.get("latest_login_timestamp")
            last_login_id = stats.get("last_login_id", 0)
            last_check_ts = stats.get("latest_access_check_timestamp")
            last_check_id = stats.get("last_access_check_id", 0)

            # 2. Fetch new event batches from storage
            new_logins = fetch_events("/auth/login", last_login_ts, last_login_id)
            new_access_checks = fetch_events("/auth/access-check", last_check_ts, last_check_id)
            logger.info(
                f"Received {len(new_logins)} new login events and "
                f"{len(new_access_checks)} new access check events from storage."
            )
 
            # 3. If new events arrived, compute updated metrics
            if new_logins or new_access_checks:
                stats["total_login_events"] += len(new_logins)
                stats["total_access_checks"] += len(new_access_checks)
       
                for login in new_logins:
                    failed = login.get("failed_attempts", 0)
                    if failed > stats["max_failed_attempts"]:
                        stats["max_failed_attempts"] = failed
      
                for check in new_access_checks:
                    level = check.get("privilege_level", 0)
                    if level > stats["max_privilege_level"]:
                        stats["max_privilege_level"] = level
 
                # Update login watermark and tie-breaker ID
                if new_logins:
                    latest_login = max(
                        new_logins,
                        key=lambda e: (e.get("recorded_timestamp") or "", e.get("id") or 0)
                    )
                    stats["latest_login_timestamp"] = latest_login.get("recorded_timestamp")
                    stats["last_login_id"] = latest_login.get("id", 0)

                # Update access check watermark and tie-breaker ID
                if new_access_checks:
                    latest_check = max(
                        new_access_checks,
                        key=lambda e: (e.get("recorded_timestamp") or "", e.get("id") or 0)
                    )
                    stats["latest_access_check_timestamp"] = latest_check.get("recorded_timestamp")
                    stats["last_access_check_id"] = latest_check.get("id", 0)

                stats["last_updated"] = datetime.now(UTC).isoformat()
           
                # 4. Save updated stats to Redis
                client.set("stats", json.dumps(stats))
                logger.info("Statistics successfully updated and saved to Redis.")
                logger.debug(f"Updated statistics values: {stats}")
            else:
                logger.debug("No new events to process in this cycle.")
 
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch events from storage service: {e}")
        except redis.exceptions.RedisError as e:
            logger.error(f"Redis error during processing cycle: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in processing cycle: {e}")
        duration = round(time.time() - cycle_start, 4)
        logger.info(f"Cycle completed in {duration} seconds. Sleeping for {POLL_INTERVAL}s...")
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    process_events()