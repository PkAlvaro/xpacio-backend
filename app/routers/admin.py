import uuid
import structlog
from fastapi import APIRouter, Depends, Query, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import redis.asyncio as aioredis

from app.database import get_session
from app.dependencies import require_role, get_redis
from app.models.user import User
from app.models.provider import Provider
from app.schemas.auth import ChangeRoleRequest, ToggleActiveRequest, UserResponse
from app.schemas.space import AdminSpaceCreate, AdminSpaceUpdate, SpaceImageOut, SpaceResponse, SpaceScheduleOut, ScheduleCreate
from app.exceptions import NotFoundError, DomainException
from app.constants import UserRole, ReservationStatus
from app.schemas.reservation import ReservationCancel
from app.schemas.system_config import SystemConfigOut, SystemConfigUpdate
from app.services import auth_service, space_service, reservation_service
from app.services.config_service import get_config as _get_config, update_config as _update_config

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
    q: str | None = Query(default=None, description="Buscar por nombre o email"),
    session: AsyncSession = Depends(get_session),
):
    users, total = await auth_service.list_users(session, page, page_size, q)
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


# ── Admin CMS: Spaces ──────────────────────────────────────────────────────

@router.get("/stats", response_model=dict, dependencies=_admin_dep, summary="Dashboard stats")
async def get_stats(session: AsyncSession = Depends(get_session)):
    stats = await space_service.admin_stats(session)
    return {"success": True, "data": stats}


@router.get("/spaces", response_model=dict, dependencies=_admin_dep, summary="Listar todos los espacios (admin)")
async def list_all_spaces(
    q: str | None = Query(default=None),
    active_only: bool | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    items, total = await space_service.admin_list_spaces(session, q=q, active_only=active_only, page=page, page_size=page_size)
    return {"success": True, "data": [i.model_dump() for i in items], "meta": {"total": total, "page": page, "page_size": page_size}}


@router.post("/spaces", response_model=dict, status_code=201, dependencies=_admin_dep, summary="Crear espacio (admin)")
async def admin_create_space(
    data: AdminSpaceCreate,
    session: AsyncSession = Depends(get_session),
    redis: aioredis.Redis = Depends(get_redis),
    user=Depends(require_role(UserRole.ADMIN)),
):
    result = await session.execute(select(Provider).limit(1))
    provider = result.scalar_one_or_none()
    if not provider:
        prov_result = await session.execute(select(User).where(User.role == UserRole.ADMIN).limit(1))
        admin_user = prov_result.scalar_one()
        provider = Provider(id=uuid.uuid4(), user_id=admin_user.id)
        session.add(provider)
        await session.flush()

    space = await space_service.admin_create_space(data, provider.id, session, redis)
    return {"success": True, "data": SpaceResponse.from_orm_with_amenities(space).model_dump()}


@router.get("/spaces/{space_id}", response_model=dict, dependencies=_admin_dep, summary="Detalle espacio (admin)")
async def admin_get_space(space_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    space = await space_service.get_space(space_id, session)
    return {"success": True, "data": SpaceResponse.from_orm_with_amenities(space).model_dump()}


@router.patch("/spaces/{space_id}", response_model=dict, dependencies=_admin_dep, summary="Editar espacio (admin)")
async def admin_update_space(
    space_id: uuid.UUID,
    data: AdminSpaceUpdate,
    session: AsyncSession = Depends(get_session),
    redis: aioredis.Redis = Depends(get_redis),
):
    space = await space_service.admin_update_space(space_id, data, session, redis)
    return {"success": True, "data": SpaceResponse.from_orm_with_amenities(space).model_dump()}


@router.delete("/spaces/{space_id}", status_code=204, dependencies=_admin_dep, summary="Eliminar espacio (admin)")
async def admin_delete_space(space_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    await space_service.admin_hard_delete_space(space_id, session)


@router.post("/spaces/{space_id}/images", response_model=dict, dependencies=_admin_dep, summary="Subir imagen")
async def upload_image(
    space_id: uuid.UUID,
    file: UploadFile = File(...),
    set_primary: bool = Query(default=False),
    session: AsyncSession = Depends(get_session),
):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise DomainException("Solo se permiten archivos de imagen")
    img = await space_service.upload_space_image(space_id, file, session, set_primary)
    return {"success": True, "data": SpaceImageOut.model_validate(img).model_dump()}


@router.delete("/spaces/{space_id}/images/{image_id}", status_code=204, dependencies=_admin_dep, summary="Eliminar imagen")
async def delete_image(space_id: uuid.UUID, image_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    await space_service.delete_space_image(space_id, image_id, session)


@router.patch("/spaces/{space_id}/images/{image_id}/primary", response_model=dict, dependencies=_admin_dep, summary="Marcar imagen como principal")
async def set_primary_image(space_id: uuid.UUID, image_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    await space_service.set_primary_image(space_id, image_id, session)
    return {"success": True}


@router.patch("/spaces/{space_id}/images/order", response_model=dict, dependencies=_admin_dep, summary="Reordenar imágenes")
async def reorder_images(space_id: uuid.UUID, order: list[dict], session: AsyncSession = Depends(get_session)):
    await space_service.reorder_space_images(space_id, order, session)
    return {"success": True}


@router.put("/spaces/{space_id}/schedules", response_model=dict, dependencies=_admin_dep, summary="Configurar horarios (admin)")
async def admin_set_schedules(
    space_id: uuid.UUID,
    schedules: list[ScheduleCreate],
    session: AsyncSession = Depends(get_session),
    user=Depends(require_role(UserRole.ADMIN)),
):
    result = await space_service.set_schedules(space_id, schedules, user.id, session, skip_owner_check=True)
    return {"success": True, "data": [SpaceScheduleOut.model_validate(s).model_dump() for s in result]}


# ── Admin: Reservaciones ───────────────────────────────────────────────────────

@router.get("/reservations", response_model=dict, dependencies=_admin_dep, summary="Listar todas las reservas (admin)")
async def admin_list_reservations(
    status: str | None = Query(default=None, description="Filtrar por estado"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=30, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    status_enum = ReservationStatus(status) if status else None
    items, total = await reservation_service.admin_list_reservations(session, status_enum, page, page_size)
    return {"success": True, "data": items, "meta": {"total": total, "page": page, "page_size": page_size}}


@router.post("/reservations/{reservation_id}/cancel", response_model=dict, dependencies=_admin_dep, summary="Cancelar reserva (admin)")
async def admin_cancel_reservation(
    reservation_id: uuid.UUID,
    data: ReservationCancel = ReservationCancel(),
    session: AsyncSession = Depends(get_session),
):
    from app.schemas.reservation import ReservationResponse
    reservation = await reservation_service.admin_cancel_reservation(reservation_id, data.reason, session)
    return {"success": True, "data": ReservationResponse.model_validate(reservation).model_dump()}


@router.get("/config", response_model=dict, dependencies=_admin_dep, summary="Ver configuración global")
async def get_system_config(session: AsyncSession = Depends(get_session)):
    config = await _get_config(session)
    return {"success": True, "data": SystemConfigOut.model_validate(config).model_dump()}


@router.patch("/config", response_model=dict, dependencies=_admin_dep, summary="Actualizar configuración global")
async def update_system_config(
    data: SystemConfigUpdate,
    session: AsyncSession = Depends(get_session),
):
    config = await _update_config(session, **data.model_dump(exclude_none=True))
    return {"success": True, "data": SystemConfigOut.model_validate(config).model_dump()}


@router.get("/health", response_model=dict, dependencies=_admin_dep, summary="Health check desde admin")
async def admin_health(
    session: AsyncSession = Depends(get_session),
    redis=Depends(get_redis),
):
    from sqlalchemy import text
    checks: dict[str, str] = {}
    try:
        await session.execute(text("SELECT 1"))
        checks["db"] = "ok"
    except Exception:
        checks["db"] = "fail"
    try:
        await redis.ping()
        checks["redis"] = "ok"
    except Exception:
        checks["redis"] = "fail"
    return {"success": True, "data": {"status": "healthy" if all(v == "ok" for v in checks.values()) else "degraded", "checks": checks}}
