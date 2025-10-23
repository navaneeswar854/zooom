"""
Integrated audio manager for the collaboration client.
Combines audio capture and playback functionality with connection management.
"""

import logging
from typing import Optional, Callable
from client.audio_capture import AudioCapture
from client.audio_playback import AudioPlayback
from client.connection_manager import ConnectionManager
from common.messages import UDPPacket

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AudioManager:
    """
    Integrated audio management system for the collaboration client.
    
    Handles:
    - Audio capture from microphone
    - Audio playback from server
    - Integration with connection manager
    - Audio controls (mute/unmute for both capture and playback)
    """
    
    def __init__(self, client_id: str, connection_manager: ConnectionManager):
        """
        Initialize the audio manager.
        
        Args:
            client_id: Unique identifier for this client
            connection_manager: Connection manager instance for network communication
        """
        self.client_id = client_id
        self.connection_manager = connection_manager
        
        # Audio components
        self.audio_capture: Optional[AudioCapture] = None
        self.audio_playback: Optional[AudioPlayback] = None
        
        # Audio state
        self.is_audio_enabled = False
        self.is_capture_muted = False
        self.is_playback_muted = False
        
        # Callbacks
        self.audio_level_callback: Optional[Callable[[float], None]] = None
        
        # Initialize audio components
        self._initialize_audio_components()
        
        # Register for incoming audio packets
        self.connection_manager.register_audio_callback(self._handle_incoming_audio)
    
    def _initialize_audio_components(self):
        """Initialize audio capture and playback components."""
        try:
            # Initialize audio capture
            self.audio_capture = AudioCapture(self.client_id)
            self.audio_capture.set_audio_callback(self._handle_captured_audio)
            
            # Initialize audio playback
            self.audio_playback = AudioPlayback()
            
            logger.info("Audio components initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize audio components: {e}")
            raise RuntimeError(f"Audio system initialization failed: {e}")
    
    def start_audio(self) -> bool:
        """
        Start audio capture and playback.
        
        Returns:
            bool: True if audio started successfully
        """
        if self.is_audio_enabled:
            logger.warning("Audio already enabled")
            return True
        
        try:
            # Start audio capture
            if not self.audio_capture.start_capture():
                logger.error("Failed to start audio capture")
                return False
            
            # Start audio playback
            if not self.audio_playback.start_playback():
                logger.error("Failed to start audio playback")
                self.audio_capture.stop_capture()
                return False
            
            self.is_audio_enabled = True
            
            # Update media status on server
            self.connection_manager.update_media_status(
                video_enabled=False,  # We're only handling audio here
                audio_enabled=True
            )
            
            logger.info("Audio system started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start audio system: {e}")
            return False
    
    def stop_audio(self):
        """Stop audio capture and playback."""
        if not self.is_audio_enabled:
            return
        
        try:
            # Stop audio capture
            if self.audio_capture:
                self.audio_capture.stop_capture()
            
            # Stop audio playback
            if self.audio_playback:
                self.audio_playback.stop_playback()
            
            self.is_audio_enabled = False
            
            # Update media status on server
            self.connection_manager.update_media_status(
                video_enabled=False,
                audio_enabled=False
            )
            
            logger.info("Audio system stopped")
            
        except Exception as e:
            logger.error(f"Error stopping audio system: {e}")
    
    def set_capture_muted(self, muted: bool):
        """
        Set mute state for audio capture (microphone).
        
        Args:
            muted: True to mute microphone, False to unmute
        """
        self.is_capture_muted = muted
        
        if self.audio_capture:
            self.audio_capture.set_muted(muted)
        
        logger.info(f"Audio capture {'muted' if muted else 'unmuted'}")
    
    def set_playback_muted(self, muted: bool):
        """
        Set mute state for audio playback (speakers).
        
        Args:
            muted: True to mute speakers, False to unmute
        """
        self.is_playback_muted = muted
        
        if self.audio_playback:
            self.audio_playback.set_muted(muted)
        
        logger.info(f"Audio playback {'muted' if muted else 'unmuted'}")
    
    def set_muted(self, muted: bool):
        """
        Set mute state for both capture and playback.
        
        Args:
            muted: True to mute both, False to unmute both
        """
        self.set_capture_muted(muted)
        # Note: Usually we don't mute playback when user mutes themselves
        # Only mute capture (microphone) when user clicks mute
    
    def is_capture_muted_state(self) -> bool:
        """
        Get current capture mute state.
        
        Returns:
            bool: True if capture is muted
        """
        return self.is_capture_muted
    
    def is_playback_muted_state(self) -> bool:
        """
        Get current playback mute state.
        
        Returns:
            bool: True if playback is muted
        """
        return self.is_playback_muted
    
    def is_enabled(self) -> bool:
        """
        Get current audio enabled state.
        
        Returns:
            bool: True if audio is enabled
        """
        return self.is_audio_enabled
    
    def set_audio_level_callback(self, callback: Callable[[float], None]):
        """
        Set callback for audio level updates.
        
        Args:
            callback: Function to call with audio level (0.0 to 1.0)
        """
        self.audio_level_callback = callback
    
    def _handle_captured_audio(self, audio_packet: UDPPacket):
        """
        Handle audio packet captured from microphone.
        
        Args:
            audio_packet: UDP packet containing captured audio data
        """
        try:
            # Send audio packet to server via connection manager
            if self.connection_manager and not self.is_capture_muted:
                self.connection_manager.send_audio_data(audio_packet.data)
            
            # Calculate audio level for GUI feedback (simple RMS calculation)
            if self.audio_level_callback and not self.is_capture_muted:
                audio_level = self._calculate_audio_level(audio_packet.data)
                self.audio_level_callback(audio_level)
            
        except Exception as e:
            logger.error(f"Error handling captured audio: {e}")
    
    def _handle_incoming_audio(self, audio_packet: UDPPacket):
        """
        Handle incoming audio packet from server.
        
        Args:
            audio_packet: UDP packet containing audio data from server
        """
        try:
            # Add audio packet to playback buffer
            if self.audio_playback and self.is_audio_enabled:
                self.audio_playback.add_audio_packet(audio_packet)
            
        except Exception as e:
            logger.error(f"Error handling incoming audio: {e}")
    
    def _calculate_audio_level(self, audio_data: bytes) -> float:
        """
        Calculate audio level from raw audio data.
        
        Args:
            audio_data: Raw audio data bytes
            
        Returns:
            float: Audio level from 0.0 to 1.0
        """
        try:
            # Convert bytes to 16-bit signed integers
            import struct
            samples = struct.unpack(f'<{len(audio_data)//2}h', audio_data)
            
            # Calculate RMS (Root Mean Square) for audio level
            if samples:
                rms = (sum(sample * sample for sample in samples) / len(samples)) ** 0.5
                # Normalize to 0.0-1.0 range (32767 is max for 16-bit signed)
                level = min(rms / 32767.0, 1.0)
                return level
            
            return 0.0
            
        except Exception as e:
            logger.error(f"Error calculating audio level: {e}")
            return 0.0
    
    def get_audio_info(self) -> dict:
        """
        Get comprehensive audio system information.
        
        Returns:
            dict: Audio system status and configuration
        """
        info = {
            'audio_enabled': self.is_audio_enabled,
            'capture_muted': self.is_capture_muted,
            'playback_muted': self.is_playback_muted,
            'capture_info': None,
            'playback_info': None
        }
        
        if self.audio_capture:
            info['capture_info'] = self.audio_capture.get_audio_info()
        
        if self.audio_playback:
            info['playback_info'] = self.audio_playback.get_playback_info()
            info['buffer_status'] = self.audio_playback.get_buffer_status()
        
        return info
    
    def cleanup(self):
        """Clean up audio resources."""
        try:
            self.stop_audio()
            
            if self.audio_capture:
                self.audio_capture.cleanup()
            
            if self.audio_playback:
                self.audio_playback.cleanup()
            
            logger.info("Audio manager cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during audio manager cleanup: {e}")