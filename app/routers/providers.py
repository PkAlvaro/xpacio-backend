import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_session
from app.dependencies import require_role
from app.constants import UserRole
from app.models.provider import Provider
from app.schemas.provider import ProviderResponse, ProviderUpdate
from app.exceptions import NotFoundError

router = APIRouter(prefix="/api/v1/providers", tags=["providers"])


async def _get_provider_for_user(user_id: uuid.UUID, session: AsyncSession) -> Provider:
    result = await session.execute(select(Provider).where(Provider.user_id == user_id))
    provider = result.scalar_one_or_none()
    if not provider:
        raise NotFoundError("Perfil de proveedor")
    return provider


@router.get(
    "/me",
    response_model=dict,
    summary="Ver mi perfil de proveedor",
    description="""
Retorna el perfil de proveedor del usuario autenticado: bio, datos bancarios y estado de verificación.

**Requiere autenticación con rol `provider` o `admin`.**
""",
)
async def get_my_provider(
    session: AsyncSession = Depends(get_session),
    user=Depends(require_role(UserRole.PROVIDER, UserRole.ADMIN)),
):
    provider = await _get_provider_for_user(user.id, session)
    return {"success": True, "data": ProviderResponse.model_validate(provider).model_dump()}


@router.patch(
    "/me",
    response_model=dict,
    summary="Actualizar mi perfil de proveedor",
    description="""
Actualiza el perfil de proveedor del usuario autenticado. Solo se modifican los campos enviados.

Campos editables: `bio`, `bank_rut`, `bank_account`.

**Requiere autenticación con rol `provider` o `admin`.**
""",
)
async def update_my_provider(
    data: ProviderUpdate,
    session: AsyncSession = Depends(get_session),
    user=Depends(require_role(UserRole.PROVIDER, UserRole.ADMIN)),
):
    provider = await _get_provider_for_user(user.id, session)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(provider, field, value)
    await session.commit()
    await session.refresh(provider)
    return {"success": True, "data": ProviderResponse.model_validate(provider).model_dump()}
