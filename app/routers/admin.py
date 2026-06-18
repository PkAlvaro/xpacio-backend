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
from app.models.user_note import UserNote
from app.models.audit_log import AuditLog
from app.models.space import Space
from app.constants import SpaceApprovalStatus
from app.services import auth_service, space_service, reservation_service
from app.services.config_service import get_config as _get_config, update_config as _update_config
from app.services.audit_service import log_action
from app.utils.time_utils import now_chile

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
    admin=Depends(require_role(UserRole.ADMIN)),
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

    await log_action(session, "user_role_changed", admin_id=admin.id, target_type="user", target_id=str(user_id), detail={"old": old_role, "new": data.role})
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
    admin=Depends(require_role(UserRole.ADMIN)),
):
    user = await auth_service.toggle_user_active(user_id, data.is_active, session)
    await log_action(session, "user_status_toggled", admin_id=admin.id, target_type="user", target_id=str(user_id), detail={"is_active": data.is_active})
    await session.commit()
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

    metrics: dict = {}
    try:
        import psutil
        metrics["cpu_percent"] = psutil.cpu_percent(interval=0.1)
        vm = psutil.virtual_memory()
        metrics["memory_used_mb"] = round(vm.used / 1024 / 1024, 1)
        metrics["memory_total_mb"] = round(vm.total / 1024 / 1024, 1)
        metrics["memory_percent"] = vm.percent
        disk = psutil.disk_usage("/")
        metrics["disk_used_gb"] = round(disk.used / 1024 / 1024 / 1024, 2)
        metrics["disk_total_gb"] = round(disk.total / 1024 / 1024 / 1024, 2)
        metrics["disk_percent"] = disk.percent
    except Exception:
        pass

    return {"success": True, "data": {
        "status": "healthy" if all(v == "ok" for v in checks.values()) else "degraded",
        "checks": checks,
        "metrics": metrics,
    }}


# ── Notas de usuario ──────────────────────────────────────────────────────────

@router.get("/users/{user_id}/notes", response_model=dict, dependencies=_admin_dep, summary="Notas internas de un usuario")
async def get_user_notes(user_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    from sqlalchemy.orm import selectinload
    rows = (await session.execute(
        select(UserNote)
        .where(UserNote.user_id == user_id)
        .order_by(UserNote.created_at.desc())
    )).scalars().all()
    out = []
    for n in rows:
        out.append({
            "id": str(n.id),
            "body": n.body,
            "admin_id": str(n.admin_id) if n.admin_id else None,
            "created_at": n.created_at.isoformat(),
        })
    return {"success": True, "data": out}


@router.post("/users/{user_id}/notes", response_model=dict, status_code=201, summary="Agregar nota interna a usuario")
async def add_user_note(
    user_id: uuid.UUID,
    body: dict,
    session: AsyncSession = Depends(get_session),
    admin=Depends(require_role(UserRole.ADMIN)),
):
    text_body = body.get("body", "").strip()
    if len(text_body) < 3:
        raise DomainException("Nota demasiado corta")
    note = UserNote(
        id=uuid.uuid4(),
        user_id=user_id,
        admin_id=admin.id,
        body=text_body,
        created_at=now_chile(),
    )
    session.add(note)
    await log_action(session, "user_note_added", admin_id=admin.id, target_type="user", target_id=str(user_id))
    await session.commit()
    return {"success": True, "data": {"id": str(note.id)}}


@router.delete("/users/{user_id}/notes/{note_id}", status_code=204, summary="Eliminar nota interna")
async def delete_user_note(
    user_id: uuid.UUID,
    note_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    admin=Depends(require_role(UserRole.ADMIN)),
):
    note = await session.get(UserNote, note_id)
    if not note or str(note.user_id) != str(user_id):
        raise NotFoundError("Nota")
    await session.delete(note)
    await session.commit()


# ── Audit log ─────────────────────────────────────────────────────────────────

@router.get("/audit-logs", response_model=dict, dependencies=_admin_dep, summary="Registro de actividad del sistema")
async def get_audit_logs(
    action: str | None = Query(default=None),
    target_type: str | None = Query(default=None),
    admin_user_id: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
):
    from sqlalchemy import func
    q = select(AuditLog, User.name.label("admin_name")).outerjoin(User, AuditLog.admin_id == User.id)
    if action:
        q = q.where(AuditLog.action == action)
    if target_type:
        q = q.where(AuditLog.target_type == target_type)
    if admin_user_id:
        q = q.where(AuditLog.admin_id == uuid.UUID(admin_user_id))

    count_q = select(func.count()).select_from(select(AuditLog).subquery())
    total = (await session.execute(count_q)).scalar_one()

    rows = (await session.execute(
        q.order_by(AuditLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    )).all()

    out = [{
        "id": str(r[0].id),
        "action": r[0].action,
        "target_type": r[0].target_type,
        "target_id": r[0].target_id,
        "detail": r[0].detail,
        "admin_id": str(r[0].admin_id) if r[0].admin_id else None,
        "admin_name": r[1],
        "created_at": r[0].created_at.isoformat(),
    } for r in rows]

    return {"success": True, "data": out, "meta": {"total": total, "page": page, "page_size": page_size}}


# ── Aprobación de espacios ────────────────────────────────────────────────────

@router.patch("/spaces/{space_id}/approve", response_model=dict, summary="Aprobar espacio")
async def approve_space(
    space_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    admin=Depends(require_role(UserRole.ADMIN)),
):
    space = await session.get(Space, space_id)
    if not space:
        raise NotFoundError("Espacio")
    space.approval_status = SpaceApprovalStatus.APPROVED
    space.approval_note = None
    await log_action(session, "space_approved", admin_id=admin.id, target_type="space", target_id=str(space_id))
    await session.commit()
    return {"success": True, "data": {"id": str(space_id), "approval_status": space.approval_status}}


@router.patch("/spaces/{space_id}/reject", response_model=dict, summary="Rechazar espacio")
async def reject_space(
    space_id: uuid.UUID,
    body: dict,
    session: AsyncSession = Depends(get_session),
    admin=Depends(require_role(UserRole.ADMIN)),
):
    space = await session.get(Space, space_id)
    if not space:
        raise NotFoundError("Espacio")
    space.approval_status = SpaceApprovalStatus.REJECTED
    space.approval_note = body.get("note")
    space.is_active = False
    await log_action(session, "space_rejected", admin_id=admin.id, target_type="space", target_id=str(space_id), detail={"note": body.get("note")})
    await session.commit()
    return {"success": True, "data": {"id": str(space_id), "approval_status": space.approval_status}}
