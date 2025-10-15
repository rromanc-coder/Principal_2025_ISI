from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.sql import func
from db import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    full_name = Column(String(255))
    password = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Activity(Base):
    __tablename__ = "activities"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=True)
    path = Column(String(512))
    method = Column(String(16))
    user_agent = Column(Text)
    remote_ip = Column(String(64))
    detail = Column(Text, nullable=True)
    ts = Column(DateTime(timezone=True), server_default=func.now())
