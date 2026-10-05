import connexion
import uvicorn
from connexion import NoContent
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import LoginEvent, AccessCheck

ENGINE = create_engine("sqlite:///events.sqlite")

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
        status=body.get('status')
    )
    
    session.add(event)
    session.commit()
    session.close()
    
    return NoContent, 201

def access_check(body):
    """Handle incoming access checks by storing them in the DB."""
    session = make_session()
    
    event = AccessCheck(
        user_id=body['user_id'],
        privilege_level=body['privilege_level'],
        timestamp=body['timestamp'],
        resource_path=body['resource_path'],
        access_granted=body['access_granted']
    )
    
    session.add(event)
    session.commit()
    session.close()
    
    return NoContent, 201

app = connexion.AsyncApp(__name__, specification_dir='')
app.add_api("storage.yaml", strict_validation=True, validate_responses=True)

if __name__ == "__main__":
    # Make sure to run this on a different port than the receiver!
    uvicorn.run(app, host="0.0.0.0", port=8090)
