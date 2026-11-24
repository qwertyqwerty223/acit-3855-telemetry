import os
import time
import logging
import logging.config
import yaml
from datetime import datetime, UTC
import connexion
import uvicorn
from connexion import NoContent
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.orm import sessionmaker
from models import LoginEvent, AccessCheck, Base

with open('log_conf.yml', 'r') as f:
    log_config = yaml.safe_load(f.read())
    logging.config.dictConfig(log_config)

logger = logging.getLogger('storage')

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    logger.error("FATAL: DATABASE_URL environment variable is not set!")
    raise RuntimeError("DATABASE_URL environment variable is required.")

ENGINE = create_engine(DATABASE_URL, pool_pre_ping=True)

def init_db(engine, max_retries=10, delay=2):
    """Ensure database tables exist on startup, retrying if DB is temporarily unreachable."""
    for attempt in range(1, max_retries + 1):
        try:
            Base.metadata.create_all(engine)
            logger.info("Database initialized successfully.")
            return
        except (OperationalError, SQLAlchemyError) as e:
            logger.warning(
                "DB not available at startup (%d/%d): %s. Retrying in %ds...",
                attempt, max_retries, e, delay
            )
            time.sleep(delay)
    logger.warning("Could not initialize database tables after %d attempts.", max_retries)

init_db(ENGINE)

def make_session():
    return sessionmaker(bind=ENGINE)()

def get_login_events(after=None, last_id=0):
    """Get all login events after the specified timestamp."""
    session = make_session()
    try:
        query = session.query(LoginEvent)

        if after:
            after_dt = datetime.fromisoformat(after.replace("Z", "+00:00"))
            if after_dt.tzinfo is not None:
                after_dt = after_dt.astimezone(UTC).replace(tzinfo=None)

            query = query.filter(
                (LoginEvent.recorded_timestamp > after_dt) |
                ((LoginEvent.recorded_timestamp == after_dt) & (LoginEvent.id > int(last_id)))
            )

        events = query.all()
        logger.debug(f"Found {len(events)} login events after {after}")
        return [event.to_dict() for event in events], 200

    except ValueError as e:
        logger.error(f"Invalid timestamp format for after parameter: {after} ({e})")
        return {"error": f"Invalid timestamp format: {after}"}, 400

    except (OperationalError, SQLAlchemyError) as e:
        logger.error(f"Database unavailable while querying login events: {e}")
        return {"error": "Database unavailable"}, 503

    finally:
        session.close()

def get_access_checks(after=None, last_id=0):
    """Get all access checks after the specified timestamp."""
    session = make_session()
    try:
        query = session.query(AccessCheck)

        if after:
            after_dt = datetime.fromisoformat(after.replace("Z", "+00:00"))
            if after_dt.tzinfo is not None:
                after_dt = after_dt.astimezone(UTC).replace(tzinfo=None)

            query = query.filter(
                (AccessCheck.recorded_timestamp > after_dt) |
                ((AccessCheck.recorded_timestamp == after_dt) & (AccessCheck.id > int(last_id)))
            )

        events = query.all()
        logger.debug(f"Found {len(events)} Access Checks after {after}")
        return [event.to_dict() for event in events], 200

    except ValueError as e:
        logger.error(f"Invalid timestamp format for after parameter: {after} ({e})")
        return {"error": f"Invalid timestamp format: {after}"}, 400

    except (OperationalError, SQLAlchemyError) as e:
        logger.error(f"Database unavailable while querying access checks: {e}")
        return {"error": "Database unavailable"}, 503

    finally:
        session.close()

def get_status():
    """Return health status and count of recorded events."""
    session = make_session()
    try:
        num_logins = session.query(LoginEvent).count()
        num_access_checks = session.query(AccessCheck).count()
        return {
            "num_logins": num_logins,
            "num_access_checks": num_access_checks
        }, 200
    except (OperationalError, SQLAlchemyError) as e:
        logger.error(f"Database unavailable during health/status check: {e}")
        return {"error": "Database unavailable"}, 503
    finally:
        session.close()

def reset_database():
    """Drop and recreate all database tables."""
    try:
        Base.metadata.drop_all(ENGINE)
        Base.metadata.create_all(ENGINE)
        logger.info("Database reset: dropped and recreated tables.")
        return NoContent, 200
    except (OperationalError, SQLAlchemyError) as e:
        logger.error(f"Database unavailable during reset: {e}")
        return {"error": "Database unavailable"}, 503

app = connexion.AsyncApp(__name__, specification_dir='')
app.add_api("storage.yaml", strict_validation=True, validate_responses=True)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8090)
