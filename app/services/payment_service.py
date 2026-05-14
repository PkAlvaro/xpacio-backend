import uuid
import stripe
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.payment import Payment
from app.models.reservation import Reservation
from app.constants import PaymentStatus, ReservationStatus
from app.exceptions import NotFoundError, DomainException, ForbiddenError
from app.services.reservation_service import confirm_reservation
from app.config import get_settings
from app.utils.time_utils import now_chile

logger = structlog.get_logger()
settings = get_settings()


def _stripe():
    stripe.api_key = settings.STRIPE_SECRET_KEY
    return stripe


async def initiate_payment(
    reservation_id: uuid.UUID,
    client_id: uuid.UUID,
    session: AsyncSession,
) -> Payment:
    result = await session.execute(select(Reservation).where(Reservation.id == reservation_id))
    reservation = result.scalar_one_or_none()
    if not reservation:
        raise NotFoundError("Reserva")
    if str(reservation.client_id) != str(client_id):
        raise ForbiddenError("No puedes pagar esta reserva")
    if reservation.status != ReservationStatus.PENDING:
        raise DomainException(f"Reserva en estado '{reservation.status}' no puede iniciar pago")

    existing = await session.execute(select(Payment).where(Payment.reservation_id == reservation_id))
    existing_payment = existing.scalar_one_or_none()
    if existing_payment and existing_payment.status == PaymentStatus.INITIATED:
        checkout = _stripe().checkout.Session.retrieve(existing_payment.token)
        existing_payment._checkout_url = checkout.url
        return existing_payment

    s = _stripe()
    buy_order = str(reservation.id)

    checkout = s.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{
            "price_data": {
                "currency": "clp",
                "product_data": {"name": f"Reserva Xpacio #{buy_order[:8]}"},
                "unit_amount": reservation.total,
            },
            "quantity": 1,
        }],
        mode="payment",
        success_url=settings.STRIPE_SUCCESS_URL,
        cancel_url=settings.STRIPE_CANCEL_URL,
        metadata={"reservation_id": str(reservation_id), "client_id": str(client_id)},
    )

    payment = Payment(
        id=uuid.uuid4(),
        reservation_id=reservation_id,
        token=checkout.id,
        buy_order=buy_order,
        amount=reservation.total,
        status=PaymentStatus.INITIATED,
    )
    session.add(payment)
    await session.commit()
    await session.refresh(payment)

    logger.info("payment_initiated", reservation_id=str(reservation_id), session_id=checkout.id[:12])
    payment._checkout_url = checkout.url
    return payment


async def handle_webhook(payload: bytes, sig_header: str, session: AsyncSession) -> None:
    try:
        event = _stripe().Webhook.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)
    except Exception as e:
        logger.error("stripe_webhook_invalid", error=str(e))
        raise DomainException("Webhook inválido", status_code=400)

    event_type = event["type"]
    checkout_session = event["data"]["object"]
    session_id = checkout_session["id"]

    if event_type == "checkout.session.completed":
        await _handle_success(session_id, session)
    elif event_type == "checkout.session.expired":
        await _handle_expired(session_id, session)
    else:
        logger.debug("stripe_event_ignored", type=event_type)


async def _handle_success(session_id: str, session: AsyncSession) -> None:
    result = await session.execute(select(Payment).where(Payment.token == session_id))
    payment = result.scalar_one_or_none()
    if not payment or payment.status == PaymentStatus.PAID:
        return

    payment.status = PaymentStatus.PAID
    payment.authorized_at = now_chile()
    payment.raw_response = {"stripe_session_id": session_id}
    await confirm_reservation(payment.reservation_id, session)
    await session.commit()
    logger.info("payment_confirmed", session_id=session_id[:12])


async def _handle_expired(session_id: str, session: AsyncSession) -> None:
    result = await session.execute(select(Payment).where(Payment.token == session_id))
    payment = result.scalar_one_or_none()
    if not payment:
        return

    payment.status = PaymentStatus.FAILED
    payment.raw_response = {"stripe_session_id": session_id, "reason": "expired"}

    res_result = await session.execute(select(Reservation).where(Reservation.id == payment.reservation_id))
    reservation = res_result.scalar_one_or_none()
    if reservation:
        reservation.status = ReservationStatus.CANCELLED

    await session.commit()
    logger.warning("payment_expired", session_id=session_id[:12])


async def get_payment(payment_id: uuid.UUID, user_id: uuid.UUID, session: AsyncSession) -> Payment:
    result = await session.execute(select(Payment).where(Payment.id == payment_id))
    payment = result.scalar_one_or_none()
    if not payment:
        raise NotFoundError("Pago")

    res_result = await session.execute(
        select(Reservation).where(Reservation.id == payment.reservation_id)
    )
    reservation = res_result.scalar_one_or_none()
    if not reservation or str(reservation.client_id) != str(user_id):
        raise ForbiddenError("Acceso denegado")

    return payment
