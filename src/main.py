import os
import sys
import asyncio
import tempfile
from dataclasses import dataclass
import discord
from discord.ext import commands
from discord.ui import Button, View
from dotenv import load_dotenv

# srcディレクトリをパスに追加（uv run ./src/main.py 対応）
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from tts import ChatterboxVoiceSynthesizer
from db import Database
from system_monitor import SystemMonitor

# =====================
# Env
# =====================
load_dotenv(os.path.join(BASE_DIR, ".env"))
TOKEN = os.getenv("TOKEN")
# 声クローン用の参照音声ファイル（オプション）
SPEAKER_WAV_NAME = os.getenv("SPEAKER_WAV")
SPEAKER_WAV = os.path.join(BASE_DIR, "audiofiles", SPEAKER_WAV_NAME) if SPEAKER_WAV_NAME else None
AUDIOFILES_DIR = os.path.join(BASE_DIR, "audiofiles")

# =====================
# Database
# =====================
db = Database(os.path.join(BASE_DIR, "kero_voice.db"))
db.refresh_speakers(AUDIOFILES_DIR)

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


@bot.event
async def on_voice_state_update(member, before, after):
    """ボイスチャンネルに誰もいなくなったら自動で退出"""
    # ボイスチャンネルから離脱したイベントだけを見る
    if before.channel is None or after.channel == before.channel:
        return

    channel = before.channel

    # このギルドにBotが接続しているか？
    if channel.guild.voice_client is None:
        return

    bot_voice = channel.guild.voice_client

    # Botが現在いるチャンネルと一致しているか？
    if bot_voice.channel != channel:
        return

    # 残っているメンバーに人間がいるかチェック
    humans = [m for m in channel.members if not m.bot]

    if len(humans) == 0:
        await bot_voice.disconnect()
        print("誰もいなくなったのでBOTは退出しました。")

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
        name="!speakers",
        value="利用可能な話者一覧を表示します",
        inline=False
    )
    embed.add_field(
        name="!myvoice",
        value="現在設定されている話者を確認します",
        inline=False
    )
    embed.add_field(
        name="!status",
        value="サーバーのシステムステータスを表示します（次のメッセージまで1秒ごとに更新）",
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
# Speaker Selection UI
# =====================
class SpeakerSelectView(View):
    """話者選択用のボタンビュー"""

    def __init__(self, speakers: list[dict]):
        super().__init__(timeout=None)  # 同一インスタンス中は有効
        for speaker in speakers[:25]:  # Discordの制限: 最大25ボタン
            # ファイル名から拡張子を除去して短縮
            label = os.path.splitext(speaker["filename"])[0][:20]
            button = Button(
                label=label,
                style=discord.ButtonStyle.primary,
                custom_id=f"speaker_{speaker['id']}"
            )
            button.callback = self.create_callback(speaker["id"])
            self.add_item(button)

    def create_callback(self, speaker_id: int):
        async def callback(interaction: discord.Interaction):
            user_id = interaction.user.id
            speaker = db.get_speaker_by_id(speaker_id)
            if speaker and db.set_user_speaker(user_id, speaker_id):
                await interaction.response.send_message(
                    f"話者を **{speaker['filename']}** に設定しました",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    "設定に失敗しました",
                    ephemeral=True
                )
        return callback


def chunk_list(lst: list, n: int) -> list[list]:
    """リストをn個ずつに分割"""
    return [lst[i:i + n] for i in range(0, len(lst), n)]


@bot.command()
async def speakers(ctx):
    """利用可能な話者一覧を表示（ボタンで選択）"""
    speaker_list = db.get_speakers()

    if not speaker_list:
        return await ctx.send("話者が登録されていません。audiofilesフォルダに音声ファイルを追加してください。")

    # 25個ずつに分割してViewを作成
    blocks = chunk_list(speaker_list, 25)
    for block in blocks:
        view = SpeakerSelectView(block)
        await ctx.send("話者を選択してください:", view=view)


@bot.command()
async def myvoice(ctx):
    """現在の話者設定を確認"""
    user_id = ctx.author.id
    speaker = db.get_user_speaker(user_id)

    if speaker:
        await ctx.send(f"現在の話者: {speaker['filename']}", delete_after=10)
    else:
        await ctx.send("話者が設定されていません。デフォルトの話者を使用します。", delete_after=10)


# アクティブなステータス更新タスクを管理（ギルドIDをキーに）
active_status_tasks: dict[int, asyncio.Task] = {}


@bot.command()
async def status(ctx):
    """システムステータスを表示（1分間自動更新、再実行で停止）"""
    guild_id = ctx.guild.id

    # 既存のタスクがあれば停止
    if guild_id in active_status_tasks:
        active_status_tasks[guild_id].cancel()
        del active_status_tasks[guild_id]
        return

    # 初回メッセージ送信
    status_msg = SystemMonitor.generate_status_message()
    message = await ctx.send(status_msg)

    async def update_status():
        """1分間、1秒ごとにステータスを更新"""
        try:
            for _ in range(60):  # 60秒間
                await asyncio.sleep(1)
                status_msg = SystemMonitor.generate_status_message()
                await message.edit(content=status_msg)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"Status update error: {e}")
        finally:
            # 完了したらタスクを削除
            if guild_id in active_status_tasks:
                del active_status_tasks[guild_id]

    # タスクを開始して保存
    active_status_tasks[guild_id] = asyncio.create_task(update_status())


# =====================
# TTS executor
# =====================
async def synthesize(text: str, out_path: str, speaker_wav: str | None = None):
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(
        None,
        tts_synth.synthesize_to_file,
        text,
        out_path,
        speaker_wav or SPEAKER_WAV,
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
    user_id = message.author.id

    # ユーザーの話者設定を取得
    user_speaker = db.get_user_speaker(user_id)
    speaker_wav = user_speaker["filepath"] if user_speaker else None

    # 文字数制限（300文字）
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
                await synthesize(text, tmp_path, speaker_wav)
            ready_event.set()
        except Exception as e:
            print(f"TTS Error: {e}")
            ready_event.set()  # エラーでも再生ワーカーを進める

    asyncio.create_task(process_tts())

bot.run(TOKEN)