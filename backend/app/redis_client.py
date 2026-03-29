import os
import redis.asyncio as aioredis
from fastapi import HTTPException

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

async def get_redis():
    """FastAPI dependency that yields an async Redis client."""
    client = aioredis.from_url(REDIS_URL, decode_responses=True)
    try:
        yield client
    finally:
        await client.aclose()

async def check_rate_limit(redis, user_id, action, limit):
    key = f"rate:{user_id}:{action}"
    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, 86400)
    if count > limit:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
