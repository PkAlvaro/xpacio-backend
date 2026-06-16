import uuid
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies import get_current_user
from app.schemas.review import ReviewCreate
from app.services import review_service

router = APIRouter(prefix="/api/v1", tags=["reviews"])


@router.post(
    "/reservations/{reservation_id}/review",
    response_model=dict,
    status_code=201,
    summary="Dejar una reseña",
    description="""
Crea una reseña para una reserva finalizada.

Requisitos:
- La reserva debe estar en estado `finished`
- Solo el cliente dueño de la reserva puede dejar reseña
- Solo se permite una reseña por reserva

**Requiere autenticación.**
""",
)
async def create_review(
    reservation_id: uuid.UUID,
    data: ReviewCreate,
    session: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
):
    review = await review_service.create_review(reservation_id, data, user.id, session)
    return {"success": True, "data": review.model_dump()}


@router.get(
    "/spaces/{space_id}/reviews",
    response_model=dict,
    summary="Reseñas de un espacio",
    description="""
Retorna las reseñas de un espacio, ordenadas por fecha descendente.

**No requiere autenticación.**
""",
)
async def list_space_reviews(
    space_id: uuid.UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
    session: AsyncSession = Depends(get_session),
):
    items, total = await review_service.list_space_reviews(space_id, session, page, page_size)
    return {
        "success": True,
        "data": [r.model_dump() for r in items],
        "meta": {"total": total, "page": page, "page_size": page_size},
    }
