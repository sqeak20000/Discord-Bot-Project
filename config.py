import os

# Bot configuration
ALLOWED_ROLES = ["Administrator", "Server Mod", "Head Moderator", "Trainee"]
LOG_CHANNEL_ID = 1397806698596405268
COMMAND_TIMEOUT = 30.0
MESSAGE_DELETE_DELAY = 5

# Bot token from environment variable
BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("DISCORD_BOT_TOKEN environment variable is not set")
