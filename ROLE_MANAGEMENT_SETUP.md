# Discord Bot Configuration - Role Management Setup Guide

## Environment Variables (.env file)

# Basic Bot Configuration
DISCORD_BOT_TOKEN=your_discord_bot_token_here

# Role Management Configuration
ENABLE_AUTO_ROLES=true
AUTO_ROLE_LOG_CHANNEL_ID=your_log_channel_id_here

# Cross-posting Configuration (existing)
DISCORD_UPDATES_CHANNEL_ID=your_discord_updates_channel_id
GUILDED_BOT_TOKEN=your_guilded_bot_token
GUILDED_SERVER_ID=your_guilded_server_id
GUILDED_ANNOUNCEMENTS_CHANNEL_ID=your_guilded_announcements_channel_id

# Roblox Integration (existing)
ROBLOX_COOKIE=your_roblox_cookie
ROBLOX_GROUP_ID=your_roblox_group_id

## Role Management Configuration

The role management system is configured in `config.py` through the `AUTO_ROLE_COMBINATIONS` list.

### Example Configuration:

```python
AUTO_ROLE_COMBINATIONS = [
    {
        'name': 'VIP Member',                    # Friendly name for logging
        'required_roles': ['Premium Subscriber', 'Active Member'],  # User must have BOTH roles
        'target_role': 'VIP Member',             # Role to assign automatically
        'enabled': True,                         # Whether this combination is active
        'remove_on_loss': True,                  # Remove target role if user loses required role
    },
    {
        'name': 'Super Moderator',
        'required_roles': ['Server Mod', 'Trusted Member'],
        'target_role': 'Super Moderator',
        'enabled': False,                        # Disabled by default
        'remove_on_loss': True,
    },
]
```

### How it works:
1. When a user gets a role update, the bot checks their new roles
2. If they have ALL required roles from a combination, they get the target role
3. If they lose a required role and `remove_on_loss` is True, the target role is removed
4. All changes are logged to the configured log channel

### Bot Permissions Required:
- **Members Intent**: Required to receive member update events
- **Manage Roles**: Required to add/remove roles automatically
- **View Channels & Send Messages**: For logging role changes

### Commands Available:
- `!checkroles` - Manually check all members for role combinations (Admin only)
- `!listrolecombo` - Show current role combination configuration (Admin only)
- `!debugguilded` - Debug Guilded API connection
- `!testcrosspost` - Test cross-posting functionality

### Setup Steps:
1. Update your `.env` file with the new environment variables
2. Modify `AUTO_ROLE_COMBINATIONS` in `config.py` to match your server's roles
3. Ensure the bot has "Manage Roles" permission and the bot's role is above the roles it needs to manage
4. Restart the bot
5. Use `!checkroles` to apply role combinations to existing members
6. Test with `!listrolecombo` to verify configuration

### Example Use Cases:
- **VIP System**: Users with "Nitro Booster" + "Active Member" automatically get "VIP Access"
- **Staff Progression**: "Junior Mod" + "Training Complete" → "Full Moderator"  
- **Special Access**: "Verified" + "Contributor" → "Beta Tester"
- **Loyalty Rewards**: "Long-time Member" + "Regular Participant" → "Veteran"

### Notes:
- Role names are case-sensitive and must match exactly
- The bot's role must be higher than the roles it manages
- Changes are applied instantly when users gain/lose roles
- All automatic role changes are logged for transparency
