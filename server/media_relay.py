"""
Media relay system for the collaboration server.
Handles audio mixing and broadcasting for real-time communication.
"""

import threading
import time
import logging
import struct
from typing import Dict, List, Optional, Tuple
from collections import deque
from common.messages import UDPPacket, MessageFactory
from server.session_manager import SessionManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AudioMixer:
    """
    Audio mixing component for combining multiple audio streams.
    
    Handles:
    - Real-time audio stream mixing from multiple clients
    - Audio buffer management and synchronization
    - Mixed audio output generation for broadcasting
    """
    
    # Audio configuration constants
    SAMPLE_RATE = 16000  # 16kHz sample rate
    CHANNELS = 1  # Mono audio
    SAMPLE_WIDTH = 2  # 16-bit samples (2 bytes per sample)
    BUFFER_DURATION_MS = 20  # 20ms audio buffers
    SAMPLES_PER_BUFFER = int(SAMPLE_RATE * BUFFER_DURATION_MS / 1000)
    BYTES_PER_BUFFER = SAMPLES_PER_BUFFER * SAMPLE_WIDTH * CHANNELS
    
    def __init__(self):
        """Initialize the audio mixer."""
        self.client_buffers: Dict[str, deque] = {}  # client_id -> audio buffer queue
        self.mixed_audio_callback: Optional[callable] = None
        self.is_mixing = False
        self.mixing_thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()
        
        # Audio processing statistics
        self.stats = {
            'total_mixed_packets': 0,
            'active_audio_clients': 0,
            'mixing_start_time': None,
            'last_mix_time': None
        }
        
        # Adaptive quality settings
        self.current_quality_settings = {
            'sample_rate': self.SAMPLE_RATE,
            'bitrate': 64000,
            'channels': self.CHANNELS
        }
    
    def set_mixed_audio_callback(self, callback: callable):
        """
        Set callback function to handle mixed audio output.
        
        Args:
            callback: Function to call with mixed audio data (UDPPacket)
        """
        self.mixed_audio_callback = callback
    
    def start_mixing(self) -> bool:
        """
        Start the audio mixing process.
        
        Returns:
            bool: True if mixing started successfully
        """
        if self.is_mixing:
            logger.warning("Audio mixing already running")
            return True
        
        try:
            self.is_mixing = True
            self.stats['mixing_start_time'] = time.time()
            
            # Start mixing thread
            self.mixing_thread = threading.Thread(
                target=self._mixing_loop,
                daemon=True
            )
            self.mixing_thread.start()
            
            logger.info("Audio mixing started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start audio mixing: {e}")
            self.is_mixing = False
            return False
    
    def stop_mixing(self):
        """Stop the audio mixing process."""
        if not self.is_mixing:
            return
        
        self.is_mixing = False
        
        # Wait for mixing thread to finish
        if self.mixing_thread and self.mixing_thread.is_alive():
            self.mixing_thread.join(timeout=1.0)
        
        # Clear all buffers
        with self._lock:
            self.client_buffers.clear()
        
        logger.info("Audio mixing stopped")
    
    def add_audio_stream(self, client_id: str, audio_packet: UDPPacket):
        """
        Add audio data from a client to the mixing buffer.
        
        Args:
            client_id: ID of the client sending audio
            audio_packet: UDP packet containing audio data
        """
        with self._lock:
            # Initialize buffer for new client
            if client_id not in self.client_buffers:
                self.client_buffers[client_id] = deque(maxlen=10)  # Keep last 10 packets
                logger.info(f"Added audio stream for client {client_id}")
            
            # Add audio data to client's buffer
            self.client_buffers[client_id].append({
                'data': audio_packet.data,
                'timestamp': audio_packet.timestamp,
                'sequence': audio_packet.sequence_num
            })
    
    def remove_audio_stream(self, client_id: str):
        """
        Remove audio stream for a disconnected client.
        
        Args:
            client_id: ID of the client to remove
        """
        with self._lock:
            if client_id in self.client_buffers:
                del self.client_buffers[client_id]
                logger.info(f"Removed audio stream for client {client_id}")
    
    def _mixing_loop(self):
        """Main audio mixing loop running in separate thread."""
        logger.info("Audio mixing loop started")
        
        while self.is_mixing:
            try:
                # Mix audio from all active clients
                mixed_audio = self._mix_audio_buffers()
                
                if mixed_audio and self.mixed_audio_callback:
                    # Create mixed audio packet
                    mixed_packet = MessageFactory.create_audio_packet(
                        sender_id="server_mixer",
                        sequence_num=self.stats['total_mixed_packets'],
                        audio_data=mixed_audio
                    )
                    
                    # Send mixed audio via callback
                    self.mixed_audio_callback(mixed_packet)
                    
                    self.stats['total_mixed_packets'] += 1
                    self.stats['last_mix_time'] = time.time()
                
                # Sleep to maintain mixing rate (50Hz = 20ms intervals)
                time.sleep(0.02)
                
            except Exception as e:
                if self.is_mixing:  # Only log if we're still supposed to be mixing
                    logger.error(f"Error in audio mixing loop: {e}")
                break
        
        logger.info("Audio mixing loop ended")
    
    def _mix_audio_buffers(self) -> Optional[bytes]:
        """
        Mix audio data from all client buffers.
        
        Returns:
            bytes: Mixed audio data or None if no audio available
        """
        with self._lock:
            if not self.client_buffers:
                return None
            
            # Collect audio samples from all clients
            audio_samples = []
            active_clients = 0
            
            for client_id, buffer in self.client_buffers.items():
                if buffer:
                    # Get the most recent audio packet
                    audio_data = buffer.popleft()['data']
                    
                    # Convert bytes to 16-bit signed integers
                    try:
                        samples = struct.unpack(f'<{len(audio_data)//2}h', audio_data)
                        audio_samples.append(samples)
                        active_clients += 1
                    except struct.error:
                        logger.warning(f"Invalid audio data from client {client_id}")
                        continue
            
            self.stats['active_audio_clients'] = active_clients
            
            if not audio_samples:
                return None
            
            # Mix audio by averaging samples
            mixed_samples = self._average_audio_samples(audio_samples)
            
            # Convert back to bytes
            try:
                mixed_audio = struct.pack(f'<{len(mixed_samples)}h', *mixed_samples)
                return mixed_audio
            except struct.error as e:
                logger.error(f"Error packing mixed audio: {e}")
                return None
    
    def _average_audio_samples(self, audio_samples_list: List[Tuple[int, ...]]) -> List[int]:
        """
        Average audio samples from multiple sources.
        
        Args:
            audio_samples_list: List of audio sample tuples from different clients
            
        Returns:
            List of mixed audio samples
        """
        if not audio_samples_list:
            return []
        
        # Find the minimum length to avoid index errors
        min_length = min(len(samples) for samples in audio_samples_list)
        
        mixed_samples = []
        for i in range(min_length):
            # Average the samples at position i from all clients
            sample_sum = sum(samples[i] for samples in audio_samples_list)
            avg_sample = sample_sum // len(audio_samples_list)
            
            # Clamp to 16-bit signed integer range
            avg_sample = max(-32768, min(32767, avg_sample))
            mixed_samples.append(avg_sample)
        
        return mixed_samples
    
    def get_mixing_stats(self) -> Dict:
        """
        Get audio mixing statistics.
        
        Returns:
            dict: Mixing statistics and performance metrics
        """
        with self._lock:
            stats = self.stats.copy()
            stats['is_mixing'] = self.is_mixing
            stats['connected_audio_clients'] = len(self.client_buffers)
            
            if stats['mixing_start_time']:
                stats['mixing_duration'] = time.time() - stats['mixing_start_time']
            
            return stats
    
    def update_quality_settings(self, quality_settings: Dict):
        """
        Update audio quality settings for adaptive compression.
        
        Args:
            quality_settings: New quality settings dictionary
        """
        with self._lock:
            self.current_quality_settings.update(quality_settings)
            logger.info(f"Updated audio mixer quality settings: {quality_settings}")
    
    def get_quality_settings(self) -> Dict:
        """Get current audio quality settings."""
        with self._lock:
            return self.current_quality_settings.copy()


class VideoBroadcaster:
    """
    Video broadcasting component for relaying video streams to clients.
    
    Handles:
    - Video stream management for multiple participants
    - Video packet relay to all connected clients
    - Video stream statistics and monitoring
    """
    
    def __init__(self):
        """Initialize the video broadcaster."""
        self.active_video_streams: Dict[str, Dict] = {}  # client_id -> stream info
        self.video_broadcast_callback: Optional[callable] = None
        self._lock = threading.RLock()
        
        # Video broadcasting statistics
        self.stats = {
            'video_packets_relayed': 0,
            'active_video_clients': 0,
            'total_video_bytes_relayed': 0,
            'broadcast_start_time': None
        }
        
        # Adaptive quality settings
        self.current_quality_settings = {
            'bitrate': 1000000,  # 1 Mbps default
            'fps': 24,
            'resolution_scale': 1.0
        }
    
    def set_video_broadcast_callback(self, callback: callable):
        """
        Set callback function to handle video packet broadcasting.
        
        Args:
            callback: Function to call with video packet for broadcasting
        """
        self.video_broadcast_callback = callback
    
    def add_video_stream(self, client_id: str, video_packet: UDPPacket):
        """
        Add video packet from a client for broadcasting.
        
        Args:
            client_id: ID of the client sending video
            video_packet: UDP packet containing video data
        """
        with self._lock:
            # Initialize stream info for new client
            if client_id not in self.active_video_streams:
                self.active_video_streams[client_id] = {
                    'last_packet_time': time.time(),
                    'packets_received': 0,
                    'bytes_received': 0,
                    'last_sequence': -1
                }
                logger.info(f"Added video stream for client {client_id}")
            
            stream_info = self.active_video_streams[client_id]
            
            # Update stream statistics
            stream_info['last_packet_time'] = time.time()
            stream_info['packets_received'] += 1
            stream_info['bytes_received'] += len(video_packet.data)
            stream_info['last_sequence'] = video_packet.sequence_num
            
            # Update global statistics
            self.stats['video_packets_relayed'] += 1
            self.stats['total_video_bytes_relayed'] += len(video_packet.data)
            self.stats['active_video_clients'] = len(self.active_video_streams)
            
            # Broadcast video packet to other clients
            if self.video_broadcast_callback:
                self.video_broadcast_callback(video_packet)
    
    def remove_video_stream(self, client_id: str):
        """
        Remove video stream for a disconnected client.
        
        Args:
            client_id: ID of the client to remove
        """
        with self._lock:
            if client_id in self.active_video_streams:
                stream_info = self.active_video_streams[client_id]
                logger.info(f"Removed video stream for client {client_id} "
                          f"(received {stream_info['packets_received']} packets, "
                          f"{stream_info['bytes_received']} bytes)")
                
                del self.active_video_streams[client_id]
                self.stats['active_video_clients'] = len(self.active_video_streams)
    
    def cleanup_inactive_streams(self, timeout_seconds: float = 30.0):
        """
        Remove video streams that haven't sent packets recently.
        
        Args:
            timeout_seconds: Timeout in seconds for inactive streams
        """
        current_time = time.time()
        inactive_clients = []
        
        with self._lock:
            for client_id, stream_info in self.active_video_streams.items():
                if current_time - stream_info['last_packet_time'] > timeout_seconds:
                    inactive_clients.append(client_id)
            
            for client_id in inactive_clients:
                logger.info(f"Removing inactive video stream: {client_id}")
                self.remove_video_stream(client_id)
    
    def get_active_video_clients(self) -> List[str]:
        """
        Get list of clients currently sending video.
        
        Returns:
            List of client IDs with active video streams
        """
        with self._lock:
            return list(self.active_video_streams.keys())
    
    def get_video_stats(self) -> Dict:
        """
        Get video broadcasting statistics.
        
        Returns:
            dict: Video broadcasting statistics and performance metrics
        """
        with self._lock:
            stats = self.stats.copy()
            stats['active_streams'] = {}
            
            # Add per-client statistics
            for client_id, stream_info in self.active_video_streams.items():
                stats['active_streams'][client_id] = {
                    'packets_received': stream_info['packets_received'],
                    'bytes_received': stream_info['bytes_received'],
                    'last_packet_time': stream_info['last_packet_time'],
                    'last_sequence': stream_info['last_sequence']
                }
            
            return stats
    
    def update_quality_settings(self, quality_settings: Dict):
        """
        Update video quality settings for adaptive compression.
        
        Args:
            quality_settings: New quality settings dictionary
        """
        with self._lock:
            self.current_quality_settings.update(quality_settings)
            logger.info(f"Updated video broadcaster quality settings: {quality_settings}")
    
    def get_quality_settings(self) -> Dict:
        """Get current video quality settings."""
        with self._lock:
            return self.current_quality_settings.copy()


class ScreenShareRelay:
    """
    Screen sharing relay component for broadcasting screen frames.
    
    Handles:
    - Screen frame relay from presenter to all participants
    - Screen sharing session management
    - Screen frame statistics and monitoring
    """
    
    def __init__(self):
        """Initialize the screen share relay."""
        self.screen_broadcast_callback: Optional[callable] = None
        self._lock = threading.RLock()
        
        # Screen sharing statistics
        self.stats = {
            'screen_frames_relayed': 0,
            'total_screen_bytes_relayed': 0,
            'last_frame_time': None,
            'presenter_id': None
        }
    
    def set_screen_broadcast_callback(self, callback: callable):
        """
        Set callback function to handle screen frame broadcasting.
        
        Args:
            callback: Function to call with screen frame for broadcasting
        """
        self.screen_broadcast_callback = callback
    
    def relay_screen_frame(self, screen_message, presenter_id: str):
        """
        Relay screen frame from presenter to all other clients.
        
        Args:
            screen_message: TCP message containing screen frame data
            presenter_id: ID of the presenter client
        """
        with self._lock:
            # Update statistics
            self.stats['screen_frames_relayed'] += 1
            self.stats['last_frame_time'] = time.time()
            self.stats['presenter_id'] = presenter_id
            
            # Calculate frame size from hex data
            if 'frame_data' in screen_message.data:
                frame_size = len(screen_message.data['frame_data']) // 2  # hex string to bytes
                self.stats['total_screen_bytes_relayed'] += frame_size
            
            # Broadcast screen frame to other clients
            if self.screen_broadcast_callback:
                self.screen_broadcast_callback(screen_message, presenter_id)
    
    def get_screen_stats(self) -> Dict:
        """
        Get screen sharing statistics.
        
        Returns:
            dict: Screen sharing statistics and performance metrics
        """
        with self._lock:
            return self.stats.copy()


class MediaRelay:
    """
    Media relay system for handling audio, video, and screen sharing.
    
    Manages:
    - Audio mixing and broadcasting via AudioMixer
    - Video stream relay to connected clients via VideoBroadcaster
    - Screen sharing relay via ScreenShareRelay
    - Media stream coordination and synchronization
    """
    
    def __init__(self, session_manager: SessionManager, udp_server, tcp_server=None):
        """
        Initialize the media relay system.
        
        Args:
            session_manager: SessionManager instance for client tracking
            udp_server: UDP server instance for media transmission
            tcp_server: TCP server instance for screen sharing (optional)
        """
        self.session_manager = session_manager
        self.udp_server = udp_server
        self.tcp_server = tcp_server
        
        # Audio mixing component
        self.audio_mixer = AudioMixer()
        self.audio_mixer.set_mixed_audio_callback(self._broadcast_mixed_audio)
        
        # Video broadcasting component
        self.video_broadcaster = VideoBroadcaster()
        self.video_broadcaster.set_video_broadcast_callback(self._broadcast_video_packet)
        
        # Screen sharing component
        self.screen_share_relay = ScreenShareRelay()
        self.screen_share_relay.set_screen_broadcast_callback(self._broadcast_screen_frame)
        
        # Media relay state
        self.is_running = False
        self._lock = threading.RLock()
        
        # Cleanup thread for inactive streams
        self.cleanup_thread: Optional[threading.Thread] = None
        
        # Statistics
        self.stats = {
            'audio_packets_processed': 0,
            'video_packets_processed': 0,
            'screen_frames_processed': 0,
            'broadcast_packets_sent': 0,
            'relay_start_time': None
        }
    
    def start_relay(self) -> bool:
        """
        Start the media relay system.
        
        Returns:
            bool: True if relay started successfully
        """
        if self.is_running:
            logger.warning("Media relay already running")
            return True
        
        try:
            self.is_running = True
            self.stats['relay_start_time'] = time.time()
            
            # Start audio mixing
            if not self.audio_mixer.start_mixing():
                logger.error("Failed to start audio mixer")
                self.is_running = False
                return False
            
            # Start cleanup thread for inactive video streams
            self.cleanup_thread = threading.Thread(
                target=self._cleanup_loop,
                daemon=True
            )
            self.cleanup_thread.start()
            
            logger.info("Media relay started with audio mixing and video broadcasting")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start media relay: {e}")
            self.is_running = False
            return False
    
    def stop_relay(self):
        """Stop the media relay system."""
        if not self.is_running:
            return
        
        self.is_running = False
        
        # Stop audio mixing
        self.audio_mixer.stop_mixing()
        
        # Wait for cleanup thread to finish
        if self.cleanup_thread and self.cleanup_thread.is_alive():
            self.cleanup_thread.join(timeout=1.0)
        
        logger.info("Media relay stopped")
    
    def process_audio_packet(self, audio_packet: UDPPacket, sender_address: Tuple[str, int]):
        """
        Process an incoming audio packet from a client.
        
        Args:
            audio_packet: UDP packet containing audio data
            sender_address: Network address of the sender
        """
        if not self.is_running:
            return
        
        try:
            # Add audio to mixer
            self.audio_mixer.add_audio_stream(audio_packet.sender_id, audio_packet)
            
            self.stats['audio_packets_processed'] += 1
            
        except Exception as e:
            logger.error(f"Error processing audio packet: {e}")
    
    def process_video_packet(self, video_packet: UDPPacket, sender_address: Tuple[str, int]):
        """
        Process an incoming video packet from a client.
        
        Args:
            video_packet: UDP packet containing video data
            sender_address: Network address of the sender
        """
        if not self.is_running:
            return
        
        try:
            # Add video packet to broadcaster for relay
            self.video_broadcaster.add_video_stream(video_packet.sender_id, video_packet)
            
            self.stats['video_packets_processed'] += 1
            
        except Exception as e:
            logger.error(f"Error processing video packet: {e}")
    
    def process_screen_frame(self, screen_message, presenter_id: str):
        """
        Process an incoming screen frame from the presenter.
        
        Args:
            screen_message: TCP message containing screen frame data
            presenter_id: ID of the presenter client
        """
        if not self.is_running:
            return
        
        try:
            # Verify presenter is authorized
            if not self.session_manager.is_screen_sharing_active():
                logger.warning(f"Received screen frame but screen sharing not active")
                return
            
            current_presenter = self.session_manager.get_presenter()
            if not current_presenter or current_presenter.client_id != presenter_id:
                logger.warning(f"Received screen frame from unauthorized client {presenter_id}")
                return
            
            # Update screen frame timestamp in session manager
            self.session_manager.update_screen_frame_time()
            
            # Relay screen frame to other clients
            self.screen_share_relay.relay_screen_frame(screen_message, presenter_id)
            
            self.stats['screen_frames_processed'] += 1
            
        except Exception as e:
            logger.error(f"Error processing screen frame: {e}")
    
    def _broadcast_mixed_audio(self, mixed_audio_packet: UDPPacket):
        """
        Broadcast mixed audio to all connected clients.
        
        Args:
            mixed_audio_packet: UDP packet containing mixed audio data
        """
        try:
            # Get all clients with UDP addresses
            clients_with_udp = self.session_manager.get_clients_with_udp()
            
            if not clients_with_udp:
                return
            
            # Serialize packet once for efficiency
            packet_data = mixed_audio_packet.serialize()
            
            # Broadcast to all clients
            for client in clients_with_udp:
                try:
                    self.udp_server.send_data(packet_data, client.udp_address)
                    self.stats['broadcast_packets_sent'] += 1
                except Exception as e:
                    logger.warning(f"Failed to send mixed audio to client {client.client_id}: {e}")
            
        except Exception as e:
            logger.error(f"Error broadcasting mixed audio: {e}")
    
    def _broadcast_video_packet(self, video_packet: UDPPacket):
        """
        Broadcast video packet to all clients except sender.
        
        Args:
            video_packet: UDP packet containing video data
        """
        try:
            # Get all clients with UDP addresses (excluding sender)
            clients_with_udp = self.session_manager.get_clients_with_udp()
            
            logger.debug(f"Broadcasting video from {video_packet.sender_id} to {len(clients_with_udp)} clients")
            
            if not clients_with_udp:
                logger.warning("No clients with UDP addresses for video broadcast")
                return
            
            # Serialize packet once for efficiency
            packet_data = video_packet.serialize()
            
            # Broadcast to all clients except sender
            broadcast_count = 0
            for client in clients_with_udp:
                if client.client_id != video_packet.sender_id:
                    try:
                        self.udp_server.send_data(packet_data, client.udp_address)
                        self.stats['broadcast_packets_sent'] += 1
                        broadcast_count += 1
                        logger.debug(f"Sent video packet to {client.client_id} at {client.udp_address}")
                    except Exception as e:
                        logger.warning(f"Failed to send video to client {client.client_id}: {e}")
            
            logger.debug(f"Video packet broadcast to {broadcast_count} clients")
            
        except Exception as e:
            logger.error(f"Error broadcasting video packet: {e}")
    
    def _broadcast_screen_frame(self, screen_message, presenter_id: str):
        """
        Broadcast screen frame to all clients except presenter.
        
        Args:
            screen_message: TCP message containing screen frame data
            presenter_id: ID of the presenter client
        """
        try:
            # Get all connected clients (excluding presenter)
            all_clients = self.session_manager.get_all_clients()
            
            if not all_clients:
                return
            
            # Serialize message once for efficiency
            message_data = screen_message.serialize()
            
            # Broadcast to all clients except presenter
            for client in all_clients:
                if client.client_id != presenter_id:
                    try:
                        # Send via TCP socket for reliability
                        client.tcp_socket.send(len(message_data).to_bytes(4, byteorder='big'))
                        client.tcp_socket.send(message_data)
                        self.stats['broadcast_packets_sent'] += 1
                    except Exception as e:
                        logger.warning(f"Failed to send screen frame to client {client.client_id}: {e}")
            
        except Exception as e:
            logger.error(f"Error broadcasting screen frame: {e}")
    
    def add_client_audio_stream(self, client_id: str):
        """
        Add audio stream for a new client.
        
        Args:
            client_id: ID of the client
        """
        # Audio streams are added automatically when first packet arrives
        logger.info(f"Audio stream ready for client {client_id}")
    
    def remove_client_audio_stream(self, client_id: str):
        """
        Remove audio stream for a disconnected client.
        
        Args:
            client_id: ID of the client
        """
        self.audio_mixer.remove_audio_stream(client_id)
    
    def add_client_video_stream(self, client_id: str):
        """
        Add video stream for a new client.
        
        Args:
            client_id: ID of the client
        """
        # Video streams are added automatically when first packet arrives
        logger.info(f"Video stream ready for client {client_id}")
    
    def remove_client_video_stream(self, client_id: str):
        """
        Remove video stream for a disconnected client.
        
        Args:
            client_id: ID of the client
        """
        self.video_broadcaster.remove_video_stream(client_id)
    
    def _cleanup_loop(self):
        """Periodic cleanup of inactive video streams."""
        logger.info("Media relay cleanup loop started")
        
        while self.is_running:
            try:
                # Clean up inactive video streams every 30 seconds
                time.sleep(30)
                
                if self.is_running:
                    self.video_broadcaster.cleanup_inactive_streams()
                
            except Exception as e:
                if self.is_running:
                    logger.error(f"Error in cleanup loop: {e}")
                break
        
        logger.info("Media relay cleanup loop ended")
    
    def get_relay_stats(self) -> Dict:
        """
        Get media relay statistics.
        
        Returns:
            dict: Relay statistics and performance metrics
        """
        with self._lock:
            stats = self.stats.copy()
            stats['is_running'] = self.is_running
            stats['audio_mixer_stats'] = self.audio_mixer.get_mixing_stats()
            stats['video_broadcaster_stats'] = self.video_broadcaster.get_video_stats()
            stats['screen_share_stats'] = self.screen_share_relay.get_screen_stats()
            
            if stats['relay_start_time']:
                stats['relay_duration'] = time.time() - stats['relay_start_time']
            
            return stats
    
    def get_screen_share_relay(self) -> ScreenShareRelay:
        """
        Get the screen share relay instance.
        
        Returns:
            ScreenShareRelay: The screen share relay component
        """
        return self.screen_share_relay
    
    def get_audio_mixer(self) -> AudioMixer:
        """
        Get the audio mixer instance.
        
        Returns:
            AudioMixer: The audio mixer component
        """
        return self.audio_mixer
    
    def get_video_broadcaster(self) -> VideoBroadcaster:
        """
        Get the video broadcaster instance.
        
        Returns:
            VideoBroadcaster: The video broadcaster component
        """
        return self.video_broadcaster