import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Bot configuration
ALLOWED_ROLES = ["Administrator", "Server Mod", "Head Moderator", "Trainee"]
TICKETBLACKLIST_ROLE_NAME = "ticket blacklist"  # Role name for ticket blacklist
LOG_CHANNEL_ID = 1397806698596405268
COMMAND_TIMEOUT = 30.0
MESSAGE_DELETE_DELAY = 5

# Rate limiting configuration
RATE_LIMIT_DELAY = 2  # seconds between API calls when rate limited
RATE_LIMIT_RETRY_DELAY = 5  # seconds to wait before retrying after rate limit
ATTACHMENT_SEND_DELAY = 1  # seconds between sending multiple attachments

# Bot token from environment variable
BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("DISCORD_BOT_TOKEN environment variable is not set")
