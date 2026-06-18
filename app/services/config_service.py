import uuid
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.system_config import SystemConfig

logger = structlog.get_logger()

SINGLETON_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


async def get_config(session: AsyncSession) -> SystemConfig:
    result = await session.execute(select(SystemConfig).where(SystemConfig.id == SINGLETON_ID))
    config = result.scalar_one_or_none()
    if not config:
        config = SystemConfig(id=SINGLETON_ID)
        session.add(config)
        await session.commit()
        await session.refresh(config)
    return config


async def update_config(session: AsyncSession, **kwargs) -> SystemConfig:
    config = await get_config(session)
    for key, value in kwargs.items():
        if hasattr(config, key) and value is not None:
            setattr(config, key, value)
    await session.commit()
    await session.refresh(config)
    logger.info("config_updated", changes=list(kwargs.keys()))
    return config
