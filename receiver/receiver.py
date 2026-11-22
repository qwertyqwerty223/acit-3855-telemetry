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
from aiokafka.errors import KafkaError
from connexion import NoContent, request

# for use the log_conf.yml file to start logging events
with open("log_conf.yml", "r") as f:
    log_config = yaml.safe_load(f.read())
    logging.config.dictConfig(log_config)

logger = logging.getLogger("receiver")

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "redpanda:9092")
KAFKA_TOPIC_LOGIN = os.getenv("KAFKA_TOPIC_LOGIN", "login")
KAFKA_TOPIC_ACCESS = os.getenv("KAFKA_TOPIC_ACCESS", "accessChecks")


@asynccontextmanager
async def lifespan(app):
    producer = AIOKafkaProducer(bootstrap_servers=[KAFKA_BROKER])

    await producer.start()
    try:
        yield {"kafka": producer}
    finally:
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

    try:
        # 4. Send and wait until Redpanda confirms it received the message
        metadata = await request.state.kafka.send_and_wait(
            KAFKA_TOPIC_LOGIN, payload.encode("utf-8")
        )

        # 3. Log the response from kafka (DEBUG level)
        logger.debug(
            f"Publisohed login event to Kafka (trace_id: {body['trace_id']}) to partition {metadata.partition}, offset {metadata.offset}"
        )

        return NoContent, 201
    except KafkaError as e:
        logger.error(f"Error publishing to Kafka (trace_id: {body['trace_id']}): {e}")
        return NoContent, 500


async def access_check(body):
    """Handle incoming access check events and publish them to Kafka."""

    body["trace_id"] = str(time.time_ns())

    logger.info(
        f"Received 'Access Check' event - user_id : {body['user_id']} | trace_id {body['trace_id']}"
    )

    payload = json.dumps(body)

    try:
        metadata = await request.state.kafka.send_and_wait(
            KAFKA_TOPIC_ACCESS, payload.encode("utf-8")
        )
        logger.debug(
            f"Published access check event to Kafka (trace_id: {body['trace_id']}) "
            f"to partition {metadata.partition}, offset {metadata.offset}"
        )
        return NoContent, 201
    except KafkaError as e:
        logger.error(f"Error publishing to Kafka (trace_id: {body['trace_id']}): {e}")
        return NoContent, 500


def get_status():
    """Healthcheck endpoint."""
    return NoContent, 200


# Initialize the Connexion application
app = connexion.AsyncApp(__name__, specification_dir="", lifespan=lifespan)
app.add_api("receiver.yaml", strict_validation=True, validate_responses=True)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
