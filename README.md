# kero-voice

Discord用の日本語テキスト読み上げBot。Chatterbox Multilingual TTSを使用した音声クローン機能付き。

## 機能

- テキストチャンネルのメッセージをボイスチャンネルで読み上げ
- 音声ファイルを参照した声クローン
- ユーザーごとの話者設定
- ボイスチャンネルに誰もいなくなると自動退出

## 必要環境

- Docker
- NVIDIA GPU（CUDA対応）
- NVIDIA Container Toolkit

## セットアップ

### 1. 参照音声ファイルを配置

声クローン用の参照音声ファイル（.mp3 または .wav）を以下のディレクトリに配置します。

```
./src/audiofiles/
```

### 2. 環境変数を設定

`./src/.env.example` をコピーして `./src/.env` を作成し、環境変数を設定します。

```bash
cp ./src/.env.example ./src/.env
```

```env
TOKEN=DiscordのBotトークン
SPEAKER_WAV=デフォルトの参照音声ファイル名（例: voice.wav）
```

### 3. Dockerで起動

```bash
docker-compose up -d
```

初回起動時はTTSモデルのダウンロードに時間がかかります。

## コマンド一覧

| コマンド | 説明 |
|----------|------|
| `!join` | Botをあなたのボイスチャンネルに参加させます |
| `!leave` | Botをボイスチャンネルから切断します |
| `!speakers` | 利用可能な話者一覧をボタンで表示します |
| `!myvoice` | 現在設定されている話者を確認します |
| `!help` | ヘルプを表示します |

## 使い方

1. ボイスチャンネルに参加
2. テキストチャンネルで `!join` を実行
3. テキストチャンネルにメッセージを送信すると、Botが音声で読み上げます
4. `!speakers` で話者を選択できます（ボタンをクリック）
5. `!leave` でBotを退出させます

## 直接実行（開発用）

```bash
uv run ./src/main.py
```
