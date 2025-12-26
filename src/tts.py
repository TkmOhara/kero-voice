import os
import torch
from TTS.api import TTS
from TTS.tts.models.xtts import XttsAudioConfig, XttsArgs
from TTS.tts.configs.xtts_config import XttsConfig
from TTS.config.shared_configs import BaseDatasetConfig

class XTTSVoiceSynthesizer:
    def __init__(self):
        # GPU確認
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        if self.device == "cuda":
            print(f"GPU detected: {torch.cuda.get_device_name(0)}")
            print(f"Compute Capability: {torch.cuda.get_device_capability(0)}")

        # safe_globals にカスタムクラスを登録
        torch.serialization.add_safe_globals([
            XttsAudioConfig,
            XttsConfig,
            BaseDatasetConfig,
            XttsArgs  # 追加
        ])

        try:
            # TTS モデルのロード
            self.tts = TTS(
                model_name="tts_models/multilingual/multi-dataset/xtts_v2",
                gpu=self.device == "cuda"
            )
            print("XTTS v2 loaded successfully.")
        except Exception as e:
            print(f"TTS load error: {e}")
            raise

    def synthesize_to_file(self, text, speaker_wav, out_path, language="ja"):
        self.tts.tts_to_file(
            text=text,
            speaker_wav=speaker_wav,
            language=language,
            file_path=out_path
        )
