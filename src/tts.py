import torch
import numpy as np
from scipy.io import wavfile
from chatterbox.mtl_tts import ChatterboxMultilingualTTS


class ChatterboxVoiceSynthesizer:
    def __init__(self, device: str | None = None):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")

        if self.device == "cuda":
            print(f"GPU: {torch.cuda.get_device_name(0)}")
            torch.backends.cudnn.benchmark = True
            torch.backends.cuda.matmul.allow_tf32 = True
            torch.backends.cudnn.allow_tf32 = True

        self.model = ChatterboxMultilingualTTS.from_pretrained(device=self.device)
        self.sr = self.model.sr
        print(f"TTS loaded (device: {self.device})")

    def synthesize_to_file(
        self,
        text: str,
        out_path: str,
        speaker_wav: str | None = None,
        language: str = "ja",
    ):
        with torch.inference_mode(), torch.autocast(
            device_type="cuda", enabled=self.device == "cuda"
        ):
            wav = self.model.generate(
                text,
                audio_prompt_path=speaker_wav,
                language_id=language,
                exaggeration=0.5,
                cfg_weight=0.5,
            )

        # Tensor -> int16 WAV
        if wav.dim() == 2:
            wav = wav.squeeze(0)
        wav_int16 = (wav.cpu().numpy() * 32767).clip(-32768, 32767).astype(np.int16)
        wavfile.write(out_path, self.sr, wav_int16)
