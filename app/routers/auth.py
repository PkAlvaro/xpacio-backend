from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis

from app.database import get_session
from app.dependencies import get_redis, get_current_user
from app.schemas.auth import RegisterRequest, LoginRequest, RefreshRequest, TokenResponse, UserResponse
from app.services import auth_service
from app.config import get_settings

settings = get_settings()
router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/register", response_model=dict, status_code=201)
async def register(
    data: RegisterRequest,
    session: AsyncSession = Depends(get_session),
):
    user, tokens = await auth_service.register_user(data, session)
    return {"success": True, "data": {"user": UserResponse.model_validate(user), "tokens": tokens}}


@router.post("/login", response_model=dict)
async def login(
    data: LoginRequest,
    session: AsyncSession = Depends(get_session),
    redis: aioredis.Redis = Depends(get_redis),
):
    tokens = await auth_service.login_user(data, session, redis)
    return {"success": True, "data": tokens}


@router.post("/refresh", response_model=dict)
async def refresh(
    data: RefreshRequest,
    redis: aioredis.Redis = Depends(get_redis),
):
    tokens = await auth_service.refresh_tokens(data.refresh_token, redis)
    return {"success": True, "data": tokens}


@router.post("/logout", status_code=204)
async def logout(
    request: Request,
    redis: aioredis.Redis = Depends(get_redis),
    _=Depends(get_current_user),
):
    token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    await auth_service.logout_user(token, redis)


@router.get("/me", response_model=dict)
async def me(user=Depends(get_current_user)):
    return {"success": True, "data": UserResponse.model_validate(user)}
