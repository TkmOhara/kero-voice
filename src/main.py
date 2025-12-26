import os
import asyncio
import signal
import tempfile
import discord
from discord.ext import commands
from dotenv import load_dotenv
from tts import XTTSVoiceSynthesizer

# =====================
# Env
# =====================
load_dotenv()
TOKEN = os.getenv("TOKEN")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # このスクリプトファイルのあるディレクトリ
SPEAKER_WAV = os.path.join(BASE_DIR, "audiofiles", os.getenv("SPEAKER_WAV", "sample.wav"))

# =====================
# Discord
# =====================
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    help_command=None
)

# =====================
# TTS
# =====================
tts_synth: XTTSVoiceSynthesizer | None = None
tts_lock = asyncio.Lock()

shutdown_event = asyncio.Event()

# =====================
# Events
# =====================
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")
    global tts_synth
    tts_synth = XTTSVoiceSynthesizer()
    print("✅ TTS Synthesizer initialized")

# =====================
# Commands
# =====================
@bot.command()
async def join(ctx):
    if ctx.author.voice is None:
        return await ctx.send("🔊 VCに入ってください")

    if ctx.voice_client is None:
        await ctx.author.voice.channel.connect()


@bot.command()
async def leave(ctx):
    vc = ctx.guild.voice_client
    if vc:
        await vc.disconnect()
        await ctx.send("👋 VCから切断しました")
    else:
        await ctx.send("ℹ VCにいません")

# =====================
# TTS executor
# =====================
async def synthesize(text: str, out_path: str):
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(
        None,
        tts_synth.synthesize_to_file,
        text,
        SPEAKER_WAV,
        out_path,
        "ja"
    )

# =====================
# Message handler
# =====================
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    await bot.process_commands(message)

    if (
        not message.guild
        or not message.guild.voice_client
        or message.content.startswith("!")
        or not message.content.strip()
        or tts_synth is None
        or shutdown_event.is_set()
    ):
        return

    vc = message.guild.voice_client
    text = message.content.strip()

    async with tts_lock:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            tmp_path = f.name

        try:
            await synthesize(text, tmp_path)

            if vc.is_playing():
                vc.stop()

            def cleanup(_):
                try:
                    os.remove(tmp_path)
                except:
                    pass

            vc.play(
                discord.FFmpegPCMAudio(tmp_path),
                after=cleanup
            )

        except Exception as e:
            print("❌ TTS Error:", e)
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

bot.run(TOKEN)