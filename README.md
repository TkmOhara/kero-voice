(The file `c:\Users\ponz0\OneDrive\Desktop\kero-voice\README.md` exists, but is empty)
**Project**: kero-voice

- **Description**: Discordボット。Discordで受信したメッセージを `tts.py` で音声化し、送信者のボイスチャンネルで再生します。

**Requirements**
- **Python**: 3.8+
- **ffmpeg**: システムにインストールし、PATHに追加してください。
- **Python packages**: 以下をインストールしてください。

```bash
pip install -r requirements.txt
```

最低限必要なパッケージ例:

```bash
pip install TTS torch discord.py python-dotenv
```

（`torch` は環境とCUDAの有無に応じて適切なバージョンを選んでください）

**Environment variables**
このリポジトリは `config.json` を使って設定を読み込みます（環境変数は不要です）。

プロジェクトルートに `config.json` を配置してください。例:

```json
{
	"TOKEN": "YOUR_DISCORD_BOT_TOKEN",
	"SPEAKER_WAV": "./speaker.wav"
}
```

**Usage**
ローカルで実行する場合:

```bash
python main.py
```

Docker Compose を使って実行する（推奨、GPUを自動で渡します）:

```bash
docker compose build --progress=plain --no-cache
docker compose up -d
```

`docker-compose.yml` は `gpus: all` を指定しています。ホストに NVIDIA Container Toolkit が入っていれば、コンテナに自動でGPUが渡されます。

マウント例: プロジェクト直下に `speaker.wav` と `config.json` を置くとそのまま使えます。

**Notes / Troubleshooting**
- `SPEAKER_WAV` に指定したファイルが見つからない場合、`main.py` がエラーを返します。パスが正しいことを確認してください。
- `ffmpeg` が見つからない場合、音声再生に失敗します。コマンドラインで `ffmpeg -version` が動作することを確認してください。
- GPUを使いたい場合、`tts.py` の `XTTSVoiceSynthesizer` がCUDAを検出すると自動的に `cuda` を選択しますが、`torch` のインストールがCUDA対応である必要があります。

**Files**
- [main.py](main.py)
- [tts.py](tts.py)
- [docker-compose.yml](docker-compose.yml)

