import redis.asyncio as aioredis
from app.config import get_settings

settings = get_settings()


class RedisService:
    def __init__(self, client: aioredis.Redis):
        self._r = client

    async def get(self, key: str) -> str | None:
        return await self._r.get(key)

    async def set_with_ttl(self, key: str, value: str, ttl: int) -> None:
        await self._r.setex(key, ttl, value)

    async def delete(self, key: str) -> None:
        await self._r.delete(key)

    async def delete_pattern(self, pattern: str) -> None:
        keys = await self._r.keys(pattern)
        if keys:
            await self._r.delete(*keys)

    async def ping(self) -> bool:
        return await self._r.ping()
