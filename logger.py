"""PostgreSQL log manager for used chunk × dimension combinations."""

import asyncio
import logging
import os
import ssl

import asyncpg

logger = logging.getLogger(__name__)

_pool: asyncpg.Pool | None = None

_RETRY_DELAYS = [2, 4, 8]  # seconds between attempts (4 total tries)


def _get_dsn() -> str:
    """Return a cleaned-up DSN that asyncpg can parse.

    Railway may expose the URL as postgres:// (libpq legacy form) or as an
    unresolved reference string.  asyncpg requires postgresql://.
    """
    url = os.getenv("DATABASE_URL", "").strip()
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if not url.startswith("postgresql://"):
        raise RuntimeError(
            "DATABASE_URL is missing or invalid. "
            "Set it to the public Railway PostgreSQL URL "
            "(e.g. postgresql://user:pass@host.railway.app:5432/railway)."
        )
    return url


def _ssl_context() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE  # Railway uses self-signed certs
    return ctx


async def get_pool() -> asyncpg.Pool:
    """Return (or create) the shared connection pool, with retry logic."""
    global _pool
    if _pool is not None:
        return _pool

    dsn = _get_dsn()
    last_exc: Exception | None = None

    for attempt, delay in enumerate([0] + _RETRY_DELAYS, start=1):
        if delay:
            logger.warning("DB connection attempt %d failed, retrying in %ds…", attempt - 1, delay)
            await asyncio.sleep(delay)
        try:
            _pool = await asyncpg.create_pool(
                dsn,
                min_size=1,
                max_size=5,
                ssl=_ssl_context(),
                command_timeout=30,
            )
            logger.info("PostgreSQL connection pool established (attempt %d).", attempt)
            return _pool
        except Exception as exc:
            last_exc = exc
            logger.error("DB connection attempt %d error: %s", attempt, exc)

    raise RuntimeError(f"Could not connect to PostgreSQL after {len(_RETRY_DELAYS) + 1} attempts: {last_exc}") from last_exc


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
