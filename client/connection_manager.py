"""
Connection manager for the collaboration client.
Handles TCP and UDP socket connections to the server with status tracking and error handling.
"""

import socket
import threading
import logging
import time
import uuid
import os
from typing import Optional, Callable, Tuple, Dict, Any
from common.networking import TCPClient, UDPClient
from common.messages import (
    TCPMessage, UDPPacket, MessageType, MessageFactory,
    deserialize_tcp_message, deserialize_udp_packet
)
from common.file_metadata import FileMetadata, FileValidator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConnectionStatus:
    """Enumeration of connection states."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    ERROR = "error"


class ConnectionManager:
    """
    Manages client-server communication for the collaboration suite.
    
    Handles:
    - TCP connection for reliable communication (chat, files, control messages)
    - UDP connection for media streaming (audio, video)
    - Connection status tracking and error handling
    - Message routing and callbacks
    - Automatic reconnection attempts
    """
    
    def __init__(self, server_host: str = 'localhost', tcp_port: int = 8080, udp_port: int = 8081):
        self.server_host = server_host
        self.tcp_port = tcp_port
        self.udp_port = udp_port
        
        # Connection components
        self.tcp_client: Optional[TCPClient] = None
        self.udp_client: Optional[UDPClient] = None
        
        # Client identification
        self.client_id: Optional[str] = None
        self.username: str = ""
        
        # Connection state
        self.status = ConnectionStatus.DISCONNECTED
        self.last_heartbeat = 0
        self.connection_start_time = 0
        
        # Threading
        self.tcp_receive_thread: Optional[threading.Thread] = None
        self.udp_receive_thread: Optional[threading.Thread] = None
        self.heartbeat_thread: Optional[threading.Thread] = None
        self.running = False
        self._lock = threading.Lock()
        
        # Message callbacks
        self.message_callbacks: Dict[str, Callable] = {}
        self.status_callback: Optional[Callable[[str], None]] = None
        
        # UDP sequence tracking
        self.udp_sequence_num = 0
        self._udp_seq_lock = threading.Lock()
        
        # Error handling
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.reconnect_delay = 2.0
        
        # Session info
        self.session_info: Dict[str, Any] = {}
        self.participants: Dict[str, Dict[str, Any]] = {}
    
    def connect(self, username: str) -> bool:
        """
        Connect to the collaboration server.
        
        Args:
            username: Display name for this client
            
        Returns:
            bool: True if connection successful
        """
        with self._lock:
            if self.status in [ConnectionStatus.CONNECTED, ConnectionStatus.CONNECTING]:
                logger.warning("Already connected or connecting")
                return False
            
            self.username = username
            self._update_status(ConnectionStatus.CONNECTING)
        
        try:
            # Initialize TCP connection
            self.tcp_client = TCPClient(self.server_host, self.tcp_port)
            if not self.tcp_client.connect():
                self._update_status(ConnectionStatus.ERROR)
                return False
            
            # Initialize UDP client
            self.udp_client = UDPClient(self.server_host, self.udp_port)
            
            # Connect UDP client for receiving (Windows compatibility)
            if not self.udp_client.connect_for_receiving():
                logger.warning("Failed to initialize UDP client for receiving")
                # Continue without UDP - TCP will still work
                self.udp_client = None
            
            # Send join message
            join_message = MessageFactory.create_client_join_message(
                sender_id=str(uuid.uuid4()),  # Temporary ID until server assigns one
                username=username
            )
            
            if not self._send_tcp_message(join_message):
                self._cleanup_connection()
                self._update_status(ConnectionStatus.ERROR)
                return False
            
            # Wait for welcome message
            welcome_data = self.tcp_client.receive_data()
            if not welcome_data:
                self._cleanup_connection()
                self._update_status(ConnectionStatus.ERROR)
                return False
            
            try:
                welcome_message = deserialize_tcp_message(welcome_data)
                if welcome_message.msg_type == 'welcome':
                    self.client_id = welcome_message.data.get('client_id')
                    self.session_info = welcome_message.data.get('session_info', {})
                    
                    # Convert participant list to dictionary
                    participants_data = welcome_message.data.get('participants', [])
                    if isinstance(participants_data, list):
                        self.participants = {p['client_id']: p for p in participants_data}
                    else:
                        self.participants = participants_data
                    
                    logger.info(f"Connected successfully with client ID: {self.client_id}")
                else:
                    logger.error(f"Unexpected welcome message type: {welcome_message.msg_type}")
                    self._cleanup_connection()
                    self._update_status(ConnectionStatus.ERROR)
                    return False
            
            except Exception as e:
                logger.error(f"Error processing welcome message: {e}")
                self._cleanup_connection()
                self._update_status(ConnectionStatus.ERROR)
                return False
            
            # Start communication threads
            self.running = True
            self.connection_start_time = time.time()
            self.last_heartbeat = time.time()
            
            self._start_communication_threads()
            
            # Send UDP address to server for media streaming
            self._send_udp_address_update()
            
            # Send initial heartbeat to keep connection alive
            initial_heartbeat = MessageFactory.create_heartbeat_message(self.client_id)
            self._send_tcp_message(initial_heartbeat)
            
            self._update_status(ConnectionStatus.CONNECTED)
            self.reconnect_attempts = 0
            
            logger.info(f"Successfully connected to server as {username}")
            return True
        
        except Exception as e:
            logger.error(f"Error connecting to server: {e}")
            self._cleanup_connection()
            self._update_status(ConnectionStatus.ERROR)
            return False
    
    def disconnect(self):
        """Disconnect from the server gracefully."""
        with self._lock:
            if self.status == ConnectionStatus.DISCONNECTED:
                return
            
            self.running = False
        
        try:
            # Send leave message if connected
            if self.client_id and self.tcp_client and self.tcp_client.connected:
                leave_message = MessageFactory.create_client_leave_message(self.client_id)
                self._send_tcp_message(leave_message)
        
        except Exception as e:
            logger.error(f"Error sending leave message: {e}")
        
        self._cleanup_connection()
        self._update_status(ConnectionStatus.DISCONNECTED)
        logger.info("Disconnected from server")
    
    def send_chat_message(self, message_text: str) -> bool:
        """
        Send a chat message to all participants via TCP for reliable delivery.
        
        Args:
            message_text: The chat message content
            
        Returns:
            bool: True if sent successfully
        """
        if not self._is_connected():
            logger.warning("Cannot send chat message: not connected")
            return False
        
        # Validate message content
        if not message_text or not isinstance(message_text, str):
            logger.warning("Cannot send empty or invalid chat message")
            return False
        
        # Trim and validate message length
        message_text = message_text.strip()
        if len(message_text) == 0:
            logger.warning("Cannot send empty chat message")
            return False
        
        if len(message_text) > 1000:
            logger.warning("Chat message too long, truncating")
            message_text = message_text[:1000]
        
        try:
            # Create chat message with reliable TCP delivery
            chat_message = MessageFactory.create_chat_message(self.client_id, message_text)
            
            # Send via TCP for guaranteed delivery
            success = self._send_tcp_message(chat_message)
            
            if success:
                logger.info(f"Sent chat message: {message_text}")
            else:
                logger.error("Failed to send chat message")
            
            return success
        
        except Exception as e:
            logger.error(f"Error sending chat message: {e}")
            return False
    
    def send_audio_data(self, audio_data: bytes) -> bool:
        """
        Send audio data via UDP.
        
        Args:
            audio_data: Encoded audio data
            
        Returns:
            bool: True if sent successfully
        """
        if not self._is_connected() or not self.udp_client:
            return False
        
        with self._udp_seq_lock:
            audio_packet = MessageFactory.create_audio_packet(
                self.client_id, self.udp_sequence_num, audio_data
            )
            self.udp_sequence_num += 1
        
        return self.udp_client.send_to_server(audio_packet.serialize())
    
    def send_video_data(self, video_data: bytes) -> bool:
        """
        Send video data via UDP.
        
        Args:
            video_data: Compressed video frame data
            
        Returns:
            bool: True if sent successfully
        """
        if not self._is_connected() or not self.udp_client:
            return False
        
        with self._udp_seq_lock:
            video_packet = MessageFactory.create_video_packet(
                self.client_id, self.udp_sequence_num, video_data
            )
            self.udp_sequence_num += 1
        
        return self.udp_client.send_to_server(video_packet.serialize())
    
    def send_screen_frame(self, frame_data: bytes) -> tuple[bool, str]:
        """
        Send screen frame data via TCP with enhanced network error handling.
        
        Args:
            frame_data: Compressed screen frame data
            
        Returns:
            tuple[bool, str]: (success, error_message_or_success_message)
        """
        if not self._is_connected():
            error_msg = "Cannot send screen frame: not connected to server"
            logger.warning(error_msg)
            # Trigger reconnection attempt if not already in progress
            if self.status != ConnectionStatus.RECONNECTING:
                self._handle_connection_lost()
            return False, error_msg
        
        if not self.client_id:
            error_msg = "Cannot send screen frame: client ID not available"
            logger.warning(error_msg)
            return False, error_msg
        
        if not frame_data:
            error_msg = "Cannot send empty screen frame data"
            logger.warning(error_msg)
            return False, error_msg
        
        # Check frame size to prevent network overload
        max_frame_size = 1024 * 1024  # 1MB limit
        if len(frame_data) > max_frame_size:
            error_msg = f"Screen frame too large ({len(frame_data)} bytes, max {max_frame_size})"
            logger.warning(error_msg)
            return False, error_msg
        
        try:
            # Create screen share message with frame data
            screen_message = TCPMessage(
                msg_type=MessageType.SCREEN_SHARE.value,
                sender_id=self.client_id,
                data={
                    'frame_data': frame_data.hex(),  # Convert to hex for JSON serialization
                    'timestamp': time.time(),
                    'frame_size': len(frame_data)
                }
            )
            
            # Validate message before sending
            if not screen_message.is_valid():
                error_msg = "Invalid screen frame message created"
                logger.error(error_msg)
                return False, error_msg
            
            # Attempt to send with retry logic for network issues
            max_retries = 2
            retry_delay = 0.1
            
            for attempt in range(max_retries):
                # Check connection before each attempt
                if not self._is_connected():
                    error_msg = "Connection lost during screen frame transmission"
                    logger.warning(error_msg)
                    self._handle_connection_lost()
                    return False, error_msg
                
                success = self._send_tcp_message(screen_message)
                
                if success:
                    success_msg = f"Screen frame sent successfully ({len(frame_data)} bytes)"
                    logger.debug(success_msg)  # Use debug level to avoid spam
                    return True, success_msg
                else:
                    if attempt < max_retries - 1:
                        logger.debug(f"Screen frame send failed, retrying in {retry_delay}s (attempt {attempt + 1}/{max_retries})")
                        time.sleep(retry_delay)
                        retry_delay *= 2
                    else:
                        error_msg = f"Failed to send screen frame after {max_retries} attempts"
                        logger.error(error_msg)
                        # Check if connection is still valid
                        if not self._is_connected():
                            self._handle_connection_lost()
                        return False, error_msg
        
        except ConnectionError as e:
            error_msg = f"Network connection error sending screen frame: {e}"
            logger.error(error_msg)
            self._handle_connection_lost()
            return False, error_msg
        
        except Exception as e:
            error_msg = f"Unexpected error sending screen frame: {e}"
            logger.error(error_msg)
            # Check if this might be a network issue
            if "connection" in str(e).lower() or "socket" in str(e).lower():
                self._handle_connection_lost()
            return False, error_msg
    
    def test_screen_sharing_messages(self) -> tuple[bool, str]:
        """
        Test screen sharing message creation and validation.
        
        Returns:
            tuple[bool, str]: (all_tests_passed, test_results)
        """
        test_results = []
        all_passed = True
        
        try:
            # Import MessageValidator here to avoid circular imports
            from common.messages import MessageValidator
            
            # Test 1: Presenter request message
            try:
                presenter_request = MessageFactory.create_presenter_request_message("test_client_123")
                is_valid, error_msg = MessageValidator.validate_screen_sharing_message(presenter_request)
                if is_valid:
                    test_results.append("✓ Presenter request message creation and validation: PASSED")
                else:
                    test_results.append(f"✗ Presenter request message validation: FAILED - {error_msg}")
                    all_passed = False
            except Exception as e:
                test_results.append(f"✗ Presenter request message creation: FAILED - {e}")
                all_passed = False
            
            # Test 2: Screen share start message
            try:
                start_message = MessageFactory.create_screen_share_start_message("test_client_123")
                is_valid, error_msg = MessageValidator.validate_screen_sharing_message(start_message)
                if is_valid:
                    test_results.append("✓ Screen share start message creation and validation: PASSED")
                else:
                    test_results.append(f"✗ Screen share start message validation: FAILED - {error_msg}")
                    all_passed = False
            except Exception as e:
                test_results.append(f"✗ Screen share start message creation: FAILED - {e}")
                all_passed = False
            
            # Test 3: Screen share stop message
            try:
                stop_message = MessageFactory.create_screen_share_stop_message("test_client_123")
                is_valid, error_msg = MessageValidator.validate_screen_sharing_message(stop_message)
                if is_valid:
                    test_results.append("✓ Screen share stop message creation and validation: PASSED")
                else:
                    test_results.append(f"✗ Screen share stop message validation: FAILED - {error_msg}")
                    all_passed = False
            except Exception as e:
                test_results.append(f"✗ Screen share stop message creation: FAILED - {e}")
                all_passed = False
            
            # Test 4: Presenter granted message
            try:
                granted_message = MessageFactory.create_presenter_granted_message("server", "test_client_123")
                is_valid, error_msg = MessageValidator.validate_screen_sharing_message(granted_message)
                if is_valid:
                    test_results.append("✓ Presenter granted message creation and validation: PASSED")
                else:
                    test_results.append(f"✗ Presenter granted message validation: FAILED - {error_msg}")
                    all_passed = False
            except Exception as e:
                test_results.append(f"✗ Presenter granted message creation: FAILED - {e}")
                all_passed = False
            
            # Test 5: Presenter denied message
            try:
                denied_message = MessageFactory.create_presenter_denied_message("server", "Another user is already presenting")
                is_valid, error_msg = MessageValidator.validate_screen_sharing_message(denied_message)
                if is_valid:
                    test_results.append("✓ Presenter denied message creation and validation: PASSED")
                else:
                    test_results.append(f"✗ Presenter denied message validation: FAILED - {error_msg}")
                    all_passed = False
            except Exception as e:
                test_results.append(f"✗ Presenter denied message creation: FAILED - {e}")
                all_passed = False
            
            # Test 6: Screen frame message
            try:
                test_frame_data = b"test_screen_frame_data_123"
                screen_message = TCPMessage(
                    msg_type=MessageType.SCREEN_SHARE.value,
                    sender_id="test_client_123",
                    data={
                        'frame_data': test_frame_data.hex(),
                        'timestamp': time.time(),
                        'frame_size': len(test_frame_data)
                    }
                )
                is_valid, error_msg = MessageValidator.validate_screen_sharing_message(screen_message)
                if is_valid:
                    test_results.append("✓ Screen frame message creation and validation: PASSED")
                else:
                    test_results.append(f"✗ Screen frame message validation: FAILED - {error_msg}")
                    all_passed = False
            except Exception as e:
                test_results.append(f"✗ Screen frame message creation: FAILED - {e}")
                all_passed = False
            
            # Test 7: Message serialization/deserialization
            try:
                test_message = MessageFactory.create_presenter_request_message("test_client_123")
                serialized = test_message.serialize()
                deserialized = deserialize_tcp_message(serialized)
                
                if (deserialized.msg_type == test_message.msg_type and 
                    deserialized.sender_id == test_message.sender_id and
                    deserialized.data == test_message.data):
                    test_results.append("✓ Message serialization/deserialization: PASSED")
                else:
                    test_results.append("✗ Message serialization/deserialization: FAILED - Data mismatch")
                    all_passed = False
            except Exception as e:
                test_results.append(f"✗ Message serialization/deserialization: FAILED - {e}")
                all_passed = False
            
            # Test 8: TCP message sending (if connected)
            if self._is_connected():
                try:
                    # Test with a harmless heartbeat message to verify TCP sending works
                    test_heartbeat = MessageFactory.create_heartbeat_message(self.client_id)
                    send_success = self._send_tcp_message(test_heartbeat)
                    if send_success:
                        test_results.append("✓ TCP message transmission: PASSED")
                    else:
                        test_results.append("✗ TCP message transmission: FAILED - Send returned False")
                        all_passed = False
                except Exception as e:
                    test_results.append(f"✗ TCP message transmission: FAILED - {e}")
                    all_passed = False
            else:
                test_results.append("⚠ TCP message transmission: SKIPPED - Not connected")
            
            result_summary = "\n".join(test_results)
            
            if all_passed:
                logger.info("All screen sharing message tests passed")
                return True, f"All screen sharing message tests passed:\n{result_summary}"
            else:
                logger.warning("Some screen sharing message tests failed")
                return False, f"Some screen sharing message tests failed:\n{result_summary}"
        
        except Exception as e:
            error_msg = f"Error running screen sharing message tests: {e}"
            logger.error(error_msg)
            return False, error_msg
    
    def send_udp_packet(self, packet: UDPPacket) -> bool:
        """
        Send a UDP packet to the server.
        
        Args:
            packet: The UDP packet to send
            
        Returns:
            bool: True if sent successfully
        """
        if not self._is_connected():
            return False
        
        if not self.udp_client or not self.udp_client.connected:
            # UDP not available, but don't spam warnings
            return False
        
        try:
            packet_data = packet.serialize()
            return self.udp_client.send_to_server(packet_data)
        except Exception as e:
            logger.debug(f"UDP packet send failed (non-critical): {e}")
            return False
    
    def send_tcp_message(self, message: TCPMessage) -> bool:
        """
        Send a TCP message to the server.
        
        Args:
            message: The TCP message to send
            
        Returns:
            bool: True if sent successfully
        """
        return self._send_tcp_message(message)
    
    def request_presenter_role(self) -> tuple[bool, str]:
        """
        Request presenter role for screen sharing with enhanced network error handling.
        
        Returns:
            tuple[bool, str]: (success, error_message_or_success_message)
        """
        if not self._is_connected():
            error_msg = "Cannot request presenter role: not connected to server"
            logger.warning(error_msg)
            # Trigger reconnection if not already in progress
            if self.status != ConnectionStatus.RECONNECTING:
                self._handle_connection_lost()
            return False, error_msg
        
        if not self.client_id:
            error_msg = "Cannot request presenter role: client ID not available"
            logger.warning(error_msg)
            return False, error_msg
        
        # Check if we already have presenter role
        if hasattr(self, '_is_presenter') and self._is_presenter:
            success_msg = "Already have presenter role"
            logger.info(success_msg)
            return True, success_msg
        
        try:
            presenter_request = MessageFactory.create_presenter_request_message(self.client_id)
            logger.info(f"Created presenter request message: {presenter_request.msg_type}")
            
            # Attempt to send with retry logic and connection monitoring
            max_retries = 3
            retry_delay = 0.5
            
            for attempt in range(max_retries):
                # Check connection before each attempt
                if not self._is_connected():
                    error_msg = "Connection lost during presenter role request"
                    logger.warning(error_msg)
                    self._handle_connection_lost()
                    return False, error_msg
                
                success = self._send_tcp_message(presenter_request)
                
                if success:
                    success_msg = "Presenter role request sent successfully"
                    logger.info(success_msg)
                    return True, success_msg
                else:
                    if attempt < max_retries - 1:
                        logger.warning(f"Failed to send presenter role request, retrying in {retry_delay}s (attempt {attempt + 1}/{max_retries})")
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                    else:
                        error_msg = f"Failed to send presenter role request after {max_retries} attempts"
                        logger.error(error_msg)
                        # Check if connection is still valid
                        if not self._is_connected():
                            self._handle_connection_lost()
                        return False, error_msg
        
        except ConnectionError as e:
            error_msg = f"Network connection error requesting presenter role: {e}"
            logger.error(error_msg)
            self._handle_connection_lost()
            return False, error_msg
        
        except Exception as e:
            error_msg = f"Unexpected error requesting presenter role: {e}"
            logger.error(error_msg)
            # Check if this might be a network issue
            if "connection" in str(e).lower() or "socket" in str(e).lower():
                self._handle_connection_lost()
            return False, error_msg
    
    def start_screen_sharing(self) -> tuple[bool, str]:
        """
        Start screen sharing session with enhanced network error handling.
        
        Returns:
            tuple[bool, str]: (success, error_message_or_success_message)
        """
        if not self._is_connected():
            error_msg = "Cannot start screen sharing: not connected to server"
            logger.warning(error_msg)
            # Trigger reconnection if not already in progress
            if self.status != ConnectionStatus.RECONNECTING:
                self._handle_connection_lost()
            return False, error_msg
        
        if not self.client_id:
            error_msg = "Cannot start screen sharing: client ID not available"
            logger.warning(error_msg)
            return False, error_msg
        
        try:
            start_message = MessageFactory.create_screen_share_start_message(self.client_id)
            logger.info(f"Creating screen share start message: {start_message.msg_type}")
            
            # Attempt to send with retry logic and connection monitoring
            max_retries = 3
            retry_delay = 0.5
            
            for attempt in range(max_retries):
                # Check connection before each attempt
                if not self._is_connected():
                    error_msg = "Connection lost during screen sharing start"
                    logger.warning(error_msg)
                    self._handle_connection_lost()
                    return False, error_msg
                
                success = self._send_tcp_message(start_message)
                
                if success:
                    success_msg = "Screen sharing start message sent successfully"
                    logger.info(success_msg)
                    return True, success_msg
                else:
                    if attempt < max_retries - 1:
                        logger.warning(f"Failed to send screen sharing start message, retrying in {retry_delay}s (attempt {attempt + 1}/{max_retries})")
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                    else:
                        error_msg = f"Failed to send screen sharing start message after {max_retries} attempts"
                        logger.error(error_msg)
                        # Check if connection is still valid
                        if not self._is_connected():
                            self._handle_connection_lost()
                        return False, error_msg
        
        except ConnectionError as e:
            error_msg = f"Network connection error starting screen sharing: {e}"
            logger.error(error_msg)
            self._handle_connection_lost()
            return False, error_msg
        
        except Exception as e:
            error_msg = f"Unexpected error starting screen sharing: {e}"
            logger.error(error_msg)
            # Check if this might be a network issue
            if "connection" in str(e).lower() or "socket" in str(e).lower():
                self._handle_connection_lost()
            return False, error_msg
    
    def stop_screen_sharing(self) -> tuple[bool, str]:
        """
        Stop screen sharing session with enhanced network error handling.
        
        Returns:
            tuple[bool, str]: (success, error_message_or_success_message)
        """
        if not self._is_connected():
            # For stop messages, we still try to send even if connection appears lost
            # as it might be a temporary issue and the stop is important
            logger.warning("Connection appears lost, but attempting to send stop message anyway")
        
        if not self.client_id:
            error_msg = "Cannot stop screen sharing: client ID not available"
            logger.warning(error_msg)
            return False, error_msg
        
        try:
            stop_message = MessageFactory.create_screen_share_stop_message(self.client_id)
            
            # Attempt to send with retry logic and connection monitoring
            max_retries = 3
            retry_delay = 0.5
            
            for attempt in range(max_retries):
                success = self._send_tcp_message(stop_message)
                
                if success:
                    success_msg = "Screen sharing stop message sent successfully"
                    logger.info(success_msg)
                    return True, success_msg
                else:
                    if attempt < max_retries - 1:
                        logger.warning(f"Failed to send screen sharing stop message, retrying in {retry_delay}s (attempt {attempt + 1}/{max_retries})")
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                    else:
                        # For stop messages, we consider it partially successful even if server wasn't notified
                        # The local cleanup is more important
                        error_msg = f"Failed to notify server of screen sharing stop after {max_retries} attempts"
                        logger.warning(error_msg)
                        return False, error_msg
        
        except ConnectionError as e:
            error_msg = f"Network connection error stopping screen sharing: {e}"
            logger.warning(error_msg)  # Warning instead of error for stop messages
            # Don't trigger reconnection for stop messages
            return False, error_msg
        
        except Exception as e:
            error_msg = f"Unexpected error stopping screen sharing: {e}"
            logger.error(error_msg)
            return False, error_msg
    
    def update_media_status(self, video_enabled: bool, audio_enabled: bool) -> bool:
        """
        Update media status (video/audio enabled state).
        
        Args:
            video_enabled: Whether video is enabled
            audio_enabled: Whether audio is enabled
            
        Returns:
            bool: True if sent successfully
        """
        if not self._is_connected():
            return False
        
        status_message = TCPMessage(
            msg_type='media_status_update',
            sender_id=self.client_id,
            data={
                'video_enabled': video_enabled,
                'audio_enabled': audio_enabled
            }
        )
        
        return self._send_tcp_message(status_message)
    

    
    def upload_file(self, file_path: str, description: str = "") -> tuple[bool, str]:
        """
        Upload a file to the server for sharing with other participants.
        
        Args:
            file_path: Path to the file to upload
            description: Optional description for the file
            
        Returns:
            tuple: (success, message/error)
        """
        if not self._is_connected():
            return False, "Not connected to server"
        
        # Validate file
        is_valid, error_msg = FileValidator.validate_file(file_path)
        if not is_valid:
            return False, f"File validation failed: {error_msg}"
        
        try:
            # Get file information
            filename = os.path.basename(file_path)
            filesize = os.path.getsize(file_path)
            
            # Create file metadata
            file_metadata = FileMetadata(
                filename=filename,
                filesize=filesize,
                uploader_id=self.client_id,
                mime_type=FileValidator.get_mime_type(filename),
                description=description
            )
            
            # Calculate file hash for integrity
            file_metadata.calculate_hash(file_path)
            
            # Send file metadata first with thread safety
            metadata_message = TCPMessage(
                msg_type=MessageType.FILE_METADATA.value,
                sender_id=self.client_id,
                data=file_metadata.to_dict()
            )
            
            with self._lock:
                if not self._send_tcp_message(metadata_message):
                    return False, "Failed to send file metadata"
            
            # Send file data in chunks with improved connection stability
            chunk_size = 4096  # Smaller 4KB chunks for better stability
            total_chunks = (filesize + chunk_size - 1) // chunk_size
            
            with open(file_path, 'rb') as f:
                for chunk_num in range(total_chunks):
                    # Check connection before each chunk
                    if not self._is_connected():
                        return False, f"Connection lost during upload at chunk {chunk_num + 1}/{total_chunks}"
                    
                    chunk_data = f.read(chunk_size)
                    if not chunk_data:
                        break
                    
                    # Send file chunk
                    chunk_message = TCPMessage(
                        msg_type=MessageType.FILE_UPLOAD.value,
                        sender_id=self.client_id,
                        data={
                            'file_id': file_metadata.file_id,
                            'chunk_num': chunk_num,
                            'total_chunks': total_chunks,
                            'chunk_data': chunk_data.hex(),  # Convert to hex for JSON serialization
                            'chunk_size': len(chunk_data)
                        }
                    )
                    
                    # Retry mechanism for failed chunks with thread safety
                    max_retries = 3
                    for retry in range(max_retries):
                        # Use lock to prevent conflicts with heartbeat
                        with self._lock:
                            chunk_success = self._send_tcp_message(chunk_message)
                        
                        if chunk_success:
                            break
                        elif retry < max_retries - 1:
                            logger.warning(f"Retrying chunk {chunk_num + 1}/{total_chunks} (attempt {retry + 2})")
                            time.sleep(0.1)  # Brief pause before retry
                        else:
                            return False, f"Failed to send chunk {chunk_num + 1}/{total_chunks} after {max_retries} attempts"
                    
                    # Add delay to prevent overwhelming and allow heartbeats
                    if chunk_num % 5 == 0:  # Every 5 chunks
                        time.sleep(0.02)  # 20ms delay for connection stability
            
            logger.info(f"Successfully uploaded file: {filename} ({filesize} bytes)")
            return True, f"File '{filename}' uploaded successfully"
        
        except Exception as e:
            logger.error(f"Error uploading file: {e}")
            return False, f"Upload failed: {e}"
    
    def request_file_download(self, file_id: str, save_path: str = None) -> bool:
        """
        Request to download a shared file from the server.
        
        Args:
            file_id: ID of the file to download
            save_path: Optional local path where to save the downloaded file
            
        Returns:
            bool: True if download request sent successfully
        """
        if not self._is_connected():
            logger.warning("Cannot download file: not connected to server")
            return False
        
        try:
            # Create downloaded_files directory if not specified
            if save_path is None:
                # Use absolute path to ensure it's in project root
                downloads_dir = os.path.abspath("downloaded_files")
                if not os.path.exists(downloads_dir):
                    os.makedirs(downloads_dir, exist_ok=True)
                    logger.info(f"Created downloads directory: {downloads_dir}")
                save_path = downloads_dir
            
            # Validate save path
            if os.path.isdir(save_path):
                # If directory provided, we'll use it as base directory
                save_dir = save_path
            else:
                save_dir = os.path.dirname(save_path)
                if save_dir and not os.path.exists(save_dir):
                    os.makedirs(save_dir, exist_ok=True)
            
            # Initialize download tracking
            if not hasattr(self, '_active_downloads'):
                self._active_downloads = {}
            
            # Check if download already in progress
            if file_id in self._active_downloads:
                logger.warning(f"Download already in progress for file: {file_id}")
                return False
            
            # Send download request
            download_request = TCPMessage(
                msg_type=MessageType.FILE_REQUEST.value,
                sender_id=self.client_id,
                data={
                    'file_id': file_id,
                    'save_directory': save_dir
                }
            )
            
            success = self._send_tcp_message(download_request)
            if success:
                logger.info(f"File download request sent for file: {file_id}")
            else:
                logger.error(f"Failed to send download request for file: {file_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error requesting file download: {e}")
            return False
    
    def register_message_callback(self, message_type: str, callback: Callable):
        """
        Register a callback for specific message types.
        
        Args:
            message_type: Type of message to listen for
            callback: Function to call when message is received
        """
        self.message_callbacks[message_type] = callback
    
    def register_audio_callback(self, callback: Callable[[UDPPacket], None]):
        """
        Register a callback for incoming audio packets.
        
        Args:
            callback: Function to call when audio packet is received
        """
        self.register_message_callback(MessageType.AUDIO.value, callback)
    
    def register_status_callback(self, callback: Callable[[str], None]):
        """
        Register a callback for connection status changes.
        
        Args:
            callback: Function to call when status changes
        """
        self.status_callback = callback
    
    def get_status(self) -> str:
        """Get current connection status."""
        return self.status
    
    def get_client_id(self) -> Optional[str]:
        """Get the assigned client ID."""
        return self.client_id
    
    def get_participants(self) -> Dict[str, Dict[str, Any]]:
        """Get current participant list."""
        return self.participants.copy()
    
    def get_connection_info(self) -> Dict[str, Any]:
        """
        Get connection information.
        
        Returns:
            dict: Connection details including uptime, status, etc.
        """
        uptime = time.time() - self.connection_start_time if self.connection_start_time > 0 else 0
        
        return {
            'status': self.status,
            'client_id': self.client_id,
            'username': self.username,
            'server_host': self.server_host,
            'tcp_port': self.tcp_port,
            'udp_port': self.udp_port,
            'uptime': uptime,
            'last_heartbeat': self.last_heartbeat,
            'participant_count': len(self.participants)
        }
    
    def _is_connected(self) -> bool:
        """Check if currently connected to server."""
        return self.status == ConnectionStatus.CONNECTED and self.client_id is not None
    
    def _send_tcp_message(self, message: TCPMessage) -> bool:
        """
        Send a TCP message to the server.
        
        Args:
            message: The message to send
            
        Returns:
            bool: True if sent successfully
        """
        if not self.tcp_client or not self.tcp_client.connected:
            return False
        
        try:
            data = message.serialize()
            return self.tcp_client.send_data(data)
        except Exception as e:
            logger.error(f"Error sending TCP message: {e}")
            return False
    
    def _send_udp_address_update(self):
        """Send UDP address information to server for media streaming."""
        try:
            # Get local UDP socket address
            if self.udp_client and self.udp_client.socket:
                local_address = self.udp_client.socket.getsockname()
                
                udp_update_message = TCPMessage(
                    msg_type='udp_address_update',
                    sender_id=self.client_id,
                    data={
                        'udp_host': local_address[0],
                        'udp_port': local_address[1]
                    }
                )
                
                self._send_tcp_message(udp_update_message)
        
        except Exception as e:
            logger.error(f"Error sending UDP address update: {e}")
    
    def _start_communication_threads(self):
        """Start threads for handling incoming messages."""
        # TCP receive thread
        self.tcp_receive_thread = threading.Thread(
            target=self._tcp_receive_loop,
            daemon=True
        )
        self.tcp_receive_thread.start()
        
        # UDP receive thread
        self.udp_receive_thread = threading.Thread(
            target=self._udp_receive_loop,
            daemon=True
        )
        self.udp_receive_thread.start()
        
        # Heartbeat thread
        self.heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop,
            daemon=True
        )
        self.heartbeat_thread.start()
    
    def _tcp_receive_loop(self):
        """Main loop for receiving TCP messages."""
        while self.running and self.tcp_client and self.tcp_client.connected:
            try:
                data = self.tcp_client.receive_data()
                if not data:
                    logger.warning("TCP connection closed by server")
                    break
                
                message = deserialize_tcp_message(data)
                self._handle_tcp_message(message)
            
            except Exception as e:
                logger.error(f"Error in TCP receive loop: {e}")
                break
        
        # Connection lost, attempt reconnection
        if self.running:
            self._handle_connection_lost()
    
    def _udp_receive_loop(self):
        """Main loop for receiving UDP packets."""
        while self.running and self.udp_client and self.udp_client.connected:
            try:
                result = self.udp_client.receive_data()
                if result:
                    data, address = result
                    packet = deserialize_udp_packet(data)
                    self._handle_udp_packet(packet)
                else:
                    # No data received, small delay to prevent busy waiting
                    time.sleep(0.01)
            
            except Exception as e:
                if self.running and self.udp_client and self.udp_client.connected:
                    logger.error(f"Error in UDP receive loop: {e}")
                # UDP errors are less critical, continue
                time.sleep(0.1)  # Longer delay on error
                continue
    
    def _heartbeat_loop(self):
        """Send periodic heartbeat messages to maintain connection."""
        heartbeat_interval = 5  # Send heartbeat every 5 seconds
        missed_heartbeats = 0
        max_missed_heartbeats = 5  # Increased tolerance for file operations
        
        while self.running:
            try:
                time.sleep(heartbeat_interval)
                
                if self._is_connected():
                    heartbeat = MessageFactory.create_heartbeat_message(self.client_id)
                    
                    # Use a lock to prevent conflicts with file operations
                    with self._lock:
                        heartbeat_success = self._send_tcp_message(heartbeat)
                    
                    if heartbeat_success:
                        self.last_heartbeat = time.time()
                        missed_heartbeats = 0  # Reset counter on successful heartbeat
                    else:
                        missed_heartbeats += 1
                        logger.warning(f"Failed to send heartbeat ({missed_heartbeats}/{max_missed_heartbeats})")
                        
                        # If too many heartbeats failed, consider connection lost
                        if missed_heartbeats >= max_missed_heartbeats:
                            logger.error("Too many missed heartbeats, connection may be lost")
                            self._handle_connection_lost()
                            break
            
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")
                missed_heartbeats += 1
                if missed_heartbeats >= max_missed_heartbeats:
                    self._handle_connection_lost()
                    break
    
    def _handle_tcp_message(self, message: TCPMessage):
        """
        Handle incoming TCP messages.
        
        Args:
            message: The received TCP message
        """
        try:
            # Handle system messages
            if message.msg_type == 'participant_joined':
                client_id = message.data.get('client_id')
                username = message.data.get('username')
                if client_id and username:
                    self.participants[client_id] = {'username': username}
                    logger.info(f"Participant joined: {username}")
            
            elif message.msg_type == 'participant_left':
                client_id = message.data.get('client_id')
                username = message.data.get('username')
                reason = message.data.get('reason', 'Disconnected')
                if client_id in self.participants:
                    del self.participants[client_id]
                    logger.info(f"Participant left: {username} - {reason}")
                    
                    # Notify callback about participant leaving
                    if 'participant_left' in self.message_callbacks:
                        self.message_callbacks['participant_left'](message)
            
            elif message.msg_type == 'participant_status_update':
                client_id = message.data.get('client_id')
                if client_id in self.participants:
                    self.participants[client_id].update({
                        'video_enabled': message.data.get('video_enabled'),
                        'audio_enabled': message.data.get('audio_enabled')
                    })
                
                # Trigger callback for participant status update
                if 'participant_status_update' in self.message_callbacks:
                    self.message_callbacks['participant_status_update'](message)
            
            elif message.msg_type == MessageType.CHAT.value:
                # Handle incoming chat messages with reliable delivery confirmation
                self._handle_chat_message(message)
            
            elif message.msg_type == 'heartbeat_ack':
                # Heartbeat acknowledged
                pass
            
            elif message.msg_type == MessageType.FILE_AVAILABLE.value:
                # Handle file availability notification
                self._handle_file_available(message)
            
            elif message.msg_type == MessageType.FILE_DOWNLOAD_CHUNK.value:
                # Handle file download chunk
                self._handle_file_download_chunk(message)
            
            elif message.msg_type == 'server_shutdown':
                # Handle server shutdown notification
                shutdown_message = message.data.get('message', 'Server is shutting down')
                logger.info(f"Server shutdown notification: {shutdown_message}")
                
                # Update status and stop trying to reconnect
                self._update_status(ConnectionStatus.DISCONNECTED)
                self.running = False
                
                # Notify callback about server shutdown
                if 'server_shutdown' in self.message_callbacks:
                    self.message_callbacks['server_shutdown'](message)
            
            elif message.msg_type == 'quality_update':
                # Handle adaptive quality update from server
                video_settings = message.data.get('video_settings', {})
                audio_settings = message.data.get('audio_settings', {})
                reason = message.data.get('reason', 'server_optimization')
                
                logger.info(f"Received quality update: {reason}")
                logger.info(f"Video settings: {video_settings}")
                logger.info(f"Audio settings: {audio_settings}")
                
                # Notify callback about quality update
                if 'quality_update' in self.message_callbacks:
                    self.message_callbacks['quality_update'](message)
            
            # Call registered callback if available
            if message.msg_type in self.message_callbacks:
                self.message_callbacks[message.msg_type](message)
        
        except Exception as e:
            logger.error(f"Error handling TCP message: {e}")
    
    def _handle_chat_message(self, message: TCPMessage):
        """
        Handle incoming chat messages with validation and logging.
        
        Args:
            message: The chat message to handle
        """
        try:
            # Validate chat message structure
            if not self._validate_incoming_chat_message(message):
                logger.warning("Received invalid chat message")
                return
            
            # Extract message details
            sender_id = message.sender_id
            message_text = message.data.get('message', '')
            sender_username = message.data.get('sender_username', 'Unknown')
            timestamp = message.timestamp
            
            # Log received message
            logger.info(f"Received chat message from {sender_username}: {message_text}")
            
            # Update participant info if needed
            if sender_id not in self.participants and sender_id != self.client_id:
                self.participants[sender_id] = {'username': sender_username}
        
        except Exception as e:
            logger.error(f"Error handling chat message: {e}")
    
    def _validate_incoming_chat_message(self, message: TCPMessage) -> bool:
        """
        Validate incoming chat message structure.
        
        Args:
            message: The message to validate
            
        Returns:
            bool: True if message is valid
        """
        try:
            # Check message type
            if message.msg_type != MessageType.CHAT.value:
                return False
            
            # Check required fields
            if not isinstance(message.data, dict):
                return False
            
            # Check message content
            message_text = message.data.get('message')
            if not message_text or not isinstance(message_text, str):
                return False
            
            # Check sender information
            if not message.sender_id:
                return False
            
            # Check timestamp
            if not message.timestamp or message.timestamp <= 0:
                return False
            
            return True
        
        except Exception as e:
            logger.error(f"Error validating chat message: {e}")
            return False
    
    def _handle_udp_packet(self, packet: UDPPacket):
        """
        Handle incoming UDP packets.
        
        Args:
            packet: The received UDP packet
        """
        try:
            # Call registered callback if available
            packet_type = packet.packet_type
            if packet_type in self.message_callbacks:
                self.message_callbacks[packet_type](packet)
        
        except Exception as e:
            logger.error(f"Error handling UDP packet: {e}")
    
    def _handle_connection_lost(self):
        """Handle connection loss and attempt reconnection with screen sharing awareness."""
        logger.warning("Connection lost, attempting to reconnect...")
        self._update_status(ConnectionStatus.RECONNECTING)
        
        # Notify about connection loss affecting screen sharing
        self._notify_screen_sharing_connection_lost()
        
        # Cleanup current connection
        self._cleanup_connection()
        
        # Attempt reconnection
        while self.running and self.reconnect_attempts < self.max_reconnect_attempts:
            self.reconnect_attempts += 1
            logger.info(f"Reconnection attempt {self.reconnect_attempts}/{self.max_reconnect_attempts}")
            
            time.sleep(self.reconnect_delay)
            
            if self.connect(self.username):
                logger.info("Reconnection successful")
                # Notify about successful reconnection
                self._notify_screen_sharing_reconnected()
                return
            
            # Exponential backoff
            self.reconnect_delay = min(self.reconnect_delay * 2, 30)
        
        # Max attempts reached
        logger.error("Max reconnection attempts reached")
        self._update_status(ConnectionStatus.ERROR)
        self._notify_screen_sharing_connection_failed()
    
    def _notify_screen_sharing_connection_lost(self):
        """Notify callbacks about connection loss affecting screen sharing."""
        try:
            if 'screen_sharing_connection_lost' in self.message_callbacks:
                self.message_callbacks['screen_sharing_connection_lost']()
            
            if 'connection_lost' in self.message_callbacks:
                self.message_callbacks['connection_lost']()
        except Exception as e:
            logger.error(f"Error notifying about connection loss: {e}")
    
    def _notify_screen_sharing_reconnected(self):
        """Notify callbacks about successful reconnection."""
        try:
            if 'screen_sharing_reconnected' in self.message_callbacks:
                self.message_callbacks['screen_sharing_reconnected']()
            
            if 'connection_restored' in self.message_callbacks:
                self.message_callbacks['connection_restored']()
        except Exception as e:
            logger.error(f"Error notifying about reconnection: {e}")
    
    def _notify_screen_sharing_connection_failed(self):
        """Notify callbacks about permanent connection failure."""
        try:
            if 'screen_sharing_connection_failed' in self.message_callbacks:
                self.message_callbacks['screen_sharing_connection_failed']()
            
            if 'connection_failed' in self.message_callbacks:
                self.message_callbacks['connection_failed']()
        except Exception as e:
            logger.error(f"Error notifying about connection failure: {e}")
    
    def _cleanup_connection(self):
        """Clean up connection resources."""
        self.running = False
        
        # Close TCP connection
        if self.tcp_client:
            self.tcp_client.close()
            self.tcp_client = None
        
        # Close UDP connection
        if self.udp_client:
            self.udp_client.disconnect()
            self.udp_client = None
        
        # Wait for threads to finish (but not the current thread)
        current_thread = threading.current_thread()
        for thread in [self.tcp_receive_thread, self.udp_receive_thread, self.heartbeat_thread]:
            if thread and thread.is_alive() and thread != current_thread:
                try:
                    thread.join(timeout=2)
                except RuntimeError as e:
                    logger.debug(f"Thread join issue (non-critical): {e}")
        
        self.tcp_receive_thread = None
        self.udp_receive_thread = None
        self.heartbeat_thread = None
    
    def _handle_file_available(self, message: TCPMessage):
        """
        Handle file availability notification from server.
        
        Args:
            message: Message containing file metadata
        """
        try:
            file_data = message.data
            file_id = file_data.get('file_id')
            filename = file_data.get('filename')
            filesize = file_data.get('filesize')
            uploader_id = file_data.get('uploader_id')
            
            if file_id and filename and filesize is not None and uploader_id:
                # Get uploader username
                uploader_username = self.participants.get(uploader_id, {}).get('username', 'Unknown')
                
                logger.info(f"File available: {filename} ({filesize} bytes) from {uploader_username}")
                
                # Notify callback if registered
                if MessageType.FILE_AVAILABLE.value in self.message_callbacks:
                    self.message_callbacks[MessageType.FILE_AVAILABLE.value](message)
        
        except Exception as e:
            logger.error(f"Error handling file available message: {e}")
    
    def _handle_file_download_chunk(self, message: TCPMessage):
        """
        Handle file download chunk from server with enhanced progress tracking.
        
        Args:
            message: Message containing file chunk data
        """
        try:
            chunk_data = message.data
            file_id = chunk_data.get('file_id')
            chunk_num = chunk_data.get('chunk_num')
            total_chunks = chunk_data.get('total_chunks')
            chunk_hex = chunk_data.get('chunk_data')
            filename = chunk_data.get('filename')
            filesize = chunk_data.get('filesize', 0)
            
            if not all([file_id, chunk_num is not None, total_chunks, chunk_hex, filename]):
                logger.warning("Invalid file download chunk received")
                return
            
            # Convert hex back to bytes
            chunk_bytes = bytes.fromhex(chunk_hex)
            
            # Initialize download tracking if first chunk
            if not hasattr(self, '_active_downloads'):
                self._active_downloads = {}
            
            if file_id not in self._active_downloads:
                # Create download directory if needed
                download_dir = os.path.abspath("downloaded_files")
                try:
                    if not os.path.exists(download_dir):
                        os.makedirs(download_dir, exist_ok=True)
                        logger.info(f"Created download directory: {download_dir}")
                    else:
                        logger.info(f"Using existing download directory: {download_dir}")
                except Exception as e:
                    logger.error(f"Failed to create download directory: {e}")
                    return
                
                # Generate safe filename to prevent path traversal
                safe_filename = os.path.basename(filename)
                download_path = os.path.join(download_dir, safe_filename)
                logger.info(f"Download path: {download_path}")
                
                # Handle filename conflicts
                counter = 1
                base_name, ext = os.path.splitext(safe_filename)
                while os.path.exists(download_path):
                    new_filename = f"{base_name}_{counter}{ext}"
                    download_path = os.path.join(download_dir, new_filename)
                    counter += 1
                
                try:
                    file_handle = open(download_path, 'wb')
                    logger.info(f"Created download file: {download_path}")
                except Exception as e:
                    logger.error(f"Failed to create download file '{download_path}': {e}")
                    return
                
                self._active_downloads[file_id] = {
                    'file_handle': file_handle,
                    'chunks_received': 0,
                    'total_chunks': total_chunks,
                    'filename': filename,
                    'download_path': download_path,
                    'filesize': filesize,
                    'bytes_received': 0,
                    'start_time': time.time()
                }
                
                logger.info(f"Started downloading: {filename} ({total_chunks} chunks, {filesize} bytes)")
            
            download_info = self._active_downloads[file_id]
            
            # Validate chunk sequence (basic check)
            expected_chunk = download_info['chunks_received']
            if chunk_num != expected_chunk:
                logger.warning(f"Received chunk {chunk_num}, expected {expected_chunk}")
            
            # Write chunk to file
            try:
                download_info['file_handle'].write(chunk_bytes)
                download_info['file_handle'].flush()  # Ensure data is written
                download_info['chunks_received'] += 1
                download_info['bytes_received'] += len(chunk_bytes)
            except Exception as e:
                logger.error(f"Failed to write chunk to file: {e}")
                self._cleanup_failed_download(file_id)
                return
            
            # Calculate progress
            progress = download_info['chunks_received'] / total_chunks
            
            # Log progress for large files
            if total_chunks > 100 and chunk_num % 50 == 0:  # Log every 50 chunks for large files
                elapsed_time = time.time() - download_info['start_time']
                speed_kbps = (download_info['bytes_received'] / 1024) / elapsed_time if elapsed_time > 0 else 0
                logger.info(f"Download progress: {filename} - {progress*100:.1f}% ({speed_kbps:.1f} KB/s)")
            
            # Notify progress callback
            if 'file_download_progress' in self.message_callbacks:
                self.message_callbacks['file_download_progress'](filename, progress)
            
            # Check if download complete
            if download_info['chunks_received'] >= total_chunks:
                try:
                    download_info['file_handle'].close()
                    download_path = download_info['download_path']
                    
                    # Verify file exists and has correct size
                    if os.path.exists(download_path):
                        actual_size = os.path.getsize(download_path)
                        logger.info(f"Downloaded file exists: {download_path} ({actual_size} bytes)")
                        
                        if filesize > 0 and actual_size != filesize:
                            logger.warning(f"File size mismatch: expected {filesize}, got {actual_size}")
                    else:
                        logger.error(f"Downloaded file does not exist: {download_path}")
                        self._cleanup_failed_download(file_id)
                        return
                    
                    # Calculate download statistics
                    elapsed_time = time.time() - download_info['start_time']
                    avg_speed_kbps = (download_info['bytes_received'] / 1024) / elapsed_time if elapsed_time > 0 else 0
                    
                    logger.info(f"File download completed: {filename} saved to {download_path}")
                    logger.info(f"Download stats: {download_info['bytes_received']} bytes in {elapsed_time:.1f}s ({avg_speed_kbps:.1f} KB/s)")
                    
                    # Clean up tracking
                    del self._active_downloads[file_id]
                    
                    # Notify completion callback
                    if 'file_download_complete' in self.message_callbacks:
                        self.message_callbacks['file_download_complete'](filename, download_path)
                    else:
                        logger.warning("No file_download_complete callback registered")
                        
                except Exception as e:
                    logger.error(f"Error completing download: {e}")
                    self._cleanup_failed_download(file_id)
        
        except Exception as e:
            logger.error(f"Error handling file download chunk: {e}")
            # Try to clean up on error
            if 'file_id' in locals():
                self._cleanup_failed_download(file_id)
    
    def _cleanup_failed_download(self, file_id: str):
        """
        Clean up resources for a failed download.
        
        Args:
            file_id: ID of the failed download
        """
        try:
            if hasattr(self, '_active_downloads') and file_id in self._active_downloads:
                download_info = self._active_downloads[file_id]
                
                # Close file handle
                if download_info.get('file_handle'):
                    download_info['file_handle'].close()
                
                # Remove incomplete file
                download_path = download_info.get('download_path')
                if download_path and os.path.exists(download_path):
                    os.remove(download_path)
                    logger.info(f"Removed incomplete download file: {download_path}")
                
                # Remove from tracking
                del self._active_downloads[file_id]
                
                # Notify error callback
                if 'file_download_error' in self.message_callbacks:
                    filename = download_info.get('filename', 'Unknown')
                    self.message_callbacks['file_download_error'](filename, "Download failed")
                
                logger.info(f"Cleaned up failed download: {file_id}")
        
        except Exception as e:
            logger.error(f"Error cleaning up failed download: {e}")
    
    def cancel_file_download(self, file_id: str) -> bool:
        """
        Cancel an active file download.
        
        Args:
            file_id: ID of the download to cancel
            
        Returns:
            bool: True if download was cancelled
        """
        try:
            if hasattr(self, '_active_downloads') and file_id in self._active_downloads:
                download_info = self._active_downloads[file_id]
                filename = download_info.get('filename', 'Unknown')
                
                self._cleanup_failed_download(file_id)
                logger.info(f"Cancelled download: {filename}")
                return True
            
            return False
        
        except Exception as e:
            logger.error(f"Error cancelling download: {e}")
            return False
    
    def get_active_downloads(self) -> Dict[str, Dict[str, Any]]:
        """
        Get information about active downloads.
        
        Returns:
            dict: Dictionary of active downloads with progress info
        """
        if not hasattr(self, '_active_downloads'):
            return {}
        
        active_info = {}
        for file_id, download_info in self._active_downloads.items():
            progress = download_info['chunks_received'] / download_info['total_chunks']
            active_info[file_id] = {
                'filename': download_info['filename'],
                'progress': progress,
                'chunks_received': download_info['chunks_received'],
                'total_chunks': download_info['total_chunks'],
                'bytes_received': download_info['bytes_received'],
                'filesize': download_info['filesize']
            }
        
        return active_info
    
    def _update_status(self, new_status: str):
        """
        Update connection status and notify callback.
        
        Args:
            new_status: The new connection status
        """
        old_status = self.status
        self.status = new_status
        
        if old_status != new_status:
            logger.info(f"Connection status changed: {old_status} -> {new_status}")
            
            if self.status_callback:
                try:
                    self.status_callback(new_status)
                except Exception as e:
                    logger.error(f"Error in status callback: {e}")