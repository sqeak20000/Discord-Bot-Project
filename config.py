import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Bot configuration
ALLOWED_ROLES = ["Administrator", "Server Mod", "Head Moderator", "Trainee"]
BLACKLIST_ROLE_NAMES = {
    "tickets": "ticket blacklist",
    "code_sharing": "code sharing blacklist",
    "exalted": "exalted blacklist",
    "creations": "creations blacklist",
}
TICKETBLACKLIST_ROLE_NAME = BLACKLIST_ROLE_NAMES["tickets"]
LOG_CHANNEL_ID = 1397806698596405268
FORUM_CHANNEL_ID = 1441865464740581561  # Forum channel ID for restricted commenting
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

# Roblox integration configuration
ROBLOX_API_KEY = os.getenv('ROBLOX_API_KEY')
UNIVERSE_ID = os.getenv('UNIVERSE_ID')
ROBLOX_TOPIC_NAME = os.getenv('ROBLOX_TOPIC_NAME', 'RemoteBan')

# Optional guild-specific sync target. If set, old slash commands in that guild are
# cleared and re-registered against that guild instead of relying on global sync.
DISCORD_GUILD_ID = int(os.getenv('DISCORD_GUILD_ID', 0)) or None
ROBLOX_LOG_CHANNEL_ID = int(os.getenv('ROBLOX_LOG_CHANNEL_ID', 1022159810315173938))


# Automatic role management configuration
# Role combinations that should trigger automatic role assignment
# Format: {'required_roles': ['Role1', 'Role2'], 'target_role': 'NewRole', 'enabled': True}
AUTO_ROLE_COMBINATIONS = [
    {
        'name': 'Verified',  # Friendly name for logging
        'required_roles': ['Rover verified', 'Double Counter verified'],  # User must have BOTH of these roles
        'target_role': 'Verified',  # Role to assign when user has both required roles
        'enabled': True,  # Whether this combination is active
        'remove_on_loss': False,  # Whether to remove target role if user loses a required role
    },
    # You can add more combinations here:
    # {
    #     'name': 'Super Moderator',
    #     'required_roles': ['Server Mod', 'Trusted Member'],
    #     'target_role': 'Super Moderator',
    #     'enabled': False,  # Disabled by default
    #     'remove_on_loss': True,
    # },
]

# Enable/disable automatic role management
ENABLE_AUTO_ROLES = os.getenv('ENABLE_AUTO_ROLES', 'true').lower() == 'true'

# Role management logging
AUTO_ROLE_LOG_CHANNEL_ID = int(os.getenv('AUTO_ROLE_LOG_CHANNEL_ID', LOG_CHANNEL_ID))  # Channel for role change logs

# Role self-service configuration
ROLE_CHECK_COOLDOWN = int(os.getenv('ROLE_CHECK_COOLDOWN', '60'))  # Cooldown in seconds between user role checks
