import asyncio
from passlib.context import CryptContext

_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)


async def hash_password(plain: str) -> str:
    return await asyncio.to_thread(_ctx.hash, plain)


async def verify_password(plain: str, hashed: str) -> bool:
    return await asyncio.to_thread(_ctx.verify, plain, hashed)
