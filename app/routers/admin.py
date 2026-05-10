import uuid
import structlog
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_session
from app.dependencies import require_role
from app.constants import UserRole
from app.models.user import User
from app.models.provider import Provider
from app.schemas.auth import ChangeRoleRequest, UserResponse
from app.exceptions import NotFoundError, DomainException

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


@router.patch(
    "/users/{user_id}/role",
    response_model=dict,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def change_user_role(
    user_id: uuid.UUID,
    data: ChangeRoleRequest,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise NotFoundError("Usuario no encontrado")

    if data.role == UserRole.ADMIN and user.role != UserRole.ADMIN:
        raise DomainException("No se puede promover a admin por esta vía", status_code=403)

    old_role = user.role
    user.role = data.role

    # Si pasa a provider, crear registro Provider si no existe
    if data.role == UserRole.PROVIDER and old_role != UserRole.PROVIDER:
        existing = await session.execute(
            select(Provider).where(Provider.user_id == user.id)
        )
        if not existing.scalar_one_or_none():
            session.add(Provider(id=uuid.uuid4(), user_id=user.id))

    await session.commit()
    await session.refresh(user)

    logger.info("role_changed", user_id=str(user.id), old=old_role, new=data.role)
    return {"success": True, "data": UserResponse.model_validate(user)}
