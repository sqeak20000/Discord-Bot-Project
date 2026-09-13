import discord
from discord import app_commands
import aiohttp
import json

# Ensure these are defined in your config.py
from config import ALLOWED_ROLES, ROBLOX_API_KEY, UNIVERSE_ID, ROBLOX_TOPIC_NAME, ROBLOX_LOG_CHANNEL_ID
from utils import has_permission


async def get_user_id(username: str) -> int | None:
    """Convert a Roblox username to a UserId using the Roblox API."""
    url = "https://users.roblox.com/v1/usernames/users"
    payload = {"usernames": [username], "excludeBannedUsers": False}

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as response:
            if response.status == 200:
                data = await response.json()
                if data.get("data") and len(data["data"]) > 0:
                    return data["data"][0]["id"]
    return None


async def get_user_thumbnail(user_id: int) -> str:
    """Fetches the player's avatar headshot thumbnail URL."""
    url = f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={user_id}&size=150x150&format=Png&isCircular=false"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                if data.get("data") and len(data["data"]) > 0:
                    return data["data"][0]["imageUrl"]
    return ""


async def send_roblox_message(action: str, user_id: int, reason: str = ""):
    """Send a message to the Roblox Open Cloud topic."""
    if not ROBLOX_API_KEY or not UNIVERSE_ID:
        return False, "Roblox integration is not configured. Set ROBLOX_API_KEY and UNIVERSE_ID in your config."

    url = f"https://apis.roblox.com/messaging-service/v1/universes/{UNIVERSE_ID}/topics/{ROBLOX_TOPIC_NAME}"
    headers = {
        "x-api-key": ROBLOX_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "message": json.dumps({
            "action": action,
            "userId": user_id,
            "reason": reason,
        })
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=payload) as response:
            if response.status == 200:
                return True, None

            error_msg = await response.text()
            return False, f"HTTP {response.status}: {error_msg}"


async def setup_remote_ban_command(bot):
    """Register /roblox_ban and /roblox_unban commands."""

    @bot.tree.command(name="roblox_ban", description="Permanently ban a user from the Roblox game")
    @app_commands.describe(username="The exact Roblox username to ban", reason="The reason shown to the player")
    async def ban_command(interaction: discord.Interaction, username: str, reason: str = "Banned by a moderator."):
        if not has_permission(interaction.user, ALLOWED_ROLES):
            await interaction.response.send_message("❌ You lack permission to use this.", ephemeral=True)
            return

        await interaction.response.defer()

        user_id = await get_user_id(username)
        if not user_id:
            await interaction.followup.send(f"❌ Could not find a Roblox account with the username `{username}`.")
            return

        success, error = await send_roblox_message("ban", user_id, reason)
        if success:
            await interaction.followup.send(f"🔨 Successfully requested ban for `{username}` (ID: {user_id}).")
            
            # Logging to Discord
            log_channel = interaction.guild.get_channel(ROBLOX_LOG_CHANNEL_ID)
            if log_channel:
                thumbnail_url = await get_user_thumbnail(user_id)
                description = (
                    f"**User:** {username}\n"
                    f"**Moderator:** {interaction.user.name}\n"
                    f"**Reason:** {reason}\n"
                    f"**Duration:** Permanent\n"
                    f"https://www.roblox.com/users/{user_id}/profile"
                )
                embed = discord.Embed(title="User Banned", description=description, color=discord.Color.dark_theme())
                if thumbnail_url:
                    embed.set_thumbnail(url=thumbnail_url)
                await log_channel.send(embed=embed)
        else:
            await interaction.followup.send(f"❌ Failed to send ban to Roblox: {error}")

    @bot.tree.command(name="roblox_unban", description="Unban a user from the Roblox game")
    @app_commands.describe(username="The exact Roblox username to unban")
    async def unban_command(interaction: discord.Interaction, username: str):
        if not has_permission(interaction.user, ALLOWED_ROLES):
            await interaction.response.send_message("❌ You lack permission to use this.", ephemeral=True)
            return

        await interaction.response.defer()

        user_id = await get_user_id(username)
        if not user_id:
            await interaction.followup.send(f"❌ Could not find a Roblox account with the username `{username}`.")
            return

        success, error = await send_roblox_message("unban", user_id)
        if success:
            await interaction.followup.send(f"✅ Successfully requested unban for `{username}` (ID: {user_id}).")
            
            # Logging to Discord
            log_channel = interaction.guild.get_channel(ROBLOX_LOG_CHANNEL_ID)
            if log_channel:
                thumbnail_url = await get_user_thumbnail(user_id)
                description = (
                    f"**User:** {username}\n"
                    f"**Moderator:** {interaction.user.name}\n"
                    f"https://www.roblox.com/users/{user_id}/profile"
                )
                embed = discord.Embed(title="User Unbanned", description=description, color=discord.Color.green())
                if thumbnail_url:
                    embed.set_thumbnail(url=thumbnail_url)
                await log_channel.send(embed=embed)
        else:
            await interaction.followup.send(f"❌ Failed to send unban to Roblox: {error}")