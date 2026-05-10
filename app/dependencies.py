from typing import Annotated
import redis.asyncio as aioredis
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.constants import UserRole
from app.database import get_session

settings = get_settings()

_redis_pool: aioredis.Redis | None = None

bearer_scheme = HTTPBearer()


def get_redis() -> aioredis.Redis:
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis_pool


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
    session: AsyncSession = Depends(get_session),
    redis: aioredis.Redis = Depends(get_redis),
):
    from app.services.jwt_service import decode_token
    from app.models.user import User
    from sqlalchemy import select

    token_data = decode_token(credentials.credentials)

    blacklisted = await redis.get(f"blacklist:{token_data.jti}")
    if blacklisted:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token revocado")

    result = await session.execute(select(User).where(User.id == token_data.sub))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no encontrado o inactivo")

    return user


def require_role(*roles: UserRole):
    async def _check(user=Depends(get_current_user)):
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Rol insuficiente")
        return user
    return _check
