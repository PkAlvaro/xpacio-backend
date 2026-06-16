import uuid
import structlog
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import DomainException, NotFoundError
from app.constants import ReservationStatus
from app.models.reservation import Reservation, Review
from app.models.space import Space
from app.models.user import User
from app.schemas.review import ReviewCreate, ReviewResponse

logger = structlog.get_logger()


async def create_review(
    reservation_id: uuid.UUID,
    data: ReviewCreate,
    client_id: uuid.UUID,
    session: AsyncSession,
) -> ReviewResponse:
    result = await session.execute(
        select(Reservation).where(Reservation.id == reservation_id)
    )
    reservation = result.scalar_one_or_none()
    if not reservation:
        raise NotFoundError("Reserva")

    if str(reservation.client_id) != str(client_id):
        raise DomainException("No tienes permiso para reseñar esta reserva", 403)

    if reservation.status != ReservationStatus.FINISHED:
        raise DomainException("Solo puedes reseñar reservas finalizadas")

    existing = await session.execute(
        select(Review).where(Review.reservation_id == reservation_id)
    )
    if existing.scalar_one_or_none():
        raise DomainException("Ya existe una reseña para esta reserva")

    review = Review(
        reservation_id=reservation_id,
        client_id=client_id,
        space_id=reservation.space_id,
        rating=data.rating,
        comment=data.comment,
    )
    session.add(review)

    avg_result = await session.execute(
        select(func.avg(Review.rating), func.count(Review.id)).where(
            Review.space_id == reservation.space_id
        )
    )
    avg_rating, count = avg_result.one()
    new_avg = float(avg_rating or 0)
    new_count = int(count or 0)

    space_result = await session.execute(
        select(Space).where(Space.id == reservation.space_id)
    )
    space = space_result.scalar_one_or_none()
    if space:
        space.rating = (new_avg * new_count + data.rating) / (new_count + 1)
        space.review_count = new_count + 1

    await session.commit()
    await session.refresh(review)

    user_result = await session.execute(select(User).where(User.id == client_id))
    user = user_result.scalar_one_or_none()
    client_name = user.name if user else "Usuario"

    return ReviewResponse(
        id=review.id,
        reservation_id=review.reservation_id,
        space_id=review.space_id,
        rating=review.rating,
        comment=review.comment,
        client_name=client_name,
        created_at=review.created_at,
    )


async def list_space_reviews(
    space_id: uuid.UUID,
    session: AsyncSession,
    page: int = 1,
    page_size: int = 10,
) -> tuple[list[ReviewResponse], int]:
    count_result = await session.execute(
        select(func.count(Review.id)).where(Review.space_id == space_id)
    )
    total = count_result.scalar_one()

    result = await session.execute(
        select(Review, User.name)
        .join(User, Review.client_id == User.id)
        .where(Review.space_id == space_id)
        .order_by(Review.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = result.all()

    items = [
        ReviewResponse(
            id=r.id,
            reservation_id=r.reservation_id,
            space_id=r.space_id,
            rating=r.rating,
            comment=r.comment,
            client_name=name,
            created_at=r.created_at,
        )
        for r, name in rows
    ]
    return items, total
