"""Enforce attachment requirements in configured Discord channels."""

import logging
from datetime import timedelta

import discord


async def enforce_file_required_channel(message, channel_ids):
    """React to file posts and remove/timeout attachment-free posts."""
    if not channel_ids:
        return False

    channel_id = message.channel.id
    parent_id = getattr(message.channel, "parent_id", None)
    if channel_id not in channel_ids and parent_id not in channel_ids:
        return False

    if message.author.bot:
        return False

    if message.attachments:
        try:
            await message.add_reaction("⭐")
        except discord.HTTPException:
            logging.exception(
                "Failed to add star reaction to message %s in channel %s",
                message.id,
                channel_id,
            )
        return False

    try:
        await message.delete()
    except discord.HTTPException:
        logging.exception(
            "Failed to delete attachment-free message %s in channel %s",
            message.id,
            channel_id,
        )

    if not isinstance(message.author, discord.Member):
        logging.error(
            "Cannot timeout author of attachment-free message %s: "
            "author is not a guild member",
            message.id,
        )
        return True

    try:
        await message.author.timeout(
            timedelta(minutes=2),
            reason="Posted in a file-required channel without an attachment",
        )
    except discord.HTTPException:
        logging.exception(
            "Failed to timeout author %s of message %s for 2 minutes",
            message.author.id,
            message.id,
        )

    return True
