# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

kero-voice is a Discord voice bot that synthesizes Japanese text-to-speech using Chatterbox Multilingual TTS with voice cloning capabilities. When users send text messages in a Discord channel where the bot is connected, it synthesizes speech and plays it in the voice channel.

## Commands

### Running the Bot

**Docker (recommended):**
```bash
docker-compose up
```

**Direct execution:**
```bash
uv run ./src/main.py
```

### Setup

1. Copy `src/.env.example` to `src/.env`
2. Set `TOKEN` (Discord bot token) and `SPEAKER_WAV` (reference audio filename) in `.env`
3. Place voice cloning reference audio files in `src/audiofiles/`

## Architecture

### Core Components

- **src/main.py** - Discord bot entry point using discord.py. Handles bot commands (`!join`, `!leave`) and message events. TTS model is loaded once at startup before Discord connection.

- **src/tts.py** - `ChatterboxVoiceSynthesizer` class wrapping Chatterbox Multilingual TTS. Auto-detects GPU/CPU, manages VRAM/RAM cleanup after each synthesis.

### Key Patterns

- **Thread-safe synthesis**: Uses `asyncio.Lock()` to prevent concurrent TTS operations, with synthesis running in executor pool to avoid blocking
- **Memory management**: Explicit `gc.collect()` and `torch.cuda.empty_cache()` after each synthesis to prevent VRAM accumulation
- **Temporary file cleanup**: WAV files written to temp directory, cleaned up via FFmpeg `after` callback

### Environment

- Python 3.11 (strict: `>=3.11,<3.12`)
- CUDA 12.8 for GPU acceleration
- Dependencies managed with `uv` (Astral's Python package manager)
- PyTorch pulled from CUDA-specific index (`pytorch-cu128`)
- chatterbox-tts installed from git: `https://github.com/resemble-ai/chatterbox.git`
