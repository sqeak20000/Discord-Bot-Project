# Self-Service Role Check System 

## Overview

The bot now includes a **self-service role check button** that allows users to manually verify and update their roles without needing moderator intervention. This is perfect for situations where:

- The bot was offline when someone got new roles
- Automatic role assignment failed or was delayed
- Users want to verify they have all the roles they should have
- New members want to check if they qualify for additional roles

## 🎯 How It Works

### For Users
1. **Find the Role Panel**: Look for a message with the "🔄 Check My Roles" button
2. **Click the Button**: Press the button to start a role check
3. **Get Instant Results**: The bot checks your roles and assigns any you're missing
4. **Private Response**: All results are sent as private messages (only you can see them)
5. **Cooldown Protection**: 60-second cooldown prevents spam and keeps the bot responsive

### For Administrators
1. **Send a Panel**: Use `/rolepanel` or `!rolepanel` to send a role check panel to any channel
2. **Persistent Button**: The button stays active permanently - no need to resend
3. **Monitor Logs**: All automatic role changes are logged to your configured log channel
4. **Zero Maintenance**: Once sent, the panel works automatically

## 🚀 Commands

### Slash Commands (Recommended)
- `/rolepanel [channel]` - Send the role check panel to a channel (defaults to current channel)
- `/rolecombo` - View current role combination settings
- `/checkroles` - Manually check all server members (admin bulk operation)

### Message Commands (Legacy Support)
- `!rolepanel` - Send the role check panel to current channel
- `!listrolecombo` - View current role combination settings  
- `!checkroles` - Manually check all server members (admin bulk operation)

## 🎭 Example Use Case

**Your current setup:** Users with both "Rover verified" + "Double Counter verified" should get "Verified" role.

**Scenario:** A user joins, gets verified through Rover, then later gets verified through Double Counter, but the bot was briefly offline during the second verification.

**Solution:** The user clicks the "🔄 Check My Roles" button and instantly receives the "Verified" role they were missing.

## 💡 User Experience

### Button Click Result Examples

**✅ User Gets New Role:**
```
🎭 Role Check Results
✅ Great news! You've been assigned new roles based on your current roles!

📈 Status
You now have 5 roles (gained 1)

🎯 Available Role Combinations  
✅ Verified: You have this role!
```

**✅ User Already Has All Roles:**
```
🎭 Role Check Results
✅ All good! Your roles are already up to date.

📊 Status
You have 4 roles and they're all correctly assigned.

🎯 Available Role Combinations
✅ Verified: You have this role!
```

**⏳ User Missing Required Roles:**
```  
🎭 Role Check Results
✅ All good! Your roles are already up to date.

📊 Status
You have 3 roles and they're all correctly assigned.

🎯 Available Role Combinations
⏳ Verified: Need Double Counter verified
```

## 🛠️ Setup Instructions

### 1. Send a Role Panel
Use either command to send a panel to your desired channel:
```
/rolepanel #verification
```
or
```
!rolepanel
```

### 2. Pin the Message (Recommended)
Pin the role panel message so users can easily find it. The button works permanently.

### 3. Inform Your Community
Let your members know about the new self-service option:

> "Having trouble with automatic roles? Click the 🔄 Check My Roles button in #verification to instantly check and update your roles!"

## 🔧 Configuration

### Environment Variables (.env)
```bash
# Role check cooldown (seconds between button clicks per user)
ROLE_CHECK_COOLDOWN=60

# Auto-role settings (existing)
ENABLE_AUTO_ROLES=true
AUTO_ROLE_LOG_CHANNEL_ID=your_log_channel_id
```

### Cooldown Settings
- **Default**: 60 seconds between clicks per user
- **Minimum Recommended**: 30 seconds (prevents excessive API calls)
- **Maximum**: No limit, but longer cooldowns may frustrate users

## 🎯 Best Practices

### Channel Placement
- **#verification**: Perfect for verification-related role combinations
- **#roles**: Good for general role assignment channels  
- **#help**: Helpful for users having role issues
- **#general**: Works but may get buried in conversation

### Message Pinning
- Pin the role panel message for easy access
- Consider adding it to your server guide or rules
- Update channel topic to mention the self-service option

### Community Communication
```markdown
## Self-Service Role Check 🎭

Having issues with automatic roles? Use our self-service button!

📍 **Location**: #verification (pinned message)
🔄 **How**: Click "Check My Roles" button  
⚡ **Speed**: Instant results
🔒 **Privacy**: Results sent privately to you
⏰ **Cooldown**: 60 seconds between uses
```

## 🚨 Troubleshooting

### Button Not Working?
1. **Check Bot Permissions**: Bot needs "Manage Roles" permission
2. **Check Role Hierarchy**: Bot's role must be above roles it manages
3. **Check Configuration**: Verify `ENABLE_AUTO_ROLES=true` in settings
4. **Check Role Names**: Ensure role names in config match server exactly (case-sensitive)

### Users Getting Errors?
1. **Check Logs**: Look for error messages in bot logs
2. **Check Cooldown**: User may be clicking too frequently
3. **Check Permissions**: Bot may lack permissions for specific roles
4. **Check Role Existence**: Target roles must exist in server

### Button Disappeared?
Buttons are persistent and should stay forever. If lost:
1. Send a new panel with `/rolepanel`
2. Check if message was deleted
3. Restart bot to restore persistent views

## 📊 Monitoring

### What Gets Logged
- All automatic role additions/removals
- User information (username, ID, display name)
- Timestamp of changes
- Reason for changes (which combination triggered it)

### Log Format Example
```
🤖 Automatic Role Update
User: @JohnDoe (John Doe)
✅ Roles Added
• Verified

User ID: 123456789012345678
```

## 🔮 Future Enhancements

The button system is designed to be easily expandable:

### Potential Features
- **Multiple Buttons**: Different buttons for different role categories
- **Role Selection Menus**: Dropdown menus for choosing specific roles
- **Temporary Roles**: Buttons that assign roles for limited time
- **Conditional Logic**: More complex role assignment rules
- **Statistics**: Track button usage and role assignment trends
- **Custom Cooldowns**: Different cooldowns for different role types

### Integration Options  
- **Level Systems**: Check user level before assigning roles
- **External APIs**: Verify external account connections
- **Time Requirements**: Only assign roles after specific membership duration
- **Activity Requirements**: Check message/voice activity before role assignment

## ✅ Benefits

### For Users
- **Self-Service**: Fix role issues instantly without bothering staff
- **Privacy**: Results sent privately, not publicly
- **Convenience**: One-click solution for role problems  
- **Always Available**: Works 24/7 without staff intervention

### For Staff
- **Reduced Workload**: Fewer role-related support requests
- **Better User Experience**: Users get instant help
- **Comprehensive Logging**: Full audit trail of all changes
- **Zero Maintenance**: Set it up once, works forever

### For Community
- **Improved Engagement**: Users get proper roles faster
- **Better Organization**: Automated role management keeps things tidy
- **Scalability**: Handles large communities without additional staff workload
- **Professional Feel**: Modern, interactive bot features

---

**Your verification system is now enhanced with self-service capabilities! Users can instantly resolve role issues with a simple button click.**
