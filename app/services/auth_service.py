import uuid
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
import redis.asyncio as aioredis

from app.models.user import User
from app.models.provider import Provider
from app.constants import UserRole
from app.exceptions import ConflictError, NotFoundError, DomainException
from app.services.password_service import hash_password, verify_password
from app.services.jwt_service import (
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse
from app.config import get_settings

logger = structlog.get_logger()
settings = get_settings()

REFRESH_PREFIX = "refresh:"
BLACKLIST_PREFIX = "blacklist:"


async def register_user(
    data: RegisterRequest,
    session: AsyncSession,
) -> tuple[User, TokenResponse]:
    existing = await session.execute(select(User).where(User.email == data.email))
    if existing.scalar_one_or_none():
        raise ConflictError("El email ya está registrado")

    hashed = await hash_password(data.password)
    user = User(
        id=uuid.uuid4(),
        name=data.name,
        email=data.email,
        password_hash=hashed,
        role=data.role,
        phone=data.phone,
    )
    session.add(user)

    if data.role == UserRole.PROVIDER:
        provider = Provider(id=uuid.uuid4(), user_id=user.id)
        session.add(provider)

    try:
        await session.commit()
        await session.refresh(user)
    except IntegrityError:
        await session.rollback()
        raise ConflictError("El email ya está registrado")

    logger.info("user_registered", user_id=str(user.id), role=user.role)
    tokens = _build_tokens(user)
    return user, tokens


async def login_user(
    data: LoginRequest,
    session: AsyncSession,
    redis: aioredis.Redis,
) -> TokenResponse:
    result = await session.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    if not user or not await verify_password(data.password, user.password_hash):
        raise DomainException("Credenciales inválidas", status_code=401)

    if not user.is_active:
        raise DomainException("Cuenta desactivada", status_code=403)

    tokens = _build_tokens(user)
    refresh_data = decode_token(tokens.refresh_token)
    ttl = settings.REFRESH_TOKEN_TTL_DAYS * 86400
    await redis.setex(f"{REFRESH_PREFIX}{refresh_data.jti}", ttl, str(user.id))

    logger.info("user_login", user_id=str(user.id))
    return tokens


async def refresh_tokens(
    refresh_token: str,
    redis: aioredis.Redis,
) -> TokenResponse:
    token_data = decode_token(refresh_token)

    stored = await redis.get(f"{REFRESH_PREFIX}{token_data.jti}")
    if not stored:
        raise DomainException("Refresh token inválido o expirado", status_code=401)

    await redis.delete(f"{REFRESH_PREFIX}{token_data.jti}")

    # issue new pair
    from app.models.user import User as UserModel
    # reconstruct User mini-object for token building
    class _Mini:
        id = uuid.UUID(stored)
        role = token_data.role

    tokens = _build_tokens(_Mini())
    new_data = decode_token(tokens.refresh_token)
    ttl = settings.REFRESH_TOKEN_TTL_DAYS * 86400
    await redis.setex(f"{REFRESH_PREFIX}{new_data.jti}", ttl, stored)
    return tokens


async def logout_user(access_token: str, redis: aioredis.Redis) -> None:
    token_data = decode_token(access_token)
    ttl = settings.ACCESS_TOKEN_TTL_MINUTES * 60
    await redis.setex(f"{BLACKLIST_PREFIX}{token_data.jti}", ttl, "1")
    logger.info("user_logout", jti=token_data.jti)


def _build_tokens(user) -> TokenResponse:
    access, _ = create_access_token(str(user.id), user.role)
    refresh, _ = create_refresh_token(str(user.id), user.role)
    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        expires_in=settings.ACCESS_TOKEN_TTL_MINUTES * 60,
    )
