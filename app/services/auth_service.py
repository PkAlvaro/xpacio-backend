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
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse, UpdateProfileRequest
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
        role=UserRole.CLIENT,
        phone=data.phone,
    )
    session.add(user)

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


async def update_profile(
    user: User,
    data: UpdateProfileRequest,
    session: AsyncSession,
) -> User:
    if data.new_password:
        if not data.current_password:
            raise DomainException("Se requiere la contraseña actual para cambiarla", status_code=400)
        if not await verify_password(data.current_password, user.password_hash):
            raise DomainException("Contraseña actual incorrecta", status_code=400)
        user.password_hash = await hash_password(data.new_password)

    if data.name is not None:
        user.name = data.name
    if data.phone is not None:
        user.phone = data.phone

    await session.commit()
    await session.refresh(user)
    logger.info("profile_updated", user_id=str(user.id))
    return user


async def list_users(session: AsyncSession, page: int = 1, page_size: int = 20) -> tuple[list[User], int]:
    from sqlalchemy import func
    count_result = await session.execute(select(func.count()).select_from(User))
    total = count_result.scalar_one()
    result = await session.execute(
        select(User).order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    return result.scalars().all(), total


async def get_user(user_id: uuid.UUID, session: AsyncSession) -> User:
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise NotFoundError("Usuario")
    return user


async def toggle_user_active(user_id: uuid.UUID, is_active: bool, session: AsyncSession) -> User:
    user = await get_user(user_id, session)
    user.is_active = is_active
    await session.commit()
    await session.refresh(user)
    logger.info("user_active_toggled", user_id=str(user_id), is_active=is_active)
    return user


def _build_tokens(user) -> TokenResponse:
    access, _ = create_access_token(str(user.id), user.role)
    refresh, _ = create_refresh_token(str(user.id), user.role)
    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        expires_in=settings.ACCESS_TOKEN_TTL_MINUTES * 60,
    )
