import uuid
from pydantic import BaseModel, EmailStr, field_validator
from app.constants import UserRole


class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: UserRole = UserRole.CLIENT
    phone: str | None = None

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("La contraseña debe tener al menos 8 caracteres")
        return v

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("El nombre no puede estar vacío")
        return v.strip()


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    role: UserRole
    phone: str | None = None

    model_config = {"from_attributes": True}
