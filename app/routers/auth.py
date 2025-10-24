from fastapi import APIRouter, Depends, Response, HTTPException, status
from sqlalchemy.orm import Session

from deps import db_session
from models import User
from schemas import UserCreate, LoginIn, UserOut
from auth import hash_password, verify_password, create_token, get_current_user

router = APIRouter(prefix="/api")

@router.post("/register")
def api_register(payload: UserCreate, db: Session = Depends(db_session)):
    exists = db.query(User).filter(User.email == payload.email).first()
    if exists:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Correo ya registrado")
    user = User(email=payload.email, full_name=payload.full_name, password=hash_password(payload.password))
    db.add(user); db.commit(); db.refresh(user)
    return {"ok": True, "user": UserOut.model_validate(user).model_dump()}

@router.post("/login")
def api_login(payload: LoginIn, response: Response, db: Session = Depends(db_session)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas")
    token = create_token(user.id, user.email)
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=60*60*12,
        path="/",
        # secure=True,  # habilitar en HTTPS
    )
    return {"ok": True, "user": UserOut.model_validate(user).model_dump()}

@router.post("/logout")
def api_logout(response: Response):
    response.delete_cookie("access_token", path="/")
    return {"ok": True}

@router.get("/me")
def api_me(user: User = Depends(get_current_user)):
    return UserOut.model_validate(user).model_dump()
