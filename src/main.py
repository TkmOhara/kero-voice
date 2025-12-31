import os
import asyncio
import tempfile
import discord
from discord.ext import commands
from dotenv import load_dotenv
from tts import ChatterboxVoiceSynthesizer

# =====================
# Env
# =====================
load_dotenv()
TOKEN = os.getenv("TOKEN")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # このスクリプトファイルのあるディレクトリ
# 声クローン用の参照音声ファイル（オプション）
SPEAKER_WAV_NAME = os.getenv("SPEAKER_WAV")
SPEAKER_WAV = os.path.join(BASE_DIR, "audiofiles", SPEAKER_WAV_NAME) if SPEAKER_WAV_NAME else None

# =====================
# TTS (Discord接続前に初期化)
# =====================
print("🔄 Loading TTS model... (this may take a while)")
tts_synth = ChatterboxVoiceSynthesizer()
print("✅ TTS Synthesizer initialized")

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

tts_lock = asyncio.Lock()
shutdown_event = asyncio.Event()

# =====================
# Events
# =====================
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")
    print("✅ Bot is ready!")

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
        out_path,
        SPEAKER_WAV,
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

            # 再生完了を通知するEvent
            play_done = asyncio.Event()

            def after_play(error):
                if error:
                    print(f"❌ Playback error: {error}")
                try:
                    os.remove(tmp_path)
                except:
                    pass
                # メインループでEventをセット
                bot.loop.call_soon_threadsafe(play_done.set)

            vc.play(
                discord.FFmpegPCMAudio(tmp_path),
                after=after_play
            )

            # 再生完了まで待機
            await play_done.wait()

        except Exception as e:
            print("❌ TTS Error:", e)
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

bot.run(TOKEN)