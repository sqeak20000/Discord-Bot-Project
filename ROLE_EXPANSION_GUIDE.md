# Discord Bot Role Management System

## Overview

This expanded bot now includes a powerful **automatic role management system** that can detect when users get role updates and automatically assign new roles based on configured combinations. Here's how it works and how to expand its capabilities further.

## 🎯 Current Capabilities

### Automatic Role Assignment
- **Real-time Detection**: The bot listens for role updates using Discord's `on_member_update` event
- **Combination Logic**: When a user has ALL required roles from a combination, they automatically get the target role
- **Smart Removal**: Optionally removes target roles when users lose required roles
- **Logging**: All automatic role changes are logged with detailed information
- **Admin Controls**: Moderators can manually trigger role checks and view configurations

### Available Commands

#### Message Commands (Legacy)
- `!checkroles` - Manually check all members for role combinations
- `!listrolecombo` - Show current role combination configuration

#### Slash Commands (Recommended)
- `/checkroles` - Check all members for role combinations and apply them
- `/rolecombo` - Show current role combination configuration

### Current Configuration Example
```python
AUTO_ROLE_COMBINATIONS = [
    {
        'name': 'VIP Member',                    # Friendly name for logging
        'required_roles': ['Premium Subscriber', 'Active Member'],  # User must have BOTH roles
        'target_role': 'VIP Member',             # Role to assign automatically
        'enabled': True,                         # Whether this combination is active
        'remove_on_loss': True,                  # Remove target role if user loses required role
    },
]
```

## 🚀 How to Expand Capabilities

### 1. Adding More Role Combinations

Simply add more entries to `AUTO_ROLE_COMBINATIONS` in `config.py`:

```python
AUTO_ROLE_COMBINATIONS = [
    # VIP System
    {
        'name': 'VIP Member',
        'required_roles': ['Nitro Booster', 'Active Member'],
        'target_role': 'VIP Access',
        'enabled': True,
        'remove_on_loss': True,
    },
    
    # Staff Progression
    {
        'name': 'Senior Moderator',
        'required_roles': ['Junior Moderator', 'Training Complete'],
        'target_role': 'Senior Moderator',
        'enabled': True,
        'remove_on_loss': False,  # Keep role even if they lose junior mod
    },
    
    # Community Rewards
    {
        'name': 'Veteran Member',
        'required_roles': ['Long-time Member', 'Helper'],
        'target_role': 'Veteran',
        'enabled': True,
        'remove_on_loss': True,
    },
    
    # Beta Access
    {
        'name': 'Beta Tester',
        'required_roles': ['Verified', 'Contributor'],
        'target_role': 'Beta Access',
        'enabled': False,  # Disabled until ready
        'remove_on_loss': True,
    },
]
```

### 2. Advanced Role Logic

You can expand the `RoleManager` class to support more complex logic:

#### Time-Based Requirements
```python
# Add to role combination config
{
    'name': 'Long-term VIP',
    'required_roles': ['VIP Member'],
    'target_role': 'Elite VIP',
    'enabled': True,
    'remove_on_loss': True,
    'minimum_days': 30,  # New field - must have VIP for 30 days
}
```

#### Level-Based Requirements
```python
# Integration with leveling bots
{
    'name': 'High Level VIP',
    'required_roles': ['VIP Member'],
    'target_role': 'Elite VIP',
    'enabled': True,
    'remove_on_loss': True,
    'minimum_level': 25,  # New field - requires level 25+
}
```

#### Activity-Based Requirements
```python
# Based on message count or voice time
{
    'name': 'Active VIP',
    'required_roles': ['VIP Member'],
    'target_role': 'Super Active VIP',
    'enabled': True,
    'remove_on_loss': True,
    'minimum_messages': 1000,     # Requires 1000+ messages
    'minimum_voice_hours': 50,    # Requires 50+ hours in voice
}
```

### 3. Integration with External Systems

#### Database Integration
```python
# Add database tracking for role history
async def log_role_change_to_database(self, member, role_change):
    """Log role changes to database for analytics"""
    # Implementation here
```

#### API Integration
```python
# Sync with external APIs
async def sync_with_external_api(self, member, new_roles):
    """Sync role changes with external systems"""
    # Implementation here
```

### 4. Advanced Event Handling

You can expand beyond just role updates:

#### Voice Channel Activity
```python
@bot.event
async def on_voice_state_update(member, before, after):
    """Handle voice activity for role rewards"""
    # Award roles based on voice channel participation
```

#### Message Activity
```python
@bot.event
async def on_message(message):
    """Handle message-based role rewards"""
    # Award roles based on message activity
```

#### Reaction-Based Roles
```python
@bot.event
async def on_raw_reaction_add(payload):
    """Handle reaction-based role assignment"""
    # Award roles based on reactions to specific messages
```

### 5. Enhanced Logging and Analytics

#### Role Change Statistics
```python
class RoleAnalytics:
    def __init__(self):
        self.role_changes = []
    
    async def generate_monthly_report(self):
        """Generate monthly role change analytics"""
        # Implementation here
```

#### Role Trend Monitoring
```python
async def monitor_role_trends(self):
    """Monitor and alert on unusual role assignment patterns"""
    # Implementation here
```

### 6. Interactive Role Management

#### Role Selection Menus
```python
class RoleSelectionView(discord.ui.View):
    """Interactive role selection interface"""
    # Implementation for dropdown menus and buttons
```

#### Temporary Role Assignments
```python
async def assign_temporary_role(self, member, role, duration):
    """Assign a role for a specific duration"""
    # Implementation with scheduled removal
```

## 🛠️ Implementation Examples

### Example 1: Time-Based Role Progression

```python
# In role_manager.py - enhanced check_and_update_roles method
async def check_time_based_requirements(self, member, combo):
    """Check if user meets time-based requirements"""
    if 'minimum_days' not in combo:
        return True
    
    # Check when user first got the required roles
    # This would require a database to track role history
    role_history = await self.get_role_history(member)
    
    for required_role in combo['required_roles']:
        role_acquired_date = role_history.get(required_role)
        if not role_acquired_date:
            return False
        
        days_with_role = (datetime.utcnow() - role_acquired_date).days
        if days_with_role < combo['minimum_days']:
            return False
    
    return True
```

### Example 2: Activity-Based Role Requirements

```python
# Integration with activity tracking
async def check_activity_requirements(self, member, combo):
    """Check if user meets activity requirements"""
    if 'minimum_messages' in combo:
        message_count = await self.get_message_count(member)
        if message_count < combo['minimum_messages']:
            return False
    
    if 'minimum_voice_hours' in combo:
        voice_hours = await self.get_voice_time(member)
        if voice_hours < combo['minimum_voice_hours']:
            return False
    
    return True
```

### Example 3: Scheduled Role Reviews

```python
# Add to role_manager.py
from discord.ext import tasks

@tasks.loop(hours=24)
async def daily_role_review(self):
    """Daily review of all role assignments"""
    for guild in self.bot.guilds:
        # Check for expired temporary roles
        await self.remove_expired_roles(guild)
        
        # Revalidate complex role requirements
        await self.validate_complex_roles(guild)
        
        # Generate daily statistics
        await self.generate_daily_stats(guild)
```

## 🔧 Configuration Tips

### Environment Variables (.env)
```bash
# Role Management
ENABLE_AUTO_ROLES=true
AUTO_ROLE_LOG_CHANNEL_ID=123456789012345678

# Advanced Features (if implemented)
ROLE_DB_CONNECTION_STRING=sqlite:///roles.db
ENABLE_ROLE_ANALYTICS=true
ROLE_REVIEW_INTERVAL=86400  # 24 hours in seconds
```

### Bot Permissions Required
- `members` intent (already added)
- `guilds` intent (already added)
- `Manage Roles` permission
- `View Audit Log` (for enhanced logging)
- `Send Messages` and `Embed Links` (for logging channel)

### Performance Considerations
- The current system processes one user at a time to avoid rate limits
- Large servers (10,000+ members) may need batching for `!checkroles`
- Consider implementing a queue system for high-traffic servers

## 🎯 Real-World Use Cases

### 1. Gaming Community
```python
# Skill-based progression
{
    'name': 'Skilled Player',
    'required_roles': ['Verified Player', 'Tournament Participant'],
    'target_role': 'Pro Player',
    'enabled': True,
    'remove_on_loss': False,
}
```

### 2. Educational Server
```python
# Course completion rewards
{
    'name': 'Graduate',
    'required_roles': ['Course Complete', 'Project Submitted'],
    'target_role': 'Graduate',
    'enabled': True,
    'remove_on_loss': False,
}
```

### 3. Business Community
```python
# Membership tiers
{
    'name': 'Premium Partner',
    'required_roles': ['Verified Business', 'Premium Subscriber'],
    'target_role': 'Premium Partner',
    'enabled': True,
    'remove_on_loss': True,
}
```

## 📊 Monitoring and Maintenance

### Health Checks
- Monitor role assignment rates
- Check for failed role assignments
- Verify log channel accessibility
- Validate role permissions

### Regular Tasks
- Weekly review of active combinations
- Monthly analysis of role trends
- Quarterly review of bot permissions
- Annual update of role strategies

This system provides a solid foundation that can be expanded to meet virtually any role management need. The modular design makes it easy to add new features without breaking existing functionality.
