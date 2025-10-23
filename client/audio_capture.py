"""
Audio capture and encoding module for the collaboration client.
Handles microphone input capture, audio encoding, and UDP packet creation.
"""

import threading
import time
import logging
from typing import Optional, Callable, List
from common.messages import UDPPacket, MessageFactory
from common.platform_utils import PLATFORM_INFO, DeviceUtils, ErrorHandler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Platform-specific imports
try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False
    logger.warning("PyAudio not available - audio capture disabled")


class AudioCapture:
    """Handles microphone input capture and audio encoding."""
    
    # Audio configuration constants
    SAMPLE_RATE = 16000  # 16kHz sample rate for good quality with low bandwidth
    CHANNELS = 1  # Mono audio
    CHUNK_SIZE = 1024  # Number of frames per buffer
    FORMAT = pyaudio.paInt16  # 16-bit audio format
    
    def __init__(self, client_id: str):
        """Initialize audio capture system.
        
        Args:
            client_id: Unique identifier for this client
        """
        self.client_id = client_id
        self.pyaudio_instance: Optional[pyaudio.PyAudio] = None
        self.stream: Optional[pyaudio.Stream] = None
        self.is_capturing = False
        self.is_muted = False
        self.sequence_number = 0
        self.capture_thread: Optional[threading.Thread] = None
        self.audio_callback: Optional[Callable[[UDPPacket], None]] = None
        
        # Initialize PyAudio
        self._initialize_pyaudio()
    
    def _initialize_pyaudio(self):
        """Initialize PyAudio instance and check for available devices."""
        if not PYAUDIO_AVAILABLE:
            raise RuntimeError("PyAudio not available on this platform")
        
        if not PLATFORM_INFO.get_capability('audio_capture'):
            raise RuntimeError("Audio capture not supported on this platform")
        
        try:
            self.pyaudio_instance = pyaudio.PyAudio()
            
            # Log available audio devices for debugging
            device_count = self.pyaudio_instance.get_device_count()
            logger.info(f"Found {device_count} audio devices")
            
            # Get available audio devices using platform utils
            available_devices = DeviceUtils.get_audio_devices()
            if available_devices:
                logger.info(f"Available audio input devices: {len(available_devices)}")
                for device in available_devices[:3]:  # Log first 3 devices
                    logger.info(f"  - {device['name']} (channels: {device['channels']})")
            
            # Find default input device
            try:
                default_input = self.pyaudio_instance.get_default_input_device_info()
                logger.info(f"Default input device: {default_input['name']}")
            except Exception as e:
                logger.warning(f"Could not get default input device: {e}")
                # Try to use first available device
                if available_devices:
                    logger.info(f"Using first available device: {available_devices[0]['name']}")
            
        except Exception as e:
            error_msg = ErrorHandler.get_platform_specific_error_message(e)
            fix_suggestion = ErrorHandler.suggest_platform_fix(e)
            
            logger.error(f"Failed to initialize PyAudio: {error_msg}")
            if fix_suggestion:
                logger.error(f"Suggested fix: {fix_suggestion}")
            
            raise RuntimeError(f"Audio system initialization failed: {error_msg}")
    
    def set_audio_callback(self, callback: Callable[[UDPPacket], None]):
        """Set callback function to handle captured audio packets.
        
        Args:
            callback: Function to call with each audio packet
        """
        self.audio_callback = callback
    
    def start_capture(self) -> bool:
        """Start audio capture from microphone.
        
        Returns:
            bool: True if capture started successfully, False otherwise
        """
        if self.is_capturing:
            logger.warning("Audio capture already running")
            return True
        
        if not self.pyaudio_instance:
            logger.error("PyAudio not initialized")
            return False
        
        try:
            # Open audio stream
            self.stream = self.pyaudio_instance.open(
                format=self.FORMAT,
                channels=self.CHANNELS,
                rate=self.SAMPLE_RATE,
                input=True,
                frames_per_buffer=self.CHUNK_SIZE,
                stream_callback=None  # We'll use blocking read mode
            )
            
            self.is_capturing = True
            self.sequence_number = 0
            
            # Start capture thread
            self.capture_thread = threading.Thread(
                target=self._capture_loop,
                daemon=True
            )
            self.capture_thread.start()
            
            logger.info("Audio capture started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start audio capture: {e}")
            return False
    
    def stop_capture(self):
        """Stop audio capture."""
        if not self.is_capturing:
            return
        
        self.is_capturing = False
        
        # Wait for capture thread to finish
        if self.capture_thread and self.capture_thread.is_alive():
            self.capture_thread.join(timeout=1.0)
        
        # Close audio stream
        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except Exception as e:
                logger.error(f"Error closing audio stream: {e}")
            finally:
                self.stream = None
        
        logger.info("Audio capture stopped")
    
    def set_muted(self, muted: bool):
        """Set mute state for audio capture.
        
        Args:
            muted: True to mute audio, False to unmute
        """
        self.is_muted = muted
        logger.info(f"Audio {'muted' if muted else 'unmuted'}")
    
    def is_muted_state(self) -> bool:
        """Get current mute state.
        
        Returns:
            bool: True if muted, False if not muted
        """
        return self.is_muted
    
    def _capture_loop(self):
        """Main audio capture loop running in separate thread."""
        logger.info("Audio capture loop started")
        
        while self.is_capturing and self.stream:
            try:
                # Read audio data from stream
                audio_data = self.stream.read(
                    self.CHUNK_SIZE,
                    exception_on_overflow=False
                )
                
                # Skip processing if muted
                if self.is_muted:
                    continue
                
                # Encode audio data (currently just raw PCM, can be enhanced with Opus later)
                encoded_audio = self._encode_audio(audio_data)
                
                # Create UDP packet
                audio_packet = MessageFactory.create_audio_packet(
                    sender_id=self.client_id,
                    sequence_num=self.sequence_number,
                    audio_data=encoded_audio
                )
                
                self.sequence_number += 1
                
                # Send packet via callback if available
                if self.audio_callback:
                    self.audio_callback(audio_packet)
                
            except Exception as e:
                if self.is_capturing:  # Only log if we're still supposed to be capturing
                    logger.error(f"Error in audio capture loop: {e}")
                break
        
        logger.info("Audio capture loop ended")
    
    def _encode_audio(self, raw_audio: bytes) -> bytes:
        """Encode raw audio data.
        
        Currently returns raw PCM data. Can be enhanced with Opus codec later.
        
        Args:
            raw_audio: Raw audio data from microphone
            
        Returns:
            bytes: Encoded audio data
        """
        # For now, return raw PCM data
        # TODO: Implement Opus encoding for better compression
        return raw_audio
    
    def get_audio_info(self) -> dict:
        """Get current audio configuration information.
        
        Returns:
            dict: Audio configuration details
        """
        return {
            'sample_rate': self.SAMPLE_RATE,
            'channels': self.CHANNELS,
            'chunk_size': self.CHUNK_SIZE,
            'format': 'PCM 16-bit',
            'is_capturing': self.is_capturing,
            'is_muted': self.is_muted,
            'sequence_number': self.sequence_number
        }
    
    def cleanup(self):
        """Clean up audio resources."""
        self.stop_capture()
        
        if self.pyaudio_instance:
            try:
                self.pyaudio_instance.terminate()
            except Exception as e:
                logger.error(f"Error terminating PyAudio: {e}")
            finally:
                self.pyaudio_instance = None
        
        logger.info("Audio capture cleanup completed")


class AudioEncoder:
    """Audio encoding utilities for different codecs."""
    
    @staticmethod
    def encode_pcm(audio_data: bytes, sample_rate: int = 16000, channels: int = 1) -> bytes:
        """Encode audio as PCM (no compression).
        
        Args:
            audio_data: Raw audio data
            sample_rate: Audio sample rate
            channels: Number of audio channels
            
        Returns:
            bytes: PCM encoded audio data
        """
        # PCM is just raw audio data, no encoding needed
        return audio_data
    
    @staticmethod
    def get_supported_codecs() -> List[str]:
        """Get list of supported audio codecs.
        
        Returns:
            List[str]: List of supported codec names
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