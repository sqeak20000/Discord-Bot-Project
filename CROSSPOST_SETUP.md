# Discord to Guilded Cross-Posting Setup Guide

This guide will help you set up automatic cross-posting from a Discord updates channel to a Roblox Guilded server announcements channel.

## 🔧 Prerequisites

1. **Discord Bot** - Your existing Discord bot (already configured)
2. **Guilded Bot** - You'll need to create a bot on Guilded
3. **Channel IDs** - Discord updates channel and Guilded announcements channel

## 📋 Step-by-Step Setup

### 1. Create a Guilded Bot

1. Go to [Guilded Developer Portal](https://www.guilded.gg/developers/applications)
2. Click "Create Application"
3. Fill in your bot's name and description
4. Go to the "Bot" section
5. Copy the **Bot Token** (you'll need this for your .env file)

### 2. Add Bot to Your Guilded Server

1. In the Guilded Developer Portal, go to your bot's page
2. Go to "OAuth2" → "URL Generator"
3. Select the scopes and permissions your bot needs:
   - `bot` scope
   - `Send Messages` permission
   - `Manage Messages` permission (optional, for better functionality)
4. Copy the generated URL and visit it
5. Select your Guilded server and authorize the bot

### 3. Get Required IDs

#### Discord Updates Channel ID:
1. Enable Developer Mode in Discord (User Settings → Advanced → Developer Mode)
2. Right-click on your updates channel → "Copy ID"

#### Guilded Server ID:
1. In Guilded, right-click on your server name → "Copy Server ID"

#### Guilded Announcements Channel ID:
1. In Guilded, right-click on your announcements channel → "Copy Channel ID"

### 4. Update Environment Variables

Add these to your `.env` file:

```env
# Existing Discord bot token
DISCORD_BOT_TOKEN=your_discord_bot_token_here

# New cross-posting configuration
DISCORD_UPDATES_CHANNEL_ID=your_discord_channel_id_here
GUILDED_BOT_TOKEN=your_guilded_bot_token_here
GUILDED_SERVER_ID=your_guilded_server_id_here
GUILDED_ANNOUNCEMENTS_CHANNEL_ID=your_guilded_channel_id_here
```

### 5. Install Dependencies

```bash
pip install -r requirements.txt
```

### 6. Test the Setup

1. Start your bot: `python Main.py`
2. In any Discord channel (as a moderator), run: `!testcrosspost`
3. Check your Guilded announcements channel for the test message

## 🎯 How It Works

### Automatic Cross-Posting
- **Monitors:** Your specified Discord updates channel
- **Action:** When a message is posted in that channel, it automatically cross-posts to Guilded
- **Format:** Includes author attribution, content, embeds, and attachment links
- **Feedback:** Adds ✅ reaction to successfully cross-posted messages

### Manual Testing
- **Command:** `!testcrosspost` (moderators only)
- **Purpose:** Test that cross-posting is working correctly
- **Output:** Sends a test message to Guilded and confirms success/failure

## 📱 Message Format

When a Discord message is cross-posted to Guilded, it includes:

```
📢 Update from Discord (by Username)

[Original message content]

📎 Attachments:
1. [filename.png](attachment_url)
2. [document.pdf](attachment_url)
```

## 🚨 Troubleshooting

### Cross-posting not working?
1. Check that ALL environment variables are set in your `.env` file
2. Verify your Guilded bot has permissions to send messages in the announcements channel
3. Use `!testcrosspost` to test the connection
4. Check bot logs for error messages

### Bot can't react to messages?
- Ensure your Discord bot has "Add Reactions" permission in the updates channel

### Environment variables not loading?
- Make sure your `.env` file is in the same directory as `Main.py`
- Restart the bot after making changes to `.env`

## 🔒 Security Notes

- Keep your bot tokens secure and never share them
- Use environment variables (`.env` file) for sensitive information
- Add `.env` to your `.gitignore` file if using version control

## ✨ Features

- ✅ Automatic cross-posting from Discord to Guilded
- ✅ Preserves message formatting and embeds
- ✅ Handles attachments (converts to links)
- ✅ Author attribution
- ✅ Visual feedback with reactions
- ✅ Test command for verification
- ✅ Graceful error handling
- ✅ Automatic disable if configuration is incomplete
