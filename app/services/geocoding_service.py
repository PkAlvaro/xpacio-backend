import asyncio
import hashlib
import structlog
import googlemaps
from app.config import get_settings
from app.services.redis_service import RedisService
from app.constants import GEO_CACHE_TTL_DAYS

logger = structlog.get_logger()
settings = get_settings()

_client: googlemaps.Client | None = None


def _get_client() -> googlemaps.Client:
    global _client
    if _client is None:
        _client = googlemaps.Client(key=settings.GOOGLE_MAPS_API_KEY)
    return _client


def _cache_key(address: str) -> str:
    digest = hashlib.sha256(address.lower().encode()).hexdigest()[:16]
    return f"geo:{digest}"


async def geocode(address: str, redis: RedisService) -> tuple[float, float] | None:
    key = _cache_key(address)

    cached = await redis.get(key)
    if cached:
        lat_str, lng_str = cached.split(",")
        return float(lat_str), float(lng_str)

    result = await asyncio.to_thread(_fetch_gmaps, address)

    if result:
        lat, lng = result
        ttl = GEO_CACHE_TTL_DAYS * 86400
        await redis.set_with_ttl(key, f"{lat},{lng}", ttl)
        logger.info("geocode_ok", address=address[:50], lat=lat, lng=lng)
    else:
        logger.warning("geocode_miss", address=address[:50])

    return result


def _fetch_gmaps(address: str) -> tuple[float, float] | None:
    try:
        results = _get_client().geocode(address, region="cl", language="es")
        if results:
            loc = results[0]["geometry"]["location"]
            return loc["lat"], loc["lng"]
    except Exception as e:
        logger.error("gmaps_geocode_error", error=str(e))
    return None
