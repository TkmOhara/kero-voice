import torch
import numpy as np
from scipy.io import wavfile
from chatterbox.mtl_tts import ChatterboxMultilingualTTS


class ChatterboxVoiceSynthesizer:
    """
    Chatterbox Multilingual TTS を使用した日本語音声合成クラス
    """

    def __init__(self, device: str | None = None):
        # GPU確認
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device

        if self.device == "cuda":
            print(f"GPU detected: {torch.cuda.get_device_name(0)}")
            print(f"Compute Capability: {torch.cuda.get_device_capability(0)}")

        try:
            # Chatterbox Multilingual モデルのロード
            self.model = ChatterboxMultilingualTTS.from_pretrained(device=self.device)
            self.sr = self.model.sr
            print("Chatterbox Multilingual TTS loaded successfully.")
        except Exception as e:
            print(f"TTS load error: {e}")
            raise

    def _save_wav(self, wav: torch.Tensor, out_path: str):
        """
        wavテンソルをファイルに保存（scipy使用、torchcodec不要）
        """
        # [1, samples] or [samples] の形式を想定
        if wav.dim() == 2:
            wav = wav.squeeze(0)
        
        # torch.Tensor -> numpy配列に変換
        wav_np = wav.cpu().numpy()
        
        # float32 -> int16に変換（WAVファイル用）
        wav_int16 = np.clip(wav_np * 32767, -32768, 32767).astype(np.int16)
        
        wavfile.write(out_path, self.sr, wav_int16)

    def synthesize_to_file(
        self,
        text: str,
        out_path: str,
        speaker_wav: str | None = None,
        language: str = "ja",
    ):
        """
        テキストを音声合成してファイルに保存

        Args:
            text: 合成するテキスト
            out_path: 出力ファイルパス
            speaker_wav: 声クローン用の参照音声ファイル（オプション）
            language: 言語コード（デフォルト: ja）
        """
        wav = self.model.generate(
            text,
            audio_prompt_path=speaker_wav,
            language_id=language,
            exaggeration=0.7,
            cfg_weight=0.3
        )
        self._save_wav(wav, out_path)

    def synthesize(
        self,
        text: str,
        speaker_wav: str | None = None,
        language: str = "ja",
    ) -> tuple[torch.Tensor, int]:
        """
        テキストを音声合成してテンソルを返す

        Args:
            text: 合成するテキスト
            speaker_wav: 声クローン用の参照音声ファイル（オプション）
            language: 言語コード（デフォルト: ja）

        Returns:
            (wav_tensor, sample_rate) のタプル
        """
        wav = self.model.generate(
            text,
            audio_prompt_path=speaker_wav,
            language_id=language,
        )
        return wav, self.sr
