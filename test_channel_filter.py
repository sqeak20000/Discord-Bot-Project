import asyncio
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import discord

from channel_filter import enforce_file_required_channel


def make_message(channel_id, *, parent_id=None, attachments=None):
    author = Mock(spec=discord.Member)
    author.bot = False
    author.id = 123
    author.timeout = AsyncMock()

    channel = SimpleNamespace(id=channel_id, parent_id=parent_id)
    return SimpleNamespace(
        id=456,
        channel=channel,
        author=author,
        attachments=attachments or [],
        add_reaction=AsyncMock(),
        delete=AsyncMock(),
    )


def test_attachment_message_gets_star_reaction():
    message = make_message(10, attachments=[object()])

    consumed = asyncio.run(enforce_file_required_channel(message, {10}))

    assert consumed is False
    message.add_reaction.assert_awaited_once_with("⭐")
    message.delete.assert_not_awaited()
    message.author.timeout.assert_not_awaited()


def test_message_without_attachment_is_deleted_and_timed_out():
    message = make_message(10)

    consumed = asyncio.run(enforce_file_required_channel(message, {10}))

    assert consumed is True
    message.delete.assert_awaited_once()
    message.author.timeout.assert_awaited_once_with(
        timedelta(minutes=2),
        reason="Posted in a file-required channel without an attachment",
    )


def test_configured_forum_channel_applies_to_its_threads():
    message = make_message(20, parent_id=10)

    consumed = asyncio.run(enforce_file_required_channel(message, {10}))

    assert consumed is True
    message.delete.assert_awaited_once()
    message.author.timeout.assert_awaited_once()


def test_unconfigured_channel_is_unchanged():
    message = make_message(20)

    consumed = asyncio.run(enforce_file_required_channel(message, {10}))

    assert consumed is False
    message.delete.assert_not_awaited()
    message.add_reaction.assert_not_awaited()
    message.author.timeout.assert_not_awaited()
