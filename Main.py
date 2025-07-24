import discord
from config import BOT_TOKEN
from moderation import handle_ban_command, handle_kick_command, handle_timeout_command

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
    
    # Command routing
    command = message.content.lower()
    
    if command == "?ban":
        await handle_ban_command(client, message)
    elif command == "?kick":
        await handle_kick_command(client, message)
    elif command == "?timeout":
        await handle_timeout_command(client, message)

if __name__ == "__main__":
    client.run(BOT_TOKEN)