from fastapi import APIRouter, Depends, Request, Response, Cookie
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis

from app.database import get_session
from app.dependencies import get_redis, get_current_user
from app.schemas.auth import RegisterRequest, LoginRequest, UserResponse, UpdateProfileRequest
from app.services import auth_service
from app.config import get_settings
from app.limiter import limiter

settings = get_settings()
router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

COOKIE_NAME = "xpacio_refresh"
COOKIE_PATH = "/api/v1/auth"


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    response.set_cookie(
        key=COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=settings.is_production,
        samesite="strict",
        max_age=settings.REFRESH_TOKEN_TTL_DAYS * 86400,
        path=COOKIE_PATH,
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key=COOKIE_NAME, path=COOKIE_PATH)


@router.post("/register", response_model=dict, status_code=201)
@limiter.limit("5/minute")
async def register(
    request: Request,
    response: Response,
    data: RegisterRequest,
    session: AsyncSession = Depends(get_session),
):
    user, tokens = await auth_service.register_user(data, session)
    _set_refresh_cookie(response, tokens.refresh_token)
    return {
        "success": True,
        "data": {
            "user": UserResponse.model_validate(user),
            "tokens": {
                "access_token": tokens.access_token,
                "token_type": tokens.token_type,
                "expires_in": tokens.expires_in,
            },
        },
    }


@router.post("/login", response_model=dict)
@limiter.limit("10/minute")
async def login(
    request: Request,
    response: Response,
    data: LoginRequest,
    session: AsyncSession = Depends(get_session),
    redis: aioredis.Redis = Depends(get_redis),
):
    tokens = await auth_service.login_user(data, session, redis)
    _set_refresh_cookie(response, tokens.refresh_token)
    return {
        "success": True,
        "data": {
            "access_token": tokens.access_token,
            "token_type": tokens.token_type,
            "expires_in": tokens.expires_in,
        },
    }


@router.post("/refresh", response_model=dict)
@limiter.limit("20/minute")
async def refresh(
    request: Request,
    response: Response,
    redis: aioredis.Redis = Depends(get_redis),
    refresh_cookie: Optional[str] = Cookie(default=None, alias=COOKIE_NAME),
):
    if not refresh_cookie:
        from app.exceptions import DomainException
        raise DomainException("Sesión expirada", status_code=401)
    tokens = await auth_service.refresh_tokens(refresh_cookie, redis)
    _set_refresh_cookie(response, tokens.refresh_token)
    return {
        "success": True,
        "data": {
            "access_token": tokens.access_token,
            "token_type": tokens.token_type,
            "expires_in": tokens.expires_in,
        },
    }


@router.post("/logout", status_code=204)
async def logout(
    request: Request,
    response: Response,
    redis: aioredis.Redis = Depends(get_redis),
    _=Depends(get_current_user),
):
    token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    await auth_service.logout_user(token, redis)
    _clear_refresh_cookie(response)


@router.get("/me", response_model=dict)
async def me(user=Depends(get_current_user)):
    return {"success": True, "data": UserResponse.model_validate(user)}


@router.patch("/me", response_model=dict)
async def update_me(
    data: UpdateProfileRequest,
    session: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
):
    updated = await auth_service.update_profile(user, data, session)
    return {"success": True, "data": UserResponse.model_validate(updated)}
