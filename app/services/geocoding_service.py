import asyncio
import hashlib
import structlog
import httpx
from app.config import get_settings
from app.services.redis_service import RedisService
from app.constants import GEO_CACHE_TTL_DAYS, NOMINATIM_RATE_LIMIT_RPS

logger = structlog.get_logger()
settings = get_settings()

_semaphore = asyncio.Semaphore(NOMINATIM_RATE_LIMIT_RPS)


def _cache_key(address: str) -> str:
    digest = hashlib.sha256(address.lower().encode()).hexdigest()[:16]
    return f"geo:{digest}"


async def geocode(address: str, redis: RedisService) -> tuple[float, float] | None:
    key = _cache_key(address)

    cached = await redis.get(key)
    if cached:
        lat_str, lng_str = cached.split(",")
        return float(lat_str), float(lng_str)

    async with _semaphore:
        await asyncio.sleep(1.0 / NOMINATIM_RATE_LIMIT_RPS)
        result = await _fetch_nominatim(address)

    if result:
        lat, lng = result
        ttl = GEO_CACHE_TTL_DAYS * 86400
        await redis.set_with_ttl(key, f"{lat},{lng}", ttl)
        logger.info("geocode_ok", address=address[:50], lat=lat, lng=lng)
    else:
        logger.warning("geocode_miss", address=address[:50])

    return result


async def _fetch_nominatim(address: str) -> tuple[float, float] | None:
    params = {
        "format": "json",
        "q": address,
        "countrycodes": "cl",
        "limit": 1,
    }
    headers = {"User-Agent": settings.NOMINATIM_USER_AGENT}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{settings.NOMINATIM_BASE_URL}/search", params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            if data:
                return float(data[0]["lat"]), float(data[0]["lon"])
    except Exception as e:
        logger.error("nominatim_error", error=str(e))

    return None
