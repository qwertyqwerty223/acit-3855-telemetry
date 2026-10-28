from datetime import datetime, UTC
from sqlalchemy.orm import DeclarativeBase, mapped_column
from sqlalchemy import Integer, String, Boolean, DateTime

class Base(DeclarativeBase):
    pass

class LoginEvent(Base):
    __tablename__ = "login_event"

    id = mapped_column(Integer, primary_key=True)
    user_id = mapped_column(String(50), nullable=False)
    trace_id = mapped_column(String(100), nullable=False)
    failed_attempts = mapped_column(Integer, nullable=False)
    timestamp = mapped_column(String(50), nullable=False)
    ip_address = mapped_column(String(50))
    status = mapped_column(String(20))
    # DateTime(6) provides micro-second precision
    recorded_timestamp = mapped_column(DateTime(6), default=lambda: datetime.now(UTC))

    def to_dict(self):
        """Convert model instance to a dictionary for API responses."""
        return {
            "user_id": self.user_id,
            "trace_id": self.trace_id,
            "failed_attempts": self.failed_attempts,
            "timestamp": self.timestamp,
            "ip_address": self.ip_address,
            "status": self.status,
            "record_timestamp": self.recorded_timestamp.isoformat() if self.recorded_timestamp else None
        }

class AccessCheck(Base):
    __tablename__ = "access_check"

    id = mapped_column(Integer, primary_key=True)
    user_id = mapped_column(String(50), nullable=False)
    trace_id = mapped_column(String(100), nullable=False)
    privilege_level = mapped_column(Integer, nullable=False)
    timestamp = mapped_column(String(50), nullable=False)
    resource_path = mapped_column(String(100), nullable=False)
    access_granted = mapped_column(Boolean, nullable=False)
    recorded_timestamp = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    def to_dict(self):
        """Convert model instance to a dictionary for API responses."""
        return {
            "user_id": self.user_id,
            "trace_id": self.trace_id,
            "privilege_level": self.privilege_level,
            "timestamp": self.timestamp,
            "resource_path": self.resource_path,
            "access_granted": self.access_granted,
            "recorded_timestamp": self.recorded_timestamp.isoformat() if self.recorded_timestamp else None
        }