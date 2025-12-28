## 使用方法

### 必要環境
- Docker

### 手順

### 1. 参照音声ファイルを配置

声クローン用の参照音声ファイルを以下のディレクトリに配置します。

```bash
./src/audiofiles/
```

### 2. 環境変数を設定
./src/.env.exampleをコピーして./src/.envを作成し、環境変数を設定
```bash
TOKEN=DiscordのBotトークン
SPEAKER_WAV=先ほど配置した参照音声ファイルのファイル名
```