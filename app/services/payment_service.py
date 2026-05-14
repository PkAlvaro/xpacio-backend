import uuid
import asyncio
import stripe
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.payment import Payment
from app.models.reservation import Reservation
from app.constants import PaymentStatus, PaymentProvider, ReservationStatus
from app.exceptions import NotFoundError, DomainException, ForbiddenError
from app.services.reservation_service import confirm_reservation
from app.config import get_settings
from app.utils.time_utils import now_chile

logger = structlog.get_logger()
settings = get_settings()


def _stripe():
    stripe.api_key = settings.STRIPE_SECRET_KEY
    return stripe


def _transbank():
    from transbank.webpay.webpay_plus.transaction import Transaction
    from transbank.common.integration_type import IntegrationType
    from transbank.common.options import WebpayOptions

    integration = IntegrationType.LIVE if settings.TRANSBANK_ENV == "production" else IntegrationType.TEST
    opts = WebpayOptions(
        commerce_code=settings.TRANSBANK_COMMERCE_CODE,
        api_key=settings.TRANSBANK_API_KEY,
        integration_type=integration,
    )
    return Transaction(opts)


async def _get_reservation_for_payment(
    reservation_id: uuid.UUID,
    client_id: uuid.UUID,
    session: AsyncSession,
) -> Reservation:
    result = await session.execute(select(Reservation).where(Reservation.id == reservation_id))
    reservation = result.scalar_one_or_none()
    if not reservation:
        raise NotFoundError("Reserva")
    if str(reservation.client_id) != str(client_id):
        raise ForbiddenError("No puedes pagar esta reserva")
    if reservation.status != ReservationStatus.PENDING:
        raise DomainException(f"Reserva en estado '{reservation.status}' no puede iniciar pago")
    return reservation


async def initiate_payment(
    reservation_id: uuid.UUID,
    client_id: uuid.UUID,
    provider: PaymentProvider,
    session: AsyncSession,
) -> Payment:
    reservation = await _get_reservation_for_payment(reservation_id, client_id, session)

    existing = await session.execute(select(Payment).where(Payment.reservation_id == reservation_id))
    existing_payment = existing.scalar_one_or_none()
    if existing_payment and existing_payment.status == PaymentStatus.INITIATED:
        if existing_payment.provider != provider:
            raise DomainException("Ya existe un pago iniciado con otro proveedor. Cancela la reserva e intenta de nuevo.")
        await _attach_redirect_url(existing_payment)
        return existing_payment

    if provider == PaymentProvider.STRIPE:
        return await _initiate_stripe(reservation, client_id, session)
    return await _initiate_transbank(reservation, session)


async def _initiate_stripe(
    reservation: Reservation,
    client_id: uuid.UUID,
    session: AsyncSession,
) -> Payment:
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
        metadata={"reservation_id": str(reservation.id), "client_id": str(client_id)},
    )

    payment = Payment(
        id=uuid.uuid4(),
        reservation_id=reservation.id,
        provider=PaymentProvider.STRIPE,
        token=checkout.id,
        buy_order=buy_order,
        amount=reservation.total,
        status=PaymentStatus.INITIATED,
    )
    session.add(payment)
    await session.commit()
    await session.refresh(payment)

    logger.info("stripe_payment_initiated", reservation_id=str(reservation.id), session_id=checkout.id[:12])
    payment._redirect_url = checkout.url
    return payment


async def _initiate_transbank(reservation: Reservation, session: AsyncSession) -> Payment:
    buy_order = str(reservation.id)[:26]
    session_id = str(reservation.client_id)[:61]

    def _create():
        tx = _transbank()
        return tx.create(buy_order, session_id, reservation.total, settings.TRANSBANK_RETURN_URL)

    response = await asyncio.to_thread(_create)

    payment = Payment(
        id=uuid.uuid4(),
        reservation_id=reservation.id,
        provider=PaymentProvider.TRANSBANK,
        token=response["token"],
        buy_order=buy_order,
        amount=reservation.total,
        status=PaymentStatus.INITIATED,
    )
    session.add(payment)
    await session.commit()
    await session.refresh(payment)

    logger.info("transbank_payment_initiated", reservation_id=str(reservation.id), token=response["token"][:8])
    payment._redirect_url = response["url"]
    return payment


async def _attach_redirect_url(payment: Payment) -> None:
    if payment.provider == PaymentProvider.STRIPE:
        checkout = _stripe().checkout.Session.retrieve(payment.token)
        payment._redirect_url = checkout.url
    else:
        payment._redirect_url = f"https://webpay3g.transbank.cl/webpayserver/initTransaction?token_ws={payment.token}"


# --- Stripe webhook ---

async def handle_stripe_webhook(payload: bytes, sig_header: str, session: AsyncSession) -> None:
    try:
        event = _stripe().Webhook.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)
    except Exception as e:
        logger.error("stripe_webhook_invalid", error=str(e))
        raise DomainException("Webhook invalido", status_code=400)

    event_type = event["type"]
    checkout_session = event["data"]["object"]
    session_id = checkout_session["id"]

    if event_type == "checkout.session.completed":
        await _handle_stripe_success(session_id, session)
    elif event_type == "checkout.session.expired":
        await _handle_payment_expired(session_id, session)
    else:
        logger.debug("stripe_event_ignored", type=event_type)


async def _handle_stripe_success(session_id: str, session: AsyncSession) -> None:
    result = await session.execute(select(Payment).where(Payment.token == session_id))
    payment = result.scalar_one_or_none()
    if not payment or payment.status == PaymentStatus.PAID:
        return

    payment.status = PaymentStatus.PAID
    payment.authorized_at = now_chile()
    payment.raw_response = {"stripe_session_id": session_id}
    await confirm_reservation(payment.reservation_id, session)
    await session.commit()
    logger.info("stripe_payment_confirmed", session_id=session_id[:12])


# --- Transbank confirm ---

async def confirm_transbank(token_ws: str, session: AsyncSession) -> Payment:
    result = await session.execute(select(Payment).where(Payment.token == token_ws))
    payment = result.scalar_one_or_none()
    if not payment:
        raise NotFoundError("Pago")
    if payment.provider != PaymentProvider.TRANSBANK:
        raise DomainException("Token no corresponde a un pago Transbank", status_code=400)
    if payment.status == PaymentStatus.PAID:
        return payment

    def _commit():
        tx = _transbank()
        return tx.commit(token_ws)

    try:
        response = await asyncio.to_thread(_commit)
    except Exception as e:
        logger.error("transbank_commit_error", error=str(e), token=token_ws[:8])
        payment.status = PaymentStatus.FAILED
        payment.raw_response = {"error": str(e)}
        await session.commit()
        raise DomainException("Error al confirmar el pago con Transbank", status_code=502)

    payment.raw_response = response
    if response.get("response_code", -1) == 0:
        payment.status = PaymentStatus.PAID
        payment.authorized_at = now_chile()
        await confirm_reservation(payment.reservation_id, session)
        logger.info("transbank_payment_confirmed", token=token_ws[:8])
    else:
        payment.status = PaymentStatus.FAILED
        res_result = await session.execute(select(Reservation).where(Reservation.id == payment.reservation_id))
        reservation = res_result.scalar_one_or_none()
        if reservation:
            reservation.status = ReservationStatus.CANCELLED
        logger.warning("transbank_payment_failed", token=token_ws[:8], response_code=response.get("response_code"))

    await session.commit()
    return payment


# --- Shared helpers ---

async def _handle_payment_expired(token: str, session: AsyncSession) -> None:
    result = await session.execute(select(Payment).where(Payment.token == token))
    payment = result.scalar_one_or_none()
    if not payment:
        return
    payment.status = PaymentStatus.FAILED
    payment.raw_response = {"reason": "expired"}
    res_result = await session.execute(select(Reservation).where(Reservation.id == payment.reservation_id))
    reservation = res_result.scalar_one_or_none()
    if reservation:
        reservation.status = ReservationStatus.CANCELLED
    await session.commit()
    logger.warning("payment_expired", token=token[:12])


async def get_payment(payment_id: uuid.UUID, user_id: uuid.UUID, session: AsyncSession) -> Payment:
    result = await session.execute(select(Payment).where(Payment.id == payment_id))
    payment = result.scalar_one_or_none()
    if not payment:
        raise NotFoundError("Pago")
    res_result = await session.execute(select(Reservation).where(Reservation.id == payment.reservation_id))
    reservation = res_result.scalar_one_or_none()
    if not reservation or str(reservation.client_id) != str(user_id):
        raise ForbiddenError("Acceso denegado")
    return payment
