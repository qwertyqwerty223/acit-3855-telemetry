from sqlalchemy import create_engine
from models import Base
import os
import sys

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("FATAL: DATABASE_URL environment variable is not set!", file=sys.stderr)
    sys.exit(1)

ENGINE = create_engine(DATABASE_URL)

def drop_tables():
    print("Dropping tables...")
    Base.metadata.drop_all(ENGINE)
    print("Tables dropped successfully.")

if __name__ == "__main__":
    drop_tables()
