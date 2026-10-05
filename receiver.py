import connexion
import uvicorn
import requests
from connexion import NoContent

STORAGE_URL = "http://localhost:8090"

def login_event(body):
    """Handle incoming login events and forward to storage."""
    try:
        response = requests.post(f"{STORAGE_URL}/auth/login", json=body)
        print(f"Forwarded login event. Storage returned: {response.status_code}")
        return NoContent, 201
    except requests.exceptions.RequestException as e:
        print(f"Error communicating with storage service: {e}")
        return NoContent, 500

def access_check(body):
    """Handle incoming access check events and forward to storage."""
    try:
        response = requests.post(f"{STORAGE_URL}/auth/access-check", json=body)
        print(f"Forwarded access check event. Storage returned: {response.status_code}")
        return NoContent, 201
    except requests.exceptions.RequestException as e:
        print(f"Error communicating with storage service: {e}")
        return NoContent, 500

# Initialize the Connexion application
app = connexion.AsyncApp(__name__, specification_dir='')
app.add_api("receiver.yaml", strict_validation=True, validate_responses=True)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
