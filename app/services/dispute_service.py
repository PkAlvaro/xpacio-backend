import uuid
from datetime import datetime, timedelta, timezone
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import structlog

from app.models.dispute import Dispute, DisputeEvidence
from app.models.reservation import Reservation
from app.models.space import Space
from app.models.user import User
from app.constants import DisputeStatus, ReservationStatus, DISPUTE_WINDOW_DAYS
from app.exceptions import NotFoundError, ForbiddenError, DomainException
from app.utils.time_utils import now_chile

logger = structlog.get_logger()


async def open_dispute(
    reservation_id: uuid.UUID,
    client_id: uuid.UUID,
    reason: str,
    files: list[UploadFile],
    session: AsyncSession,
) -> Dispute:
    res = await session.get(Reservation, reservation_id)
    if not res:
        raise NotFoundError("Reserva")
    if str(res.client_id) != str(client_id):
        raise ForbiddenError("No tienes acceso a esta reserva")
    if res.status != ReservationStatus.FINISHED:
        raise DomainException("Solo puedes reclamar reservas completadas")

    # Ventana de 3 días desde fin de la reserva
    end_date = res.end_date or res.date
    end_dt = datetime.combine(end_date, res.end_time).replace(tzinfo=timezone.utc)
    deadline = end_dt + timedelta(days=DISPUTE_WINDOW_DAYS)
    if now_chile().replace(tzinfo=timezone.utc) > deadline:
        raise DomainException(f"El plazo para reclamar venció ({DISPUTE_WINDOW_DAYS} días tras la reserva)")

    existing = (await session.execute(
        select(Dispute).where(Dispute.reservation_id == reservation_id)
    )).scalar_one_or_none()
    if existing:
        raise DomainException("Ya existe una reclamación para esta reserva")

    dispute = Dispute(
        id=uuid.uuid4(),
        reservation_id=reservation_id,
        opened_by=client_id,
        reason=reason,
        status=DisputeStatus.OPEN,
    )
    session.add(dispute)
    await session.flush()

    from app.services.storage_service import upload_file
    now = now_chile()
    for f in files:
        if not f.content_type or not f.content_type.startswith("image/"):
            continue
        url = await upload_file(f, folder=f"disputes/{dispute.id}")
        session.add(DisputeEvidence(
            id=uuid.uuid4(),
            dispute_id=dispute.id,
            url=url,
            filename=f.filename,
            uploaded_at=now,
        ))

    await session.commit()
    await session.refresh(dispute)
    logger.info("dispute_opened", dispute_id=str(dispute.id), reservation_id=str(reservation_id))
    return dispute


async def resolve_dispute(
    dispute_id: uuid.UUID,
    admin_id: uuid.UUID,
    decision: str,
    admin_notes: str | None,
    refund_amount: int | None,
    session: AsyncSession,
) -> Dispute:
    dispute = await session.get(Dispute, dispute_id)
    if not dispute:
        raise NotFoundError("Disputa")
    if dispute.status in (DisputeStatus.RESOLVED_REFUND, DisputeStatus.RESOLVED_REJECTED):
        raise DomainException("Disputa ya resuelta")

    dispute.status = DisputeStatus.RESOLVED_REFUND if decision == "refund" else DisputeStatus.RESOLVED_REJECTED
    dispute.admin_notes = admin_notes
    dispute.refund_amount = refund_amount if decision == "refund" else None
    dispute.resolved_at = now_chile()
    dispute.resolved_by = admin_id
    await session.commit()
    await session.refresh(dispute)
    logger.info("dispute_resolved", dispute_id=str(dispute_id), decision=decision, admin=str(admin_id))
    return dispute


async def list_disputes(
    session: AsyncSession,
    status: DisputeStatus | None = None,
    page: int = 1,
    page_size: int = 30,
) -> tuple[list[dict], int]:
    from sqlalchemy import func

    base = (
        select(
            Dispute,
            User.name.label("opener_name"),
            User.email.label("opener_email"),
            Space.name.label("space_name"),
        )
        .join(User, Dispute.opened_by == User.id)
        .join(Reservation, Dispute.reservation_id == Reservation.id)
        .join(Space, Reservation.space_id == Space.id)
    )
    if status:
        base = base.where(Dispute.status == status)

    count_q = select(func.count()).select_from(
        (select(Dispute).where(Dispute.status == status) if status else select(Dispute)).subquery()
    )
    total = (await session.execute(count_q)).scalar_one()

    rows = (await session.execute(
        base.order_by(Dispute.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    )).all()

    out = []
    for row in rows:
        d = row[0]
        evidence = (await session.execute(
            select(DisputeEvidence).where(DisputeEvidence.dispute_id == d.id)
        )).scalars().all()
        item = {c.name: getattr(d, c.name) for c in d.__table__.columns}
        item["opener_name"] = row[1]
        item["opener_email"] = row[2]
        item["space_name"] = row[3]
        item["evidence"] = [{"id": str(e.id), "url": e.url, "filename": e.filename, "uploaded_at": e.uploaded_at} for e in evidence]
        out.append(item)
    return out, total


async def get_client_disputes(
    client_id: uuid.UUID,
    session: AsyncSession,
) -> list[dict]:
    rows = (await session.execute(
        select(Dispute, Space.name.label("space_name"))
        .join(Reservation, Dispute.reservation_id == Reservation.id)
        .join(Space, Reservation.space_id == Space.id)
        .where(Dispute.opened_by == client_id)
        .order_by(Dispute.created_at.desc())
    )).all()

    out = []
    for row in rows:
        d = row[0]
        evidence = (await session.execute(
            select(DisputeEvidence).where(DisputeEvidence.dispute_id == d.id)
        )).scalars().all()
        item = {c.name: getattr(d, c.name) for c in d.__table__.columns}
        item["space_name"] = row[1]
        item["evidence"] = [{"id": str(e.id), "url": e.url, "filename": e.filename, "uploaded_at": e.uploaded_at} for e in evidence]
        out.append(item)
    return out
