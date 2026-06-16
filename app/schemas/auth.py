import re
import uuid
from pydantic import BaseModel, EmailStr, Field, field_validator
from app.constants import UserRole

_CTRL_RE = re.compile(r"[\x00-\x1f\x7f]")
_SQL_RE = re.compile(r"(--|;|/\*|\*/|xp_|UNION\b|SELECT\b|INSERT\b|UPDATE\b|DELETE\b|DROP\b|EXEC\b)", re.IGNORECASE)


def _sanitize_str(v: str) -> str:
    v = _CTRL_RE.sub("", v)
    if _SQL_RE.search(v):
        raise ValueError("Entrada no válida")
    return v.strip()


class RegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    phone: str | None = Field(default=None, max_length=20)
    role: UserRole = UserRole.CLIENT

    @field_validator("role")
    @classmethod
    def role_not_admin(cls, v: UserRole) -> UserRole:
        if v == UserRole.ADMIN:
            raise ValueError("No es posible registrarse como administrador")
        return v

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = _sanitize_str(v)
        if not v:
            raise ValueError("El nombre no puede estar vacío")
        return v

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = re.sub(r"[^\d+\-\s()]", "", v).strip()
        return v or None


class ChangeRoleRequest(BaseModel):
    role: UserRole


class ToggleActiveRequest(BaseModel):
    is_active: bool


class UpdateProfileRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    phone: str | None = Field(default=None, max_length=20)
    current_password: str | None = Field(default=None, max_length=128)
    new_password: str | None = Field(default=None, min_length=8, max_length=128)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = _sanitize_str(v)
        if not v:
            raise ValueError("El nombre no puede estar vacío")
        return v

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = re.sub(r"[^\d+\-\s()]", "", v).strip()
        return v or None


class LoginRequest(BaseModel):
    email: EmailStr = Field(max_length=254)
    password: str = Field(min_length=1, max_length=128)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=10, max_length=512)


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
    is_active: bool
    phone: str | None = None

    model_config = {"from_attributes": True}
