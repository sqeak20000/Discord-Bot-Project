import aiohttp
import asyncio
import logging
import json
from config import ROBLOX_COOKIE, ROBLOX_GROUP_ID, ENABLE_ROBLOX_POSTING

# Setup logging for Roblox posting
logger = logging.getLogger('roblox')

class RobloxPoster:
    """Handles posting messages to Roblox group"""
    
    def __init__(self):
        self.session = None
        self.csrf_token = None
        self.cookies = {
            '.ROBLOSECURITY': ROBLOX_COOKIE
        }
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Content-Type': 'application/json'
        }
    
    async def init_session(self):
        """Initialize aiohttp session and get CSRF token"""
        if not self.session:
            self.session = aiohttp.ClientSession(cookies=self.cookies)
            await self._get_csrf_token()
    
    async def close_session(self):
        """Close aiohttp session"""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def _get_csrf_token(self):
        """Get CSRF token required for Roblox API requests"""
        try:
            # Make a request to get CSRF token from headers
            async with self.session.post('https://auth.roblox.com/v2/logout') as response:
                if 'x-csrf-token' in response.headers:
                    self.csrf_token = response.headers['x-csrf-token']
                    self.headers['x-csrf-token'] = self.csrf_token
                    logger.info("✅ Successfully obtained CSRF token")
                else:
                    logger.error("❌ Failed to get CSRF token")
                    
        except Exception as e:
            logger.error(f"❌ Error getting CSRF token: {e}")
    
    async def post_to_group_shout(self, message):
        """Post a message as group shout"""
        if not ENABLE_ROBLOX_POSTING:
            logger.warning("Roblox posting is disabled - missing configuration")
            return False
        
        await self.init_session()
        
        if not self.csrf_token:
            logger.error("❌ No CSRF token available")
            return False
        
        try:
            # Roblox group shout API endpoint
            url = f"https://groups.roblox.com/v1/groups/{ROBLOX_GROUP_ID}/status"
            
            # Truncate message to Roblox's character limit (255 chars for shouts)
            truncated_message = message[:255] if len(message) > 255 else message
            
            payload = {
                'message': truncated_message
            }
            
            logger.info(f"Posting to Roblox group shout: {url}")
            logger.info(f"Payload: {payload}")
            
            async with self.session.patch(url, json=payload, headers=self.headers) as response:
                response_text = await response.text()
                logger.info(f"Response status: {response.status}")
                logger.info(f"Response text: {response_text}")
                
                if response.status == 200:
                    logger.info("✅ Successfully posted to Roblox group shout")
                    return True
                else:
                    logger.error(f"❌ Failed to post to Roblox: {response.status} - {response_text}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Error posting to Roblox: {e}")
            return False
    
    async def post_to_group_wall(self, message):
        """Post a message to group wall"""
        if not ENABLE_ROBLOX_POSTING:
            logger.warning("Roblox posting is disabled - missing configuration")
            return False
        
        await self.init_session()
        
        if not self.csrf_token:
            logger.error("❌ No CSRF token available")
            return False
        
        try:
            # Roblox group wall post API endpoint
            url = f"https://groups.roblox.com/v2/groups/{ROBLOX_GROUP_ID}/wall/posts"
            
            # Truncate message to Roblox's character limit (500 chars for wall posts)
            truncated_message = message[:500] if len(message) > 500 else message
            
            payload = {
                'body': truncated_message
            }
            
            logger.info(f"Posting to Roblox group wall: {url}")
            logger.info(f"Payload: {payload}")
            
            async with self.session.post(url, json=payload, headers=self.headers) as response:
                response_text = await response.text()
                logger.info(f"Response status: {response.status}")
                logger.info(f"Response text: {response_text}")
                
                if response.status == 200:
                    logger.info("✅ Successfully posted to Roblox group wall")
                    return True
                else:
                    logger.error(f"❌ Failed to post to Roblox wall: {response.status} - {response_text}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Error posting to Roblox wall: {e}")
            return False
    
    async def get_user_info(self):
        """Get information about the authenticated user"""
        await self.init_session()
        
        try:
            url = "https://users.roblox.com/v1/users/authenticated"
            
            async with self.session.get(url, headers=self.headers) as response:
                if response.status == 200:
                    user_data = await response.json()
                    return user_data
                else:
                    logger.error(f"Failed to get user info: {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error getting user info: {e}")
            return None
    
    async def get_group_info(self):
        """Get information about the group"""
        await self.init_session()
        
        try:
            url = f"https://groups.roblox.com/v1/groups/{ROBLOX_GROUP_ID}"
            
            async with self.session.get(url, headers=self.headers) as response:
                if response.status == 200:
                    group_data = await response.json()
                    return group_data
                else:
                    logger.error(f"Failed to get group info: {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error getting group info: {e}")
            return None

# Global instance
roblox_poster = RobloxPoster()

async def format_message_for_roblox(content, title=None):
    """Format Discord message content for Roblox posting"""
    # Clean up Discord formatting
    formatted = content.replace('**', '').replace('*', '').replace('`', '')
    
    # Remove Discord mentions and channels
    import re
    formatted = re.sub(r'<@!?\d+>', '', formatted)  # Remove user mentions
    formatted = re.sub(r'<#\d+>', '', formatted)    # Remove channel mentions
    formatted = re.sub(r'<:\w+:\d+>', '', formatted) # Remove custom emojis
    
    # Clean up extra whitespace
    formatted = ' '.join(formatted.split())
    
    # Add title if provided
    if title:
        clean_title = title.replace('**', '').replace('`', '').strip()
        formatted = f"{clean_title}\n\n{formatted}"
    
    return formatted

async def setup_roblox_posting():
    """Initialize Roblox posting functionality"""
    if ENABLE_ROBLOX_POSTING:
        await roblox_poster.init_session()
        logger.info("✅ Roblox posting functionality enabled")
        logger.info(f"   • Roblox Group ID: {ROBLOX_GROUP_ID}")
        
        # Test authentication
        user_info = await roblox_poster.get_user_info()
        if user_info:
            logger.info(f"   • Authenticated as: {user_info.get('name', 'Unknown')} (ID: {user_info.get('id', 'Unknown')})")
        else:
            logger.warning("   • Failed to authenticate with Roblox")
            
        # Get group info
        group_info = await roblox_poster.get_group_info()
        if group_info:
            logger.info(f"   • Target Group: {group_info.get('name', 'Unknown')}")
        
    else:
        logger.warning("⚠️ Roblox posting functionality disabled - check environment variables:")
        logger.warning(f"   • ROBLOX_COOKIE: {'✅' if ROBLOX_COOKIE else '❌'}")
        logger.warning(f"   • ROBLOX_GROUP_ID: {'✅' if ROBLOX_GROUP_ID else '❌'}")

async def cleanup_roblox_posting():
    """Cleanup Roblox posting resources"""
    await roblox_poster.close_session()
    logger.info("🔌 Roblox posting cleanup completed")
