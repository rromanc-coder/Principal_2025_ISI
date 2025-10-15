from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
    email: EmailStr
    full_name: str | None = None
    password: str

class UserOut(BaseModel):
    id: int
    email: EmailStr
    full_name: str | None = None
    class Config:
        from_attributes = True

class LoginIn(BaseModel):
    email: EmailStr
    password: str
