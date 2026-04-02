"""PostgreSQL log manager for used chunk × dimension combinations."""

import logging
import os
import ssl

import asyncpg

logger = logging.getLogger(__name__)

_pool: asyncpg.Pool | None = None

_CONNECT_TIMEOUT = 5  # seconds — fail fast, don't block content generation


def _get_dsn() -> str:
    """Return a cleaned-up DSN that asyncpg can parse.

    Railway may expose the URL as postgres:// (libpq legacy form) or as an
    unresolved reference string.  asyncpg requires postgresql://.
    """
    url = os.getenv("DATABASE_URL", "").strip()
    # Log what Railway actually injected (mask password) to aid debugging
    masked = url[:30] + "…" if len(url) > 30 else url
    logger.info("DATABASE_URL raw value (first 30 chars): %r", masked)
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if not url.startswith("postgresql://"):
        raise RuntimeError(
            f"DATABASE_URL is missing or invalid (got: {masked!r}). "
            "In Railway: open your service → Variables → add DATABASE_URL "
            "and set it to the value from the Postgres plugin's 'Connect' tab "
            "(public URL starting with postgresql://)."
        )
    return url


def _ssl_context() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE  # Railway uses self-signed certs
    return ctx


async def get_pool() -> asyncpg.Pool:
    """Return (or create) the shared connection pool. Fails fast — no retries."""
    global _pool
    if _pool is not None:
        return _pool

    dsn = _get_dsn()
    _pool = await asyncpg.create_pool(
        dsn,
        min_size=1,
        max_size=5,
        ssl=_ssl_context(),
        command_timeout=_CONNECT_TIMEOUT,
        timeout=_CONNECT_TIMEOUT,
    )
    logger.info("PostgreSQL connection pool established.")
    await _create_table(_pool)
    return _pool


async def close_pool() -> None:
    """Close the connection pool on shutdown."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


async def _create_table(pool: asyncpg.Pool) -> None:
    """Create the used_combinations table if it does not exist."""
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


async def ensure_table() -> None:
    """Public helper — triggers lazy pool init + table creation."""
    await get_pool()


async def get_used_combinations() -> list[tuple[str, str]]:
    """Return used (chunk_id, dimension) pairs. Returns [] if DB is unavailable."""
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT chunk_id, dimension FROM used_combinations"
            )
        return [(row["chunk_id"], row["dimension"]) for row in rows]
    except Exception as exc:
        logger.warning("DB unavailable — skipping deduplication: %s", exc)
        return []


async def log_combination(chunk_id: str, dimension: str) -> None:
    """Insert a used combination. Silently skips if DB is unavailable."""
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO used_combinations (chunk_id, dimension) VALUES ($1, $2)",
                chunk_id,
                dimension,
            )
        logger.info("Logged combination: chunk_id=%s, dimension=%s", chunk_id, dimension)
    except Exception as exc:
        logger.warning("DB unavailable — combination not logged: %s", exc)
