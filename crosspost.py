import discord
import aiohttp
import asyncio
import logging
from config import (
    GUILDED_BOT_TOKEN, 
    GUILDED_SERVER_ID, 
    GUILDED_ANNOUNCEMENTS_CHANNEL_ID,
    DISCORD_UPDATES_CHANNEL_ID,
    ENABLE_CROSS_POSTING
)

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
    
    async def send_to_guilded(self, content, embeds=None, attachments=None):
        """Send a message to the Guilded announcements channel"""
        if not ENABLE_CROSS_POSTING:
            logger.warning("Cross-posting is disabled - missing configuration")
            return False
        
        await self.init_session()
        
        try:
            # Prepare the message payload
            payload = {
                'content': content,
                'isPublic': True,  # Make announcement public
                'isSilent': False  # Don't silence the notification
            }
            
            # Add embeds if provided
            if embeds:
                payload['embeds'] = embeds
            
            # Send message to Guilded
            url = f"{self.guilded_base_url}/channels/{GUILDED_ANNOUNCEMENTS_CHANNEL_ID}/messages"
            
            async with self.session.post(url, json=payload, headers=self.guilded_headers) as response:
                if response.status == 200 or response.status == 201:
                    logger.info(f"✅ Successfully cross-posted message to Guilded")
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"❌ Failed to send to Guilded: {response.status} - {error_text}")
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
        
        # Add author attribution
        author_info = f"**📢 Update from Discord** (by {message.author.display_name})\n\n"
        content = author_info + content
        
        # Convert embeds
        guilded_embeds = []
        if message.embeds:
            for embed in message.embeds:
                guilded_embed = await cross_poster.convert_discord_embed_to_guilded(embed)
                guilded_embeds.append(guilded_embed)
        
        # Handle attachments (convert to links)
        if message.attachments:
            attachment_text = "\n\n**📎 Attachments:**\n"
            for i, attachment in enumerate(message.attachments, 1):
                attachment_text += f"{i}. [{attachment.filename}]({attachment.url})\n"
            content += attachment_text
        
        # Cross-post to Guilded
        success = await cross_poster.send_to_guilded(
            content=content,
            embeds=guilded_embeds if guilded_embeds else None
        )
        
        if success:
            # React to the original message to show it was cross-posted
            try:
                await message.add_reaction("✅")
            except discord.Forbidden:
                pass  # Bot doesn't have permission to react
        
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

async def cleanup_cross_posting():
    """Cleanup cross-posting resources"""
    await cross_poster.close_session()
    logger.info("🔌 Cross-posting cleanup completed")
