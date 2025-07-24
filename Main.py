import discord
import asyncio
import os
from datetime import timedelta

intents = discord.Intents.default()
intents.message_content = True  # Needed to read message content

client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')

@client.event
async def on_message(message):
    if message.author == client.user:
        return  # Ignore messages from the bot itself
    
    if message.content.lower() == "?ban":
        # List of roles that can ban
        allowed_roles = ["Administrator", "Server Mod", "Head Moderator", "Trainee"]
        
        # Check if the user has any of the allowed roles
        user_has_permission = any(role.name in allowed_roles for role in message.author.roles)
        
        if user_has_permission:
            await message.channel.send("Who do you want to ban? Please mention them and attach evidence.")
            
            
            # Wait for the next message from the same user
            def check(msg):
                return msg.author == message.author and msg.channel == message.channel
            
            try:
                next_message = await client.wait_for('message', check=check, timeout=30.0)

                
                # Check if the message mentions a user
                if next_message.mentions:
                    user_to_ban = next_message.mentions[0]  # Get the first mentioned user
                    
                    # Check if the message contains a link OR has attachments (images)
                    has_link = "http://" in next_message.content or "https://" in next_message.content
                    has_attachment = len(next_message.attachments) > 0
                    
                    if has_link or has_attachment:
                        # Post the message content to a specific channel
                        log_channel_id = 1397806698596405268  # Replace with your channel ID
                        log_channel = client.get_channel(log_channel_id)

                        if log_channel:
                            # Send the text content first
                            await log_channel.send(f"{next_message.content} Banned by {message.author.mention}: ")
                            
                            # Send any attachments (images)
                            for attachment in next_message.attachments:
                                await log_channel.send(attachment.url)


                        try:
                            await message.guild.ban(user_to_ban, reason=f"Banned by {message.author}")
                            await message.channel.send(f"✅ {user_to_ban.mention} has been banned!")
                        except discord.Forbidden:
                            await message.channel.send("❌ I don't have permission to ban this user.")
                        except discord.HTTPException:
                            await message.channel.send("❌ Failed to ban the user.")
                        # Wait before deleting the message (5 seconds)
                        await asyncio.sleep(5)
                        
                        # Delete the user's message after delay
                        try:
                            await next_message.delete()
                        except discord.Forbidden:
                            pass  # Bot doesn't have permission to delete messages
                        except discord.NotFound:
                            pass  # Message was already deleted
                    else:
                        await message.channel.send("❌ Please provide a link or image as evidence before banning.")
                else:
                    await message.channel.send("❌ Please mention a valid user to ban.")
                
            except asyncio.TimeoutError:
                await message.channel.send("You took too long to respond!")

    if message.content.lower() == "?timeout":
            # List of roles that can timeout
            allowed_roles = ["Administrator", "Server Mod", "Head Moderator", "Trainee"]
            
            # Check if the user has any of the allowed roles
            user_has_permission = any(role.name in allowed_roles for role in message.author.roles)
            
            if user_has_permission:
                await message.channel.send("Who do you want to timeout? Please mention them and attach evidence.")
                
                # Wait for the next message from the same user
                def check(msg):
                    return msg.author == message.author and msg.channel == message.channel
                
                try:
                    next_message = await client.wait_for('message', check=check, timeout=30.0)
                    
                    # Check if the message mentions a user
                    if next_message.mentions:
                        user_to_timeout = next_message.mentions[0]  # Get the first mentioned user
                        
                        # Check if the message contains a link OR has attachments (images)
                        has_link = "http://" in next_message.content or "https://" in next_message.content
                        has_attachment = len(next_message.attachments) > 0
                        
                        if has_link or has_attachment:
                            # Ask for timeout duration
                            await message.channel.send("How long should the timeout be? (e.g., 10m, 1h, 2d)")
                            
                            # Wait for duration response
                            duration_message = await client.wait_for('message', check=check, timeout=30.0)
                            
                            # Parse duration
                            duration_text = duration_message.content.lower().strip()
                            timeout_duration = None
                            
                            if duration_text.endswith('m'):
                                minutes = int(duration_text[:-1])
                                timeout_duration = discord.utils.utcnow() + timedelta(minutes=minutes)
                            elif duration_text.endswith('h'):
                                hours = int(duration_text[:-1])
                                timeout_duration = discord.utils.utcnow() + timedelta(hours=hours)
                            elif duration_text.endswith('d'):
                                days = int(duration_text[:-1])
                                timeout_duration = discord.utils.utcnow() + timedelta(days=days)
                            else:
                                await message.channel.send("❌ Invalid duration format. Use 10m, 1h, or 2d")
                                return
                            
                            # Post the message content to a specific channel
                            log_channel_id = 1397806698596405268  # Replace with your channel ID
                            log_channel = client.get_channel(log_channel_id)

                            if log_channel:
                                # Send the text content first
                                await log_channel.send(f"{next_message.content} Timed out by {message.author.mention}: ")
                                
                                # Send any attachments (images)
                                for attachment in next_message.attachments:
                                    await log_channel.send(attachment.url)

                            try:
                                
                                await user_to_timeout.timeout(timeout_duration, reason=f"Timed out by {message.author}")
                                await message.channel.send(f"✅ {user_to_timeout.mention} has been timed out for {duration_text}")
                            except discord.Forbidden:
                                await message.channel.send("❌ I don't have permission to timeout this user.")
                            except discord.HTTPException:
                                await message.channel.send("❌ Failed to timeout the user.")
                            
                            # Wait before deleting the message (5 seconds)
                            await asyncio.sleep(5)
                            
                            # Delete the user's message after delay
                            try:
                                await next_message.delete()
                            except discord.Forbidden:
                                pass  # Bot doesn't have permission to delete messages
                            except discord.NotFound:
                                pass  # Message was already deleted
                        else:
                            await message.channel.send("❌ Please provide a link or image as evidence before timing out.")
                    else:
                        await message.channel.send("❌ Please mention a valid user to timeout.")
                    
                except asyncio.TimeoutError:
                    await message.channel.send("You took too long to respond!")

    if message.content.lower() == "?kick":
        # List of roles that can kick
        allowed_roles = ["Administrator", "Server Mod", "Head Moderator", "Trainee"]
        
        # Check if the user has any of the allowed roles
        user_has_permission = any(role.name in allowed_roles for role in message.author.roles)
        
        if user_has_permission:
            await message.channel.send("Who do you want to kick? Please mention them and attach evidence.")
            
            # Wait for the next message from the same user
            def check(msg):
                return msg.author == message.author and msg.channel == message.channel
            
            try:
                next_message = await client.wait_for('message', check=check, timeout=30.0)
                
                # Check if the message mentions a user
                if next_message.mentions:
                    user_to_kick = next_message.mentions[0]  # Get the first mentioned user
                    
                    # Check if the message contains a link OR has attachments (images)
                    has_link = "http://" in next_message.content or "https://" in next_message.content
                    has_attachment = len(next_message.attachments) > 0
                    
                    if has_link or has_attachment:
                        # Post the message content to a specific channel
                        log_channel_id = 1397806698596405268  # Replace with your channel ID
                        log_channel = client.get_channel(log_channel_id)

                        if log_channel:
                            # Send the text content first
                            await log_channel.send(f"{next_message.content} Kicked by {message.author.mention}: ")
                            
                            # Send any attachments (images)
                            for attachment in next_message.attachments:
                                await log_channel.send(attachment.url)

                        try:
                            await message.guild.kick(user_to_kick, reason=f"Kicked by {message.author}")
                            await message.channel.send(f"✅ {user_to_kick.mention} has been kicked!")
                        except discord.Forbidden:
                            await message.channel.send("❌ I don't have permission to kick this user.")
                        except discord.HTTPException:
                            await message.channel.send("❌ Failed to kick the user.")
                        
                        # Wait before deleting the message (5 seconds)
                        await asyncio.sleep(5)
                        
                        # Delete the user's message after delay
                        try:
                            await next_message.delete()
                        except discord.Forbidden:
                            pass  # Bot doesn't have permission to delete messages
                        except discord.NotFound:
                            pass  # Message was already deleted
                    else:
                        await message.channel.send("❌ Please provide a link or image as evidence before kicking.")
                else:
                    await message.channel.send("❌ Please mention a valid user to kick.")
                
            except asyncio.TimeoutError:
                await message.channel.send("You took too long to respond!")

# Get bot token from environment variable
bot_token = os.getenv('DISCORD_BOT_TOKEN')
if not bot_token:
    raise ValueError("DISCORD_BOT_TOKEN environment variable is not set")

client.run(bot_token)