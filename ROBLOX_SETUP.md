# Roblox Integration Setup Guide

This guide explains how to set up Roblox group posting functionality for your Discord bot.

## Prerequisites

1. A Roblox account with permissions to post in your target group
2. The Roblox group ID where you want to post messages
3. Your bot already configured with Discord and Guilded integration

## Step 1: Get Your Roblox Cookie

1. **Login to Roblox** in your web browser
2. **Open Developer Tools** (F12 or right-click → Inspect)
3. **Go to the Application/Storage tab**
4. **Find Cookies** and locate the `.ROBLOSECURITY` cookie
5. **Copy the cookie value** (it's a long string starting with `_|WARNING:-DO-NOT...`)

⚠️ **Important Security Notes:**
- Never share your `.ROBLOSECURITY` cookie with anyone
- This cookie gives full access to your Roblox account
- Consider using a dedicated bot account for posting

## Step 2: Find Your Group ID

1. **Go to your Roblox group page**
2. **Look at the URL** - it will be something like: `https://www.roblox.com/groups/12345678/GroupName`
3. **The group ID is the number** in the URL (12345678 in this example)

## Step 3: Configure Environment Variables

Add these variables to your `.env` file:

```env
# Roblox Integration
ROBLOX_COOKIE=_|WARNING:-DO-NOT-SHARE-THIS.--Cookies-are-browser-data...
ROBLOX_GROUP_ID=12345678
```

**Note:** The bot will automatically enable Roblox posting if both variables are present.

## Step 4: Restart Your Bot

After adding the environment variables, restart your bot to load the new configuration.

## Testing the Integration

Use these debug commands in Discord to test your setup:

### `!debugroblox`
- Tests authentication with your Roblox account
- Verifies group access permissions
- Checks CSRF token status
- Shows user and group information

### `!testroblox`
- Sends a test message to your Roblox group
- Tries group shout first (more visible)
- Falls back to wall post if shout fails
- Shows success/failure status

## How It Works

When a message is posted in your configured Discord updates channel:

1. **Message Processing:** The bot formats the Discord message for Roblox
2. **Group Shout:** First attempts to post as a group shout (more visible)
3. **Wall Post Fallback:** If shout fails, tries posting to the group wall
4. **Status Reactions:** Adds different emoji reactions based on success:
   - 🎯 Both Discord → Guilded and Roblox successful
   - 🟢 Only Guilded successful
   - 🔶 Only Roblox successful
   - ❌ Both failed

## Message Formatting

The bot automatically:
- Removes Discord-specific formatting (`**bold**`, `*italic*`, etc.)
- Strips out Discord mentions and emojis
- Truncates messages to Roblox limits (255 chars for shouts, 500 for wall posts)
- Adds author attribution
- Includes title if detected from the message

## Troubleshooting

### "Authentication Failed"
- Check that your `.ROBLOSECURITY` cookie is correct and not expired
- Make sure you're logged into the correct Roblox account
- Try logging out and back into Roblox, then get a fresh cookie

### "Group Access Failed"
- Verify the group ID is correct
- Ensure your account has permission to post in the group
- Check that the group exists and is not private

### "CSRF Token Missing"
- This usually resolves automatically on the first API call
- If persistent, try restarting the bot

### "Failed to post to Roblox"
- Your account might not have posting permissions in the group
- The group might have posting restrictions
- Rate limiting - Roblox has strict rate limits for posting

## Rate Limiting

Roblox has strict rate limits:
- **Group Shouts:** Very limited (few per day)
- **Wall Posts:** More frequent but still limited
- The bot automatically handles rate limit errors

## Security Best Practices

1. **Use a dedicated bot account** for Roblox posting
2. **Regularly rotate your cookie** (every few months)
3. **Monitor for unauthorized access** to your Roblox account
4. **Keep your `.env` file secure** and never commit it to version control
5. **Use environment variables** in production, not hardcoded values

## Group Permissions Required

Your Roblox account needs these permissions in the target group:
- **Post to group wall** (for wall posts)
- **Manage group** (for group shouts)

Note: Group shouts typically require higher permissions than wall posts.

## Example Messages

**Original Discord Message:**
```
**🎉 New Update Available!**

We've just released version 2.0 with exciting new features:
- Enhanced performance
- New user interface
- Bug fixes

Check it out now! 🚀
```

**Formatted for Roblox:**
```
New Update Available!

Posted by ModeratorName

We've just released version 2.0 with exciting new features:
- Enhanced performance
- New user interface  
- Bug fixes

Check it out now!
```

## Error Codes

Common Roblox API error responses:
- `401` - Authentication failed (bad cookie)
- `403` - No permission to post
- `429` - Rate limited
- `400` - Invalid request data

The bot automatically logs detailed error information for debugging.
