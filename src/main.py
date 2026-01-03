import os
import sys
import asyncio
import tempfile
from dataclasses import dataclass
import discord
from discord.ext import commands
from dotenv import load_dotenv

# srcディレクトリをパスに追加（uv run ./src/main.py 対応）
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from tts import ChatterboxVoiceSynthesizer

# =====================
# Env
# =====================
load_dotenv(os.path.join(BASE_DIR, ".env"))
TOKEN = os.getenv("TOKEN")
# 声クローン用の参照音声ファイル（オプション）
SPEAKER_WAV_NAME = os.getenv("SPEAKER_WAV")
SPEAKER_WAV = os.path.join(BASE_DIR, "audiofiles", SPEAKER_WAV_NAME) if SPEAKER_WAV_NAME else None

# =====================
# TTS (Discord接続前に初期化)
# =====================
print("Loading TTS model... (this may take a while)")
tts_synth = ChatterboxVoiceSynthesizer()
print("TTS Synthesizer initialized")

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
# Audio Queue System
# =====================
@dataclass
class AudioItem:
    wav_path: str
    ready: asyncio.Event

# ギルドごとの再生キュー
audio_queues: dict[int, asyncio.Queue[AudioItem]] = {}
playback_tasks: dict[int, asyncio.Task] = {}


async def playback_worker(guild_id: int):
    """キューから音声を順次再生するワーカー"""
    queue = audio_queues[guild_id]

    while not shutdown_event.is_set():
        try:
            item = await asyncio.wait_for(queue.get(), timeout=1.0)
        except asyncio.TimeoutError:
            continue
        except asyncio.CancelledError:
            break

        try:
            # TTS処理完了を待つ
            await item.ready.wait()

            guild = bot.get_guild(guild_id)
            if not guild or not guild.voice_client:
                continue

            vc = guild.voice_client

            # 再生完了を通知するEvent
            play_done = asyncio.Event()

            def after_play(error):
                if error:
                    print(f"Playback error: {error}")
                try:
                    os.remove(item.wav_path)
                except:
                    pass
                bot.loop.call_soon_threadsafe(play_done.set)

            vc.play(
                discord.FFmpegPCMAudio(item.wav_path),
                after=after_play
            )

            # 再生完了まで待機
            await play_done.wait()

        except Exception as e:
            print(f"Playback worker error: {e}")
            if os.path.exists(item.wav_path):
                try:
                    os.remove(item.wav_path)
                except:
                    pass
        finally:
            queue.task_done()


def get_or_create_queue(guild_id: int) -> asyncio.Queue[AudioItem]:
    """ギルドの再生キューを取得または作成"""
    if guild_id not in audio_queues:
        audio_queues[guild_id] = asyncio.Queue()
        playback_tasks[guild_id] = asyncio.create_task(playback_worker(guild_id))
    return audio_queues[guild_id]

# =====================
# Events
# =====================
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("Bot is ready!")

# =====================
# Commands
# =====================
@bot.command()
async def help(ctx):
    """ヘルプを表示"""
    embed = discord.Embed(
        title="kero-voice Bot",
        description="テキストを音声に変換してVCで再生するBotです",
        color=discord.Color.green()
    )
    embed.add_field(
        name="!join",
        value="Botをあなたのボイスチャンネルに参加させます",
        inline=False
    )
    embed.add_field(
        name="!leave",
        value="Botをボイスチャンネルから切断します",
        inline=False
    )
    embed.add_field(
        name="!help",
        value="このヘルプを表示します",
        inline=False
    )
    embed.add_field(
        name="使い方",
        value="Botがボイスチャンネルに参加中、テキストチャンネルにメッセージを送ると音声で読み上げます",
        inline=False
    )
    await ctx.send(embed=embed)


@bot.command()
async def join(ctx):
    """ボイスチャンネルに参加"""
    if ctx.author.voice is None:
        return await ctx.send("VCに入ってください")

    target_channel = ctx.author.voice.channel

    if ctx.voice_client is None:
        # 未接続の場合は接続
        await target_channel.connect()
        await ctx.send(f"{target_channel.name} に参加しました")
    elif ctx.voice_client.channel != target_channel:
        # 別チャンネルにいる場合は移動
        await ctx.voice_client.move_to(target_channel)
        await ctx.send(f"{target_channel.name} に移動しました")
    else:
        await ctx.send("既に同じVCにいます")


@bot.command()
async def leave(ctx):
    """ボイスチャンネルから退出"""
    vc = ctx.guild.voice_client
    if vc:
        await vc.disconnect()
        await ctx.send("VCから切断しました")
    else:
        await ctx.send("VCにいません")

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

    text = message.content.strip()
    guild_id = message.guild.id

    # 文字数制限（100文字）
    MAX_MESSAGE_LENGTH = 300
    if len(text) > MAX_MESSAGE_LENGTH:
        text = "This message is too long"

    # 一時ファイルを作成
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        tmp_path = f.name

    # キューにアイテムを追加（TTS完了前に予約）
    ready_event = asyncio.Event()
    item = AudioItem(wav_path=tmp_path, ready=ready_event)
    queue = get_or_create_queue(guild_id)
    await queue.put(item)

    # TTS処理をバックグラウンドで実行
    async def process_tts():
        try:
            async with tts_lock:
                await synthesize(text, tmp_path)
            ready_event.set()
        except Exception as e:
            print(f"TTS Error: {e}")
            ready_event.set()  # エラーでも再生ワーカーを進める

    asyncio.create_task(process_tts())

bot.run(TOKEN)