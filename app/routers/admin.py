import uuid
import structlog
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_session
from app.dependencies import require_role
from app.constants import UserRole
from app.models.user import User
from app.models.provider import Provider
from app.schemas.auth import ChangeRoleRequest, ToggleActiveRequest, UserResponse
from app.exceptions import NotFoundError, DomainException
from app.services import auth_service

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

_admin_dep = [Depends(require_role(UserRole.ADMIN))]


@router.get(
    "/users",
    response_model=dict,
    dependencies=_admin_dep,
    summary="Listar todos los usuarios",
    description="""
Retorna todos los usuarios del sistema con paginación.

**Requiere autenticación con rol `admin`.**
""",
)
async def list_users(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    users, total = await auth_service.list_users(session, page, page_size)
    return {
        "success": True,
        "data": [UserResponse.model_validate(u).model_dump() for u in users],
        "meta": {"total": total, "page": page, "page_size": page_size},
    }


@router.get(
    "/users/{user_id}",
    response_model=dict,
    dependencies=_admin_dep,
    summary="Ver detalle de un usuario",
    description="""
Retorna el perfil completo de un usuario.

**Requiere autenticación con rol `admin`.**
""",
)
async def get_user(
    user_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    user = await auth_service.get_user(user_id, session)
    return {"success": True, "data": UserResponse.model_validate(user).model_dump()}


@router.patch(
    "/users/{user_id}/role",
    response_model=dict,
    dependencies=_admin_dep,
    summary="Cambiar rol de un usuario",
    description="""
Cambia el rol de cualquier usuario del sistema.

Roles disponibles: `client`, `provider`, `admin`.

**Regla:** Al promover a `provider`, se crea su perfil de proveedor automáticamente.

**Cómo crear el primer admin:**
```sql
UPDATE users SET role='admin' WHERE email='tu@email.com';
```

**Requiere autenticación con rol `admin`.**
""",
)
async def change_user_role(
    user_id: uuid.UUID,
    data: ChangeRoleRequest,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise NotFoundError("Usuario")

    old_role = user.role
    user.role = data.role

    if data.role == UserRole.PROVIDER and old_role != UserRole.PROVIDER:
        existing = await session.execute(select(Provider).where(Provider.user_id == user.id))
        if not existing.scalar_one_or_none():
            session.add(Provider(id=uuid.uuid4(), user_id=user.id))

    await session.commit()
    await session.refresh(user)
    logger.info("role_changed", user_id=str(user.id), old=old_role, new=data.role)
    return {"success": True, "data": UserResponse.model_validate(user).model_dump()}


@router.patch(
    "/users/{user_id}/status",
    response_model=dict,
    dependencies=_admin_dep,
    summary="Activar o desactivar usuario",
    description="""
Activa (`is_active: true`) o desactiva (`is_active: false`) una cuenta de usuario.

Un usuario desactivado no puede iniciar sesión.

**Requiere autenticación con rol `admin`.**
""",
)
async def toggle_user_status(
    user_id: uuid.UUID,
    data: ToggleActiveRequest,
    session: AsyncSession = Depends(get_session),
):
    user = await auth_service.toggle_user_active(user_id, data.is_active, session)
    return {"success": True, "data": UserResponse.model_validate(user).model_dump()}
