import discord
from discord.ext import commands
import yt_dlp
import asyncio
import random
import time
import os   # ← ADDED (only this)

queues = {}
loops = {}
bass_enabled = {}
volumes = {}
current_song = {}
start_times = {}
restart_flags = {}
filters = {}
durations = {}

# ← CHANGED ONLY THIS LINE (keeps your original Windows path as fallback)
FFMPEG_PATH = os.getenv("FFMPEG_PATH", r"C:\Users\hp\Downloads\ffmpeg\bin\ffmpeg.exe")

YDL_OPTIONS = {
    "format": "bestaudio/best",
    "quiet": True,
    "cookiefile": os.path.join(os.getcwd(), "cookies.txt"),  # ✅ FIXED PATH
    "nocheckcertificate": True,
    "ignoreerrors": False,
    "default_search": "ytsearch",
    "source_address": "0.0.0.0"
}

# ────────────────────────────────────────────────
#     ADDED FOR YOUTUBE "SIGN IN" / BOT DETECTION FIX
# ────────────────────────────────────────────────
COOKIES_FILE = "cookies.txt"           # put cookies.txt in the same folder as this file

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

        if vc and vc.is_playing():
            vc.pause()
            await interaction.response.send_message("Paused", ephemeral=True)

        elif vc and vc.is_paused():
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
            await vc.disconnect()
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

        bass = bass_enabled.get(guild, False)
        volume = volumes.get(guild, 100)
        filter_type = filters.get(guild, "Normal")

        options = "-vn"
        af = []

        if bass:
            af.append("bass=g=15")

        if filter_type == "8D":
            af.append("apulsator=hz=0.125")

        elif filter_type == "Nightcore":
            af.append("asetrate=48000*1.25,atempo=1.1")

        elif filter_type == "Vaporwave":
            af.append("asetrate=48000*0.8,atempo=0.8")

        if af:
            options += f" -af {','.join(af)}"

        before_opts = f"-ss {start} -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"

        source = discord.PCMVolumeTransformer(
            discord.FFmpegPCMAudio(
                url,
                executable=FFMPEG_PATH,
                before_options=before_opts,
                options=options
            ),
            volume=volume / 100
        )

        def after_playing(error):

            fut = asyncio.run_coroutine_threadsafe(
                self.after_song(ctx),
                self.bot.loop
            )

            try:
                fut.result()
            except:
                pass

        ctx.voice_client.play(source, after=after_playing)

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


    async def after_song(self, ctx):

        guild = ctx.guild.id
        flag = restart_flags.get(guild)

        if flag == "restart":
            restart_flags[guild] = None
            return

        if flag == "skip":
            restart_flags[guild] = None
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
    async def play(self, ctx, *, search):

        if not ctx.author.voice:
            return await ctx.send("Join a voice channel")

        vc = ctx.voice_client

        if not vc:
            vc = await ctx.author.voice.channel.connect()

        # ────────────────────────────────────────────────
        #     ADDED: use cookies to bypass "Sign in to confirm you're not a bot"
        # ────────────────────────────────────────────────
        ydl_opts = YDL_OPTIONS.copy()
        ydl_opts["cookiefile"] = COOKIES_FILE

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f"ytsearch:{search}", download=False)["entries"][0]


            formats = info.get("formats", [])
            audio_url = None

            for f in formats:
                if f.get("acodec") != "none":
                    audio_url = f.get("url")
                break

            if not audio_url:
                raise Exception("No audio stream found")

            url = audio_url
            title = info["title"]
            thumb = info["thumbnail"]
            duration = info["duration"]

            queues.setdefault(ctx.guild.id, [])
            queues[ctx.guild.id].append((url, title, thumb))

            durations[ctx.guild.id] = duration

            await ctx.send(f"Added to queue: **{title}**")

            if not vc.is_playing():
                await self.play_next(ctx)

        except Exception as e:
            await ctx.send(
                "Error searching/playing song.\n\n"
                "If you see 'Sign in to confirm you’re not a bot':\n"
                "→ cookies.txt file is missing, old, or invalid.\n"
                "→ Update cookies.txt and redeploy the bot."
            )
            print("yt-dlp error:", str(e))


    @commands.command()
    async def volume(self, ctx, vol: int):

        if vol < 0 or vol > 500:
            return await ctx.send("Volume must be between 0 and 500")

        vc = ctx.voice_client

        if not vc:
            return await ctx.send("Bot not in voice channel")

        volumes[ctx.guild.id] = vol

        if vc.source:
            vc.source.volume = vol / 100

        await ctx.send(f"🔊 Volume set to {vol}%")


    @commands.command()
    async def bass(self, ctx):

        guild = ctx.guild.id
        vc = ctx.voice_client

        if not vc or guild not in current_song:
            return await ctx.send("Nothing playing")

        bass_enabled[guild] = not bass_enabled.get(guild, False)

        url, title, thumb = current_song[guild]

        elapsed = int(time.time() - start_times[guild])

        restart_flags[guild] = "restart"

        vc.stop()

        await self.play_audio(ctx, url, title, thumb, start=elapsed)

        state = "Enabled" if bass_enabled[guild] else "Disabled"
        await ctx.send(f"Bass {state}")


    @commands.command()
    async def help(self, ctx):

        embed = discord.Embed(
            title="🎵 Music Bot Help",
            description="Available Commands",
            color=discord.Color.blurple()
        )

        embed.add_field(
            name="Music",
            value="""
`+play <song>`
`+skip`
`+pause`
`+resume`
`+leave`
""",
            inline=False
        )

        embed.add_field(
            name="Audio",
            value="""
`+volume <0-500>`
`+bass`
Filters: 8D, Nightcore, Vaporwave
""",
            inline=False
        )

        embed.add_field(
            name="Queue",
            value="""
`+queue`
`+shuffle`
`+loop`
""",
            inline=False
        )

        await ctx.send(embed=embed)


    @commands.command()
    async def skip(self, ctx):

        vc = ctx.voice_client

        if vc:
            restart_flags[ctx.guild.id] = "skip"
            vc.stop()


    @commands.command()
    async def pause(self, ctx):

        vc = ctx.voice_client
        if vc:
            vc.pause()


    @commands.command()
    async def resume(self, ctx):

        vc = ctx.voice_client
        if vc:
            vc.resume()


    @commands.command()
    async def queue(self, ctx):

        if not queues.get(ctx.guild.id):
            return await ctx.send("Queue empty")

        embed = discord.Embed(title="Queue")

        for i, (_, title, _) in enumerate(queues[ctx.guild.id][:10], 1):
            embed.add_field(name=f"{i}.", value=title, inline=False)

        await ctx.send(embed=embed)


    @commands.command()
    async def shuffle(self, ctx):

        if queues.get(ctx.guild.id):
            random.shuffle(queues[ctx.guild.id])
            await ctx.send("Queue shuffled")


    @commands.command()
    async def loop(self, ctx):

        guild = ctx.guild.id
        loops[guild] = not loops.get(guild, False)

        await ctx.send(f"Loop {'Enabled' if loops[guild] else 'Disabled'}")


    @commands.command()
    async def leave(self, ctx):

        vc = ctx.voice_client
        if vc:
            await vc.disconnect()


    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):

        vc = member.guild.voice_client

        if vc and len(vc.channel.members) == 1:
            await vc.disconnect()


async def setup(bot):
    await bot.add_cog(Music(bot))