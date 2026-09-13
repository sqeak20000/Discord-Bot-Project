"""Example of how to add a custom Discord command to this bot.

Enable it by importing this module in commands/__init__.py and calling
setup_custom_example_command(bot) inside register_all_commands().
"""

import discord
from discord import app_commands

from config import ALLOWED_ROLES
from utils import has_permission


async def setup_custom_example_command(bot):
    """Example slash command that greets a user."""

    @bot.tree.command(name="hello", description="Say hello to the bot")
    @app_commands.describe(name="The name to greet")
    async def hello_command(interaction: discord.Interaction, name: str = "friend"):
        if not has_permission(interaction.user, ALLOWED_ROLES):
            await interaction.response.send_message(
                "❌ You do not have permission to use this command.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(f"Hello, {name}! 👋")
