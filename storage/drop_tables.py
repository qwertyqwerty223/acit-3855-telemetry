from sqlalchemy import create_engine
from models import Base

ENGINE = create_engine("sqlite:///events.sqlite")

def drop_tables():
    print("Dropping tables...")
    Base.metadata.drop_all(ENGINE)
    print("Tables dropped successfully.")

if __name__ == "__main__":
    drop_tables()
