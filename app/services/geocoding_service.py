import asyncio
import hashlib
import structlog
import httpx
import googlemaps
from app.config import get_settings
from app.services.redis_service import RedisService
from app.constants import GEO_CACHE_TTL_DAYS

logger = structlog.get_logger()
settings = get_settings()

_client: googlemaps.Client | None = None


def _has_real_gmaps_key() -> bool:
    key = settings.GOOGLE_MAPS_API_KEY or ""
    return key.startswith("AIza") and "..." not in key and "placeholder" not in key.lower()


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

    # Si hay una API key real de Google, usar Google; si no, usar Nominatim (OpenStreetMap)
    # como fallback gratuito para que los espacios igualmente obtengan coordenadas reales.
    if _has_real_gmaps_key():
        result = await asyncio.to_thread(_fetch_gmaps, address)
    else:
        result = await _fetch_nominatim(address)

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


async def _fetch_nominatim(address: str) -> tuple[float, float] | None:
    """Fallback gratuito vía OpenStreetMap Nominatim (no requiere API key)."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": address, "format": "json", "limit": 1, "countrycodes": "cl"},
                headers={"User-Agent": "Xpacio/1.0 (geocoding)"},
            )
            resp.raise_for_status()
            data = resp.json()
            if data:
                return float(data[0]["lat"]), float(data[0]["lon"])
    except Exception as e:
        logger.warning("nominatim_geocode_error", error=str(e))
    return None
