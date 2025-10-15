from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from db import Base

class User(Base):
    __tablename__ = "users"
    id         = Column(Integer, primary_key=True, index=True)
    email      = Column(String(255), unique=True, index=True, nullable=False)
    full_name  = Column(String(255), nullable=True)
    password   = Column(String(255), nullable=False)  # hash
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Activity(Base):
    __tablename__ = "activities"
    id         = Column(Integer, primary_key=True, index=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=True)
    path       = Column(String(512), nullable=False)
    method     = Column(String(16), nullable=False)
    user_agent = Column(String(512), nullable=True)
    remote_ip  = Column(String(64), nullable=True)
    detail     = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user       = relationship("User")
