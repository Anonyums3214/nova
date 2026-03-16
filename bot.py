import discord
from discord.ext import commands, tasks
import json
import asyncio
import os

# Load configuration
with open("config.json") as f:
    config = json.load(f)

TOKEN = os.getenv("TOKEN")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

# Minimal intents
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

# Create bot
bot = commands.Bot(
    command_prefix=config["prefix"],
    intents=intents,
    help_command=None
)

# Rotating statuses
statuses = [
    ("playing", "🎵 Music"),
    ("playing", "⚡ Powered by NOVA"),
    ("listening", "+play <song>"),
    ("watching", "🌍 Servers")
]

# Rotating status task
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

# Bot ready event
@bot.event
async def on_ready():

    print(f"NOVA Music Bot Online as {bot.user}")

    if not rotate_status.is_running():
        rotate_status.start()

# Async startup
async def main():
    async with bot:
        await bot.load_extension("music")
        await bot.start(TOKEN)

# Run bot
asyncio.run(main())