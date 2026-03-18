import discord
from discord.ext import commands
import yt_dlp
import asyncio
import random
import time
import os

queues = {}
loops = {}
bass_enabled = {}
volumes = {}
current_song = {}
start_times = {}
restart_flags = {}
filters = {}
durations = {}

# On Railway → ffmpeg is in PATH after apt install
FFMPEG_PATH = os.getenv("FFMPEG_PATH", "ffmpeg")   # "ffmpeg" = use system one

YDL_OPTIONS = {
    "format": "bestaudio/best",
    "quiet": True,
    "no_warnings": True,
    "default_search": "ytsearch",
    "extract_flat": False,          # important
}

FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn"
}

def format_time(seconds):
    m, s = divmod(int(seconds), 60)
    return f"{m:02d}:{s:02d}"


class FilterDropdown(discord.ui.Select):
    def __init__(self, ctx):
        options = [
            discord.SelectOption(label="Normal", description="No filter"),
            discord.SelectOption(label="8D", description="8D surround effect"),
            discord.SelectOption(label="Nightcore", description="Nightcore speed"),
            discord.SelectOption(label="Vaporwave", description="Slow vaporwave")
        ]
        super().__init__(placeholder="Audio Filter", options=options)
        self.ctx = ctx

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild.id
        vc = interaction.guild.voice_client

        if not vc or guild not in current_song:
            return await interaction.response.send_message("Nothing playing", ephemeral=True)

        filters[guild] = self.values[0]
        url, title, thumb = current_song[guild]
        elapsed = int(time.time() - start_times[guild])

        restart_flags[guild] = "restart"
        vc.stop()

        await self.ctx.cog.play_audio(self.ctx, url, title, thumb, start=elapsed)
        await interaction.response.send_message(f"Filter set to {self.values[0]}", ephemeral=True)


class PlayerButtons(discord.ui.View):
    def __init__(self, ctx):
        super().__init__(timeout=None)
        self.ctx = ctx
        self.add_item(FilterDropdown(ctx))

    @discord.ui.button(label="⏸ Pause", style=discord.ButtonStyle.primary)
    async def pause(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client
        if vc:
            if vc.is_playing():
                vc.pause()
                await interaction.response.send_message("Paused", ephemeral=True)
            elif vc.is_paused():
                vc.resume()
                await interaction.response.send_message("Resumed", ephemeral=True)

    @discord.ui.button(label="⏭ Skip", style=discord.ButtonStyle.secondary)
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client
        if vc:
            restart_flags[interaction.guild.id] = "skip"
            vc.stop()
            await interaction.response.send_message("Skipped", ephemeral=True)

    @discord.ui.button(label="⏹ Stop", style=discord.ButtonStyle.danger)
    async def stop(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client
        if vc:
            await vc.disconnect(force=True)
            await interaction.response.send_message("Disconnected", ephemeral=True)

    @discord.ui.button(label="🎚 Bass", style=discord.ButtonStyle.success)
    async def bass(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild.id
        vc = interaction.guild.voice_client

        if not vc or guild not in current_song:
            return await interaction.response.send_message("Nothing playing", ephemeral=True)

        bass_enabled[guild] = not bass_enabled.get(guild, False)

        url, title, thumb = current_song[guild]
        elapsed = int(time.time() - start_times[guild])

        restart_flags[guild] = "restart"
        vc.stop()

        await self.ctx.cog.play_audio(self.ctx, url, title, thumb, start=elapsed)

        state = "Enabled" if bass_enabled[guild] else "Disabled"
        await interaction.response.send_message(f"Bass {state}", ephemeral=True)


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def play_audio(self, ctx, url, title, thumb, start=0):
        guild = ctx.guild.id

        if not ctx.voice_client:
            await ctx.send("Bot is not connected to voice channel!")
            return

        vc: discord.VoiceClient = ctx.voice_client

        bass = bass_enabled.get(guild, False)
        volume = volumes.get(guild, 100)
        filter_type = filters.get(guild, "Normal")

        af = []
        if bass:
            af.append("bass=g=15")
        if filter_type == "8D":
            af.append("apulsator=hz=0.125")
        elif filter_type == "Nightcore":
            af.append("asetrate=48000*1.25,atempo=1.1")
        elif filter_type == "Vaporwave":
            af.append("asetrate=48000*0.8,atempo=0.8")

        options = "-vn"
        if af:
            options += f" -af {','.join(af)}"

        ffmpeg_opts = FFMPEG_OPTIONS.copy()
        ffmpeg_opts["before_options"] += f" -ss {start}"

        try:
            source = discord.PCMVolumeTransformer(
                discord.FFmpegPCMAudio(
                    url,
                    executable=FFMPEG_PATH,
                    before_options=ffmpeg_opts["before_options"],
                    options=options
                ),
                volume=volume / 100.0
            )

            def after_playing(error):
                if error:
                    print(f"Player error: {error}")
                asyncio.run_coroutine_threadsafe(self.after_song(ctx), self.bot.loop)

            vc.play(source, after=after_playing)

            start_times[guild] = time.time() - start
            current_song[guild] = (url, title, thumb)

            bass_state = "On" if bass else "Off"
            elapsed = format_time(time.time() - start_times[guild])
            duration = format_time(durations.get(guild, 0))

            embed = discord.Embed(
                title="🎵 Now Playing",
                description=f"**{title}**",
                color=discord.Color.blurple()
            )
            embed.set_thumbnail(url=thumb)
            embed.add_field(name="⏱ Duration", value=f"{elapsed} / {duration}", inline=False)
            embed.add_field(name="Volume", value=f"{volume}%", inline=True)
            embed.add_field(name="Bass", value=bass_state, inline=True)
            embed.add_field(name="Filter", value=filter_type, inline=True)

            await ctx.send(embed=embed, view=PlayerButtons(ctx))

        except Exception as e:
            await ctx.send(f"Error playing audio: {e}")
            print(f"Play error: {e}")

    async def after_song(self, ctx):
        guild = ctx.guild.id
        flag = restart_flags.pop(guild, None)

        if flag == "restart":
            return

        if flag == "skip":
            await self.play_next(ctx)
            return

        await self.play_next(ctx)

    async def play_next(self, ctx):
        guild = ctx.guild.id

        if loops.get(guild) and current_song.get(guild):
            queues.setdefault(guild, []).insert(0, current_song[guild])

        if not queues.get(guild):
            if ctx.voice_client:
                await ctx.voice_client.disconnect()
            return

        url, title, thumb = queues[guild].pop(0)
        await self.play_audio(ctx, url, title, thumb)

    @commands.command()
    async def play(self, ctx, *, search: str = None):
        if not search:
            return await ctx.send("Please provide a song name or URL")

        if not ctx.author.voice:
            return await ctx.send("You must be in a voice channel")

        channel = ctx.author.voice.channel

        if not ctx.voice_client:
            try:
                await channel.connect()
                await ctx.send(f"Joined **{channel.name}**")
            except Exception as e:
                return await ctx.send(f"Cannot join voice channel: {e}")
        elif ctx.voice_client.channel != channel:
            await ctx.voice_client.move_to(channel)
            await ctx.send(f"Moved to **{channel.name}**")

        await ctx.send(f"Searching: **{search}** ...")

        try:
            with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
                info = ydl.extract_info(search, download=False)
                if "entries" in info:
                    info = info["entries"][0]
                url = info.get("url") or info.get("formats", [{}])[0].get("url")
                title = info.get("title", "Unknown")
                thumb = info.get("thumbnail", "")
                duration = info.get("duration", 0)

            if not url:
                return await ctx.send("Could not extract playable URL")

            queues.setdefault(ctx.guild.id, []).append((url, title, thumb))
            durations[ctx.guild.id] = duration

            await ctx.send(f"Added to queue: **{title}**")

            if not ctx.voice_client.is_playing() and not ctx.voice_client.is_paused():
                await self.play_next(ctx)

        except Exception as e:
            await ctx.send(f"Error searching/playing: {str(e)}")
            print(f"Play command error: {e}")

    # ─── other commands (volume, bass, skip, pause, resume, queue, shuffle, loop, leave, help) ───
    # keep them exactly as you had, just make sure to use ctx.voice_client consistently

    @commands.command()
    async def leave(self, ctx):
        if ctx.voice_client:
            await ctx.voice_client.disconnect()
            await ctx.send("Left voice channel")
        else:
            await ctx.send("Not in a voice channel")

    # ... add your other commands here ...

async def setup(bot):
    await bot.add_cog(Music(bot))