from sqlalchemy import create_engine
from models import Base
import os
import sys

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("FATAL: DATABASE_URL environment variable is not set!", file=sys.stderr)
    sys.exit(1)

ENGINE = create_engine(DATABASE_URL)

def create_tables():
    print("Creating tables...")
    Base.metadata.create_all(ENGINE)
    print("Tables created successfully.")

if __name__ == "__main__":
    create_tables()
