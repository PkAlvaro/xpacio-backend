from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis

from app.database import get_session
from app.dependencies import get_redis, get_current_user
from app.schemas.auth import RegisterRequest, LoginRequest, RefreshRequest, TokenResponse, UserResponse, UpdateProfileRequest
from app.services import auth_service
from app.config import get_settings

settings = get_settings()
router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=dict,
    status_code=201,
    summary="Registrar nuevo usuario",
    description="""
Crea una cuenta nueva. Todos los usuarios se registran con rol `client`.

Para obtener rol `provider` o `admin`, un administrador debe usar
`PATCH /admin/users/{id}/role` después del registro.

Retorna el perfil del usuario y un par de tokens (access + refresh).
""",
)
async def register(
    data: RegisterRequest,
    session: AsyncSession = Depends(get_session),
):
    user, tokens = await auth_service.register_user(data, session)
    return {"success": True, "data": {"user": UserResponse.model_validate(user), "tokens": tokens}}


@router.post(
    "/login",
    response_model=dict,
    summary="Iniciar sesión",
    description="""
Autentica al usuario con email y contraseña.

Retorna:
- `access_token`: token JWT válido por 15 minutos. Incluir en el header
  `Authorization: Bearer <token>` en cada petición protegida.
- `refresh_token`: token válido por 7 días. Usar en `POST /auth/refresh`
  para obtener un nuevo `access_token` sin volver a ingresar contraseña.
""",
)
async def login(
    data: LoginRequest,
    session: AsyncSession = Depends(get_session),
    redis: aioredis.Redis = Depends(get_redis),
):
    tokens = await auth_service.login_user(data, session, redis)
    return {"success": True, "data": tokens}


@router.post(
    "/refresh",
    response_model=dict,
    summary="Renovar access token",
    description="""
Genera un nuevo par de tokens usando el `refresh_token` vigente.

El `refresh_token` anterior queda invalidado inmediatamente (rotación de tokens).
Usar cuando el `access_token` haya expirado (respuesta 401) para no pedir
contraseña al usuario nuevamente.
""",
)
async def refresh(
    data: RefreshRequest,
    redis: aioredis.Redis = Depends(get_redis),
):
    tokens = await auth_service.refresh_tokens(data.refresh_token, redis)
    return {"success": True, "data": tokens}


@router.post(
    "/logout",
    status_code=204,
    summary="Cerrar sesión",
    description="""
Invalida el `access_token` actual añadiéndolo a una blacklist en Redis.
El token queda inutilizable hasta su expiración natural (15 min).

**Requiere autenticación.**
""",
)
async def logout(
    request: Request,
    redis: aioredis.Redis = Depends(get_redis),
    _=Depends(get_current_user),
):
    token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    await auth_service.logout_user(token, redis)


@router.get(
    "/me",
    response_model=dict,
    summary="Ver mi perfil",
    description="""
Retorna el perfil del usuario actualmente autenticado: id, nombre, email, rol y teléfono.

Útil para verificar que el token es válido y para conocer el rol del usuario.

**Requiere autenticación.**
""",
)
async def me(user=Depends(get_current_user)):
    return {"success": True, "data": UserResponse.model_validate(user)}


@router.patch(
    "/me",
    response_model=dict,
    summary="Actualizar mi perfil",
    description="""
Actualiza el perfil del usuario autenticado. Solo se modifican los campos enviados.

Para cambiar la contraseña, enviar `current_password` y `new_password`.

**Requiere autenticación.**
""",
)
async def update_me(
    data: UpdateProfileRequest,
    session: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
):
    updated = await auth_service.update_profile(user, data, session)
    return {"success": True, "data": UserResponse.model_validate(updated)}
