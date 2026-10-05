from sqlalchemy import create_engine
from models import Base

# Using a SQLite database file named 'events.sqlite'
ENGINE = create_engine("sqlite:///events.sqlite")

def create_tables():
    print("Creating tables...")
    Base.metadata.create_all(ENGINE)
    print("Tables created successfully.")

if __name__ == "__main__":
    create_tables()
