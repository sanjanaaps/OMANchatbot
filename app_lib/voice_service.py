"""
Voice recording and live transcription service (placeholders).

This module provides a minimal, dependency-free surface you can wire to the
chat UI's record button, waveform preview, and live transcript area. Replace
the placeholder implementations with real microphone ingestion, audio
processing, and streaming speech-to-text as needed.
"""

from __future__ import annotations

import os
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# Default max duration for a recording session in milliseconds (1 minute)
DEFAULT_MAX_DURATION_MS: int = 60_000


@dataclass
class RecordingSession:
    """In-memory model for a single recording session.

    Note: This stores audio chunks in memory as placeholders. In production,
    prefer streaming to disk or a message bus to avoid memory pressure.
    """

    session_id: str
    user_id: Optional[str]
    created_at_ms: int
    max_duration_ms: int = DEFAULT_MAX_DURATION_MS
    sample_rate_hz: Optional[int] = None
    # Raw audio chunk storage (placeholder: assumed PCM or encoded bytes)
    chunks: List[bytes] = field(default_factory=list)
    # Timestamps for each accepted chunk (ms since epoch)
    chunk_timestamps_ms: List[int] = field(default_factory=list)
    # Placeholder transcript text accumulated in real time
    live_transcript: str = ""
    # Whether the session has been finalized or canceled
    closed: bool = False

    def elapsed_ms(self) -> int:
        return int(time.time() * 1000) - self.created_at_ms

    def is_over_limit(self) -> bool:
        return self.elapsed_ms() >= self.max_duration_ms


class VoiceRecordingService:
    """Service to manage audio recording sessions and live transcription.

    All methods are designed to be dependency-free and safe to call from
    route handlers or websockets. Replace placeholder sections with real
    audio decoding, VAD, streaming STT, etc.
    """

    def __init__(self, base_dir: Optional[str] = None) -> None:
        # Where finalized recordings are saved (placeholder)
        self.base_dir: Path = Path(base_dir or os.path.join(os.getcwd(), "uploads", "recordings"))
        self.base_dir.mkdir(parents=True, exist_ok=True)
        # Active sessions indexed by session_id
        self._sessions: Dict[str, RecordingSession] = {}

    # -------- Session lifecycle --------

    def begin_session(self, user_id: Optional[str] = None, max_duration_ms: int = DEFAULT_MAX_DURATION_MS) -> str:
        """Create and register a new recording session.

        Returns the new session_id.
        """
        session_id = str(uuid.uuid4())
        self._sessions[session_id] = RecordingSession(
            session_id=session_id,
            user_id=user_id,
            created_at_ms=int(time.time() * 1000),
            max_duration_ms=max_duration_ms,
        )
        return session_id

    def cancel_session(self, session_id: str) -> None:
        """Cancel and remove a session without saving any artifact."""
        session = self._require_session(session_id)
        session.closed = True
        # Optionally clear buffers
        session.chunks.clear()
        session.chunk_timestamps_ms.clear()
        session.live_transcript = ""
        # Remove from registry
        self._sessions.pop(session_id, None)

    def finalize_session(self, session_id: str) -> Dict[str, Optional[str]]:
        """Finalize a session and write a placeholder artifact to disk.

        Returns a dict with basic metadata. Replace the write path/format to
        match your actual audio container and encoder.
        """
        session = self._require_session(session_id)
        session.closed = True

        artifact_path: Optional[Path] = None
        if session.chunks:
            artifact_path = self._write_placeholder_artifact(session)

        result = {
            "session_id": session.session_id,
            "user_id": session.user_id or "",
            "duration_ms": str(session.elapsed_ms()),
            "transcript": session.live_transcript,
            "artifact_path": str(artifact_path) if artifact_path else "",
        }

        # Remove from registry after finalization
        self._sessions.pop(session_id, None)
        return result

    # -------- Audio ingestion --------

    def accept_audio_chunk(self, session_id: str, chunk: bytes, sample_rate_hz: Optional[int] = None) -> None:
        """Accept an audio chunk for a session.

        Placeholder behavior:
        - Stores raw bytes to memory
        - Updates sample rate if first time provided
        - Enforces max duration by marking the session closed when exceeded
        - Appends a tiny placeholder to the live transcript to simulate progress
        """
        session = self._require_session(session_id)
        if session.closed:
            raise RuntimeError("Session is closed")

        now_ms = int(time.time() * 1000)
        if sample_rate_hz and session.sample_rate_hz is None:
            session.sample_rate_hz = sample_rate_hz

        session.chunks.append(chunk)
        session.chunk_timestamps_ms.append(now_ms)

        # Placeholder: Simulate STT by appending a dot periodically
        if len(session.chunks) % 3 == 0:
            session.live_transcript = (session.live_transcript + " ").strip() + " ..."

        if session.is_over_limit():
            session.closed = True

    # -------- Waveform & transcript accessors --------

    def get_waveform_points(self, session_id: str, max_points: int = 200) -> List[float]:
        """Return normalized waveform points in range [-1.0, 1.0].

        Placeholder implementation returns a deterministic pseudo waveform based
        on chunk count. Replace with real-time RMS/peak extraction or FFT-based
        visualization from decoded PCM samples.
        """
        session = self._require_session(session_id)
        points: List[float] = []
        count = max(1, min(max_points, len(session.chunks)))
        for i in range(count):
            # Pseudo pattern using a simple triangle/sine mix
            phase = (i / count) * 6.28318  # 2π
            value = 0.6 * _fast_sin(phase) + 0.4 * _triangle(i, period=max(4, count // 8))
            # Clamp to [-1, 1]
            value = max(-1.0, min(1.0, value))
            points.append(value)
        return points

    def get_live_transcript(self, session_id: str) -> str:
        """Return the accumulated live transcript (placeholder)."""
        session = self._require_session(session_id)
        return session.live_transcript

    def get_best_effort_audio(self, session_id: str) -> bytes:
        """Return a best-effort audio payload from stored chunks.

        For container formats like WebM/Opus, naive concatenation may not
        yield a valid file. As a pragmatic fallback, we choose the largest
        single chunk, which is often decodable by downstream tools.
        """
        session = self._require_session(session_id)
        if not session.chunks:
            return b""
        # Pick the largest chunk as best-effort audio
        return max(session.chunks, key=lambda b: len(b) if isinstance(b, (bytes, bytearray)) else 0)

    # -------- Helpers --------

    def _require_session(self, session_id: str) -> RecordingSession:
        session = self._sessions.get(session_id)
        if not session:
            raise KeyError(f"Unknown session_id: {session_id}")
        return session

    def _write_placeholder_artifact(self, session: RecordingSession) -> Path:
        """Write a naive concatenation of chunks to a .bin file.

        Replace with real containerization (e.g., WAV headers) and encoding
        as needed.
        """
        filename = f"{session.session_id}.bin"
        path = self.base_dir / filename
        with path.open("wb") as f:
            for chunk in session.chunks:
                f.write(chunk)
        return path


# -------- Math utilities (lightweight, no deps) --------

def _fast_sin(x: float) -> float:
    """Cheap sine approximation; sufficient for placeholder waveforms."""
    # Using Python's math.sin would be fine; keeping this trivial and fast.
    import math
    return math.sin(x)


def _triangle(i: int, period: int = 16) -> float:
    """Triangle wave in [-1, 1] for placeholder visualization."""
    if period <= 0:
        period = 1
    pos = i % period
    half = period / 2
    if pos <= half:
        return (pos / half) * 1.0  # 0 -> 1
    # 1 -> -1 scaled to fit [-1,1]
    return 1.0 - ((pos - half) / half) * 2.0


__all__ = [
    "VoiceRecordingService",
    "RecordingSession",
    "DEFAULT_MAX_DURATION_MS",
]


