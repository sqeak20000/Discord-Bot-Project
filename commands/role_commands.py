"""Role management command registration."""


async def setup_registered_role_commands(bot):
    """Register automation and role-management commands."""
    from role_manager import setup_role_management

    await setup_role_management(bot)
