import asyncio
import json
import logging
import logging.config
import os
import time
from contextlib import asynccontextmanager

import connexion
import requests
import uvicorn
import yaml
from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaConnectionError, KafkaError
from connexion import NoContent, request

# for use the log_conf.yml file to start logging events
with open("log_conf.yml", "r") as f:
    log_config = yaml.safe_load(f.read())
    logging.config.dictConfig(log_config)

logger = logging.getLogger("receiver")

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "redpanda:9092")
KAFKA_TOPIC_LOGIN = os.getenv("KAFKA_TOPIC_LOGIN", "login")
KAFKA_TOPIC_ACCESS = os.getenv("KAFKA_TOPIC_ACCESS", "accessChecks")

async def start_producer():
    """Start Kafka producer with exponential backoff on startup failure."""
    delay = 1
    while True:
        producer = AIOKafkaProducer(
            bootstrap_servers=KAFKA_BROKER,
            enable_idempotence=True,
            request_timeout_ms=10_000,
            retry_backoff_ms=250,
            linger_ms=5,
        )

        try:
            await producer.start()
            logger.info("Successfully connected to Kafka broker.")
            return producer
        except KafkaConnectionError:
            logger.warning("Kafka not reachable, retrying in %ss", delay)
            await producer.stop()
            await asyncio.sleep(delay)
            # Cap backoff delay at 30 seconds
            delay = min(delay * 2, 30)

@asynccontextmanager
async def lifespan(app):
    producer = await start_producer()
    try:
        yield {"kafka": producer}
    finally:
        logger.info("Closing Kafka producer connection...")
        await producer.stop()


async def login_event(body):
    """Handle incoming login events and publish them to Kafka."""

    # 1. Generate the trace_id
    body["trace_id"] = str(time.time_ns())

    # 2. Log that the event was received (INFO level)
    logger.info(
        f"Received 'login' event - user_id : {body['user_id']} | trace_id {body['trace_id']}"
    )

    # 3. Prepare Payload for kafka
    payload = json.dumps(body)
    producer = request.state.kafka

    try:
        # 4. Send and wait until Redpanda confirms it received the message
        metadata = await asyncio.wait_for(
            producer.send_and_wait(KAFKA_TOPIC_LOGIN, payload.encode("utf-8")),
            timeout=5
        )

        # 3. Log the response from kafka (DEBUG level)
        logger.debug(
            f"Publisohed login event to Kafka (trace_id: {body['trace_id']}) to partition {metadata.partition}, offset {metadata.offset}"
        )
        return NoContent, 201
    except (KafkaError, asyncio.TimeoutError) as e:
        logger.exception(f"Kafka unavailable, rejecting login event (trace_id: {body['trace_id']}): {e}")
        return {"error": "temporarily unavailable"}, 503


async def access_check(body):
    """Handle incoming access check events and publish them to Kafka."""
    body["trace_id"] = str(time.time_ns())
    logger.info(
        f"Received 'Access Check' event - user_id : {body['user_id']} | trace_id {body['trace_id']}"
    )
    payload = json.dumps(body)
    producer = request.state.kafka
    try:
        metadata = await asyncio.wait_for(
            producer.send_and_wait(KAFKA_TOPIC_ACCESS, payload.encode("utf-8")),
            timeout=5,
        )
        logger.debug(
            f"Published access check event to Kafka (trace_id: {body['trace_id']}) to partition {metadata.partition}, offset {metadata.offset}"
        )
        return NoContent, 201
    except (KafkaError, asyncio.TimeoutError) as e:
        logger.exception(f"Kafka unavailable, rejecting access check event (trace_id: {body['trace_id']}): {e}")
        return {"error": "temporarily unavailable"}, 503

def get_status():
    """Healthcheck endpoint."""
    return NoContent, 200


# Initialize the Connexion application
app = connexion.AsyncApp(__name__, specification_dir="", lifespan=lifespan)
app.add_api("receiver.yaml", strict_validation=True, validate_responses=True)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
