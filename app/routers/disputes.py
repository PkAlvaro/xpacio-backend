import uuid
from fastapi import APIRouter, Depends, Query, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies import get_current_user, require_role
from app.constants import DisputeStatus, UserRole
from app.schemas.dispute import DisputeResolve
from app.services import dispute_service

router = APIRouter(prefix="/api/v1", tags=["disputes"])


@router.post("/reservations/{reservation_id}/dispute", response_model=dict, status_code=201,
             summary="Abrir reclamación sobre una reserva completada")
async def open_dispute(
    reservation_id: uuid.UUID,
    reason: str = Form(..., min_length=20),
    files: list[UploadFile] = File(default=[]),
    session: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
):
    dispute = await dispute_service.open_dispute(reservation_id, user.id, reason, files, session)
    return {"success": True, "data": {"id": str(dispute.id), "status": dispute.status}}


@router.get("/disputes/my", response_model=dict, summary="Mis reclamaciones")
async def my_disputes(
    session: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
):
    items = await dispute_service.get_client_disputes(user.id, session)
    return {"success": True, "data": items}


@router.get("/admin/disputes", response_model=dict,
            dependencies=[Depends(require_role(UserRole.ADMIN))],
            summary="Listar todas las reclamaciones (admin)")
async def admin_list_disputes(
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=30, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    status_enum = DisputeStatus(status) if status else None
    items, total = await dispute_service.list_disputes(session, status_enum, page, page_size)
    return {"success": True, "data": items, "meta": {"total": total, "page": page, "page_size": page_size}}


@router.patch("/admin/disputes/{dispute_id}/resolve", response_model=dict,
              summary="Resolver reclamación (admin)")
async def resolve_dispute(
    dispute_id: uuid.UUID,
    data: DisputeResolve,
    session: AsyncSession = Depends(get_session),
    user=Depends(require_role(UserRole.ADMIN)),
):
    dispute = await dispute_service.resolve_dispute(
        dispute_id, user.id, data.decision, data.admin_notes, data.refund_amount, session
    )
    return {"success": True, "data": {"id": str(dispute.id), "status": dispute.status, "refund_amount": dispute.refund_amount}}
