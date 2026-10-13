import connexion
import uvicorn
from connexion import NoContent
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import LoginEvent, AccessCheck, Base
import logging
import logging.config
import yaml

with open('log_conf.yml', 'r') as f:
    log_config = yaml.safe_load(f.read())
    logging.config.dictConfig(log_config)

logger = logging.getLogger('storage')

ENGINE = create_engine("mysql://skibidi:helpme@127.0.0.1:3306/events")

def make_session():
    return sessionmaker(bind=ENGINE)()

def login_event(body):
    """Handle incoming login events by storing them in the DB."""
    session = make_session()
    
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
    session.close()

    logger.debug(f"Stored event 'login' with a trace id of {body['trace_id']}")
    
    return NoContent, 201

def access_check(body):
    """Handle incoming access checks by storing them in the DB."""
    session = make_session()
    
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
    session.close()
    
    logger.debug(f"Stored event 'Access Check' with a trace id of {body['trace_id']}")

    return NoContent, 201

def get_status():
    """Return health status and count of recorded events."""
    session = make_session()
    num_logins = session.query(LoginEvent).count()
    num_access_checks = session.query(AccessCheck).count()
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
