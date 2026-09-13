"""Command registration helpers for the bot."""


async def register_all_commands(bot):
    """Register all command groups once for the current bot instance."""
    if getattr(bot, "_commands_registered", False):
        return

    from .moderation_commands import setup_registered_moderation_commands
    from .role_commands import setup_registered_role_commands
    from .roblox_commands import setup_registered_roblox_commands
    from .remote_ban import setup_remote_ban_command

    await setup_registered_moderation_commands(bot)
    await setup_registered_role_commands(bot)
    await setup_registered_roblox_commands(bot)
    await setup_remote_ban_command(bot)

    bot._commands_registered = True
