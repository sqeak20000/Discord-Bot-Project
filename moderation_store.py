"""SQLite storage and one-time import for moderation log entries."""

import json
import re
import sqlite3
from datetime import datetime, timezone

from config import MODERATION_DB_PATH

_MENTION_RE = re.compile(r"<@!?(\d+)>")
_EVIDENCE_RE = re.compile(r"\]\((https?://[^)\s]+)\)")


def _connect():
    MODERATION_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(MODERATION_DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("""
        CREATE TABLE IF NOT EXISTS moderation_actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_key TEXT NOT NULL UNIQUE,
            guild_id INTEGER,
            target_id INTEGER NOT NULL,
            target_name TEXT NOT NULL,
            moderator_id INTEGER,
            moderator_name TEXT NOT NULL,
            action_type TEXT NOT NULL,
            reason TEXT NOT NULL,
            duration TEXT,
            evidence_json TEXT NOT NULL,
            occurred_at TEXT NOT NULL,
            action_id TEXT,
            source TEXT NOT NULL
        )
    """)
    connection.execute("""
        CREATE INDEX IF NOT EXISTS idx_moderation_actions_target
        ON moderation_actions (guild_id, target_id, occurred_at DESC)
    """)
    connection.execute("""
        CREATE TABLE IF NOT EXISTS moderation_metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)
    return connection


def record_action(
    *,
    entry_key,
    guild_id,
    target_id,
    target_name,
    moderator_id,
    moderator_name,
    action_type,
    reason,
    duration,
    evidence,
    occurred_at,
    action_id=None,
    source="live",
):
    with _connect() as connection:
        connection.execute(
            """
            INSERT OR IGNORE INTO moderation_actions (
                entry_key, guild_id, target_id, target_name, moderator_id,
                moderator_name, action_type, reason, duration, evidence_json,
                occurred_at, action_id, source
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entry_key,
                guild_id,
                target_id,
                target_name,
                moderator_id,
                moderator_name,
                action_type,
                reason or "",
                duration,
                json.dumps(evidence or []),
                occurred_at.isoformat() if isinstance(occurred_at, datetime) else occurred_at,
                action_id,
                source,
            ),
        )
        return connection.execute("SELECT changes()").fetchone()[0] == 1


def find_actions(guild_id, target_id, limit=10):
    with _connect() as connection:
        return connection.execute(
            """
            SELECT action_type, reason, duration, occurred_at, moderator_name
            FROM moderation_actions
            WHERE guild_id = ? AND target_id = ?
            ORDER BY occurred_at DESC, id DESC
            LIMIT ?
            """,
            (guild_id, target_id, limit),
        ).fetchall()


def history_was_indexed(guild_id):
    with _connect() as connection:
        row = connection.execute(
            "SELECT value FROM moderation_metadata WHERE key = ?",
            (f"history_indexed:{guild_id}",),
        ).fetchone()
        return row["value"] if row else None


def index_log_embed(embed, guild_id, log_message_id):
    """Import one moderation embed; return whether a new record was inserted."""
    title = embed.title or ""
    prefix = "🔨 Moderation Action: "
    if not title.startswith(prefix):
        return False

    fields = {field.name.strip().casefold(): field.value for field in embed.fields}

    def field_value(terms):
        for name, value in fields.items():
            if any(term in name for term in terms):
                return value
        return ""

    target_field = field_value(("target user",))
    moderator_field = field_value(("moderator",))
    target_match = _MENTION_RE.search(target_field)
    moderator_match = _MENTION_RE.search(moderator_field)
    if target_match is None:
        return False

    footer = embed.footer.text if embed.footer else ""
    action_id = footer.removeprefix("Action ID: ").strip() or None
    evidence_field = field_value(("evidence",))
    evidence = _EVIDENCE_RE.findall(evidence_field)
    occurred_at = embed.timestamp or datetime.now(timezone.utc)

    return record_action(
        entry_key=f"discord-log:{guild_id}:{log_message_id}",
        guild_id=guild_id,
        target_id=int(target_match.group(1)),
        target_name=target_field,
        moderator_id=int(moderator_match.group(1)) if moderator_match else None,
        moderator_name=moderator_field,
        action_type=title[len(prefix):].strip(),
        reason=field_value(("reason",)),
        duration=field_value(("duration",)) or None,
        evidence=evidence,
        occurred_at=occurred_at,
        action_id=action_id,
        source="backfill",
    )


def finish_history_index(guild_id, completed_at):
    with _connect() as connection:
        connection.execute(
            """
            INSERT INTO moderation_metadata (key, value)
            VALUES (?, ?)
            """,
            (f"history_indexed:{guild_id}", completed_at.isoformat()),
        )
