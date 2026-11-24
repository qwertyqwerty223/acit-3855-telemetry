import json
import logging
import logging.config
import os
import signal
import sys
import time
import yaml
from confluent_kafka import Consumer, KafkaError, KafkaException
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError
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

# Database engine with pool_pre_ping to verify connection health
ENGINE = create_engine(DATABASE_URL, pool_pre_ping=True)

def init_db(engine, max_retries=10, delay=2):
    """Ensure database tables exist on startup, retrying if DB is temporarily unreachable."""
    for attempt in range(1, max_retries + 1):
        try:
            Base.metadata.create_all(engine)
            logger.info("Database initialized successfully.")
            return
        except (OperationalError, SQLAlchemyError) as e:
            logger.warning("DB not available at startup (%d/%d): %s. Retrying in %ds...", attempt, max_retries, e, delay)
            time.sleep(delay)
    logger.warning("Could not initialize database tables after %d attempts; worker will retry on writes.", max_retries)

def make_session():
    return sessionmaker(bind=ENGINE)()

def handle_sigterm(signum, frame):
    """Convert SIGTERM from Docker into KeyboardInterrupt for graceful shutdown."""
    logger.info("Received SIGTERM. Initiating graceful shutdown...")
    raise KeyboardInterrupt

signal.signal(signal.SIGTERM, handle_sigterm)

def save_event_to_db(session, topic, body):
    """Persist event to MySQL based on the Kafka topic."""
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

def save_to_db_with_retry(topic, body, max_attempts=5):
    """Wrap database persistence with retry logic, backoff, and idempotency handling."""
    trace_id = body.get("trace_id", "unknown")
    for attempt in range(1, max_attempts + 1):
        session = make_session()
        try:
            save_event_to_db(session, topic, body)
            return True
        except IntegrityError:
            session.rollback()
            logger.info("Duplicate trace_id %s, already stored. Skipping duplicate.", trace_id)
            return True  # Idempotent: already persisted in DB, safe to commit Kafka offset
        except OperationalError as e:
            session.rollback()
            logger.warning(
                "Database error on attempt %d/%d for trace_id %s: %s",
                attempt, max_attempts, trace_id, e
            )
            time.sleep(min(2 ** attempt, 30))
        except Exception as e:
            session.rollback()
            logger.exception("Permanent failure saving event (trace_id %s): %s", trace_id, e)
            return False
        finally:
            session.close()

    logger.error("Database unavailable after %d attempts for trace_id %s", max_attempts, trace_id)
    return False

def main():
    init_db(ENGINE)
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
                if msg.error().fatal():
                    raise KafkaException(msg.error())
                logger.warning("Kafka error: %s", msg.error())
                continue

            try:
                payload = json.loads(msg.value().decode("utf-8"))
            except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as e:
                logger.error("Malformed message at offset %d, skipping: %s", msg.offset(), e)
                # Commit offset for malformed message so it does not block the consumer loop
                consumer.commit(msg, asynchronous=False)
                continue

            success = save_to_db_with_retry(msg.topic(), payload)
            if success:
                # Commit offset synchronously only after successful DB storage or idempotent deduplication
                consumer.commit(msg, asynchronous=False)
            else:
                logger.warning(
                    "DB persistence failed for offset %d. Offset not committed; will re-attempt.",
                    msg.offset()
                )
                time.sleep(2)

    except KeyboardInterrupt:
        logger.info("Storage worker interrupted. Shutting down...")
    finally:
        logger.info("Closing Kafka consumer connection...")
        consumer.close()

if __name__ == "__main__":
    main()
