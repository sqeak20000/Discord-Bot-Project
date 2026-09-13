import discord
from discord import app_commands
import aiohttp
import json

from config import ALLOWED_ROLES, ROBLOX_API_KEY, UNIVERSE_ID, ROBLOX_TOPIC_NAME, LOG_CHANNEL_ID
from utils import has_permission


def parse_duration(duration_str: str | None) -> int:
    """Converts a duration string (e.g., '3d', '1w', '4m') into seconds."""
    if not duration_str:
        return -1
    
    unit = duration_str[-1].lower()
    val_str = duration_str[:-1]
    
    try:
        val = int(val_str)
        if unit == 'h':
            return val * 3600
        elif unit == 'd':
            return val * 86400
        elif unit == 'w':
            return val * 604800
        elif unit == 'm':
            return val * 2592000 # Approx 30 days
        else:
            return -1
    except ValueError:
        return -1


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


async def send_roblox_message(action: str, user_id: int, reason: str = "", duration: int = -1, exclude_alts: bool = False):
    """Send a message to the Roblox Open Cloud topic."""
    if not ROBLOX_API_KEY or not UNIVERSE_ID:
        return False, "Roblox integration is not configured. Set ROBLOX_API_KEY and UNIVERSE_ID in your environment."

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
            "duration": duration,
            "exclude_alts": exclude_alts,
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

    @bot.tree.command(name="roblox_ban", description="Ban a user from the Roblox game")
    @app_commands.describe(
        username="The exact Roblox username to ban", 
        reason="The reason shown to the player",
        duration="Optional: e.g. 3d (days), 1w (weeks), 4m (months). Blank = permanent.",
        ban_alts="Ban alternate accounts as well? Defaults to True."
    )
    async def ban_command(interaction: discord.Interaction, username: str, reason: str = "Banned by a moderator.", duration: str = None, ban_alts: bool = True):
        if not has_permission(interaction.user, ALLOWED_ROLES):
            await interaction.response.send_message("❌ You lack permission to use this.", ephemeral=True)
            return

        await interaction.response.defer()

        user_id = await get_user_id(username)
        if not user_id:
            await interaction.followup.send(f"❌ Could not find a Roblox account with the username `{username}`.")
            return

        parsed_duration_seconds = parse_duration(duration)
        duration_display = "Permanent" if not duration or parsed_duration_seconds == -1 else duration
        
        # Roblox API uses ExcludeAltAccounts, which is the inverse of ban_alts
        exclude_alts = not ban_alts 

        success, error = await send_roblox_message("ban", user_id, reason, parsed_duration_seconds, exclude_alts)
        if success:
            await interaction.followup.send(f"🔨 Successfully requested ban for `{username}` (ID: {user_id}). Duration: {duration_display}.")
            
            log_channel = interaction.guild.get_channel(LOG_CHANNEL_ID)
            if log_channel:
                thumbnail_url = await get_user_thumbnail(user_id)
                description = (
                    f"**User:** {username}\n"
                    f"**Moderator:** {interaction.user.name}\n"
                    f"**Reason:** {reason}\n"
                    f"**Duration:** {duration_display}\n"
                    f"**Banned Alts:** {'Yes' if ban_alts else 'No'}\n"
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
            
            log_channel = interaction.guild.get_channel(LOG_CHANNEL_ID)
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