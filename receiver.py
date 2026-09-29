import json
import os
import connexion
from connexion import NoContent

EVENTS_FILE = 'events.json'

def init_file():
    """Initialize the events.json file if it doesn't exist."""
    if not os.path.exists(EVENTS_FILE):
        with open(EVENTS_FILE, 'w') as f:
            json.dump({
                "events": [],
                "login_event_count": 0,
                "access_check_count": 0
            }, f, indent=4)

def login_event(body):
    """Handle incoming login events."""
    init_file()
    
    # Read the current events
    with open(EVENTS_FILE, 'r') as f:
        data = json.load(f)
        
    # Append the new event and update the counter
    data['events'].append({
        "event_type": "login_event",
        "data": body
    })
    data['login_event_count'] += 1
    
    # Write back to the file
    with open(EVENTS_FILE, 'w') as f:
        json.dump(data, f, indent=4)
        
    print(f"Received login event: {body}")
    return NoContent, 201

def access_check(body):
    """Handle incoming access check events."""
    init_file()
    
    # Read the current events
    with open(EVENTS_FILE, 'r') as f:
        data = json.load(f)
        
    # Append the new event and update the counter
    data['events'].append({
        "event_type": "access_check",
        "data": body
    })
    data['access_check_count'] += 1
    
    # Write back to the file
    with open(EVENTS_FILE, 'w') as f:
        json.dump(data, f, indent=4)
        
    print(f"Received access check event: {body}")
    return NoContent, 201

# Initialize the Connexion application
app = connexion.AsyncApp(__name__, specification_dir='')
app.add_api("receiver.yaml", strict_validation=True, validate_responses=True)

