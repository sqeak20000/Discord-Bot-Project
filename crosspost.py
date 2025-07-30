import discord
import aiohttp
import asyncio
import logging
from config import (
    GUILDED_BOT_TOKEN, 
    GUILDED_SERVER_ID, 
    GUILDED_ANNOUNCEMENTS_CHANNEL_ID,
    DISCORD_UPDATES_CHANNEL_ID,
    ENABLE_CROSS_POSTING,
    ENABLE_ROBLOX_POSTING
)
from roblox_integration import roblox_poster, format_message_for_roblox

# Setup logging for cross-posting
logger = logging.getLogger('crosspost')

class GuildedCrossPoster:
    """Handles cross-posting messages from Discord to Guilded"""
    
    def __init__(self):
        self.guilded_headers = {
            'Authorization': f'Bearer {GUILDED_BOT_TOKEN}',
            'Content-Type': 'application/json'
        }
        self.guilded_base_url = 'https://www.guilded.gg/api/v1'
        self.session = None
    
    async def init_session(self):
        """Initialize aiohttp session"""
        if not self.session:
            self.session = aiohttp.ClientSession()
    
    async def close_session(self):
        """Close aiohttp session"""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def send_to_guilded(self, content, title=None, embeds=None, attachments=None):
        """Send a message to the Guilded announcements channel"""
        if not ENABLE_CROSS_POSTING:
            logger.warning("Cross-posting is disabled - missing configuration")
            return False
        
        await self.init_session()
        
        try:
            # First, get channel info to determine the correct endpoint
            channel_info_url = f"{self.guilded_base_url}/channels/{GUILDED_ANNOUNCEMENTS_CHANNEL_ID}"
            
            async with self.session.get(channel_info_url, headers=self.guilded_headers) as response:
                if response.status == 200:
                    channel_data = await response.json()
                    channel_type = channel_data.get('channel', {}).get('type', 'chat')
                    logger.info(f"Channel type detected: {channel_type}")
                else:
                    logger.warning(f"Could not get channel info: {response.status}")
                    channel_type = 'chat'  # Default assumption
            
            # Use different endpoint and payload based on channel type
            if channel_type == 'announcements':
                # For announcement channels, use the announcements endpoint
                payload = {
                    'title': title or 'Discord Update',
                    'content': content
                }
                url = f"{self.guilded_base_url}/channels/{GUILDED_ANNOUNCEMENTS_CHANNEL_ID}/announcements"
                logger.info(f"Using announcements endpoint: {url}")
            else:
                # For regular chat channels, use messages endpoint
                payload = {
                    'content': content
                }
                url = f"{self.guilded_base_url}/channels/{GUILDED_ANNOUNCEMENTS_CHANNEL_ID}/messages"
                logger.info(f"Using messages endpoint: {url}")
            
            logger.info(f"Payload: {payload}")
            logger.info(f"Headers: {dict(self.guilded_headers)}")
            
            # Send to Guilded
            async with self.session.post(url, json=payload, headers=self.guilded_headers) as response:
                response_text = await response.text()
                logger.info(f"Response status: {response.status}")
                logger.info(f"Response text: {response_text}")
                
                if response.status == 200 or response.status == 201:
                    logger.info(f"✅ Successfully cross-posted message to Guilded")
                    return True
                else:
                    logger.error(f"❌ Failed to send to Guilded: {response.status} - {response_text}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Error sending to Guilded: {e}")
            return False
    
    async def convert_discord_embed_to_guilded(self, discord_embed):
        """Convert Discord embed to Guilded embed format"""
        guilded_embed = {}
        
        if discord_embed.title:
            guilded_embed['title'] = discord_embed.title
        
        if discord_embed.description:
            guilded_embed['description'] = discord_embed.description
        
        if discord_embed.url:
            guilded_embed['url'] = discord_embed.url
        
        if discord_embed.color:
            guilded_embed['color'] = discord_embed.color.value
        
        if discord_embed.timestamp:
            guilded_embed['timestamp'] = discord_embed.timestamp.isoformat()
        
        # Handle footer
        if discord_embed.footer:
            guilded_embed['footer'] = {
                'text': discord_embed.footer.text
            }
            if discord_embed.footer.icon_url:
                guilded_embed['footer']['iconUrl'] = discord_embed.footer.icon_url
        
        # Handle author
        if discord_embed.author:
            guilded_embed['author'] = {
                'name': discord_embed.author.name
            }
            if discord_embed.author.url:
                guilded_embed['author']['url'] = discord_embed.author.url
            if discord_embed.author.icon_url:
                guilded_embed['author']['iconUrl'] = discord_embed.author.icon_url
        
        # Handle thumbnail
        if discord_embed.thumbnail:
            guilded_embed['thumbnail'] = {
                'url': discord_embed.thumbnail.url
            }
        
        # Handle image
        if discord_embed.image:
            guilded_embed['image'] = {
                'url': discord_embed.image.url
            }
        
        # Handle fields
        if discord_embed.fields:
            guilded_embed['fields'] = []
            for field in discord_embed.fields:
                guilded_embed['fields'].append({
                    'name': field.name,
                    'value': field.value,
                    'inline': field.inline
                })
        
        return guilded_embed

# Global instance
cross_poster = GuildedCrossPoster()

async def handle_discord_update_message(message):
    """Handle messages from the Discord updates channel"""
    if not ENABLE_CROSS_POSTING:
        return
    
    if message.channel.id != DISCORD_UPDATES_CHANNEL_ID:
        return
    
    if message.author.bot and message.author.id == message.guild.me.id:
        return  # Don't cross-post our own messages
    
    logger.info(f"📢 Cross-posting message from Discord updates channel...")
    
    try:
        # Prepare content
        content = message.content if message.content else ""
        
        # For announcements, we want a good title and clean content
        # Extract title from first line if it looks like a title
        lines = content.split('\n') if content else []
        
        if lines and len(lines) > 1:
            first_line = lines[0].strip()
            # If first line is short and looks like a title, use it
            if len(first_line) < 100 and ('update' in first_line.lower() or 
                                        first_line.startswith('**') or 
                                        first_line.startswith('# ') or
                                        first_line.endswith(':') or
                                        '🎉' in first_line or '📢' in first_line):
                title = first_line.replace('**', '').replace('# ', '').strip(' :')
                content = '\n'.join(lines[1:]).strip()
            else:
                title = f"Discord Update from {message.author.display_name}"
        else:
            title = f"Discord Update from {message.author.display_name}"
            # If content is short, we'll use it as-is
        
        # Clean up title
        title = title[:100]  # Guilded title limit
        if not title:
            title = "Discord Update"
        
        # Add author attribution to content if not already there
        if message.author.display_name.lower() not in content.lower():
            attribution = f"*Posted by {message.author.display_name}*\n\n"
            content = attribution + content
        
        # Handle attachments (convert to links)
        if message.attachments:
            attachment_text = "\n\n**📎 Attachments:**\n"
            for i, attachment in enumerate(message.attachments, 1):
                attachment_text += f"{i}. [{attachment.filename}]({attachment.url})\n"
            content += attachment_text
        
        # Cross-post to Guilded
        guilded_success = await cross_poster.send_to_guilded(
            content=content,
            title=title  # Pass title separately for announcements
        )
        
        # Cross-post to Roblox
        roblox_success = False
        if ENABLE_ROBLOX_POSTING:
            try:
                # Format message for Roblox
                roblox_message = await format_message_for_roblox(content, title)
                
                # Try posting to group shout first (more visible)
                roblox_success = await roblox_poster.post_to_group_shout(roblox_message)
                
                # If shout fails, try wall post as fallback
                if not roblox_success:
                    logger.info("Group shout failed, trying wall post...")
                    roblox_success = await roblox_poster.post_to_group_wall(roblox_message)
                    
            except Exception as e:
                logger.error(f"❌ Error posting to Roblox: {e}")
        
        # React to show cross-posting status
        if guilded_success or roblox_success:
            # Show success if at least one platform worked
            try:
                if guilded_success and roblox_success:
                    await message.add_reaction("🎯")  # Both platforms
                elif guilded_success:
                    await message.add_reaction("🟢")  # Guilded only
                elif roblox_success:
                    await message.add_reaction("🔶")  # Roblox only
                else:
                    await message.add_reaction("✅")  # Default success
            except discord.Forbidden:
                pass  # Bot doesn't have permission to react
        else:
            # Both failed
            try:
                await message.add_reaction("❌")
            except discord.Forbidden:
                pass
        
    except Exception as e:
        logger.error(f"❌ Error handling Discord update message: {e}")
        try:
            await message.add_reaction("❌")
        except discord.Forbidden:
            pass

async def setup_cross_posting():
    """Initialize cross-posting functionality"""
    if ENABLE_CROSS_POSTING:
        await cross_poster.init_session()
        logger.info("✅ Cross-posting functionality enabled")
        logger.info(f"   • Discord Updates Channel: {DISCORD_UPDATES_CHANNEL_ID}")
        logger.info(f"   • Guilded Server: {GUILDED_SERVER_ID}")
        logger.info(f"   • Guilded Announcements Channel: {GUILDED_ANNOUNCEMENTS_CHANNEL_ID}")
    else:
        logger.warning("⚠️ Cross-posting functionality disabled - check environment variables:")
        logger.warning(f"   • DISCORD_UPDATES_CHANNEL_ID: {'✅' if DISCORD_UPDATES_CHANNEL_ID else '❌'}")
        logger.warning(f"   • GUILDED_BOT_TOKEN: {'✅' if GUILDED_BOT_TOKEN else '❌'}")
        logger.warning(f"   • GUILDED_SERVER_ID: {'✅' if GUILDED_SERVER_ID else '❌'}")
        logger.warning(f"   • GUILDED_ANNOUNCEMENTS_CHANNEL_ID: {'✅' if GUILDED_ANNOUNCEMENTS_CHANNEL_ID else '❌'}")
    
    # Initialize Roblox posting
    if ENABLE_ROBLOX_POSTING:
        from roblox_integration import setup_roblox_posting
        await setup_roblox_posting()

async def cleanup_cross_posting():
    """Cleanup cross-posting resources"""
    await cross_poster.close_session()
    
    # Cleanup Roblox posting
    if ENABLE_ROBLOX_POSTING:
        from roblox_integration import cleanup_roblox_posting
        await cleanup_roblox_posting()
    
    logger.info("🔌 Cross-posting cleanup completed")
