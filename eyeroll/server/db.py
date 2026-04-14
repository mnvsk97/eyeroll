"""Database helpers — raw asyncpg, no ORM.

Schema
------
users      — one row per email address
api_keys   — many keys per user, each with an optional name/label
usage_logs — one row per analysis, linked to user + key used

Tables are created at startup via CREATE TABLE IF NOT EXISTS.
All functions accept a connection pool from asyncpg.create_pool().
"""

import os
import secrets
import uuid

import asyncpg


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id         TEXT PRIMARY KEY,
    email      TEXT UNIQUE NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS api_keys (
    id         TEXT PRIMARY KEY,
    user_id    TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    key        TEXT UNIQUE NOT NULL,
    name       TEXT NOT NULL DEFAULT 'default',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS api_keys_key_idx ON api_keys(key);
CREATE INDEX IF NOT EXISTS api_keys_user_idx ON api_keys(user_id);

CREATE TABLE IF NOT EXISTS usage_logs (
    id         TEXT PRIMARY KEY,
    user_id    TEXT NOT NULL REFERENCES users(id),
    key_id     TEXT REFERENCES api_keys(id) ON DELETE SET NULL,
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


def _new_key() -> str:
    return "er_" + secrets.token_hex(24)


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

async def create_user(pool: asyncpg.Pool, email: str) -> tuple[dict, dict]:
    """Create a new user with a default key, or return existing user + all their keys.

    Returns (user_row, first_key_row).
    For new users the first_key_row is the freshly created default key.
    For existing users the first_key_row is their oldest key.
    """
    async with pool.acquire() as conn:
        user = await conn.fetchrow("SELECT id, email FROM users WHERE email = $1", email)
        if user:
            # Return existing user + their oldest key
            key_row = await conn.fetchrow(
                "SELECT id, key, name, created_at FROM api_keys "
                "WHERE user_id = $1 ORDER BY created_at ASC LIMIT 1",
                user["id"],
            )
            return dict(user), dict(key_row) if key_row else {}

        uid = str(uuid.uuid4())
        await conn.execute("INSERT INTO users (id, email) VALUES ($1, $2)", uid, email)
        key_row = await _insert_key(conn, uid, "default")
        return {"id": uid, "email": email}, key_row


async def _insert_key(conn, user_id: str, name: str) -> dict:
    kid = str(uuid.uuid4())
    key = _new_key()
    await conn.execute(
        "INSERT INTO api_keys (id, user_id, key, name) VALUES ($1, $2, $3, $4)",
        kid, user_id, key, name,
    )
    row = await conn.fetchrow(
        "SELECT id, key, name, created_at FROM api_keys WHERE id = $1", kid
    )
    return dict(row)


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

async def get_user_by_key(pool: asyncpg.Pool, raw_key: str) -> dict | None:
    """Return {user_id, email, key_id} for the given key, or None."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT u.id AS user_id, u.email, k.id AS key_id
            FROM api_keys k
            JOIN users u ON u.id = k.user_id
            WHERE k.key = $1
            """,
            raw_key,
        )
        return dict(row) if row else None


# ---------------------------------------------------------------------------
# Key CRUD
# ---------------------------------------------------------------------------

async def list_keys(pool: asyncpg.Pool, user_id: str) -> list[dict]:
    """Return all API keys for a user, newest first."""
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, name, key, created_at FROM api_keys "
            "WHERE user_id = $1 ORDER BY created_at DESC",
            user_id,
        )
        return [dict(r) for r in rows]


async def create_key(pool: asyncpg.Pool, user_id: str, name: str = "default") -> dict:
    """Create and return a new API key for the user."""
    async with pool.acquire() as conn:
        return await _insert_key(conn, user_id, name)


async def rename_key(pool: asyncpg.Pool, user_id: str, key_id: str, name: str) -> dict | None:
    """Rename a key. Returns updated row or None if key not found / not owned by user."""
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE api_keys SET name = $1 WHERE id = $2 AND user_id = $3",
            name, key_id, user_id,
        )
        row = await conn.fetchrow(
            "SELECT id, name, key, created_at FROM api_keys WHERE id = $1 AND user_id = $2",
            key_id, user_id,
        )
        return dict(row) if row else None


async def delete_key(pool: asyncpg.Pool, user_id: str, key_id: str) -> bool:
    """Delete a key. Returns True if deleted, False if not found / not owned by user.

    Prevents deleting the last key — users must always have at least one.
    """
    async with pool.acquire() as conn:
        count = await conn.fetchval(
            "SELECT COUNT(*) FROM api_keys WHERE user_id = $1", user_id
        )
        if count <= 1:
            raise ValueError("Cannot delete the last API key. Create a new one first.")
        result = await conn.execute(
            "DELETE FROM api_keys WHERE id = $1 AND user_id = $2", key_id, user_id
        )
        return result == "DELETE 1"


# ---------------------------------------------------------------------------
# Usage / rate limit
# ---------------------------------------------------------------------------

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


async def log_usage(pool: asyncpg.Pool, user_id: str, key_id: str) -> None:
    """Record one analysis against this user + key."""
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO usage_logs (id, user_id, key_id) VALUES ($1, $2, $3)",
            str(uuid.uuid4()), user_id, key_id,
        )


async def check_rate_limit(pool: asyncpg.Pool, user_id: str) -> tuple[bool, int]:
    """Return (allowed, used_today). allowed is False when limit is reached."""
    used = await usage_today(pool, user_id)
    return used < RATE_LIMIT, used
