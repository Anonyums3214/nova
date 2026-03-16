import discord
from discord.ext import commands, tasks
import asyncio
import os
import sys

# ==========================
# Load configuration from environment variables
# ==========================
TOKEN = os.getenv("TOKEN")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
PREFIX = os.getenv("PREFIX", "+")  # Default prefix is "+"

# ==========================
# Debug check to confirm env variables
# ==========================
if not TOKEN:
    print("ERROR: TOKEN environment variable not set!")
    sys.exit(1)

print(f"TOKEN loaded: {'Yes' if TOKEN else 'No'}")
print(f"YOUTUBE_API_KEY loaded: {'Yes' if YOUTUBE_API_KEY else 'No'}")
print(f"PREFIX loaded: {PREFIX}")

# ==========================
# Minimal intents
# ==========================
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

# ==========================
# Create bot
# ==========================
bot = commands.Bot(
    command_prefix=PREFIX,
    intents=intents,
    help_command=None
)

# ==========================
# Rotating statuses
# ==========================
statuses = [
    ("playing", "🎵 Music"),
    ("playing", "⚡ Powered by NOVA"),
    ("listening", f"{PREFIX}play <song>"),
    ("watching", "🌍 Servers")
]

@tasks.loop(seconds=40)
async def rotate_status():
    for status_type, text in statuses:
        if status_type == "playing":
            activity = discord.Game(name=text)
        elif status_type == "listening":
            activity = discord.Activity(
                type=discord.ActivityType.listening,
                name=text
            )
        elif status_type == "watching":
            activity = discord.Activity(
                type=discord.ActivityType.watching,
                name=text
            )
        await bot.change_presence(
            status=discord.Status.dnd,
            activity=activity
        )
        await asyncio.sleep(10)

# ==========================
# Bot ready event
# ==========================
@bot.event
async def on_ready():
    print(f"NOVA Music Bot Online as {bot.user}")
    if not rotate_status.is_running():
        rotate_status.start()

# ==========================
# Async startup
# ==========================
async def main():
    async with bot:
        await bot.load_extension("music")  # make sure music.py exists
        await bot.start(TOKEN)

# ==========================
# Run bot
# ==========================
asyncio.run(main())