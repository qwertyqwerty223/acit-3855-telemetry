import connexion
import uvicorn
from connexion import NoContent
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import LoginEvent, AccessCheck, Base
from datetime import datetime, UTC
import logging
import logging.config
import yaml
import os

with open('log_conf.yml', 'r') as f:
    log_config = yaml.safe_load(f.read())
    logging.config.dictConfig(log_config)

logger = logging.getLogger('storage')

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    logger.error("FATAL: DATABASE_URL environment variable is not set!")
    raise RuntimeError("DATABASE_URL environment variable is required.")

ENGINE = create_engine(DATABASE_URL)
Base.metadata.create_all(ENGINE)

def make_session():
    return sessionmaker(bind=ENGINE)()

def login_event(body):
    """Handle incoming login events by storing them in the DB."""
    session = make_session()
    try:
        event = LoginEvent(
            user_id=body['user_id'],
            failed_attempts=body['failed_attempts'],
            timestamp=body['timestamp'],
            ip_address=body.get('ip_address'),
            status=body.get('status'),
            trace_id=str(body['trace_id'])
        )
        
        session.add(event)
        session.commit()
    finally:
        session.close()

    logger.debug(f"Stored event 'login' with a trace id of {body['trace_id']}")
    
    return NoContent, 201

def access_check(body):
    """Handle incoming access checks by storing them in the DB."""
    session = make_session()
    try:
        event = AccessCheck(
            user_id=body['user_id'],
            privilege_level=body['privilege_level'],
            timestamp=body['timestamp'],
            resource_path=body['resource_path'],
            access_granted=body['access_granted'],
            trace_id=str(body['trace_id'])
        )
        
        session.add(event)
        session.commit()
    finally:
        session.close()
    
    logger.debug(f"Stored event 'Access Check' with a trace id of {body['trace_id']}")

    return NoContent, 201

def get_login_events(after=None, last_id=0):
    """Get all login events after the specified timestamp in the 'After' param. Return all if timestamp is not given."""
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
        arr = [event.to_dict() for event in events]

        return arr, 200

    except ValueError as e:
        logger.error(f"Invalid timestamp format for after parameter: {after} ({e})")
        return_message = {
            "message": f"Invalid timestamp format: {after}"
        }
        return return_message, 400

    finally:
        session.close()        

def get_access_checks(after=None, last_id=0):
    """Get all access checks after the specified timestamp in the 'After' param. Return all if timestamp is not given."""
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
        arr = [event.to_dict() for event in events]

        return arr, 200

    except ValueError as e:
        logger.error(f"Invalid timestamp format for after parameter: {after} ({e})")
        return_message = {
            "message": f"Invalid timestamp format: {after}"
        }
        return return_message, 400

    finally:
        session.close()        


def get_status():
    """Return health status and count of recorded events."""
    session = make_session()
    try:
        num_logins = session.query(LoginEvent).count()
        num_access_checks = session.query(AccessCheck).count()
    finally:
        session.close()

    return {
        "num_logins": num_logins,
        "num_access_checks": num_access_checks
    }, 200

def reset_database():
    """Drop and recreate all database tables."""
    Base.metadata.drop_all(ENGINE)
    Base.metadata.create_all(ENGINE)
    logger.info("Database reset: dropped and recreated tables.")
    return NoContent, 200

app = connexion.AsyncApp(__name__, specification_dir='')
app.add_api("storage.yaml", strict_validation=True, validate_responses=True)

if __name__ == "__main__":
    # Make sure to run this on a different port than the receiver!
    uvicorn.run(app, host="0.0.0.0", port=8090)
