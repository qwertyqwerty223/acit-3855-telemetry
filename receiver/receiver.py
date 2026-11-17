import logging
import logging.config
import os
import time

import connexion
import requests
import uvicorn
import yaml
from connexion import NoContent

# for use the log_conf.yml file to start logging events
with open("log_conf.yml", "r") as f:
    log_config = yaml.safe_load(f.read())
    logging.config.dictConfig(log_config)

logger = logging.getLogger("receiver")

STORAGE_SERVICE_URL = os.getenv("STORAGE_SERVICE_URL")
if not STORAGE_SERVICE_URL:
    logger.error("FATAL: STORAGE_SERVICE_URL environment variable is not set!")
    raise RuntimeError("STORAGE_SERVICE_URL environment variable is required.")


def login_event(body):
    """Handle incoming login events and forward to storage."""

    # 1. Generate teh trace_id
    body["trace_id"] = str(time.time_ns())

    # 2. Log that the event was received (INFO level)
    logger.info(
        f"Received 'login' event - user_id : {body['user_id']} | trace_id {body['trace_id']}"
    )
    try:
        response = requests.post(
            f"{STORAGE_SERVICE_URL}/auth/login", json=body, timeout=5
        )

        # 3. Log the response from storage (DEBUG level)
        logger.debug(
            f"Response for login event (trace_id: {body['trace_id']}) has status {response.status_code}"
        )

        return NoContent, 201
    except requests.exceptions.RequestException as e:
        logger.error(f"Error communicating with storage service: {e}")
        return NoContent, 500


def access_check(body):
    """Handle incoming access check events and forward to storage."""

    # 1. Generate the trace_id
    body["trace_id"] = str(time.time_ns())

    # 2. Log that the event was received (INFO level)
    logger.info(
        f"Received 'Access Check' event - user_id : {body['user_id']} | trace_id {body['trace_id']}"
    )
    try:
        response = requests.post(
            f"{STORAGE_SERVICE_URL}/auth/access-check", json=body, timeout=5
        )

        # 3. Log the response from storage (DEBUG level)
        logger.debug(
            f"Response for Access Check event (trace_id: {body['trace_id']}) has status {response.status_code}"
        )

        return NoContent, 201
    except requests.exceptions.RequestException as e:
        logger.error(f"Error communicating with storage service: {e}")
        return NoContent, 500


def get_status():
    """Healthcheck endpoint."""
    return NoContent, 200


# Initialize the Connexion application
app = connexion.AsyncApp(__name__, specification_dir="")
app.add_api("receiver.yaml", strict_validation=True, validate_responses=True)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
