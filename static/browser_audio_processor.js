/**
 * Browser Audio Processing for Whisper (No FFmpeg Required)
 * Converts browser audio to formats that Whisper can process directly
 */

class AudioProcessor {
    constructor() {
        this.audioContext = null;
        this.sampleRate = 16000; // Whisper's preferred sample rate
        this.logPrefix = '[BrowserAudioProcessor]';
        console.log(`${this.logPrefix} Initialized with sample rate: ${this.sampleRate}Hz`);
    }

    /**
     * Convert WebM/MP3 audio blob to WAV PCM format for Whisper
     */
    async blobToWhisperFormat(audioBlob) {
        console.log(`${this.logPrefix} Starting blobToWhisperFormat, blob size: ${audioBlob.size} bytes, type: ${audioBlob.type}`);
        try {
            // Method 1: Use Web Audio API to decode and convert
            const arrayBuffer = await audioBlob.arrayBuffer();
            console.log(`${this.logPrefix} Converted blob to ArrayBuffer, size: ${arrayBuffer.byteLength} bytes`);
            
            if (!this.audioContext) {
                this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
                console.log(`${this.logPrefix} Created new AudioContext, sample rate: ${this.audioContext.sampleRate}Hz`);
            }

            // Decode audio data
            console.log(`${this.logPrefix} Decoding audio data...`);
            const audioBuffer = await this.audioContext.decodeAudioData(arrayBuffer);
            console.log(`${this.logPrefix} Audio decoded - channels: ${audioBuffer.numberOfChannels}, sample rate: ${audioBuffer.sampleRate}Hz, duration: ${audioBuffer.duration.toFixed(2)}s`);
            
            // Convert to mono if stereo
            let audioData;
            if (audioBuffer.numberOfChannels === 1) {
                audioData = audioBuffer.getChannelData(0);
                console.log(`${this.logPrefix} Audio is already mono, ${audioData.length} samples`);
            } else {
                // Mix stereo to mono
                console.log(`${this.logPrefix} Converting stereo to mono`);
                const left = audioBuffer.getChannelData(0);
                const right = audioBuffer.getChannelData(1);
                audioData = new Float32Array(left.length);
                for (let i = 0; i < left.length; i++) {
                    audioData[i] = (left[i] + right[i]) / 2;
                }
                console.log(`${this.logPrefix} Stereo to mono conversion complete, ${audioData.length} samples`);
            }

            // Resample to 16kHz if necessary
            if (audioBuffer.sampleRate !== this.sampleRate) {
                console.log(`${this.logPrefix} Resampling from ${audioBuffer.sampleRate}Hz to ${this.sampleRate}Hz`);
                audioData = this.resampleAudio(audioData, audioBuffer.sampleRate, this.sampleRate);
                console.log(`${this.logPrefix} Resampling complete, ${audioData.length} samples`);
            } else {
                console.log(`${this.logPrefix} No resampling needed, already at ${this.sampleRate}Hz`);
            }

            // Convert to WAV format
            console.log(`${this.logPrefix} Encoding to WAV format...`);
            const wavBuffer = this.encodeWAV(audioData, this.sampleRate);
            console.log(`${this.logPrefix} WAV encoding complete, buffer size: ${wavBuffer.byteLength} bytes`);
            
            return {
                success: true,
                audioData: wavBuffer,
                sampleRate: this.sampleRate,
                duration: audioData.length / this.sampleRate,
                format: 'wav'
            };

        } catch (error) {
            console.error(`${this.logPrefix} Audio processing error:`, error);
            return {
                success: false,
                error: error.message
            };
        }
    }

    /**
     * Simple linear resampling (for more accuracy, use a proper resampling library)
     */
    resampleAudio(audioData, originalSampleRate, targetSampleRate) {
        console.log(`${this.logPrefix} Starting resampling: ${originalSampleRate}Hz -> ${targetSampleRate}Hz`);
        if (originalSampleRate === targetSampleRate) {
            console.log(`${this.logPrefix} No resampling needed, rates are equal`);
            return audioData;
        }

        const ratio = originalSampleRate / targetSampleRate;
        const newLength = Math.round(audioData.length / ratio);
        const result = new Float32Array(newLength);
        console.log(`${this.logPrefix} Resampling ${audioData.length} samples to ${newLength} samples (ratio: ${ratio.toFixed(3)})`);

        for (let i = 0; i < newLength; i++) {
            const originalIndex = i * ratio;
            const index = Math.floor(originalIndex);
            const fraction = originalIndex - index;
            
            if (index + 1 < audioData.length) {
                result[i] = audioData[index] * (1 - fraction) + audioData[index + 1] * fraction;
            } else {
                result[i] = audioData[index];
            }
        }

        console.log(`${this.logPrefix} Resampling complete`);
        return result;
    }

    /**
     * Encode Float32Array as WAV file
     */
    encodeWAV(audioData, sampleRate) {
        console.log(`${this.logPrefix} Encoding WAV: ${audioData.length} samples at ${sampleRate}Hz`);
        const length = audioData.length;
        const arrayBuffer = new ArrayBuffer(44 + length * 2);
        const view = new DataView(arrayBuffer);

        // WAV header
        const writeString = (offset, string) => {
            for (let i = 0; i < string.length; i++) {
                view.setUint8(offset + i, string.charCodeAt(i));
            }
        };

        writeString(0, 'RIFF');
        view.setUint32(4, 36 + length * 2, true);
        writeString(8, 'WAVE');
        writeString(12, 'fmt ');
        view.setUint32(16, 16, true);
        view.setUint16(20, 1, true);
        view.setUint16(22, 1, true); // mono
        view.setUint32(24, sampleRate, true);
        view.setUint32(28, sampleRate * 2, true);
        view.setUint16(32, 2, true);
        view.setUint16(34, 16, true);
        writeString(36, 'data');
        view.setUint32(40, length * 2, true);

        // Convert float samples to 16-bit PCM
        let offset = 44;
        for (let i = 0; i < length; i++) {
            const sample = Math.max(-1, Math.min(1, audioData[i]));
            view.setInt16(offset, sample < 0 ? sample * 0x8000 : sample * 0x7FFF, true);
            offset += 2;
        }

        console.log(`${this.logPrefix} WAV encoding complete: ${arrayBuffer.byteLength} bytes`);
        return arrayBuffer;
    }

    /**
     * Record directly to PCM format for Whisper
     */
    async recordDirectToPCM(mediaStream, maxDuration = 60000) {
        return new Promise((resolve, reject) => {
            try {
                if (!this.audioContext) {
                    this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
                }

                const source = this.audioContext.createMediaStreamSource(mediaStream);
                const processor = this.audioContext.createScriptProcessor(4096, 1, 1);
                
                const audioData = [];
                const startTime = Date.now();

                processor.onaudioprocess = (event) => {
                    const inputBuffer = event.inputBuffer;
                    const inputData = inputBuffer.getChannelData(0);
                    
                    // Resample to 16kHz if needed
                    let processedData = inputData;
                    if (this.audioContext.sampleRate !== this.sampleRate) {
                        processedData = this.resampleAudio(
                            inputData, 
                            this.audioContext.sampleRate, 
                            this.sampleRate
                        );
                    }
                    
                    audioData.push(new Float32Array(processedData));
                    
                    // Check duration
                    if (Date.now() - startTime > maxDuration) {
                        this.stopRecording();
                    }
                };

                const stopRecording = () => {
                    processor.disconnect();
                    source.disconnect();
                    
                    // Combine all audio chunks
                    const totalLength = audioData.reduce((sum, chunk) => sum + chunk.length, 0);
                    const combinedAudio = new Float32Array(totalLength);
                    let offset = 0;
                    
                    for (const chunk of audioData) {
                        combinedAudio.set(chunk, offset);
                        offset += chunk.length;
                    }

                    // Convert to WAV
                    const wavBuffer = this.encodeWAV(combinedAudio, this.sampleRate);
                    
                    resolve({
                        success: true,
                        audioData: wavBuffer,
                        sampleRate: this.sampleRate,
                        duration: totalLength / this.sampleRate,
                        format: 'wav'
                    });
                };

                this.stopRecording = stopRecording;
                source.connect(processor);
                processor.connect(this.audioContext.destination);

            } catch (error) {
                reject({
                    success: false,
                    error: error.message
                });
            }
        });
    }
}

// Usage examples for different scenarios
class WhisperAudioHandler {
    constructor() {
        this.processor = new AudioProcessor();
        this.logPrefix = '[WhisperAudioHandler]';
        console.log(`${this.logPrefix} Initialized with AudioProcessor`);
    }

    /**
     * Handle audio from MediaRecorder (WebM/MP3)
     */
    async processRecordedAudio(audioBlob) {
        console.log(`${this.logPrefix} Processing recorded audio blob, size: ${audioBlob.size} bytes, type: ${audioBlob.type}`);
        const result = await this.processor.blobToWhisperFormat(audioBlob);
        
        if (result.success) {
            console.log(`${this.logPrefix} Audio processing successful, sending to Whisper`);
            return await this.sendToWhisper(result.audioData);
        } else {
            console.error(`${this.logPrefix} Audio processing failed: ${result.error}`);
            throw new Error(`Audio processing failed: ${result.error}`);
        }
    }

    /**
     * Handle direct PCM recording
     */
    async processDirectRecording(mediaStream) {
        console.log('Recording directly to PCM format...');
        const result = await this.processor.recordDirectToPCM(mediaStream);
        
        if (result.success) {
            return await this.sendToWhisper(result.audioData);
        } else {
            throw new Error(`Direct recording failed: ${result.error}`);
        }
    }

    /**
     * Send processed audio to Whisper endpoint
     */
    async sendToWhisper(audioBuffer) {
        console.log(`${this.logPrefix} Sending audio to Whisper, buffer size: ${audioBuffer.byteLength} bytes`);
        try {
            const formData = new FormData();
            const audioBlob = new Blob([audioBuffer], { type: 'audio/wav' });
            formData.append('audio', audioBlob, 'audio.wav');
            formData.append('model', 'whisper-1');
            formData.append('response_format', 'json');

            console.log(`${this.logPrefix} Making request to /voice/transcribe`);
            const response = await fetch('/voice/transcribe', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                console.error(`${this.logPrefix} Whisper API error: ${response.status} ${response.statusText}`);
                throw new Error(`Whisper API error: ${response.status}`);
            }

            const result = await response.json();
            console.log(`${this.logPrefix} Whisper response received:`, result);
            return {
                success: true,
                transcript: result.text || result.transcript || '',
                language: result.language || '',
                confidence: result.confidence || null
            };

        } catch (error) {
            console.error(`${this.logPrefix} Whisper transcription error:`, error);
            return {
                success: false,
                error: error.message
            };
        }
    }
}

// Integration with your existing chat interface
window.WhisperAudioHandler = WhisperAudioHandler;
window.AudioProcessor = AudioProcessor;

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { WhisperAudioHandler, AudioProcessor };
}
