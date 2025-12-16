import discord
import aiohttp
import json
import logging
from discord import app_commands
from config import ROBLOX_API_KEY, UNIVERSE_ID, ROBLOX_TOPIC_NAME, ALLOWED_ROLES

# --- Helper Function: Convert Username to ID ---
async def get_id_from_username(username: str):
    """
    Queries Roblox API to convert a username into a User ID.
    Returns: (id, error_message)
    """
    url = "https://users.roblox.com/v1/usernames/users"
    payload = {
        "usernames": [username],
        "excludeBannedUsers": True
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as response:
            if response.status != 200:
                return None, f"Roblox Users API failed (Status: {response.status})"
            
            data = await response.json()
            
            # Check if any user was found
            if not data.get("data") or len(data["data"]) == 0:
                return None, f"User '{username}' not found on Roblox."
            
            # Return the ID of the first match
            return data["data"][0]["id"], None

async def send_ban_request(user_id: int, reason: str, duration: int):
    """Sends the ban payload to Roblox Open Cloud"""
    url = f"https://apis.roblox.com/messaging-service/v1/universes/{UNIVERSE_ID}/topics/{ROBLOX_TOPIC_NAME}/publish"
    
    headers = {
        "x-api-key": ROBLOX_API_KEY,
        "Content-Type": "application/json"
    }
    
    # Payload must be a stringified JSON inside the 'message' field
    message_data = {
        "UserId": user_id,
        "Reason": reason,
        "Duration": duration
    }
    
    payload = {
        "message": json.dumps(message_data)
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=payload) as response:
            if response.status == 200:
                return True, "Request sent successfully."
            else:
                # Try to get error text, but fail gracefully if response is empty
                try:
                    error_text = await response.text()
                except:
                    error_text = "Unknown error"
                return False, f"API Error {response.status}: {error_text}"

async def setup_roblox_ban_command(bot):
    """Registers the /robloxban slash command"""
    
    @bot.tree.command(name="robloxban", description="Ban a user from Roblox (supports Username or ID)")
    @app_commands.describe(
        username_or_id="Roblox Username OR User ID", 
        reason="Reason for the ban (shown to user)", 
        duration="Duration in seconds (-1 for permanent)"
    )
    async def roblox_ban(interaction: discord.Interaction, username_or_id: str, reason: str, duration: int = -1):
        # 1. Permission Check
        if not any(role.name in ALLOWED_ROLES for role in interaction.user.roles):
            await interaction.response.send_message("❌ You do not have permission to use this command.", ephemeral=True)
            return

        # 2. Defer response immediately
        await interaction.response.defer()

        # 3. Determine if input is ID or Username
        target_id = None
        target_name = username_or_id

        # If the input is purely digits, assume it's an ID
        if username_or_id.isdigit():
            target_id = int(username_or_id)
            # Optional: You could fetch the username for this ID to make the success message prettier,
            # but for now we will just use the ID.
        else:
            # Input is a username, resolve it
            found_id, error = await get_id_from_username(username_or_id)
            if not found_id:
                await interaction.followup.send(f"❌ **Error:** {error}")
                return
            target_id = found_id

        # 4. Send Request to Roblox
        logging.info(f"Sending Roblox ban request for ID {target_id} ({target_name}) by {interaction.user}")
        success, message = await send_ban_request(target_id, reason, duration)

        # 5. Respond to Discord
        if success:
            embed = discord.Embed(title="✅ Roblox Ban Initiated", color=discord.Color.green())
            embed.add_field(name="Target User", value=f"{target_name} (ID: {target_id})", inline=False)
            embed.add_field(name="Duration", value="Permanent" if duration == -1 else f"{duration}s", inline=True)
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.set_footer(text=f"Admin: {interaction.user.display_name}")
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send(f"❌ **Failed:** {message}")