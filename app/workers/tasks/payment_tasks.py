import asyncio
import structlog
from sqlalchemy import select, and_

from app.workers.celery_app import celery_app
from app.constants import PaymentStatus
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
    from app.services.payment_service import confirm_payment
    from datetime import timedelta

    SessionLocal = _get_session()
    cutoff = now_chile() - timedelta(minutes=30)

    async with SessionLocal() as session:
        result = await session.execute(
            select(Payment).where(
                and_(
                    Payment.status == PaymentStatus.INITIATED,
                    Payment.created_at <= cutoff,
                )
            )
        )
        stale = result.scalars().all()

    for payment in stale:
        try:
            async with SessionLocal() as session:
                await confirm_payment(payment.token, session)
            logger.info("payment_reconciled", token=payment.token[:8])
        except Exception as e:
            logger.warning("payment_reconcile_fail", token=payment.token[:8], error=str(e))
