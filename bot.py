import discord
from discord.ext import commands, tasks
import asyncio
import os

# ────────────────────────────── Config from env (Railway) ──────────────────────────────
config = {
    "token": os.getenv("TOKEN"),
    "youtube_api": os.getenv("YOUTUBE_API"),  # not used yet, but kept
    "prefix": os.getenv("PREFIX", "+")
}

if not config["token"]:
    print("ERROR: TOKEN environment variable is missing!")
    exit(1)

# Intents – very important in 2025
intents = discord.Intents.default()
intents.message_content = True      # required for reading messages
intents.voice_states = True
intents.members = True              # helps with voice state tracking

bot = commands.Bot(
    command_prefix=config["prefix"],
    intents=intents,
    help_command=None
)

# Rotating status
statuses = [
    ("playing", "🎵 Music"),
    ("playing", "⚡ Powered by NOVA"),
    ("listening", f"{config['prefix']}play <song>"),
    ("watching", "🌍 Servers")
]

@tasks.loop(seconds=40)
async def rotate_status():
    for status_type, text in statuses:
        if status_type == "playing":
            activity = discord.Game(name=text)
        elif status_type == "listening":
            activity = discord.Activity(type=discord.ActivityType.listening, name=text)
        elif status_type == "watching":
            activity = discord.Activity(type=discord.ActivityType.watching, name=text)

        await bot.change_presence(status=discord.Status.dnd, activity=activity)
        await asyncio.sleep(10)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("------")
    if not rotate_status.is_running():
        rotate_status.start()

async def main():
    async with bot:
        await bot.load_extension("music")
        await bot.start(config["token"])

if __name__ == "__main__":
    asyncio.run(main())