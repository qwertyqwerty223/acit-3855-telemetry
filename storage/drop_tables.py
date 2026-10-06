from sqlalchemy import create_engine
from models import Base

ENGINE = create_engine("mysql://skibidi:helpme@127.0.0.1:3306/events")


def drop_tables():
    print("Dropping tables...")
    Base.metadata.drop_all(ENGINE)
    print("Tables dropped successfully.")

if __name__ == "__main__":
    drop_tables()
