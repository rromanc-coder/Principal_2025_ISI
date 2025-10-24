from sqlalchemy.orm import Session
from db import get_db

def db_session() -> Session:
    return get_db()
