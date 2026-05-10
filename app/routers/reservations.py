import uuid
from datetime import date
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies import get_current_user
from app.constants import ReservationStatus
from app.schemas.reservation import ReservationCreate, ReservationResponse, ReservationCancel
from app.services import reservation_service, availability_service

router = APIRouter(prefix="/api/v1", tags=["reservations"])


@router.get("/spaces/{space_id}/availability", response_model=dict)
async def get_availability(
    space_id: uuid.UUID,
    date: date = Query(...),
    slot_minutes: int = Query(default=60, ge=30, le=480),
    session: AsyncSession = Depends(get_session),
):
    slots = await availability_service.get_available_slots(space_id, date, slot_minutes, session)
    return {"success": True, "data": [{"start": s.start, "end": s.end, "available": s.available} for s in slots]}


@router.post("/reservations", response_model=dict, status_code=201)
async def create_reservation(
    data: ReservationCreate,
    session: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
):
    reservation = await reservation_service.create_reservation(data, user.id, session)
    return {"success": True, "data": ReservationResponse.model_validate(reservation).model_dump()}


@router.get("/reservations", response_model=dict)
async def list_my_reservations(
    status: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
):
    status_enum = ReservationStatus(status) if status else None
    items = await reservation_service.list_client_reservations(user.id, session, status_enum)
    return {"success": True, "data": [ReservationResponse.model_validate(r).model_dump() for r in items]}


@router.get("/reservations/{reservation_id}", response_model=dict)
async def get_reservation(
    reservation_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
):
    reservation = await reservation_service.get_reservation(reservation_id, user.id, session)
    return {"success": True, "data": ReservationResponse.model_validate(reservation).model_dump()}


@router.post("/reservations/{reservation_id}/cancel", response_model=dict)
async def cancel_reservation(
    reservation_id: uuid.UUID,
    data: ReservationCancel = ReservationCancel(),
    session: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
):
    reservation = await reservation_service.cancel_reservation(reservation_id, user.id, data.reason, session)
    return {"success": True, "data": ReservationResponse.model_validate(reservation).model_dump()}
