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

logger = logging.getLogger(__name__)


def is_gpu_available() -> bool:
    try:
        import torch  # type: ignore
        return bool(getattr(torch, "cuda", None) and torch.cuda.is_available())
    except Exception:
        return False


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
        self.model_name: str = model_name
        self.device: str = device or ("cuda" if is_gpu_available() else "cpu")
        self._model = None  # lazy-loaded whisper model
        self._banking_knowledge: str = ""

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

        logger.info(f"Loading Whisper model '{self.model_name}' on device '{self.device}'...")
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

        # Ensure model is loaded
        t_load0 = time.perf_counter()
        self._lazy_load_model()
        t_load = time.perf_counter() - t_load0

        # Write to a temporary file for whisper
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=file_suffix, delete=True) as tmp:
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
            # Some Whisper forks expose .transcribe with initial_prompt
            try:
                result = self._model.transcribe(tmp.name, initial_prompt=initial_prompt)
            except TypeError:
                # Fallback without prompt if not supported
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


__all__ = ["WhisperService", "is_gpu_available"]


