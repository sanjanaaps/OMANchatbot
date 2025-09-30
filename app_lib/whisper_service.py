"""
Lightweight Whisper integration for voice transcription with banking knowledge hints.

This module intentionally avoids UI/testing code. It focuses on:
- GPU availability detection
- Whisper model initialization
- Optional static banking knowledge ingestion from uploads folder
- Transcription API and simple performance logging

Ignore any testing, Gradio, or microphone loop here. The chat page and the
voice endpoints will handle audio acquisition; this module only transcribes.
"""

from __future__ import annotations

import os
import time
import logging
from pathlib import Path
from typing import Dict, Optional, Tuple, List
import shutil

logger = logging.getLogger(__name__)


def is_gpu_available() -> bool:
    """Check if GPU is available (uses startup device check)"""
    import os
    return os.environ.get('WHISPER_DEVICE', 'cpu') == 'cuda'


def is_ffmpeg_available() -> bool:
    """Check if ffmpeg is available on PATH (required by Whisper)."""
    return shutil.which("ffmpeg") is not None


class WhisperService:
    """Encapsulates Whisper model and optional domain knowledge for prompts."""

    def __init__(
        self,
        uploads_dir: str,
        model_name: str = "base",
        device: Optional[str] = None,
        load_on_init: bool = True,
    ) -> None:
        self.uploads_dir: Path = Path(uploads_dir)
        
        # Use startup device check instead of redundant GPU detection
        import os
        self.device: str = device or os.environ.get('WHISPER_DEVICE', 'cpu')
        self.model_name: str = model_name or os.environ.get('WHISPER_MODEL', 'base')
        self._model = None  # lazy-loaded whisper model
        self._banking_knowledge: str = ""

        # Concise console summary
        ffmpeg_available = is_ffmpeg_available()
        print(f"[Service] device={self.device}, ffmpeg={int(ffmpeg_available)}, model={self.model_name}")

        # Preload knowledge and (optionally) the model
        self._load_banking_knowledge()
        if load_on_init:
            self._lazy_load_model()

    # ------- Initialization helpers -------

    def _load_banking_knowledge(self) -> None:
        """Read static banking knowledge from uploads if present."""
        knowledge_paths: List[Path] = [
            self.uploads_dir / "banking_knowledge.txt",
            self.uploads_dir / "banking_knowledge.md",
        ]
        for path in knowledge_paths:
            if path.exists():
                try:
                    self._banking_knowledge = path.read_text(encoding="utf-8", errors="ignore")
                    logger.info(f"Loaded banking knowledge from {path}")
                    return
                except Exception as e:
                    logger.warning(f"Failed to read banking knowledge: {e}")
        logger.info("No banking knowledge file found in uploads. Proceeding without it.")

    def _lazy_load_model(self) -> None:
        if self._model is not None:
            return
        t0 = time.perf_counter()
        try:
            import whisper  # type: ignore
        except Exception as e:
            logger.error(f"Whisper not installed: {e}")
            raise

        logger.debug(f"Loading Whisper model '{self.model_name}' on device '{self.device}'...")
        self._model = whisper.load_model(self.model_name, device=self.device)
        elapsed = time.perf_counter() - t0
        logger.info(f"Whisper model loaded in {elapsed:.2f}s")

    # ------- Public API -------

    def transcribe_bytes(self, audio_bytes: bytes, file_suffix: str = ".webm") -> Dict[str, str]:
        """Transcribe an in-memory audio blob and return results.

        Returns dict with: text, language (best-effort), duration_s, load_time_s, infer_time_s
        """
        if not audio_bytes:
            return {"text": "", "language": "", "duration_s": "0", "load_time_s": "0", "infer_time_s": "0"}

        # Check if FFmpeg is available, if not try fallback processor
        if not is_ffmpeg_available():
            logger.warning("FFmpeg not available, attempting fallback audio processing")
            return self._transcribe_with_fallback(audio_bytes, file_suffix)

        # Ensure model is loaded
        t_load0 = time.perf_counter()
        self._lazy_load_model()
        t_load = time.perf_counter() - t_load0

        # Write to a temporary file for whisper
        import tempfile
        # Normalize suffix to common extensions Whisper/ffmpeg can handle
        safe_suffix = file_suffix if file_suffix in ('.webm', '.ogg', '.wav', '.mp3', '.m4a') else '.webm'
        with tempfile.NamedTemporaryFile(suffix=safe_suffix, delete=True) as tmp:
            tmp.write(audio_bytes)
            tmp.flush()

            # Prompt engineering: prepend banking knowledge as a system hint
            initial_prompt = None
            if self._banking_knowledge:
                initial_prompt = (
                    "Banking domain context (Central Bank operations):\n" +
                    self._banking_knowledge[:2000]
                )

            t0 = time.perf_counter()
            # Limit language to English or Arabic to speed up inference
            forced_language = self._detect_language_limited(tmp.name)

            # If ffmpeg is unavailable but we received WAV, decode without ffmpeg
            if not is_ffmpeg_available() and safe_suffix == '.wav':
                result = self._transcribe_wav_bytes_without_ffmpeg(audio_bytes, forced_language, initial_prompt)
            else:
                # Some Whisper forks expose .transcribe with initial_prompt
                try:
                    if forced_language:
                        result = self._model.transcribe(
                            tmp.name,
                            language=forced_language,
                            initial_prompt=initial_prompt,
                        )
                    else:
                        result = self._model.transcribe(tmp.name, initial_prompt=initial_prompt)
                except TypeError:
                    # Fallback without prompt if not supported
                    if forced_language:
                        result = self._model.transcribe(tmp.name, language=forced_language)
                    else:
                        result = self._model.transcribe(tmp.name)
            infer_time = time.perf_counter() - t0

        text = (result.get("text") or "").strip()
        language = result.get("language") or ""

        return {
            "text": text,
            "language": language,
            "duration_s": str(result.get("duration", "")),
            "load_time_s": f"{t_load:.2f}",
            "infer_time_s": f"{infer_time:.2f}",
        }

    def _transcribe_with_fallback(self, audio_bytes: bytes, file_suffix: str) -> Dict[str, str]:
        """Transcribe using fallback audio processor when FFmpeg is not available"""
        logger.debug("Attempting transcription with fallback audio processor")
        try:
            # Import and use the fallback processor
            from server_audio_processor import WhisperAudioHandler
            
            handler = WhisperAudioHandler()
            if not handler.whisper_available:
                logger.error("Fallback processor: Whisper not available")
                return {"text": "", "language": "", "duration_s": "0", "load_time_s": "0", "infer_time_s": "0"}
            
            # Determine format hint
            format_hint = file_suffix.lstrip('.') if file_suffix.startswith('.') else file_suffix
            
            # Transcribe using fallback processor
            result = handler.transcribe_audio_bytes(audio_bytes, format_hint)
            
            if result.get('success'):
                processing_info = result.get('processing_info', {})
                return {
                    "text": result.get('text', ''),
                    "language": result.get('language', ''),
                    "duration_s": str(processing_info.get('duration', '')),
                    "load_time_s": "0",  # Fallback doesn't track load time separately
                    "infer_time_s": "0",  # Fallback doesn't track inference time separately
                }
            else:
                logger.error(f"Fallback transcription failed: {result.get('error', 'Unknown error')}")
                return {"text": "", "language": "", "duration_s": "0", "load_time_s": "0", "infer_time_s": "0"}
                
        except ImportError:
            logger.error("Fallback audio processor not available")
            return {"text": "", "language": "", "duration_s": "0", "load_time_s": "0", "infer_time_s": "0"}
        except Exception as e:
            logger.error(f"Fallback transcription error: {e}")
            return {"text": "", "language": "", "duration_s": "0", "load_time_s": "0", "infer_time_s": "0"}

    # ------- Internal helpers -------
    def _transcribe_wav_bytes_without_ffmpeg(self, wav_bytes: bytes, forced_language: Optional[str], initial_prompt: Optional[str]) -> Dict[str, str]:
        """Decode WAV bytes without ffmpeg and run Whisper directly.

        This path avoids ffmpeg by using soundfile and a simple resampler.
        """
        import io
        try:
            import soundfile as sf  # type: ignore
            import numpy as np  # type: ignore
            import whisper  # type: ignore
        except Exception as e:
            raise RuntimeError(f"WAV decode path unavailable: {e}")

        data, sr = sf.read(io.BytesIO(wav_bytes), dtype='float32', always_2d=False)
        if data.ndim > 1:
            # Convert to mono by averaging channels
            data = data.mean(axis=1)
        # Resample to 16000 Hz if needed
        target_sr = 16000
        if sr != target_sr:
            x_old = np.linspace(0, 1, num=len(data), endpoint=False, dtype=np.float32)
            x_new = np.linspace(0, 1, num=int(len(data) * (target_sr / sr)), endpoint=False, dtype=np.float32)
            data = np.interp(x_new, x_old, data).astype(np.float32)

        audio = whisper.pad_or_trim(data)
        mel = whisper.log_mel_spectrogram(audio).to(self._model.device)
        # Build decoding options
        try:
            from whisper.decoding import DecodingOptions, decode  # type: ignore
        except Exception:
            # Fallback older API
            DecodingOptions = None
            decode = None

        if DecodingOptions and decode:
            opts = DecodingOptions(language=forced_language or None, prompt=initial_prompt or None)
            dec = decode(self._model, mel, opts)
            text = getattr(dec, 'text', '') or ''
        else:
            # Very old fallback: use model.decode
            opts = { 'language': forced_language } if forced_language else {}
            dec = self._model.decode(mel, opts)  # type: ignore
            text = getattr(dec, 'text', '') or ''

        return {
            'text': text,
            'language': forced_language or '',
            'duration': '',
        }
    def _detect_language_limited(self, audio_path: str) -> Optional[str]:
        """Detect language but restrict to English or Arabic for speed.

        Returns 'en' or 'ar' if confidently detected, otherwise None.
        """
        try:
            import whisper  # type: ignore
            import numpy as np  # type: ignore
        except Exception as e:
            logger.debug(f"Language detect deps missing: {e}")
            return None

        try:
            audio = whisper.load_audio(audio_path)
            audio = whisper.pad_or_trim(audio)
            mel = whisper.log_mel_spectrogram(audio).to(self._model.device)
            _, probs = self._model.detect_language(mel)
            # Consider only English and Arabic
            en_p = float(probs.get('en', 0.0))
            ar_p = float(probs.get('ar', 0.0))
            if en_p == 0.0 and ar_p == 0.0:
                return None
            return 'en' if en_p >= ar_p else 'ar'
        except Exception as e:
            logger.debug(f"Limited language detect failed: {e}")
            return None


__all__ = ["WhisperService", "is_gpu_available", "is_ffmpeg_available"]


