"""Roblox command registration."""


async def setup_registered_roblox_commands(bot):
    """Register Roblox-related slash commands."""
    from robloxBan import setup_roblox_ban_command

    await setup_roblox_ban_command(bot)
