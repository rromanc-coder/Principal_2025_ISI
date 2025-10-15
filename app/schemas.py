from pydantic import BaseModel, ConfigDict, EmailStr, StringConstraints
from typing import Annotated

PasswordStr = Annotated[str, StringConstraints(min_length=6, max_length=512)]

class UserCreate(BaseModel):
    email: EmailStr
    full_name: str | None = None
    password: PasswordStr

class LoginIn(BaseModel):
    email: EmailStr
    password: PasswordStr

class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: EmailStr
    full_name: str | None = None
