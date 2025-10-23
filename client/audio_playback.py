"""
Audio playback module for the collaboration client.
Handles audio stream reception, decoding, and real-time playback.
"""

import pyaudio
import threading
import time
import logging
from typing import Optional, Callable
from collections import deque
from common.messages import UDPPacket

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AudioPlayback:
    """Handles audio stream reception, decoding, and real-time playback."""
    
    # Audio configuration constants (must match capture settings)
    SAMPLE_RATE = 16000  # 16kHz sample rate
    CHANNELS = 1  # Mono audio
    CHUNK_SIZE = 320  # Smaller chunks for lower latency (20ms at 16kHz)
    FORMAT = pyaudio.paInt16  # 16-bit audio format
    BUFFER_SIZE = 5  # Smaller buffer for lower latency
    
    def __init__(self):
        """Initialize audio playback system."""
        self.pyaudio_instance: Optional[pyaudio.PyAudio] = None
        self.stream: Optional[pyaudio.Stream] = None
        self.is_playing = False
        self.is_muted = False
        self.playback_thread: Optional[threading.Thread] = None
        
        # Audio buffer for incoming packets
        self.audio_buffer = deque(maxlen=self.BUFFER_SIZE)
        self.buffer_lock = threading.Lock()
        
        # Statistics
        self.stats = {
            'packets_received': 0,
            'packets_played': 0,
            'buffer_underruns': 0,
            'playback_start_time': None
        }
        
        # Initialize PyAudio
        self._initialize_pyaudio()
    
    def _initialize_pyaudio(self):
        """Initialize PyAudio instance and check for available devices."""
        try:
            self.pyaudio_instance = pyaudio.PyAudio()
            
            # Log available audio devices for debugging
            device_count = self.pyaudio_instance.get_device_count()
            logger.info(f"Found {device_count} audio devices")
            
            # Find default output device
            default_output = self.pyaudio_instance.get_default_output_device_info()
            logger.info(f"Default output device: {default_output['name']}")
            
        except Exception as e:
            logger.error(f"Failed to initialize PyAudio for playback: {e}")
            raise RuntimeError(f"Audio playback system initialization failed: {e}")
    
    def start_playback(self) -> bool:
        """Start audio playback.
        
        Returns:
            bool: True if playback started successfully, False otherwise
        """
        if self.is_playing:
            logger.warning("Audio playback already running")
            return True
        
        if not self.pyaudio_instance:
            logger.error("PyAudio not initialized")
            return False
        
        try:
            # Open audio stream for output
            self.stream = self.pyaudio_instance.open(
                format=self.FORMAT,
                channels=self.CHANNELS,
                rate=self.SAMPLE_RATE,
                output=True,
                frames_per_buffer=self.CHUNK_SIZE,
                stream_callback=None  # We'll use blocking write mode
            )
            
            self.is_playing = True
            self.stats['playback_start_time'] = time.time()
            
            # Start playback thread
            self.playback_thread = threading.Thread(
                target=self._playback_loop,
                daemon=True
            )
            self.playback_thread.start()
            
            logger.info("Audio playback started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start audio playback: {e}")
            return False
    
    def stop_playback(self):
        """Stop audio playback."""
        if not self.is_playing:
            return
        
        self.is_playing = False
        
        # Wait for playback thread to finish
        if self.playback_thread and self.playback_thread.is_alive():
            self.playback_thread.join(timeout=1.0)
        
        # Close audio stream
        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except Exception as e:
                logger.error(f"Error closing audio playback stream: {e}")
            finally:
                self.stream = None
        
        # Clear audio buffer
        with self.buffer_lock:
            self.audio_buffer.clear()
        
        logger.info("Audio playback stopped")
    
    def add_audio_packet(self, audio_packet: UDPPacket):
        """Add received audio packet to playback buffer.
        
        Args:
            audio_packet: UDP packet containing audio data
        """
        if not self.is_playing:
            return
        
        try:
            with self.buffer_lock:
                # Decode audio data (currently just raw PCM)
                decoded_audio = self._decode_audio(audio_packet.data)
                
                # Add to buffer
                self.audio_buffer.append({
                    'data': decoded_audio,
                    'timestamp': audio_packet.timestamp,
                    'sequence': audio_packet.sequence_num
                })
                
                self.stats['packets_received'] += 1
                
        except Exception as e:
            logger.error(f"Error adding audio packet to buffer: {e}")
    
    def set_muted(self, muted: bool):
        """Set mute state for audio playback.
        
        Args:
            muted: True to mute audio, False to unmute
        """
        self.is_muted = muted
        logger.info(f"Audio playback {'muted' if muted else 'unmuted'}")
    
    def is_muted_state(self) -> bool:
        """Get current mute state.
        
        Returns:
            bool: True if muted, False if not muted
        """
        return self.is_muted
    
    def _playback_loop(self):
        """Main audio playback loop running in separate thread."""
        logger.info("Audio playback loop started")
        
        while self.is_playing and self.stream:
            try:
                # Get audio data from buffer
                audio_data = None
                
                with self.buffer_lock:
                    if self.audio_buffer:
                        audio_packet = self.audio_buffer.popleft()
                        audio_data = audio_packet['data']
                
                if audio_data and not self.is_muted:
                    # Play audio data
                    self.stream.write(audio_data)
                    self.stats['packets_played'] += 1
                else:
                    # No audio data available or muted - play silence
                    if not audio_data:
                        self.stats['buffer_underruns'] += 1
                    
                    # Generate silence
                    silence = b'\x00' * (self.CHUNK_SIZE * 2)  # 2 bytes per sample for 16-bit
                    self.stream.write(silence)
                    
                    # Small delay to prevent busy waiting
                    time.sleep(0.005)  # 5ms for better responsiveness
                
            except Exception as e:
                if self.is_playing:  # Only log if we're still supposed to be playing
                    logger.error(f"Error in audio playback loop: {e}")
                break
        
        logger.info("Audio playback loop ended")
    
    def _decode_audio(self, encoded_audio: bytes) -> bytes:
        """Decode audio data.
        
        Currently handles raw PCM data. Can be enhanced with Opus decoding later.
        
        Args:
            encoded_audio: Encoded audio data
            
        Returns:
            bytes: Decoded audio data ready for playback
        """
        # For now, return raw PCM data as-is
        # TODO: Implement Opus decoding for better compression
        return encoded_audio
    
    def get_playback_info(self) -> dict:
        """Get current audio playback information.
        
        Returns:
            dict: Playback configuration and statistics
        """
        buffer_size = 0
        with self.buffer_lock:
            buffer_size = len(self.audio_buffer)
        
        info = {
            'sample_rate': self.SAMPLE_RATE,
            'channels': self.CHANNELS,
            'chunk_size': self.CHUNK_SIZE,
            'format': 'PCM 16-bit',
            'is_playing': self.is_playing,
            'is_muted': self.is_muted,
            'buffer_size': buffer_size,
            'max_buffer_size': self.BUFFER_SIZE
        }
        
        # Add statistics
        info.update(self.stats)
        
        if self.stats['playback_start_time']:
            info['playback_duration'] = time.time() - self.stats['playback_start_time']
        
        return info
    
    def get_buffer_status(self) -> dict:
        """Get audio buffer status information.
        
        Returns:
            dict: Buffer status and health metrics
        """
        with self.buffer_lock:
            buffer_size = len(self.audio_buffer)
        
        buffer_health = "good"
        if buffer_size == 0:
            buffer_health = "empty"
        elif buffer_size < 2:
            buffer_health = "low"
        elif buffer_size >= self.BUFFER_SIZE - 1:
            buffer_health = "full"
        
        return {
            'current_size': buffer_size,
            'max_size': self.BUFFER_SIZE,
            'fill_percentage': (buffer_size / self.BUFFER_SIZE) * 100,
            'health': buffer_health,
            'underruns': self.stats['buffer_underruns']
        }
    
    def cleanup(self):
        """Clean up audio playback resources."""
        self.stop_playback()
        
        if self.pyaudio_instance:
            try:
                self.pyaudio_instance.terminate()
            except Exception as e:
                logger.error(f"Error terminating PyAudio for playback: {e}")
            finally:
                self.pyaudio_instance = None
        
        logger.info("Audio playback cleanup completed")


class AudioDecoder:
    """Audio decoding utilities for different codecs."""
    
    @staticmethod
    def decode_pcm(audio_data: bytes, sample_rate: int = 16000, channels: int = 1) -> bytes:
        """Decode PCM audio data (no decoding needed).
        
        Args:
            audio_data: PCM audio data
            sample_rate: Audio sample rate
            channels: Number of audio channels
            
        Returns:
            bytes: Decoded audio data
        """
        # PCM is raw audio data, no decoding needed
        return audio_data
    
    @staticmethod
    def get_supported_codecs() -> list:
        """Get list of supported audio codecs for decoding.
        
        Returns:
            list: List of supported codec names
        """
        return ['PCM']  # Only PCM supported for now
    
    @staticmethod
    def get_codec_info(codec_name: str) -> dict:
        """Get information about a specific codec.
        
        Args:
            codec_name: Name of the codec
            
        Returns:
            dict: Codec information
        """
        if codec_name.upper() == 'PCM':
            return {
                'name': 'PCM',
                'description': 'Pulse Code Modulation (uncompressed)',
                'compression_ratio': 1.0,
                'quality': 'Lossless',
                'latency': 'Very Low'
            }
        else:
            return {'error': f'Codec {codec_name} not supported'}