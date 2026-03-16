import discord
from discord.ext import commands, tasks
import asyncio
import os
import sys

# ==========================
# FIXED Environment variable loading
# ==========================
try:
    TOKEN = str(os.environ["TOKEN"])  # Raises KeyError if missing
except KeyError:
    print("ERROR: TOKEN environment variable not set!")
    sys.exit(1)

YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY", "")
PREFIX = os.environ.get("PREFIX", "+")

print("✅ TOKEN loaded successfully")
print(f"PREFIX: {PREFIX}")
print(f"YOUTUBE_API_KEY loaded: {'Yes' if YOUTUBE_API_KEY else 'No'}")

# ==========================
# Intents
# ==========================
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

# ==========================
# Bot setup
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
# Ready event
# ==========================
@bot.event
async def on_ready():
    print(f"NOVA Music Bot Online as {bot.user}")
    if not rotate_status.is_running():
        rotate_status.start()

# ==========================
# Async main
# ==========================
async def main():
    async with bot:
        try:
            await bot.load_extension("music")  # Make sure music.py is in the same folder or adjust path
        except Exception as e:
            print(f"Failed to load music cog: {e}")
        await bot.start(TOKEN)

# ==========================
# Run
# ==========================
if __name__ == "__main__":
    asyncio.run(main())