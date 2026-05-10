import uuid
import asyncio
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


def _get_sdk():
    from transbank.webpay.webpay_plus.transaction import Transaction
    from transbank.common.integration_type import IntegrationType
    from transbank.common.options import WebpayOptions

    if settings.TRANSBANK_ENV == "production":
        opts = WebpayOptions(
            commerce_code=settings.TRANSBANK_COMMERCE_CODE,
            api_key=settings.TRANSBANK_API_KEY,
            integration_type=IntegrationType.LIVE,
        )
    else:
        opts = WebpayOptions(
            commerce_code=settings.TRANSBANK_COMMERCE_CODE,
            api_key=settings.TRANSBANK_API_KEY,
            integration_type=IntegrationType.TEST,
        )
    return Transaction(opts)


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

    # check existing payment
    existing = await session.execute(select(Payment).where(Payment.reservation_id == reservation_id))
    existing_payment = existing.scalar_one_or_none()
    if existing_payment and existing_payment.status == PaymentStatus.INITIATED:
        return existing_payment

    buy_order = str(reservation.id)[:26]
    session_id = str(client_id)[:61]

    def _create():
        tx = _get_sdk()
        return tx.create(buy_order, session_id, reservation.total, settings.TRANSBANK_RETURN_URL)

    response = await asyncio.to_thread(_create)

    payment = Payment(
        id=uuid.uuid4(),
        reservation_id=reservation_id,
        token=response["token"],
        buy_order=buy_order,
        amount=reservation.total,
        status=PaymentStatus.INITIATED,
    )
    session.add(payment)
    await session.commit()
    await session.refresh(payment)

    logger.info("payment_initiated", reservation_id=str(reservation_id), token=response["token"][:8])
    payment._webpay_url = response["url"]
    return payment


async def confirm_payment(token: str, session: AsyncSession) -> Payment:
    result = await session.execute(select(Payment).where(Payment.token == token))
    payment = result.scalar_one_or_none()
    if not payment:
        raise NotFoundError("Pago")

    if payment.status == PaymentStatus.PAID:
        return payment

    def _commit():
        tx = _get_sdk()
        return tx.commit(token)

    try:
        response = await asyncio.to_thread(_commit)
    except Exception as e:
        logger.error("transbank_commit_error", error=str(e), token=token[:8])
        payment.status = PaymentStatus.FAILED
        payment.raw_response = {"error": str(e)}
        await session.commit()
        raise DomainException("Error al confirmar el pago con Transbank", status_code=502)

    response_code = response.get("response_code", -1)
    payment.raw_response = response

    if response_code == 0:
        payment.status = PaymentStatus.PAID
        payment.authorized_at = now_chile()
        await confirm_reservation(payment.reservation_id, session)
        logger.info("payment_confirmed", token=token[:8])
    else:
        payment.status = PaymentStatus.FAILED
        from app.models.reservation import Reservation as Res
        res_result = await session.execute(select(Res).where(Res.id == payment.reservation_id))
        reservation = res_result.scalar_one_or_none()
        if reservation:
            reservation.status = ReservationStatus.CANCELLED
        logger.warning("payment_failed", token=token[:8], response_code=response_code)

    await session.commit()
    return payment


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
