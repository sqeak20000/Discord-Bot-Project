"""
Role Management System for Discord Bot
Handles automatic role assignment based on role combinations
"""

import discord
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Set
from discord import app_commands
from discord.ext import commands
from config import AUTO_ROLE_COMBINATIONS, ENABLE_AUTO_ROLES, AUTO_ROLE_LOG_CHANNEL_ID, ALLOWED_ROLES, ROLE_CHECK_COOLDOWN
from utils import has_permission

logger = logging.getLogger(__name__)

class RoleCheckButton(discord.ui.View):
    """Button interface for users to check their own roles"""
    
    def __init__(self, role_manager):
        super().__init__(timeout=None)  # Persistent view
        self.role_manager = role_manager
        self.user_cooldowns = {}  # Track user cooldowns to prevent spam
        self.cooldown_duration = ROLE_CHECK_COOLDOWN  # Configurable cooldown duration
    
    @discord.ui.button(
        label="🔄 Check My Roles", 
        style=discord.ButtonStyle.primary,
        emoji="🎭",
        custom_id="check_roles_button"
    )
    async def check_roles_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle role check button press"""
        await interaction.response.defer(ephemeral=True)
        
        # Check if user is on cooldown
        user_id = interaction.user.id
        current_time = datetime.utcnow()
        
        if user_id in self.user_cooldowns:
            last_used = self.user_cooldowns[user_id]
            time_diff = (current_time - last_used).total_seconds()
            
            if time_diff < self.cooldown_duration:
                remaining = int(self.cooldown_duration - time_diff)
                await interaction.followup.send(
                    f"⏰ **Cooldown Active**\n"
                    f"You can check your roles again in {remaining} seconds.\n"
                    f"This prevents spam and helps keep the bot responsive for everyone!",
                    ephemeral=True
                )
                return
        
        # Set cooldown
        self.user_cooldowns[user_id] = current_time
        
        if not ENABLE_AUTO_ROLES:
            await interaction.followup.send("❌ Automatic role management is currently disabled.", ephemeral=True)
            return
        
        if not self.role_manager:
            await interaction.followup.send("❌ Role management system not available.", ephemeral=True)
            return
        
        # Get member object
        member = interaction.guild.get_member(user_id)
        if not member:
            await interaction.followup.send("❌ Unable to find your member data.", ephemeral=True)
            return
        
        await interaction.followup.send("🔍 **Checking your roles...** This may take a moment.", ephemeral=True)
        
        try:
            # Check the user's current roles against all combinations
            old_roles = member.roles.copy()
            roles_before_count = len(old_roles)
            
            # Simulate checking by using empty old roles (this will trigger assignments if they qualify)
            await self.role_manager.check_and_update_roles(member, [], member.roles)
            
            # Check if anything changed
            new_roles = member.roles
            roles_after_count = len(new_roles)
            
            # Create response embed
            embed = discord.Embed(
                title="🎭 Role Check Results",
                color=0x00ff00 if roles_after_count > roles_before_count else 0x0099ff,
                timestamp=datetime.utcnow()
            )
            
            if roles_after_count > roles_before_count:
                # User got new roles
                embed.description = "✅ **Great news!** You've been assigned new roles based on your current roles!"
                embed.add_field(
                    name="📈 Status",
                    value=f"You now have {roles_after_count} roles (gained {roles_after_count - roles_before_count})",
                    inline=False
                )
            else:
                # No changes
                embed.description = "✅ **All good!** Your roles are already up to date."
                embed.add_field(
                    name="📊 Status", 
                    value=f"You have {roles_after_count} roles and they're all correctly assigned.",
                    inline=False
                )
            
            # Show active combinations they could potentially get
            active_combos = self.role_manager.get_active_combinations()
            if active_combos:
                combo_status = []
                user_role_names = {role.name for role in member.roles}
                
                for combo in active_combos:
                    required_roles = set(combo['required_roles'])
                    target_role = combo['target_role']
                    has_target = target_role in user_role_names
                    
                    if has_target:
                        combo_status.append(f"✅ **{combo['name']}**: You have this role!")
                    else:
                        missing_roles = required_roles - user_role_names
                        if not missing_roles:
                            combo_status.append(f"🔄 **{combo['name']}**: Processing...")
                        else:
                            missing_list = ", ".join(missing_roles)
                            combo_status.append(f"⏳ **{combo['name']}**: Need `{missing_list}`")
                
                if combo_status:
                    embed.add_field(
                        name="🎯 Available Role Combinations",
                        value="\n".join(combo_status[:5]),  # Show max 5 to avoid embed limits
                        inline=False
                    )
            
            embed.set_footer(text="Role checks help ensure everyone has the correct roles!")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error during user role check for {member}: {e}")
            await interaction.followup.send(
                f"❌ **Error checking your roles**\n"
                f"An error occurred while checking your roles. Please try again later or contact a moderator.\n"
                f"Error: {str(e)[:100]}...",
                ephemeral=True
            )

class RoleManager:
    """Manages automatic role assignments based on configured combinations"""
    
    def __init__(self, bot):
        self.bot = bot
        self.processing_users: Set[int] = set()  # Prevent duplicate processing
        self.role_check_view = None  # Will store the persistent button view
    
    async def setup_persistent_view(self):
        """Setup the persistent button view"""
        self.role_check_view = RoleCheckButton(self)
        self.bot.add_view(self.role_check_view)
    
    async def send_role_check_panel(self, channel: discord.TextChannel):
        """Send the role check panel with button to a channel"""
        
        # Get active combinations info for the embed
        active_combos = self.get_active_combinations()
        
        embed = discord.Embed(
            title="🎭 Self-Service Role Check",
            description=(
                "**Having trouble with automatic roles?** Use the button below to manually check and update your roles!\n\n"
                "This is helpful if:\n"
                "• You just got new roles but haven't received automatic roles yet\n"
                "• You think you're missing a role you should have\n"
                "• The bot was offline when you got new roles\n"
            ),
            color=0x0099ff,
            timestamp=datetime.utcnow()
        )
        
        if active_combos:
            combo_info = []
            for combo in active_combos[:3]:  # Show max 3 to avoid embed limits
                required = " + ".join(combo['required_roles'])
                target = combo['target_role']
                combo_info.append(f"• `{required}` → **{target}**")
            
            embed.add_field(
                name="🎯 Available Auto-Roles",
                value="\n".join(combo_info),
                inline=False
            )
            
            if len(active_combos) > 3:
                embed.add_field(
                    name="",
                    value=f"*...and {len(active_combos) - 3} more combinations*",
                    inline=False
                )
        
        embed.add_field(
            name="📝 How to Use",
            value=(
                "1. Click the **🔄 Check My Roles** button below\n"
                "2. The bot will check if you qualify for any automatic roles\n"
                "3. If you qualify, you'll get the roles immediately\n"
                "4. You'll receive a private message with the results\n\n"
                f"*Note: There's a {ROLE_CHECK_COOLDOWN}-second cooldown to prevent spam*"
            ),
            inline=False
        )
        
        embed.set_footer(text="This panel stays active - bookmark this message for easy access!")
        
        # Send with the persistent button view
        if not self.role_check_view:
            await self.setup_persistent_view()
        
        message = await channel.send(embed=embed, view=self.role_check_view)
        return message
    
    async def handle_member_update(self, before: discord.Member, after: discord.Member):
        """Handle member update events to check for role changes"""
        if not ENABLE_AUTO_ROLES:
            return
        
        # Check if roles actually changed
        if before.roles == after.roles:
            return
        
        # Prevent processing the same user multiple times simultaneously
        if after.id in self.processing_users:
            return
        
        self.processing_users.add(after.id)
        
        try:
            await self.check_and_update_roles(after, before.roles, after.roles)
        except Exception as e:
            logger.error(f"Error processing role update for {after}: {e}")
        finally:
            self.processing_users.discard(after.id)
    
    async def check_and_update_roles(self, member: discord.Member, old_roles: List[discord.Role], new_roles: List[discord.Role]):
        """Check if member's new roles trigger any automatic role assignments"""
        
        # Get role names for easier comparison
        old_role_names = {role.name for role in old_roles}
        new_role_names = {role.name for role in new_roles}
        
        # Track changes made
        roles_added = []
        roles_removed = []
        
        for combo in AUTO_ROLE_COMBINATIONS:
            if not combo.get('enabled', False):
                continue
            
            required_roles = set(combo['required_roles'])
            target_role_name = combo['target_role']
            remove_on_loss = combo.get('remove_on_loss', True)
            
            # Find the target role in the guild
            target_role = discord.utils.get(member.guild.roles, name=target_role_name)
            if not target_role:
                logger.warning(f"Target role '{target_role_name}' not found in guild {member.guild.name}")
                continue
            
            # Check if user has all required roles now
            has_all_required = required_roles.issubset(new_role_names)
            # Check if user had all required roles before
            had_all_required = required_roles.issubset(old_role_names)
            # Check if user currently has the target role
            has_target_role = target_role in new_roles
            
            # Case 1: User gained all required roles and doesn't have target role yet
            if has_all_required and not has_target_role:
                try:
                    await member.add_roles(target_role, reason=f"Auto-role: User has all required roles: {', '.join(required_roles)}")
                    roles_added.append(target_role_name)
                    logger.info(f"Added role '{target_role_name}' to {member} (combo: {combo['name']})")
                except discord.HTTPException as e:
                    logger.error(f"Failed to add role '{target_role_name}' to {member}: {e}")
            
            # Case 2: User lost a required role and has target role (and removal is enabled)
            elif not has_all_required and had_all_required and has_target_role and remove_on_loss:
                # Make sure they actually lost a role (not just gained extra ones)
                lost_required_roles = required_roles - new_role_names
                if lost_required_roles:
                    try:
                        await member.remove_roles(target_role, reason=f"Auto-role removal: User lost required role(s): {', '.join(lost_required_roles)}")
                        roles_removed.append(target_role_name)
                        logger.info(f"Removed role '{target_role_name}' from {member} (combo: {combo['name']}) - lost roles: {', '.join(lost_required_roles)}")
                    except discord.HTTPException as e:
                        logger.error(f"Failed to remove role '{target_role_name}' from {member}: {e}")
        
        # Log the changes if any were made
        if roles_added or roles_removed:
            await self.log_role_changes(member, roles_added, roles_removed)
    
    async def log_role_changes(self, member: discord.Member, roles_added: List[str], roles_removed: List[str]):
        """Log automatic role changes to the designated channel"""
        try:
            log_channel = self.bot.get_channel(AUTO_ROLE_LOG_CHANNEL_ID)
            if not log_channel:
                return
            
            # Create embed for the log
            embed = discord.Embed(
                title="🤖 Automatic Role Update",
                color=0x00ff00 if roles_added else 0xff9900,
                timestamp=datetime.utcnow()
            )
            
            embed.add_field(name="User", value=f"{member.mention} ({member.display_name})", inline=False)
            
            if roles_added:
                embed.add_field(name="✅ Roles Added", value="\n".join([f"• {role}" for role in roles_added]), inline=True)
            
            if roles_removed:
                embed.add_field(name="❌ Roles Removed", value="\n".join([f"• {role}" for role in roles_removed]), inline=True)
            
            embed.set_footer(text=f"User ID: {member.id}")
            
            await log_channel.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Failed to log role changes for {member}: {e}")
    
    async def check_all_members(self, guild: discord.Guild):
        """Check all members in a guild for role combinations (useful for initial setup)"""
        if not ENABLE_AUTO_ROLES:
            return {"processed": 0, "updated": 0, "errors": 0}
        
        processed = 0
        updated = 0
        errors = 0
        
        for member in guild.members:
            if member.bot:  # Skip bots
                continue
            
            try:
                # Simulate a role update by checking current roles against empty previous roles
                empty_roles = []
                
                old_roles_count = len(member.roles)
                await self.check_and_update_roles(member, empty_roles, member.roles)
                new_roles_count = len(member.roles)
                
                if new_roles_count != old_roles_count:
                    updated += 1
                
                processed += 1
                
                # Add small delay to prevent rate limiting
                if processed % 10 == 0:
                    await asyncio.sleep(1)
                    
            except Exception as e:
                logger.error(f"Error checking member {member}: {e}")
                errors += 1
        
        return {"processed": processed, "updated": updated, "errors": errors}
    
    def get_active_combinations(self) -> List[Dict]:
        """Get list of currently active role combinations"""
        return [combo for combo in AUTO_ROLE_COMBINATIONS if combo.get('enabled', False)]
    
    def get_all_combinations(self) -> List[Dict]:
        """Get list of all role combinations (enabled and disabled)"""
        return AUTO_ROLE_COMBINATIONS.copy()

# Global instance
role_manager = None

async def setup_role_management(bot):
    """Initialize the role management system"""
    global role_manager
    role_manager = RoleManager(bot)
    await setup_role_management_commands(bot)
    
    # Setup persistent view for buttons
    await role_manager.setup_persistent_view()
    
    logger.info("Role management system initialized")

async def setup_role_management_commands(bot):
    """Setup slash commands for role management"""
    
    @bot.tree.command(name="checkroles", description="Check all members for role combinations and apply them")
    @app_commands.describe()
    async def check_roles_slash(interaction: discord.Interaction):
        """Slash command to check all members for role combinations"""
        await interaction.response.defer(ephemeral=True)
        
        # Check permissions
        if not has_permission(interaction.user, ALLOWED_ROLES):
            await interaction.followup.send("❌ You don't have permission to check roles.", ephemeral=True)
            return
        
        if not ENABLE_AUTO_ROLES:
            await interaction.followup.send("❌ Automatic role management is disabled.", ephemeral=True)
            return
        
        if not role_manager:
            await interaction.followup.send("❌ Role management system not initialized.", ephemeral=True)
            return
        
        await interaction.followup.send("🔄 **Checking all members for role combinations...** This may take a while.", ephemeral=True)
        
        try:
            results = await role_manager.check_all_members(interaction.guild)
            
            embed = discord.Embed(
                title="✅ Role Check Complete",
                color=0x00ff00,
                timestamp=datetime.utcnow()
            )
            
            embed.add_field(name="Members Processed", value=results['processed'], inline=True)
            embed.add_field(name="Members Updated", value=results['updated'], inline=True)
            embed.add_field(name="Errors", value=results['errors'], inline=True)
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(f"❌ **Error during role check:** {e}", ephemeral=True)
    
    @bot.tree.command(name="rolecombo", description="Show current role combination configuration")
    @app_commands.describe()
    async def role_combo_slash(interaction: discord.Interaction):
        """Slash command to show role combinations"""
        await interaction.response.defer(ephemeral=True)
        
        # Check permissions
        if not has_permission(interaction.user, ALLOWED_ROLES):
            await interaction.followup.send("❌ You don't have permission to view role combinations.", ephemeral=True)
            return
        
        if not role_manager:
            await interaction.followup.send("❌ Role management system not initialized.", ephemeral=True)
            return
        
        active_combos = role_manager.get_active_combinations()
        all_combos = role_manager.get_all_combinations()
        
        embed = discord.Embed(
            title="🎭 Role Combinations Configuration",
            description=f"Auto-roles enabled: {'✅ Yes' if ENABLE_AUTO_ROLES else '❌ No'}",
            color=0x00ff00 if ENABLE_AUTO_ROLES else 0xff0000,
            timestamp=datetime.utcnow()
        )
        
        if active_combos:
            active_text = ""
            for combo in active_combos:
                required = " + ".join(combo['required_roles'])
                target = combo['target_role']
                remove_text = " (auto-remove)" if combo.get('remove_on_loss', True) else " (keep on loss)"
                active_text += f"• **{combo['name']}**: `{required}` → `{target}`{remove_text}\n"
            
            embed.add_field(name="✅ Active Combinations", value=active_text, inline=False)
        
        disabled_combos = [combo for combo in all_combos if not combo.get('enabled', False)]
        if disabled_combos:
            disabled_text = ""
            for combo in disabled_combos:
                required = " + ".join(combo['required_roles'])
                target = combo['target_role']
                disabled_text += f"• **{combo['name']}**: `{required}` → `{target}`\n"
            
            embed.add_field(name="❌ Disabled Combinations", value=disabled_text, inline=False)
        
        if not all_combos:
            embed.add_field(name="No Combinations", value="No role combinations are configured.", inline=False)
        
        embed.set_footer(text="Edit config.py to modify role combinations")
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    @bot.tree.command(name="rolepanel", description="Send the self-service role check panel to this channel")
    @app_commands.describe(channel="Channel to send the role panel to (optional, defaults to current channel)")
    async def role_panel_slash(interaction: discord.Interaction, channel: discord.TextChannel = None):
        """Slash command to send the role check panel"""
        await interaction.response.defer(ephemeral=True)
        
        # Check permissions
        if not has_permission(interaction.user, ALLOWED_ROLES):
            await interaction.followup.send("❌ You don't have permission to send role panels.", ephemeral=True)
            return
        
        if not ENABLE_AUTO_ROLES:
            await interaction.followup.send("❌ Automatic role management is disabled.", ephemeral=True)
            return
        
        if not role_manager:
            await interaction.followup.send("❌ Role management system not initialized.", ephemeral=True)
            return
        
        target_channel = channel or interaction.channel
        
        try:
            message = await role_manager.send_role_check_panel(target_channel)
            await interaction.followup.send(
                f"✅ **Role check panel sent successfully!**\n"
                f"Panel sent to {target_channel.mention}\n"
                f"Users can now click the button to check their roles.\n\n"
                f"[Jump to Message]({message.jump_url})",
                ephemeral=True
            )
        except discord.Forbidden:
            await interaction.followup.send(f"❌ I don't have permission to send messages in {target_channel.mention}.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ **Error sending role panel:** {e}", ephemeral=True)

async def handle_member_update(before: discord.Member, after: discord.Member):
    """Handle member update events"""
    if role_manager:
        await role_manager.handle_member_update(before, after)

# Command functions for managing role combinations
async def handle_check_roles_command(bot, message):
    """Handle the !checkroles command to manually check all members"""
    from utils import has_permission
    from config import ALLOWED_ROLES
    
    # Check permissions
    if not has_permission(message.author, ALLOWED_ROLES):
        await message.channel.send("❌ You don't have permission to check roles.", delete_after=5)
        return
    
    if not ENABLE_AUTO_ROLES:
        await message.channel.send("❌ Automatic role management is disabled.", delete_after=10)
        return
    
    if not role_manager:
        await message.channel.send("❌ Role management system not initialized.", delete_after=10)
        return
    
    await message.channel.send("🔄 **Checking all members for role combinations...** This may take a while.")
    
    try:
        results = await role_manager.check_all_members(message.guild)
        
        embed = discord.Embed(
            title="✅ Role Check Complete",
            color=0x00ff00,
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(name="Members Processed", value=results['processed'], inline=True)
        embed.add_field(name="Members Updated", value=results['updated'], inline=True)
        embed.add_field(name="Errors", value=results['errors'], inline=True)
        
        await message.channel.send(embed=embed)
        
    except Exception as e:
        await message.channel.send(f"❌ **Error during role check:** {e}")

async def handle_list_role_combos_command(bot, message):
    """Handle the !listrolecombo command to show active role combinations"""
    from utils import has_permission
    from config import ALLOWED_ROLES
    
    # Check permissions
    if not has_permission(message.author, ALLOWED_ROLES):
        await message.channel.send("❌ You don't have permission to view role combinations.", delete_after=5)
        return
    
    if not role_manager:
        await message.channel.send("❌ Role management system not initialized.", delete_after=10)
        return
    
    active_combos = role_manager.get_active_combinations()
    all_combos = role_manager.get_all_combinations()
    
    embed = discord.Embed(
        title="🎭 Role Combinations Configuration",
        description=f"Auto-roles enabled: {'✅ Yes' if ENABLE_AUTO_ROLES else '❌ No'}",
        color=0x00ff00 if ENABLE_AUTO_ROLES else 0xff0000,
        timestamp=datetime.utcnow()
    )
    
    if active_combos:
        active_text = ""
        for combo in active_combos:
            required = " + ".join(combo['required_roles'])
            target = combo['target_role']
            remove_text = " (auto-remove)" if combo.get('remove_on_loss', True) else " (keep on loss)"
            active_text += f"• **{combo['name']}**: `{required}` → `{target}`{remove_text}\n"
        
        embed.add_field(name="✅ Active Combinations", value=active_text, inline=False)
    
    disabled_combos = [combo for combo in all_combos if not combo.get('enabled', False)]
    if disabled_combos:
        disabled_text = ""
        for combo in disabled_combos:
            required = " + ".join(combo['required_roles'])
            target = combo['target_role']
            disabled_text += f"• **{combo['name']}**: `{required}` → `{target}`\n"
        
        embed.add_field(name="❌ Disabled Combinations", value=disabled_text, inline=False)
    
    if not all_combos:
        embed.add_field(name="No Combinations", value="No role combinations are configured.", inline=False)
    
    embed.set_footer(text="Edit config.py to modify role combinations")
    
    await message.channel.send(embed=embed)

async def handle_role_panel_command(bot, message):
    """Handle the !rolepanel command to send the role check panel"""
    from utils import has_permission
    from config import ALLOWED_ROLES
    
    # Check permissions
    if not has_permission(message.author, ALLOWED_ROLES):
        await message.channel.send("❌ You don't have permission to send role panels.", delete_after=5)
        return
    
    if not ENABLE_AUTO_ROLES:
        await message.channel.send("❌ Automatic role management is disabled.", delete_after=10)
        return
    
    if not role_manager:
        await message.channel.send("❌ Role management system not initialized.", delete_after=10)
        return
    
    try:
        # Send the panel to the current channel
        panel_message = await role_manager.send_role_check_panel(message.channel)
        
        # Send confirmation (will auto-delete)
        await message.channel.send(
            f"✅ **Role check panel sent!** Users can now click the button below to check their roles.\n"
            f"*This message will self-destruct in 10 seconds.*",
            delete_after=10
        )
        
        # Delete the command message to keep things clean
        try:
            await message.delete()
        except:
            pass  # Ignore if we can't delete the command message
        
    except discord.Forbidden:
        await message.channel.send("❌ I don't have permission to send messages in this channel.", delete_after=10)
    except Exception as e:
        await message.channel.send(f"❌ **Error sending role panel:** {e}", delete_after=10)
