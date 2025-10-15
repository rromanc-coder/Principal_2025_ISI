import os, datetime
from typing import Optional
from fastapi import Depends, HTTPException, status, Cookie
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from db import get_db
from models import User

JWT_SECRET = os.getenv("JWT_SECRET", "change-me-please")
JWT_ALG    = "HS256"
pwd_ctx    = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(p: str) -> str:
    return pwd_ctx.hash(p)

def verify_password(p: str, hashed: str) -> bool:
    return pwd_ctx.verify(p, hashed)

def create_token(user_id: int, email: str, expires_minutes=60*12) -> str:
    now = datetime.datetime.utcnow()
    payload = {
        "sub": str(user_id),
        "email": email,
        "iat": now,
        "exp": now + datetime.timedelta(minutes=expires_minutes)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)

def get_current_user(
    db: Session = Depends(get_db),
    access_token: Optional[str] = Cookie(default=None, alias="access_token"),
):
    if not access_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No token")
    try:
        payload = jwt.decode(access_token, JWT_SECRET, algorithms=[JWT_ALG])
        uid = int(payload.get("sub"))
    except (JWTError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")

    user = db.query(User).filter(User.id == uid).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no encontrado")
    return user
