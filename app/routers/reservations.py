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


@router.get(
    "/spaces/{space_id}/availability",
    response_model=dict,
    summary="Ver disponibilidad de un espacio",
    description="""
Retorna la lista de franjas horarias disponibles para un espacio en una fecha específica.

Cada slot indica:
- `start`: hora de inicio (HH:MM)
- `end`: hora de fin (HH:MM)
- `available`: si está disponible para reservar

El parámetro `slot_minutes` define la duración de cada franja (por defecto 60 min).
Los slots son generados según los horarios configurados por el proveedor y excluyen
las reservas ya existentes con estado `pending`, `confirmed` o `active`.

**No requiere autenticación.**
""",
)
async def get_availability(
    space_id: uuid.UUID,
    date: date = Query(..., description="Fecha a consultar (YYYY-MM-DD)"),
    slot_minutes: int = Query(default=60, ge=30, le=480, description="Duración de cada franja en minutos (30-480)"),
    session: AsyncSession = Depends(get_session),
):
    slots = await availability_service.get_available_slots(space_id, date, slot_minutes, session)
    return {"success": True, "data": [{"start": s.start, "end": s.end, "available": s.available} for s in slots]}


@router.post(
    "/reservations",
    response_model=dict,
    status_code=201,
    summary="Crear una reserva",
    description="""
Crea una nueva reserva para el usuario autenticado.

El sistema verifica automáticamente que no exista otra reserva activa para el mismo
espacio, fecha y horario (detección de conflictos a nivel de base de datos).

Estados posibles de una reserva:
- `pending`: creada, esperando pago (expira en 15 min si no se paga)
- `confirmed`: pago recibido y confirmado por Transbank
- `active`: la reserva está en curso (start_time <= ahora <= end_time)
- `finished`: finalizó
- `cancelled`: cancelada por el usuario
- `expired`: nunca se pagó y superó el tiempo límite

Después de crear la reserva, usar `POST /payments/initiate` para iniciar el pago.

**Requiere autenticación.**
""",
)
async def create_reservation(
    data: ReservationCreate,
    session: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
):
    reservation = await reservation_service.create_reservation(data, user.id, session)
    return {"success": True, "data": ReservationResponse.model_validate(reservation).model_dump()}


@router.get(
    "/reservations",
    response_model=dict,
    summary="Listar mis reservas",
    description="""
Retorna todas las reservas del usuario autenticado, ordenadas por fecha descendente.

Se puede filtrar por estado con el parámetro `status`:
- `pending`, `confirmed`, `active`, `finished`, `cancelled`, `expired`

**Requiere autenticación.**
""",
)
async def list_my_reservations(
    status: str | None = Query(default=None, description="Filtrar por estado: pending | confirmed | active | finished | cancelled | expired"),
    session: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
):
    status_enum = ReservationStatus(status) if status else None
    items = await reservation_service.list_client_reservations(user.id, session, status_enum)
    return {"success": True, "data": [ReservationResponse.model_validate(r).model_dump() for r in items]}


@router.get(
    "/reservations/{reservation_id}",
    response_model=dict,
    summary="Ver detalle de una reserva",
    description="""
Retorna el detalle completo de una reserva específica.

Solo el dueño de la reserva puede verla. Si el `reservation_id` no pertenece
al usuario autenticado, retorna 403.

**Requiere autenticación.**
""",
)
async def get_reservation(
    reservation_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
):
    reservation = await reservation_service.get_reservation(reservation_id, user.id, session)
    return {"success": True, "data": ReservationResponse.model_validate(reservation).model_dump()}


@router.post(
    "/reservations/{reservation_id}/cancel",
    response_model=dict,
    summary="Cancelar una reserva",
    description="""
Cancela una reserva existente. Solo se pueden cancelar reservas en estado
`pending` o `confirmed`. Reservas `active`, `finished` o `expired` no se pueden cancelar.

El campo `reason` (opcional) permite registrar el motivo de cancelación.

Solo el dueño de la reserva puede cancelarla.

**Requiere autenticación.**
""",
)
async def cancel_reservation(
    reservation_id: uuid.UUID,
    data: ReservationCancel = ReservationCancel(),
    session: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
):
    reservation = await reservation_service.cancel_reservation(reservation_id, user.id, data.reason, session)
    return {"success": True, "data": ReservationResponse.model_validate(reservation).model_dump()}
