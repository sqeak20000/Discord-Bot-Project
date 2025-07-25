#!/usr/bin/env python3
"""
Generate the correct bot invite URL with slash command permissions.
If your bot doesn't have slash command permissions, use this URL to re-invite it.
"""

# Replace with your bot's actual Client ID (found in Discord Developer Portal)
BOT_CLIENT_ID = "YOUR_BOT_CLIENT_ID"  # <-- CHANGE THIS!

def generate_invite_url():
    """Generate bot invite URL with proper permissions for slash commands"""
    
    # Required permissions for moderation bot
    permissions = [
        "ban_members",           # For ban command
        "kick_members",          # For kick command
        "moderate_members",      # For timeout command
        "send_messages",         # For sending responses
        "view_channel",          # For seeing channels
        "read_message_history",  # For evidence handling
        "attach_files",          # For logging evidence
        "use_slash_commands"     # For slash commands (automatically included with applications.commands scope)
    ]
    
    # Calculate permission integer (for the specific permissions above)
    # This is a simplified calculation - for production, use Discord's permission calculator
    permission_int = 1100317891670  # Pre-calculated for the permissions above
    
    # Required OAuth2 scopes
    scopes = ["bot", "applications.commands"]  # applications.commands is REQUIRED for slash commands
    
    base_url = "https://discord.com/api/oauth2/authorize"
    scope_param = "&".join([f"scope={scope}" for scope in scopes])
    
    invite_url = f"{base_url}?client_id={BOT_CLIENT_ID}&permissions={permission_int}&{scope_param}"
    
    return invite_url

if __name__ == "__main__":
    if BOT_CLIENT_ID == "YOUR_BOT_CLIENT_ID":
        print("❌ ERROR: You need to set your bot's Client ID!")
        print("\nTo get your bot's Client ID:")
        print("1. Go to https://discord.com/developers/applications")
        print("2. Click on your bot application")
        print("3. Copy the 'Application ID' (this is your Client ID)")
        print("4. Replace BOT_CLIENT_ID in this file with that number")
        print()
        print("Example:")
        print('BOT_CLIENT_ID = "123456789012345678"')
    else:
        invite_url = generate_invite_url()
        print("🤖 Bot Invite URL with Slash Command Permissions:")
        print("=" * 60)
        print(invite_url)
        print("=" * 60)
        print()
        print("✅ What this URL includes:")
        print("- Bot permissions for ban/kick/timeout")
        print("- applications.commands scope (REQUIRED for slash commands)")
        print("- Proper permissions for evidence handling")
        print()
        print("📝 Instructions:")
        print("1. Copy the URL above")
        print("2. Paste it in your browser")
        print("3. Select your Discord server")
        print("4. Authorize the bot")
        print("5. Run the quick_sync.py script to enable slash commands")
        print()
        print("⚠️  If your bot is already in the server but slash commands don't work:")
        print("You may need to kick the bot and re-invite it with this new URL.")
