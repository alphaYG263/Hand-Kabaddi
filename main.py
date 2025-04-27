import discord
from discord.ext import commands
import asyncio
import os
from datetime import datetime, timedelta

# Bot configuration
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix=".", intents=intents)

# In-memory data structures
active_matches = {}  # key: channel_id, value: match data
user_match_map = {}  # key: user_id, value: channel_id

# Helper function to cleanup timed out matches
async def check_match_timeouts():
    while True:
        current_time = datetime.now()
        channels_to_clean = []
        
        for channel_id, match in active_matches.items():
            if not match['has_started'] and (current_time - match['time_created']).total_seconds() > 300:
                channels_to_clean.append(channel_id)
                
        for channel_id in channels_to_clean:
            match = active_matches[channel_id]
            # Remove all users from user_match_map
            for player_id in match['players']:
                if player_id in user_match_map:
                    del user_match_map[player_id]
            
            # Remove match from active_matches
            del active_matches[channel_id]
            
            # Notify about timeout
            channel = bot.get_channel(channel_id)
            if channel:
                await channel.send("Match timed out after 300 seconds of inactivity and has been deleted.")
        
        await asyncio.sleep(10)  # Check every 10 seconds

@bot.event
async def on_ready():
    print(f"{bot.user.name} is online and ready!")
    # Start the background task for match timeouts
    bot.loop.create_task(check_match_timeouts())

# Load all cog files
async def load_extensions():
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            await bot.load_extension(f"cogs.{filename[:-3]}")
            print(f"Loaded extension: {filename[:-3]}")

# Run the bot
async def main():
    await load_extensions()
    TOKEN = "token"  # Replace with your actual bot token
    await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
