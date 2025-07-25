#!/usr/bin/env python3
"""
Rate limit monitoring script to help diagnose Discord API rate limiting issues.
This will show you what API calls your bot is making and help identify the source of rate limits.
"""

import asyncio
import discord
from discord.ext import commands
from config import BOT_TOKEN
import time
from datetime import datetime

class RateLimitMonitor:
    def __init__(self):
        self.api_calls = []
        self.rate_limits = []
        
    def log_api_call(self, method, url, status_code):
        """Log API calls for monitoring"""
        timestamp = datetime.now()
        self.api_calls.append({
            'timestamp': timestamp,
            'method': method,
            'url': url,
            'status': status_code
        })
        
        # Keep only last 100 calls
        if len(self.api_calls) > 100:
            self.api_calls.pop(0)
            
        print(f"[{timestamp.strftime('%H:%M:%S')}] {method} {url} -> {status_code}")
        
    def log_rate_limit(self, retry_after, bucket):
        """Log rate limit events"""
        timestamp = datetime.now()
        self.rate_limits.append({
            'timestamp': timestamp,
            'retry_after': retry_after,
            'bucket': bucket
        })
        
        print(f"🚨 [{timestamp.strftime('%H:%M:%S')}] RATE LIMITED! Bucket: {bucket}, Retry after: {retry_after}s")
        
    def get_recent_activity(self, minutes=5):
        """Get API activity from the last N minutes"""
        cutoff = datetime.now().timestamp() - (minutes * 60)
        recent_calls = [call for call in self.api_calls if call['timestamp'].timestamp() > cutoff]
        return recent_calls

# Create global monitor
monitor = RateLimitMonitor()

# Custom HTTP client to monitor API calls
class MonitoredHTTPClient(discord.http.HTTPClient):
    async def request(self, route, **kwargs):
        start_time = time.time()
        try:
            response = await super().request(route, **kwargs)
            monitor.log_api_call(route.method, route.url, response.status)
            return response
        except discord.HTTPException as e:
            monitor.log_api_call(route.method, route.url, e.status)
            if e.status == 429:
                retry_after = getattr(e.response, 'headers', {}).get('Retry-After', 'unknown')
                monitor.log_rate_limit(retry_after, route.bucket)
            raise

async def monitor_bot():
    """Run bot with rate limit monitoring"""
    intents = discord.Intents.default()
    intents.message_content = True
    
    # Create bot with custom HTTP client
    bot = commands.Bot(command_prefix='!', intents=intents)
    bot.http = MonitoredHTTPClient()
    
    @bot.event
    async def on_ready():
        print(f'🤖 Rate Limit Monitor started for {bot.user}')
        print("Monitoring Discord API calls...")
        print("=" * 50)
        
        # Monitor for rate limit patterns
        while True:
            await asyncio.sleep(30)  # Check every 30 seconds
            
            recent = monitor.get_recent_activity(1)  # Last 1 minute
            if len(recent) > 10:  # More than 10 calls per minute might be concerning
                print(f"⚠️  High API activity: {len(recent)} calls in last minute")
                
                # Show breakdown by endpoint
                endpoints = {}
                for call in recent:
                    endpoint = call['url'].split('?')[0]  # Remove query params
                    endpoints[endpoint] = endpoints.get(endpoint, 0) + 1
                    
                print("📊 Endpoint breakdown:")
                for endpoint, count in sorted(endpoints.items(), key=lambda x: x[1], reverse=True):
                    if count > 2:  # Only show endpoints with multiple calls
                        print(f"   {endpoint}: {count} calls")
                print()
    
    @bot.event
    async def on_message(message):
        if message.author == bot.user:
            return
            
        # Log message events (these can trigger API calls)
        if message.content.startswith('!'):
            print(f"💬 Command received: {message.content[:50]}...")
    
    # Add a simple command to test rate limits
    @bot.command(name='ping')
    async def ping_cmd(ctx):
        """Simple ping command for testing"""
        await ctx.send("🏓 Pong! Bot is responsive.")
    
    @bot.command(name='activity')
    async def activity_cmd(ctx):
        """Show recent API activity"""
        recent = monitor.get_recent_activity(5)
        rate_limits = [rl for rl in monitor.rate_limits if (datetime.now() - rl['timestamp']).seconds < 300]
        
        embed = discord.Embed(title="📊 API Activity Report", color=discord.Color.blue())
        embed.add_field(name="API Calls (5 min)", value=str(len(recent)), inline=True)
        embed.add_field(name="Rate Limits (5 min)", value=str(len(rate_limits)), inline=True)
        
        if rate_limits:
            last_rl = rate_limits[-1]
            embed.add_field(name="Last Rate Limit", 
                          value=f"{last_rl['timestamp'].strftime('%H:%M:%S')}\nBucket: {last_rl['bucket']}", 
                          inline=True)
        
        await ctx.send(embed=embed)
    
    try:
        await bot.start(BOT_TOKEN)
    except KeyboardInterrupt:
        print("\n🛑 Monitor stopped by user")
    except Exception as e:
        print(f"❌ Monitor error: {e}")
    finally:
        await bot.close()

if __name__ == "__main__":
    print("🔍 Discord Bot Rate Limit Monitor")
    print("This will show you what API calls your bot is making.")
    print("Press Ctrl+C to stop monitoring.")
    print()
    
    try:
        asyncio.run(monitor_bot())
    except KeyboardInterrupt:
        print("\n👋 Monitoring stopped.")
