import asyncio
import bcrypt


async def hash_password(plain: str) -> str:
    salt = bcrypt.gensalt(rounds=12)
    hashed = await asyncio.to_thread(bcrypt.hashpw, plain.encode(), salt)
    return hashed.decode()


async def verify_password(plain: str, hashed: str) -> bool:
    return await asyncio.to_thread(
        bcrypt.checkpw, plain.encode(), hashed.encode()
    )
