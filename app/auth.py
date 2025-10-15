import os, datetime
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status, Cookie, Header
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from db import get_db
from models import User

JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
ALGO = "HS256"

# Usamos bcrypt_sha256 para admitir contraseñas largas; dejamos bcrypt para compat
pwd = CryptContext(
    schemes=["bcrypt_sha256", "bcrypt"],
    deprecated="auto"
)

def hash_password(password: str) -> str:
    # bcrypt_sha256 admite contraseñas largas; será el esquema por defecto
    return pwd.hash(password)

def verify_password(password: str, hashed: str) -> bool:
    # Verifica contra el esquema usado en el hash almacenado (auto-detecta)
    return pwd.verify(password, hashed)

def create_token(user_id: int, email: str) -> str:
    now = datetime.datetime.utcnow()
    payload = {
        "sub": str(user_id),
        "email": email,
        "iat": int(now.timestamp()),
        "exp": int((now + datetime.timedelta(hours=12)).timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=ALGO)

def get_current_user(
    db: Session = Depends(get_db),
    access_token: str | None = Cookie(default=None),
    authorization: str | None = Header(default=None)
) -> User:
    token = access_token
    if not token and authorization:  # Authorization: Bearer <token>
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token = parts[1]

    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No token")

    try:
        data = jwt.decode(token, JWT_SECRET, algorithms=[ALGO])
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")

    user = db.query(User).filter(User.id == int(data.get("sub", "0"))).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no encontrado")
    return user
