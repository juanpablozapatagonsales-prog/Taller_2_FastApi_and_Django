from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    correo: EmailStr
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=72)


class UserLogin(BaseModel):
    correo: EmailStr
    password: str = Field(min_length=1, max_length=72)


class UserResponse(BaseModel):
    id: str
    username: str
    correo: EmailStr
    rol: Literal["cliente", "admin"]


class UserLoginResponse(UserResponse):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
