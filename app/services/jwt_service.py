import uuid
from dataclasses import dataclass
from datetime import timedelta

from jose import JWTError, jwt
from fastapi import HTTPException, status

from app.config import get_settings
from app.constants import UserRole
from app.utils.time_utils import now_chile

settings = get_settings()


@dataclass
class TokenData:
    sub: str
    role: UserRole
    jti: str


def _create_token(sub: str, role: str, expires_delta: timedelta, token_type: str) -> tuple[str, str]:
    jti = str(uuid.uuid4())
    now = now_chile()
    payload = {
        "sub": sub,
        "role": role,
        "jti": jti,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256"), jti


def create_access_token(user_id: str, role: UserRole) -> tuple[str, str]:
    return _create_token(
        sub=user_id,
        role=role,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_TTL_MINUTES),
        token_type="access",
    )


def create_refresh_token(user_id: str, role: UserRole) -> tuple[str, str]:
    return _create_token(
        sub=user_id,
        role=role,
        expires_delta=timedelta(days=settings.REFRESH_TOKEN_TTL_DAYS),
        token_type="refresh",
    )


def decode_token(token: str) -> TokenData:
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token inválido o expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        sub = payload.get("sub")
        role = payload.get("role")
        jti = payload.get("jti")
        if not sub or not role or not jti:
            raise credentials_exc
        return TokenData(sub=sub, role=UserRole(role), jti=jti)
    except JWTError:
        raise credentials_exc
