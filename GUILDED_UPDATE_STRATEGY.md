# Guilded Announcement Update Strategy

## The Problem with Roblox Syncing

When the Discord bot creates new announcements in Guilded, they don't automatically sync to linked Roblox groups because:

1. **Bot Account Limitations**: The bot account may not have proper Roblox linking permissions
2. **Sync Requirements**: Roblox syncing typically requires the announcement to be created by a developer/admin account
3. **Platform Integration**: Discord bots are treated differently than human users for cross-platform features

## The Solution: Update Existing Announcements

Instead of always creating new announcements, the bot can now **update existing announcements** that were created by developer accounts. This approach:

✅ **Inherits Permissions** - Updates to developer-created announcements maintain their Roblox sync capabilities  
✅ **Preserves Links** - Existing Roblox connections are maintained  
✅ **Better Integration** - Works within Guilded's permission system rather than against it  

## How It Works

### 1. **Update Strategy (Default)**
- Bot finds the most recent announcement in the channel
- Updates its content with the new Discord message
- Adds a timestamp to show when it was updated
- Preserves the original creator's permissions and integrations

### 2. **Fallback to New Post**
- If updating fails, bot creates a new announcement as before
- Configurable - can be disabled to only use update strategy

### 3. **Smart Content Formatting**
- Adds "Updated: YYYY-MM-DD HH:MM" timestamp
- Preserves original title structure
- Includes author attribution from Discord

## Configuration Options

Add these to your `.env` file to control the behavior:

```env
# Try to update existing announcements first (recommended for Roblox sync)
GUILDED_UPDATE_EXISTING=true

# If update fails, create new announcement as fallback
GUILDED_FALLBACK_TO_NEW=true
```

### Configuration Scenarios

| Update Existing | Fallback to New | Behavior |
|-----------------|----------------|----------|
| `true` | `true` | Try update first, create new if fails (**Default**) |
| `true` | `false` | Only update existing, fail if no update possible |
| `false` | `true` | Always create new announcements (old behavior) |
| `false` | `false` | Invalid - will default to true/true |

## New Debug Commands

### `!listannouncements`
Shows the 5 most recent announcements in the Guilded channel:
- Announcement ID
- Title 
- Creation date
- Creator

Use this to see which announcements are available for updating.

### `!testupdate`
Tests the announcement update functionality:
- Finds the latest announcement
- Updates it with test content
- Shows success/failure status

Use this to verify the update mechanism works before relying on it.

## Best Practices

### Initial Setup
1. **Create a "Template" Announcement**: Have a developer create an initial announcement
2. **Test with `!testupdate`**: Verify the bot can update it successfully
3. **Monitor Roblox Sync**: Check if updates sync to Roblox as expected

### Ongoing Use
1. **Let Bot Update**: Allow bot to update the template announcement
2. **Check Sync Status**: Monitor if Roblox receives the updates
3. **Fallback if Needed**: If sync breaks, create new announcement manually

### Troubleshooting
- **"No announcements found"**: Create at least one announcement manually first
- **"Update failed"**: Bot may lack edit permissions - check bot role permissions
- **"Roblox not syncing"**: Original announcement may not have been created by linked account

## Workflow Example

### Traditional Approach (May Not Sync)
```
Discord Message → Bot Creates New Guilded Announcement → ❌ No Roblox Sync
```

### New Update Approach (Better Sync Chance)
```
Developer Creates Initial Announcement → Bot Updates Existing Announcement → ✅ Roblox Sync Maintained
```

## Technical Implementation

The bot now:

1. **Checks for existing announcements** using Guilded API
2. **Attempts to update the latest one** with new content
3. **Falls back to creating new** if update fails (configurable)
4. **Logs detailed status** for monitoring and debugging

This provides a much better chance of maintaining Roblox integration while keeping the automated Discord-to-Guilded posting functionality.

## Migration from Old Behavior

If you're currently using the bot with the old behavior:

1. **Update your bot** to the latest version
2. **Add the new environment variables** (they default to the new behavior)
3. **Create an initial announcement** manually if none exist
4. **Test with `!testupdate`** to verify functionality
5. **Monitor the next few Discord updates** to ensure Roblox syncing works

The new system is backward compatible and will gracefully fall back to the old behavior if needed.
