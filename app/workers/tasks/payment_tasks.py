import asyncio
import stripe
import structlog
from sqlalchemy import select, and_

from app.workers.celery_app import celery_app
from app.constants import PaymentStatus, PaymentProvider, ReservationStatus
from app.utils.time_utils import now_chile

logger = structlog.get_logger()


def _get_session():
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from app.config import get_settings
    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL)
    return async_sessionmaker(engine, expire_on_commit=False)


@celery_app.task(name="app.workers.tasks.payment_tasks.reconcile_stale_payments")
def reconcile_stale_payments():
    asyncio.run(_reconcile())


async def _reconcile():
    from app.models.payment import Payment
    from app.models.reservation import Reservation
    from app.services.reservation_service import confirm_reservation
    from app.config import get_settings
    from datetime import timedelta

    settings = get_settings()
    stripe.api_key = settings.STRIPE_SECRET_KEY

    SessionLocal = _get_session()
    cutoff = now_chile() - timedelta(minutes=30)

    async with SessionLocal() as session:
        result = await session.execute(
            select(Payment).where(
                and_(Payment.status == PaymentStatus.INITIATED, Payment.created_at <= cutoff)
            )
        )
        stale = result.scalars().all()

    for payment in stale:
        try:
            if payment.provider == PaymentProvider.STRIPE:
                await _reconcile_stripe(payment, SessionLocal, confirm_reservation)
            else:
                await _reconcile_transbank(payment, SessionLocal)
        except Exception as e:
            logger.warning("payment_reconcile_fail", token=payment.token[:12], error=str(e))


async def _reconcile_stripe(payment, SessionLocal, confirm_reservation):
    checkout = stripe.checkout.Session.retrieve(payment.token)
    if checkout.payment_status == "paid":
        async with SessionLocal() as session:
            from app.models.payment import Payment
            res = await session.execute(select(Payment).where(Payment.id == payment.id))
            p = res.scalar_one_or_none()
            if p and p.status == PaymentStatus.INITIATED:
                from app.utils.time_utils import now_chile
                p.status = PaymentStatus.PAID
                p.authorized_at = now_chile()
                p.raw_response = {"stripe_session_id": payment.token, "source": "reconcile"}
                await confirm_reservation(p.reservation_id, session)
                await session.commit()
                logger.info("stripe_reconciled_paid", session_id=payment.token[:12])
    elif checkout.status == "expired":
        await _mark_failed(payment, SessionLocal, reason="stripe_expired")


async def _reconcile_transbank(payment, SessionLocal):
    # Transbank sessions expire after ~10 min — mark as failed after cutoff
    await _mark_failed(payment, SessionLocal, reason="transbank_timeout")


async def _mark_failed(payment, SessionLocal, reason: str):
    from app.models.payment import Payment
    from app.models.reservation import Reservation

    async with SessionLocal() as session:
        res = await session.execute(select(Payment).where(Payment.id == payment.id))
        p = res.scalar_one_or_none()
        if p and p.status == PaymentStatus.INITIATED:
            p.status = PaymentStatus.FAILED
            p.raw_response = {"reason": reason, "source": "reconcile"}
            res_result = await session.execute(
                select(Reservation).where(Reservation.id == p.reservation_id)
            )
            reservation = res_result.scalar_one_or_none()
            if reservation and reservation.status == ReservationStatus.PENDING:
                reservation.status = ReservationStatus.CANCELLED
            await session.commit()
            logger.info("payment_reconciled_failed", token=payment.token[:12], reason=reason)
