import torch
from TTS.api import TTS


class XTTSVoiceSynthesizer:
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"🧠 XTTS device: {self.device}")

        self.tts = TTS(
            "tts_models/multilingual/multi-dataset/xtts_v2"
        ).to(self.device)

    def synthesize_to_file(self, text, speaker_wav, out_path, language="ja"):
        self.tts.tts_to_file(
            text=text,
            speaker_wav=speaker_wav,
            language=language,
            file_path=out_path
        )
