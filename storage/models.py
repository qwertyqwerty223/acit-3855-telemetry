from datetime import datetime, UTC
from sqlalchemy.orm import DeclarativeBase, mapped_column
from sqlalchemy import Integer, String, Boolean, DateTime

class Base(DeclarativeBase):
    pass

class LoginEvent(Base):
    __tablename__ = "login_event"

    id = mapped_column(Integer, primary_key=True)
    user_id = mapped_column(String(50), nullable=False)
    failed_attempts = mapped_column(Integer, nullable=False)
    timestamp = mapped_column(String(50), nullable=False)
    ip_address = mapped_column(String(50))
    status = mapped_column(String(20))
    recorded_timestamp = mapped_column(DateTime, default=lambda: datetime.now(UTC))

class AccessCheck(Base):
    __tablename__ = "access_check"

    id = mapped_column(Integer, primary_key=True)
    user_id = mapped_column(String(50), nullable=False)
    privilege_level = mapped_column(Integer, nullable=False)
    timestamp = mapped_column(String(50), nullable=False)
    resource_path = mapped_column(String(100), nullable=False)
    access_granted = mapped_column(Boolean, nullable=False)
    recorded_timestamp = mapped_column(DateTime, default=lambda: datetime.now(UTC))
