import json
import logging
import logging.config
import os
import signal
import sys
import yaml
from confluent_kafka import Consumer, KafkaError, KafkaException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import LoginEvent, AccessCheck, Base

# Load logging configuration
with open("log_conf.yml", "r") as f:
    log_config = yaml.safe_load(f.read())
    logging.config.dictConfig(log_config)

logger = logging.getLogger("storage-worker")

# Environment configuration
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    logger.error("FATAL: DATABASE_URL environment variable is not set!")
    raise RuntimeError("DATABASE_URL environment variable is required.")

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "redpanda:9092")
KAFKA_TOPIC_LOGIN = os.getenv("KAFKA_TOPIC_LOGIN", "login")
KAFKA_TOPIC_ACCESS = os.getenv("KAFKA_TOPIC_ACCESS", "accessChecks")

# Database engine initialization
ENGINE = create_engine(DATABASE_URL)
Base.metadata.create_all(ENGINE)

def make_session():
    return sessionmaker(bind=ENGINE)()

def handle_sigterm(signum, frame):
    """Convert SIGTERM from Docker into KeyboardInterrupt for graceful shutdown."""
    logger.info("Received SIGTERM. Initiating graceful shutdown...")
    raise KeyboardInterrupt

signal.signal(signal.SIGTERM, handle_sigterm)

def save_event_to_db(topic, body):
    """Persist event to MySQL based on the Kafka topic."""
    session = make_session()
    try:
        if topic == KAFKA_TOPIC_LOGIN:
            event = LoginEvent(
                user_id=body["user_id"],
                failed_attempts=body["failed_attempts"],
                timestamp=body["timestamp"],
                ip_address=body.get("ip_address"),
                status=body.get("status"),
                trace_id=str(body["trace_id"]),
            )
            session.add(event)
            session.commit()
            logger.debug(
                f"Stored event 'login' from Kafka with trace_id: {body.get('trace_id')}"
            )
        elif topic == KAFKA_TOPIC_ACCESS:
            event = AccessCheck(
                user_id=body["user_id"],
                privilege_level=body["privilege_level"],
                timestamp=body["timestamp"],
                resource_path=body["resource_path"],
                access_granted=body["access_granted"],
                trace_id=str(body["trace_id"]),
            )
            session.add(event)
            session.commit()
            logger.debug(
                f"Stored event 'access_check' from Kafka with trace_id: {body.get('trace_id')}"
            )
        else:
            logger.warning(f"Received message from unrecognized topic: {topic}")
    finally:
        session.close()

def main():
    logger.info(f"Connecting to Kafka broker at {KAFKA_BROKER}...")

    conf = {
        "bootstrap.servers": KAFKA_BROKER,
        "group.id": "storage_worker_group",
        "auto.offset.reset": "earliest",
        "enable.auto.commit": False,
    }

    consumer = Consumer(conf)
    topics = [KAFKA_TOPIC_LOGIN, KAFKA_TOPIC_ACCESS]
    consumer.subscribe(topics)
    logger.info(f"Storage worker subscribed to topics: {topics}")

    try:
        while True:
            # Poll for messages with a 1.0 second timeout
            msg = consumer.poll(timeout=1.0)

            if msg is None:
                continue

            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    logger.debug(
                        f"Reached end of partition {msg.partition()} for topic {msg.topic()}"
                    )
                else:
                    logger.error(f"Kafka error encountered: {msg.error()}")
                continue

            try:
                payload = json.loads(msg.value().decode("utf-8"))
                save_event_to_db(msg.topic(), payload)
                # Manually commit offset only after successful DB transaction
                consumer.commit(msg)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to decode JSON message from Kafka: {e}")
            except Exception as e:
                logger.error(f"Failed to process message from topic {msg.topic()}: {e}")

    except KeyboardInterrupt:
        logger.info("Storage worker interrupted. Shutting down...")
    finally:
        logger.info("Closing Kafka consumer connection...")
        consumer.close()

if __name__ == "__main__":
    main()