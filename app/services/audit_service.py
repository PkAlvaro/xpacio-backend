import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.utils.time_utils import now_chile


async def log_action(
    session: AsyncSession,
    action: str,
    admin_id: uuid.UUID | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    detail: dict | None = None,
) -> None:
    session.add(AuditLog(
        id=uuid.uuid4(),
        admin_id=admin_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        detail=detail,
        created_at=now_chile(),
    ))
