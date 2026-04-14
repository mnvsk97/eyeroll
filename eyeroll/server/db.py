"""Database helpers — raw asyncpg, no ORM.

Tables are created at startup. All functions expect a connection pool
produced by asyncpg.create_pool().
"""

import os
import secrets
import uuid
from datetime import datetime, timezone, timedelta

import asyncpg


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id         TEXT PRIMARY KEY,
    email      TEXT UNIQUE NOT NULL,
    api_key    TEXT UNIQUE NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS usage_logs (
    id         TEXT PRIMARY KEY,
    user_id    TEXT NOT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS usage_logs_user_time
    ON usage_logs(user_id, created_at);
"""

RATE_LIMIT = int(os.environ.get("EYEROLL_RATE_LIMIT", "20"))


async def init_pool() -> asyncpg.Pool:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL environment variable is not set.")
    pool = await asyncpg.create_pool(database_url)
    async with pool.acquire() as conn:
        await conn.execute(SCHEMA)
    return pool


def _new_api_key() -> str:
    return "er_" + secrets.token_hex(24)


async def create_user(pool: asyncpg.Pool, email: str) -> dict:
    """Create a new user or return existing one for the given email."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT id, email, api_key FROM users WHERE email = $1", email)
        if row:
            return dict(row)
        uid = str(uuid.uuid4())
        key = _new_api_key()
        await conn.execute(
            "INSERT INTO users (id, email, api_key) VALUES ($1, $2, $3)",
            uid, email, key,
        )
        return {"id": uid, "email": email, "api_key": key}


async def get_user_by_key(pool: asyncpg.Pool, api_key: str) -> dict | None:
    """Return user row for the given API key, or None if not found."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, email, api_key FROM users WHERE api_key = $1", api_key
        )
        return dict(row) if row else None


async def rotate_key(pool: asyncpg.Pool, user_id: str) -> str:
    """Replace the user's API key with a fresh one. Returns the new key."""
    new_key = _new_api_key()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET api_key = $1 WHERE id = $2", new_key, user_id
        )
    return new_key


async def usage_today(pool: asyncpg.Pool, user_id: str) -> int:
    """Count analyses in the last 24 hours for this user."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT COUNT(*) AS cnt FROM usage_logs
            WHERE user_id = $1 AND created_at > NOW() - INTERVAL '24 hours'
            """,
            user_id,
        )
        return row["cnt"]


async def log_usage(pool: asyncpg.Pool, user_id: str) -> None:
    """Record one analysis against this user."""
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO usage_logs (id, user_id) VALUES ($1, $2)",
            str(uuid.uuid4()), user_id,
        )


async def check_rate_limit(pool: asyncpg.Pool, user_id: str) -> tuple[bool, int]:
    """Return (allowed, used_today). Allowed is False if limit reached."""
    used = await usage_today(pool, user_id)
    return used < RATE_LIMIT, used
