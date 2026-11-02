from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6, max_length=72)


class UserResponse(BaseModel):
    id: str
    email: EmailStr
    username: str


class UserAuthResponse(UserResponse):
    access_token: str
    token_type: Literal["bearer"] = "bearer"


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=72)
