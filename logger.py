"""PostgreSQL log manager for used chunk × dimension combinations."""

import logging
import os

import asyncpg

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "")

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    """Return (or create) the shared connection pool."""
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=5)
    return _pool


async def close_pool() -> None:
    """Close the connection pool on shutdown."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


async def ensure_table() -> None:
    """Create the used_combinations table if it does not exist."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS used_combinations (
                id SERIAL PRIMARY KEY,
                chunk_id VARCHAR(10),
                dimension VARCHAR(50),
                created_at TIMESTAMP DEFAULT NOW()
            )
            """
        )
    logger.info("Table 'used_combinations' is ready.")


async def get_used_combinations() -> list[tuple[str, str]]:
    """Return all (chunk_id, dimension) pairs already used."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT chunk_id, dimension FROM used_combinations"
        )
    return [(row["chunk_id"], row["dimension"]) for row in rows]


async def log_combination(chunk_id: str, dimension: str) -> None:
    """Insert a new used combination into the database."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO used_combinations (chunk_id, dimension) VALUES ($1, $2)",
            chunk_id,
            dimension,
        )
    logger.info("Logged combination: chunk_id=%s, dimension=%s", chunk_id, dimension)
