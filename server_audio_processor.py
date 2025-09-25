#!/usr/bin/env python3
"""
Server-side Audio Processing for Whisper (No FFmpeg Required)
Alternative libraries and methods to process audio without FFmpeg
"""

import io
import wave
import numpy as np
from typing import Optional, Tuple, Dict, Any
import tempfile
import os
import logging

logger = logging.getLogger(__name__)

# Option 1: Using librosa (most comprehensive, no FFmpeg needed)
try:
    import librosa
    LIBROSA_AVAILABLE = True
    logger.info("librosa available for audio processing")
except ImportError:
    LIBROSA_AVAILABLE = False
    logger.warning("librosa not available. Install with: pip install librosa")

# Option 2: Using soundfile (lightweight, good for basic operations)
try:
    import soundfile as sf
    SOUNDFILE_AVAILABLE = True
    logger.info("soundfile available for audio processing")
except ImportError:
    SOUNDFILE_AVAILABLE = False
    logger.warning("soundfile not available. Install with: pip install soundfile")

# Option 3: Using pydub (can work without FFmpeg for WAV)
try:
    from pydub import AudioSegment
    from pydub.utils import which
    PYDUB_AVAILABLE = True
    # Check if FFmpeg is available (optional with pydub)
    FFMPEG_AVAILABLE = which("ffmpeg") is not None
    logger.info(f"pydub available for audio processing, FFmpeg available: {FFMPEG_AVAILABLE}")
except ImportError:
    PYDUB_AVAILABLE = False
    FFMPEG_AVAILABLE = False
    logger.warning("pydub not available. Install with: pip install pydub")

# Option 4: Using scipy (basic WAV support)
try:
    from scipy.io import wavfile
    SCIPY_AVAILABLE = True
    logger.info("scipy available for audio processing")
except ImportError:
    SCIPY_AVAILABLE = False
    logger.warning("scipy not available. Install with: pip install scipy")

class AudioProcessor:
    """Audio processing without FFmpeg dependency"""
    
    def __init__(self):
        self.target_sample_rate = 16000  # Whisper's preferred sample rate
        self.available_processors = self._check_available_processors()
        
        # Use startup device check instead of redundant GPU detection
        import os
        self.device = os.environ.get('WHISPER_DEVICE', 'cpu')
        
        # Concise console summary
        proc_flags = ",".join([
            f"librosa={int(self.available_processors['librosa'])}",
            f"soundfile={int(self.available_processors['soundfile'])}",
            f"pydub={int(self.available_processors['pydub'])}",
            f"scipy={int(self.available_processors['scipy'])}"
        ])
        print(f"[Audio] sr=16000, procs[{proc_flags}], device={self.device}")
        
    def _check_available_processors(self) -> Dict[str, bool]:
        """Check which audio processing libraries are available"""
        return {
            'librosa': LIBROSA_AVAILABLE,
            'soundfile': SOUNDFILE_AVAILABLE,  
            'pydub': PYDUB_AVAILABLE,
            'pydub_with_ffmpeg': PYDUB_AVAILABLE and FFMPEG_AVAILABLE,
            'scipy': SCIPY_AVAILABLE
        }
    
    
    def get_best_processor(self) -> str:
        """Get the best available audio processor"""
        if self.available_processors['librosa']:
            return 'librosa'
        elif self.available_processors['soundfile']:
            return 'soundfile'
        elif self.available_processors['pydub']:
            return 'pydub'
        elif self.available_processors['scipy']:
            return 'scipy'
        else:
            raise RuntimeError("No audio processing library available. Install librosa, soundfile, pydub, or scipy")

    def process_audio_for_whisper(self, audio_data: bytes, 
                                 original_format: str = 'webm') -> Tuple[np.ndarray, int]:
        """
        Process audio data for Whisper transcription
        Returns: (audio_array, sample_rate)
        """
        logger.info(f"Processing audio for Whisper: {len(audio_data)} bytes, format: {original_format}")
        processor = self.get_best_processor()
        logger.info(f"Using processor: {processor}")
        
        # Try a robust sequence regardless of what's "best"
        errors = []
        for method in (
            lambda: self._process_with_soundfile(audio_data),
            lambda: self._process_with_scipy(audio_data),
            lambda: self._process_with_pydub(audio_data, original_format),
            lambda: self._process_with_librosa(audio_data),
        ):
            try:
                return method()
            except Exception as e:
                errors.append(str(e))
                logger.warning(f"Processor attempt failed: {e}")
        raise RuntimeError(f"All processors failed: {' | '.join(errors)}")

    def _process_with_librosa(self, audio_data: bytes) -> Tuple[np.ndarray, int]:
        """Process audio using librosa (best option - handles all formats)"""
        logger.info("Processing audio with librosa")
        try:
            # Save to temporary file
            with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as tmp_file:
                tmp_file.write(audio_data)
                tmp_path = tmp_file.name
                logger.debug(f"Saved audio to temporary file: {tmp_path}")
            
            try:
                # Load and resample with librosa
                logger.info(f"Loading audio with librosa, target sample rate: {self.target_sample_rate}Hz")
                audio_array, sample_rate = librosa.load(
                    tmp_path,
                    sr=self.target_sample_rate,
                    mono=True
                )
                
                logger.info(f"librosa processing complete: {len(audio_array)} samples at {sample_rate}Hz")
                return audio_array.astype(np.float32), sample_rate
                
            finally:
                os.unlink(tmp_path)
                logger.debug(f"Cleaned up temporary file: {tmp_path}")
                
        except Exception as e:
            logger.error(f"librosa processing failed: {e}")
            raise RuntimeError(f"librosa processing failed: {e}")

    def _process_with_soundfile(self, audio_data: bytes) -> Tuple[np.ndarray, int]:
        """Process audio using soundfile (good for WAV, FLAC)"""
        try:
            # Try to read directly from bytes
            audio_array, sample_rate = sf.read(io.BytesIO(audio_data))
            
            # Convert to mono if stereo
            if len(audio_array.shape) > 1:
                audio_array = np.mean(audio_array, axis=1)
            
            # Resample if needed (basic resampling)
            if sample_rate != self.target_sample_rate:
                audio_array = self._simple_resample(
                    audio_array, sample_rate, self.target_sample_rate
                )
                sample_rate = self.target_sample_rate
            
            return audio_array.astype(np.float32), sample_rate
            
        except Exception as e:
            raise RuntimeError(f"soundfile processing failed: {e}")

    def _process_with_pydub(self, audio_data: bytes, format_hint: str = 'webm') -> Tuple[np.ndarray, int]:
        """Process audio using pydub"""
        try:
            # Determine format
            if format_hint in ['webm', 'ogg']:
                if not FFMPEG_AVAILABLE:
                    raise RuntimeError("FFmpeg required for WebM/OGG with pydub")
                audio_segment = AudioSegment.from_file(io.BytesIO(audio_data), format='webm')
            elif format_hint == 'mp3':
                if not FFMPEG_AVAILABLE:
                    raise RuntimeError("FFmpeg required for MP3 with pydub")
                audio_segment = AudioSegment.from_mp3(io.BytesIO(audio_data))
            else:
                # Try WAV (doesn't need FFmpeg)
                audio_segment = AudioSegment.from_wav(io.BytesIO(audio_data))
            
            # Convert to mono and resample
            audio_segment = audio_segment.set_channels(1)
            audio_segment = audio_segment.set_frame_rate(self.target_sample_rate)
            
            # Convert to numpy array
            audio_array = np.array(audio_segment.get_array_of_samples(), dtype=np.float32)
            audio_array = audio_array / (2**15)  # Normalize to [-1, 1]
            
            return audio_array, self.target_sample_rate
            
        except Exception as e:
            raise RuntimeError(f"pydub processing failed: {e}")

    def _process_with_scipy(self, audio_data: bytes) -> Tuple[np.ndarray, int]:
        """Process audio using scipy (WAV only)"""
        try:
            # scipy only handles WAV files
            sample_rate, audio_array = wavfile.read(io.BytesIO(audio_data))
            
            # Convert to float32 and normalize
            if audio_array.dtype == np.int16:
                audio_array = audio_array.astype(np.float32) / 32768.0
            elif audio_array.dtype == np.int32:
                audio_array = audio_array.astype(np.float32) / 2147483648.0
            else:
                audio_array = audio_array.astype(np.float32)
            
            # Convert to mono if stereo
            if len(audio_array.shape) > 1:
                audio_array = np.mean(audio_array, axis=1)
            
            # Simple resampling if needed
            if sample_rate != self.target_sample_rate:
                audio_array = self._simple_resample(
                    audio_array, sample_rate, self.target_sample_rate
                )
                sample_rate = self.target_sample_rate
            
            return audio_array, sample_rate
            
        except Exception as e:
            raise RuntimeError(f"scipy processing failed: {e}")

    def _simple_resample(self, audio: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
        """Simple linear interpolation resampling"""
        if orig_sr == target_sr:
            return audio
        
        # Calculate new length
        new_length = int(len(audio) * target_sr / orig_sr)
        
        # Create new time axis
        old_indices = np.linspace(0, len(audio) - 1, len(audio))
        new_indices = np.linspace(0, len(audio) - 1, new_length)
        
        # Interpolate
        resampled = np.interp(new_indices, old_indices, audio)
        return resampled.astype(np.float32)

    def create_wav_from_array(self, audio_array: np.ndarray, sample_rate: int) -> bytes:
        """Convert numpy array to WAV bytes"""
        # Convert to 16-bit PCM
        audio_int16 = (audio_array * 32767).astype(np.int16)
        
        # Create WAV file in memory
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)  # mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_int16.tobytes())
        
        return wav_buffer.getvalue()


# Flask/FastAPI integration examples
class WhisperAudioHandler:
    """Complete audio handling for Whisper integration"""
    
    def __init__(self):
        logger.info("Initializing WhisperAudioHandler")
        self.processor = AudioProcessor()
        
        # Use startup device check
        import os
        device = os.environ.get('WHISPER_DEVICE', 'cpu')
        model_name = os.environ.get('WHISPER_MODEL', 'base')
        print(f"[Whisper] device={device}, model={model_name}")
        
        # Import Whisper
        try:
            import whisper
            logger.info(f"Loading Whisper model '{model_name}' on {device}")
            print(f"[Whisper] loading model '{model_name}'...")
            
            self.whisper_model = whisper.load_model(model_name, device=device)
            self.whisper_available = True
            
            logger.info(f"Whisper model loaded successfully on {device}")
            print(f"[Whisper] ready on {device}")
            
        except ImportError:
            self.whisper_available = False
            logger.warning("Whisper not available. Install with: pip install openai-whisper")
            print("[Whisper] ERROR: module not available (pip install openai-whisper)")
        except Exception as e:
            self.whisper_available = False
            logger.error(f"Failed to load Whisper model: {e}")
            print(f"[Whisper] ERROR loading model: {e}")
    
    def transcribe_audio_bytes(self, audio_bytes: bytes, 
                              format_hint: str = 'webm') -> Dict[str, Any]:
        """Transcribe audio bytes without FFmpeg"""
        logger.info(f"Starting transcription: {len(audio_bytes)} bytes, format: {format_hint}")
        try:
            if not self.whisper_available:
                logger.error("Whisper not available for transcription")
                return {"success": False, "error": "Whisper not installed"}
            
            # Process audio
            logger.info("Processing audio for transcription")
            audio_array, sample_rate = self.processor.process_audio_for_whisper(
                audio_bytes, format_hint
            )
            
            # Transcribe with Whisper
            logger.info("Starting Whisper transcription")
            result = self.whisper_model.transcribe(audio_array)
            
            transcript_text = result["text"].strip()
            logger.info(f"Transcription complete: '{transcript_text[:100]}{'...' if len(transcript_text) > 100 else ''}'")
            
            return {
                "success": True,
                "text": transcript_text,
                "language": result["language"],
                "segments": result["segments"],
                "processing_info": {
                    "sample_rate": sample_rate,
                    "duration": len(audio_array) / sample_rate,
                    "processor_used": self.processor.get_best_processor()
                }
            }
            
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get audio processing capabilities"""
        import os
        return {
            "whisper_available": self.whisper_available,
            "available_processors": self.processor.available_processors,
            "recommended_processor": self.processor.get_best_processor(),
            "target_sample_rate": self.processor.target_sample_rate,
            "device": os.environ.get('WHISPER_DEVICE', 'cpu'),
            "model": os.environ.get('WHISPER_MODEL', 'base')
        }


# Usage examples for different frameworks
def flask_example():
    """Flask integration example"""
    from flask import Flask, request, jsonify
    
    app = Flask(__name__)
    handler = WhisperAudioHandler()
    
    @app.route('/transcribe', methods=['POST'])
    def transcribe():
        if 'audio' not in request.files:
            return jsonify({"error": "No audio file provided"}), 400
        
        audio_file = request.files['audio']
        audio_bytes = audio_file.read()
        format_hint = request.form.get('format', 'webm')
        
        result = handler.transcribe_audio_bytes(audio_bytes, format_hint)
        
        if result.get('success'):
            return jsonify(result)
        else:
            return jsonify(result), 500
    
    @app.route('/audio-info')
    def audio_info():
        return jsonify(handler.get_system_info())
    
    return app

def fastapi_example():
    """FastAPI integration example"""
    from fastapi import FastAPI, File, UploadFile, Form
    from fastapi.responses import JSONResponse
    
    app = FastAPI()
    handler = WhisperAudioHandler()
    
    @app.post("/transcribe")
    async def transcribe(
        audio: UploadFile = File(...),
        format_hint: str = Form("webm")
    ):
        audio_bytes = await audio.read()
        result = handler.transcribe_audio_bytes(audio_bytes, format_hint)
        
        if result.get('success'):
            return result
        else:
            return JSONResponse(content=result, status_code=500)
    
    @app.get("/audio-info")
    async def audio_info():
        return handler.get_system_info()
    
    return app


if __name__ == "__main__":
    # Test the audio processor
    processor = AudioProcessor()
    print("Available audio processors:", processor.available_processors)
    print("Recommended processor:", processor.get_best_processor())
    
    handler = WhisperAudioHandler()
    print("System info:", handler.get_system_info())
