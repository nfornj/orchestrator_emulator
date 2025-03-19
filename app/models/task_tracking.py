import datetime
import uuid
from sqlalchemy import Column, String, JSON, DateTime, Boolean, ForeignKey, Enum, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from app.database import Base

class TaskStatus(enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

class ServiceStatus(enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress" 
    COMPLETED = "completed"
    FAILED = "failed"

class Task(Base):
    """
    Represents an orchestration task.
    """
    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(String, unique=True, index=True)
    task_name = Column(String, nullable=False)
    task_description = Column(String, nullable=True)
    status = Column(Enum(TaskStatus), default=TaskStatus.PENDING, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False)
    payload = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # One-to-many relationship with ServiceRequests
    service_requests = relationship("ServiceRequest", back_populates="task", cascade="all, delete-orphan")

class ServiceRequest(Base):
    """
    Represents a request to an individual service as part of an orchestration task.
    """
    __tablename__ = "service_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False)
    service_name = Column(String, nullable=False)  # "revenue", "rebates", "specialty"
    scenario_id = Column(String, nullable=True)
    business_type_id = Column(String, nullable=True)
    status = Column(Enum(ServiceStatus), default=ServiceStatus.PENDING, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False)
    request_payload = Column(JSON, nullable=True)
    response_payload = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Many-to-one relationship with Task
    task = relationship("Task", back_populates="service_requests") 