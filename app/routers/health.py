import structlog
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies import get_redis

router = APIRouter(tags=["health"])
logger = structlog.get_logger()


@router.get("/health")
async def health_check(
    session: AsyncSession = Depends(get_session),
    redis=Depends(get_redis),
):
    checks = {}

    try:
        await session.execute(text("SELECT 1"))
        checks["db"] = "ok"
    except Exception as e:
        logger.error("health_db_fail", error=str(e))
        checks["db"] = "fail"

    try:
        await redis.ping()
        checks["redis"] = "ok"
    except Exception as e:
        logger.error("health_redis_fail", error=str(e))
        checks["redis"] = "fail"

    healthy = all(v == "ok" for v in checks.values())
    status_code = 200 if healthy else 503

    return JSONResponse(
        status_code=status_code,
        content={"status": "healthy" if healthy else "degraded", "checks": checks},
    )
