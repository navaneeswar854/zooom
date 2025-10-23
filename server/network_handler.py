"""
Network handler for the collaboration server.
Manages TCP and UDP socket servers with multi-threaded client handling.
"""

import socket
import threading
import logging
import os
import time
from typing import Optional, Callable, Tuple, Dict, List
from concurrent.futures import ThreadPoolExecutor
from common.networking import TCPServer, UDPServer
from common.messages import TCPMessage, UDPPacket, MessageType, deserialize_tcp_message, deserialize_udp_packet
from common.file_metadata import FileMetadata
from server.session_manager import SessionManager
from server.media_relay import MediaRelay
from server.performance_monitor import PerformanceMonitor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NetworkHandler:
    """
    Handles server-side network communication for the collaboration suite.
    
    Manages:
    - TCP server socket for reliable communication
    - UDP server socket for media streaming
    - Multi-threaded client connection handling
    - Message routing between clients via SessionManager
    """
    
    def __init__(self, tcp_port: int = 8080, udp_port: int = 8081, host: str = 'localhost'):
        self.tcp_port = tcp_port
        self.udp_port = udp_port
        self.host = host
        
        # Network servers
        self.tcp_server: Optional[TCPServer] = None
        self.udp_server: Optional[UDPServer] = None
        
        # Session management
        self.session_manager = SessionManager()
        
        # Media relay system (will be initialized after UDP server is created)
        self.media_relay: Optional[MediaRelay] = None
        
        # Server state
        self.running = False
        self.tcp_thread: Optional[threading.Thread] = None
        self.udp_thread: Optional[threading.Thread] = None
        self.heartbeat_monitor_thread: Optional[threading.Thread] = None
        
        # Client connection tracking
        self.client_threads: Dict[str, threading.Thread] = {}
        self._lock = threading.Lock()
        
        # Thread pool for efficient client handling
        self.max_workers = min(32, (os.cpu_count() or 1) + 4)  # Reasonable thread pool size
        self.thread_pool: Optional[ThreadPoolExecutor] = None
        
        # Heartbeat configuration
        self.heartbeat_interval = 10  # Check every 10 seconds
        self.heartbeat_timeout = 30   # 30 seconds timeout
        
        # Performance monitoring
        self.performance_monitor = PerformanceMonitor(monitoring_interval=5.0)
        self.performance_monitor.add_performance_callback(self._handle_performance_update)
    
    def start_servers(self) -> bool:
        """
        Start both TCP and UDP servers.
        
        Returns:
            bool: True if both servers started successfully
        """
        try:
            self.running = True
            
            # Initialize servers
            self.tcp_server = TCPServer(self.host, self.tcp_port)
            self.udp_server = UDPServer(self.host, self.udp_port)
            
            # Initialize thread pool for client handling
            self.thread_pool = ThreadPoolExecutor(
                max_workers=self.max_workers,
                thread_name_prefix="ClientHandler"
            )
            
            # Initialize media relay system
            self.media_relay = MediaRelay(self.session_manager, self.udp_server)
            if not self.media_relay.start_relay():
                logger.error("Failed to start media relay")
                return False
            
            # Start TCP server in separate thread
            self.tcp_thread = threading.Thread(
                target=self._run_tcp_server,
                daemon=True
            )
            self.tcp_thread.start()
            
            # Start UDP server in separate thread
            self.udp_thread = threading.Thread(
                target=self._run_udp_server,
                daemon=True
            )
            self.udp_thread.start()
            
            # Start heartbeat monitor thread
            self.heartbeat_monitor_thread = threading.Thread(
                target=self._heartbeat_monitor_loop,
                daemon=True
            )
            self.heartbeat_monitor_thread.start()
            
            # Start performance monitoring
            if not self.performance_monitor.start_monitoring():
                logger.warning("Failed to start performance monitoring, continuing without optimization")
            
            logger.info(f"Network servers started - TCP: {self.host}:{self.tcp_port}, UDP: {self.host}:{self.udp_port}")
            return True
            
        except Exception as e:
            logger.error(f"Error starting network servers: {e}")
            self.stop_servers()
            return False
    
    def stop_servers(self):
        """Stop both TCP and UDP servers and cleanup resources."""
        logger.info("Initiating graceful server shutdown...")
        
        # Notify all clients about server shutdown
        self._notify_clients_server_shutdown()
        
        self.running = False
        
        # Stop performance monitoring
        if self.performance_monitor:
            self.performance_monitor.stop_monitoring()
        
        # Shutdown thread pool
        if self.thread_pool:
            self.thread_pool.shutdown(wait=True, timeout=5)
        
        # Stop media relay
        if self.media_relay:
            self.media_relay.stop_relay()
        
        # Stop TCP server
        if self.tcp_server:
            self.tcp_server.stop_server()
        
        # Stop UDP server
        if self.udp_server:
            self.udp_server.stop_server()
        
        # Wait for server threads to finish
        if self.tcp_thread and self.tcp_thread.is_alive():
            self.tcp_thread.join(timeout=5)
        
        if self.udp_thread and self.udp_thread.is_alive():
            self.udp_thread.join(timeout=5)
        
        if self.heartbeat_monitor_thread and self.heartbeat_monitor_thread.is_alive():
            self.heartbeat_monitor_thread.join(timeout=5)
        
        # Cleanup client threads
        with self._lock:
            for client_id, thread in self.client_threads.items():
                if thread.is_alive():
                    thread.join(timeout=2)
            self.client_threads.clear()
        
        logger.info("Network servers stopped gracefully")
    
    def _notify_clients_server_shutdown(self):
        """Notify all connected clients about server shutdown."""
        try:
            shutdown_message = TCPMessage(
                msg_type='server_shutdown',
                sender_id='server',
                data={'message': 'Server is shutting down gracefully'}
            )
            
            # Send shutdown notification to all clients
            clients = self.session_manager.get_all_clients()
            for client in clients:
                try:
                    self._send_tcp_message(client.tcp_socket, shutdown_message)
                except Exception as e:
                    logger.debug(f"Could not notify client {client.client_id} of shutdown: {e}")
            
            # Give clients a moment to process the shutdown message
            time.sleep(1)
            
            logger.info(f"Notified {len(clients)} clients about server shutdown")
        
        except Exception as e:
            logger.error(f"Error notifying clients about shutdown: {e}")
    
    def _run_tcp_server(self):
        """Run the TCP server to handle client connections."""
        try:
            self.tcp_server.start_server(self._handle_tcp_client)
        except Exception as e:
            logger.error(f"TCP server error: {e}")
    
    def _run_udp_server(self):
        """Run the UDP server to handle media packets."""
        try:
            self.udp_server.start_server(self._handle_udp_packet)
        except Exception as e:
            logger.error(f"UDP server error: {e}")
    
    def _handle_tcp_client(self, client_socket: socket.socket, client_address: Tuple[str, int]):
        """
        Handle a new TCP client connection.
        
        Args:
            client_socket: The client's TCP socket
            client_address: Tuple of (host, port) for the client
        """
        client_id = None
        
        try:
            logger.info(f"Handling TCP client from {client_address}")
            
            # Wait for initial join message
            initial_data = self._receive_tcp_data(client_socket)
            if not initial_data:
                logger.warning(f"No initial data from client {client_address}")
                return
            
            try:
                join_message = deserialize_tcp_message(initial_data)
                
                if join_message.msg_type != MessageType.CLIENT_JOIN.value:
                    logger.warning(f"Expected join message, got {join_message.msg_type}")
                    return
                
                username = join_message.data.get('username', 'Unknown')
                
                # Add client to session
                client_id = self.session_manager.add_client(client_socket, username)
                logger.info(f"Client {username} ({client_id}) joined from {client_address}")
                
                # Clean up any stale audio streams to prevent echo issues
                if self.media_relay:
                    self.media_relay.cleanup_stale_audio_streams()
                
                # Send welcome message with client ID
                welcome_data = {
                    'client_id': client_id,
                    'session_info': self.session_manager.get_session_info(),
                    'participants': self.session_manager.get_participant_list()
                }
                welcome_message = TCPMessage(
                    msg_type='welcome',
                    sender_id='server',
                    data=welcome_data
                )
                self._send_tcp_message(client_socket, welcome_message)
                
                # Notify other clients about new participant
                participant_join_message = TCPMessage(
                    msg_type='participant_joined',
                    sender_id='server',
                    data={'client_id': client_id, 'username': username}
                )
                self._broadcast_tcp_message(participant_join_message, exclude_client=client_id)
                
                # Handle ongoing communication with this client using thread pool
                logger.info(f"Starting client message handler for {client_id}")
                if self.thread_pool:
                    logger.info(f"Using thread pool for client {client_id}")
                    future = self.thread_pool.submit(
                        self._handle_client_messages, 
                        client_socket, 
                        client_id, 
                        client_address
                    )
                    
                    # Store future for tracking (optional)
                    with self._lock:
                        self.client_threads[client_id] = future
                else:
                    # Fallback to direct thread creation
                    logger.info(f"Using direct thread creation for client {client_id}")
                    client_thread = threading.Thread(
                        target=self._handle_client_messages,
                        args=(client_socket, client_id, client_address),
                        daemon=True
                    )
                    client_thread.start()
                    
                    with self._lock:
                        self.client_threads[client_id] = client_thread
                
                logger.info(f"Client message handler started for {client_id}")
                # Don't cleanup here - let the message handler do it when it's done
                return
                
            except Exception as e:
                logger.error(f"Error processing join message from {client_address}: {e}")
                return
        
        except Exception as e:
            logger.error(f"Error handling TCP client {client_address}: {e}")
            # Cleanup when there's an error
            if client_id:
                self._cleanup_client(client_id, client_socket)
    
    def _handle_client_messages(self, client_socket: socket.socket, client_id: str, 
                              client_address: Tuple[str, int]):
        """
        Handle ongoing messages from a connected client.
        
        Args:
            client_socket: The client's TCP socket
            client_id: Unique client identifier
            client_address: Client's network address
        """
        try:
            logger.info(f"Starting message handling for client {client_id}")
            while self.running:
                # Receive message from client
                data = self._receive_tcp_data(client_socket)
                if not data:
                    logger.info(f"Client {client_id} disconnected - no data received")
                    break
                
                try:
                    message = deserialize_tcp_message(data)
                    logger.debug(f"Received message from {client_id}: {message.msg_type}")
                    self._process_tcp_message(message, client_id, client_socket)
                    
                except Exception as e:
                    logger.error(f"Error processing message from client {client_id}: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Error in client message loop for {client_id}: {e}")
        
        finally:
            # This method ending means the client has disconnected
            logger.info(f"Message handling ended for client {client_id}")
            self._cleanup_client(client_id, client_socket)
    
    def _process_tcp_message(self, message: TCPMessage, sender_id: str, sender_socket: socket.socket):
        """
        Process a TCP message from a client.
        
        Args:
            message: The received TCP message
            sender_id: ID of the sending client
            sender_socket: Socket of the sending client
        """
        try:
            if message.msg_type == MessageType.CHAT.value:
                # Validate chat message content
                if not self._validate_chat_message(message, sender_id):
                    logger.warning(f"Invalid chat message from client {sender_id}")
                    return
                
                # Add sender information to message data for reliable delivery
                message.data['sender_username'] = self._get_client_username(sender_id)
                
                # Add to chat history and broadcast to all clients
                self.session_manager.add_chat_message(message)
                
                # Broadcast message to all other clients via TCP for reliability
                self._broadcast_tcp_message(message, exclude_client=sender_id)
                
                logger.info(f"Chat message from {message.data.get('sender_username', sender_id)}: {message.data.get('message', '')}")
            
            elif message.msg_type == MessageType.HEARTBEAT.value:
                # Update client heartbeat
                self.session_manager.update_client_heartbeat(sender_id)
                
                # Send heartbeat response
                response = TCPMessage(
                    msg_type='heartbeat_ack',
                    sender_id='server',
                    data={'status': 'alive'}
                )
                self._send_tcp_message(sender_socket, response)
            
            elif message.msg_type == MessageType.SCREEN_SHARE_START.value:
                # Handle screen sharing start with lock system
                success, msg = self.session_manager.start_screen_sharing(sender_id)
                
                if success:
                    logger.info(f"Client {sender_id} started screen sharing")
                    # Broadcast start message to other clients
                    self._broadcast_tcp_message(message, exclude_client=sender_id)
                else:
                    logger.warning(f"Client {sender_id} failed to start screen sharing: {msg}")
                    # Send error message back to client
                    error_message = TCPMessage(
                        msg_type='screen_share_error',
                        sender_id='server',
                        data={'error': msg}
                    )
                    self._send_tcp_message(sender_socket, error_message)
            
            elif message.msg_type == MessageType.SCREEN_SHARE_STOP.value:
                # Handle screen sharing stop
                success, msg = self.session_manager.stop_screen_sharing(sender_id)
                
                if success:
                    logger.info(f"Client {sender_id} stopped screen sharing")
                    # Broadcast stop message to other clients
                    self._broadcast_tcp_message(message, exclude_client=sender_id)
                else:
                    logger.warning(f"Client {sender_id} failed to stop screen sharing: {msg}")
            
            elif message.msg_type == MessageType.SCREEN_SHARE.value:
                # Handle screen frame data - only relay if sender is the active sharer
                if self.session_manager.get_active_screen_sharer() == sender_id:
                    self._broadcast_tcp_message(message, exclude_client=sender_id)
                else:
                    logger.warning(f"Received screen frame from non-active sharer {sender_id}")
            
            elif message.msg_type == MessageType.FILE_METADATA.value:
                # Handle file metadata for upload
                try:
                    file_metadata = FileMetadata.from_dict(message.data)
                    file_metadata.uploader_id = sender_id  # Ensure correct uploader
                    
                    if self.session_manager.add_file_metadata(file_metadata):
                        success, error_msg = self.session_manager.start_file_upload(file_metadata)
                        if success:
                            logger.info(f"Started file upload: {file_metadata.filename}")
                        else:
                            logger.error(f"Failed to start file upload: {error_msg}")
                    else:
                        logger.warning(f"Invalid file metadata from client {sender_id}")
                
                except Exception as e:
                    logger.error(f"Error processing file metadata: {e}")
            
            elif message.msg_type == MessageType.FILE_UPLOAD.value:
                # Handle file chunk upload
                try:
                    file_id = message.data.get('file_id')
                    chunk_num = message.data.get('chunk_num')
                    total_chunks = message.data.get('total_chunks')
                    chunk_data_hex = message.data.get('chunk_data')
                    
                    if not all([file_id, chunk_num is not None, total_chunks, chunk_data_hex]):
                        logger.warning(f"Invalid file chunk data from client {sender_id}")
                        return
                    
                    # Convert hex back to bytes
                    chunk_data = bytes.fromhex(chunk_data_hex)
                    
                    # Process the chunk
                    success, error_msg, is_complete = self.session_manager.process_file_chunk(
                        file_id, chunk_num, total_chunks, chunk_data
                    )
                    
                    if not success:
                        logger.error(f"Error processing file chunk: {error_msg}")
                    elif is_complete:
                        logger.info(f"File upload completed: {file_id}")
                        
                        # Broadcast file availability to all clients with error handling
                        try:
                            pending_broadcasts = self.session_manager.get_pending_broadcasts()
                            logger.info(f"Found {len(pending_broadcasts)} pending broadcasts")
                            
                            for broadcast_message in pending_broadcasts:
                                logger.info(f"Broadcasting file availability: {broadcast_message.msg_type}")
                                self._broadcast_tcp_message(broadcast_message)
                                
                        except Exception as broadcast_error:
                            logger.error(f"Error during file availability broadcast: {broadcast_error}")
                            # Don't let broadcast errors affect the upload completion
                
                except Exception as e:
                    logger.error(f"Error processing file chunk: {e}")
            
            elif message.msg_type == MessageType.FILE_REQUEST.value:
                # Handle file download request
                try:
                    file_id = message.data.get('file_id')
                    if not file_id:
                        logger.warning(f"Invalid file request from client {sender_id}")
                        return
                    
                    # Send file data to requesting client
                    self._send_file_to_client(file_id, sender_socket, sender_id)
                
                except Exception as e:
                    logger.error(f"Error processing file request: {e}")
            
            elif message.msg_type == 'media_status_update':
                # Update client media status
                video_enabled = message.data.get('video_enabled')
                audio_enabled = message.data.get('audio_enabled')
                
                logger.info(f"Media status update from {sender_id}: video={video_enabled}, audio={audio_enabled}")
                
                self.session_manager.update_client_media_status(
                    sender_id, video_enabled, audio_enabled
                )
                
                # Broadcast status update
                status_message = TCPMessage(
                    msg_type='participant_status_update',
                    sender_id='server',
                    data={
                        'client_id': sender_id,
                        'video_enabled': video_enabled,
                        'audio_enabled': audio_enabled
                    }
                )
                logger.info(f"Broadcasting media status update for {sender_id}")
                self._broadcast_tcp_message(status_message, exclude_client=sender_id)
            
            elif message.msg_type == 'udp_address_update':
                # Update client's UDP address for media streaming
                udp_host = message.data.get('udp_host')
                udp_port = message.data.get('udp_port')
                
                # Use the client's actual IP address instead of their local address
                client_ip = sender_socket.getpeername()[0]  # Get actual client IP
                
                if udp_port:
                    # Use client's real IP with their UDP port
                    actual_udp_address = (client_ip, udp_port)
                    logger.info(f"Updating UDP address for {sender_id}: {actual_udp_address}")
                    self.session_manager.update_client_udp_address(
                        sender_id, actual_udp_address
                    )
            
            else:
                logger.warning(f"Unknown message type: {message.msg_type}")
        
        except Exception as e:
            logger.error(f"Error processing TCP message: {e}")
    
    def _handle_udp_packet(self, data: bytes, client_address: Tuple[str, int]):
        """
        Handle a UDP packet (audio/video data).
        
        Args:
            data: Raw UDP packet data
            client_address: Address of the sending client
        """
        try:
            packet = deserialize_udp_packet(data)
            
            if packet.packet_type == MessageType.AUDIO.value:
                self._process_audio_packet(packet, client_address)
            elif packet.packet_type == MessageType.VIDEO.value:
                self._process_video_packet(packet, client_address)
            else:
                logger.warning(f"Unknown UDP packet type: {packet.packet_type}")
        
        except Exception as e:
            logger.error(f"Error processing UDP packet from {client_address}: {e}")
    
    def _process_audio_packet(self, packet: UDPPacket, sender_address: Tuple[str, int]):
        """
        Process an audio packet using the media relay system.
        
        Args:
            packet: The audio UDP packet
            sender_address: Address of the sending client
        """
        try:
            # Track packet for performance monitoring
            if self.performance_monitor:
                # For simplicity, assume sequential packets (in real implementation, 
                # you'd track expected vs received sequence numbers)
                self.performance_monitor.track_packet_loss(
                    packet.sender_id, 
                    packet.sequence_num, 
                    packet.sequence_num
                )
            
            if self.media_relay:
                # Use media relay for audio mixing and broadcasting
                self.media_relay.process_audio_packet(packet, sender_address)
            else:
                logger.warning("Media relay not available for audio processing")
        
        except Exception as e:
            logger.error(f"Error processing audio packet: {e}")
    
    def _process_video_packet(self, packet: UDPPacket, sender_address: Tuple[str, int]):
        """
        Process a video packet using the media relay system.
        
        Args:
            packet: The video UDP packet
            sender_address: Address of the sending client
        """
        try:
            # Track packet for performance monitoring
            if self.performance_monitor:
                self.performance_monitor.track_packet_loss(
                    packet.sender_id, 
                    packet.sequence_num, 
                    packet.sequence_num
                )
            
            if self.media_relay:
                # Use media relay for video broadcasting
                self.media_relay.process_video_packet(packet, sender_address)
            else:
                logger.warning("Media relay not available for video processing")
        
        except Exception as e:
            logger.error(f"Error processing video packet: {e}")
    
    def _receive_tcp_data(self, client_socket: socket.socket) -> Optional[bytes]:
        """
        Receive data from a TCP client socket.
        
        Args:
            client_socket: The client's TCP socket
            
        Returns:
            bytes or None if connection closed
        """
        try:
            # Receive data length first
            length_bytes = self._receive_exact(client_socket, 4)
            if not length_bytes:
                return None
            
            data_length = int.from_bytes(length_bytes, byteorder='big')
            
            # Receive the actual data
            data = self._receive_exact(client_socket, data_length)
            return data
        
        except Exception as e:
            logger.error(f"Error receiving TCP data: {e}")
            return None
    
    def _receive_exact(self, client_socket: socket.socket, num_bytes: int) -> Optional[bytes]:
        """
        Receive exact number of bytes from socket.
        
        Args:
            client_socket: The client socket
            num_bytes: Number of bytes to receive
            
        Returns:
            bytes or None if connection closed
        """
        data = b''
        while len(data) < num_bytes:
            chunk = client_socket.recv(num_bytes - len(data))
            if not chunk:
                return None
            data += chunk
        return data
    
    def _send_tcp_message(self, client_socket: socket.socket, message: TCPMessage) -> bool:
        """
        Send a TCP message to a specific client with improved error handling.
        
        Args:
            client_socket: The client's TCP socket
            message: The message to send
            
        Returns:
            bool: True if sent successfully
        """
        try:
            # Check if socket is still valid
            if not client_socket or client_socket.fileno() == -1:
                logger.debug("Socket is closed or invalid")
                return False
            
            data = message.serialize()
            data_length = len(data)
            length_bytes = data_length.to_bytes(4, byteorder='big')
            
            # Send with timeout to prevent blocking
            client_socket.settimeout(5.0)  # 5 second timeout
            client_socket.sendall(length_bytes + data)
            client_socket.settimeout(None)  # Reset to blocking
            return True
        
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError) as e:
            logger.debug(f"Client connection lost during send: {e}")
            return False
        except socket.timeout:
            logger.warning("TCP message send timeout")
            return False
        except Exception as e:
            logger.error(f"Error sending TCP message: {e}")
            return False
    
    def _broadcast_tcp_message(self, message: TCPMessage, exclude_client: str = None):
        """
        Broadcast a TCP message to all connected clients with reliable delivery.
        
        Args:
            message: The message to broadcast
            exclude_client: Client ID to exclude from broadcast
        """
        clients = self.session_manager.get_all_clients()
        failed_deliveries = []
        successful_deliveries = 0
        
        for client in clients:
            if exclude_client and client.client_id == exclude_client:
                continue
            
            try:
                # Validate client before sending
                if not client.tcp_socket or client.tcp_socket.fileno() == -1:
                    failed_deliveries.append(client.client_id)
                    logger.debug(f"Skipping invalid socket for client {client.client_id}")
                    continue
                
                # Send message via TCP for reliable delivery
                if self._send_tcp_message(client.tcp_socket, message):
                    successful_deliveries += 1
                else:
                    failed_deliveries.append(client.client_id)
                    logger.debug(f"Failed to deliver message to client {client.client_id}")
            except Exception as e:
                failed_deliveries.append(client.client_id)
                logger.debug(f"Exception broadcasting to client {client.client_id}: {e}")
                # Continue with other clients even if one fails
        
        # Log broadcast results
        total_targets = len(clients) - (1 if exclude_client else 0)
        
        if message.msg_type == MessageType.CHAT.value:
            logger.info(f"Chat message broadcast completed: {successful_deliveries}/{total_targets} successful deliveries")
        elif message.msg_type == MessageType.FILE_AVAILABLE.value:
            logger.info(f"File availability broadcast completed: {successful_deliveries}/{total_targets} successful deliveries")
        
        if failed_deliveries:
            if message.msg_type == MessageType.CHAT.value:
                logger.warning(f"Failed to deliver chat message to clients: {failed_deliveries}")
                self._handle_chat_delivery_failures(failed_deliveries, message)
            elif message.msg_type == MessageType.FILE_AVAILABLE.value:
                logger.warning(f"Failed to deliver file availability to clients: {failed_deliveries}")
                self._handle_file_delivery_failures(failed_deliveries, message)
    
    def _handle_chat_delivery_failures(self, failed_client_ids: List[str], message: TCPMessage):
        """
        Handle failed chat message deliveries.
        
        Args:
            failed_client_ids: List of client IDs that failed to receive the message
            message: The chat message that failed to deliver
        """
        try:
            # For now, log the failures. In a production system, you might:
            # 1. Queue messages for retry
            # 2. Remove disconnected clients
            # 3. Notify other clients about delivery issues
            
            for client_id in failed_client_ids:
                client = self.session_manager.get_client(client_id)
                if client:
                    logger.warning(f"Chat delivery failed for {client.username} ({client_id})")
                    # Could implement retry logic here
                else:
                    logger.info(f"Removing disconnected client {client_id} from session")
                    self.session_manager.remove_client(client_id)
        
        except Exception as e:
            logger.error(f"Error handling chat delivery failures: {e}")
    
    def _handle_file_delivery_failures(self, failed_client_ids: List[str], message: TCPMessage):
        """
        Handle failed file availability message deliveries.
        
        Args:
            failed_client_ids: List of client IDs that failed to receive the message
            message: The file availability message that failed to deliver
        """
        try:
            for client_id in failed_client_ids:
                client = self.session_manager.get_client(client_id)
                if client:
                    logger.warning(f"File availability delivery failed for {client.username} ({client_id})")
                    # Don't disconnect clients for file delivery failures
                    # They can still participate in other activities
                else:
                    logger.info(f"Client {client_id} already disconnected, removing from session")
                    self.session_manager.remove_client(client_id)
        
        except Exception as e:
            logger.error(f"Error handling file delivery failures: {e}")
    
    def _validate_chat_message(self, message: TCPMessage, sender_id: str) -> bool:
        """
        Validate chat message content and sender.
        
        Args:
            message: The chat message to validate
            sender_id: ID of the sending client
            
        Returns:
            bool: True if message is valid
        """
        try:
            # Check if sender exists in session
            if not self.session_manager.get_client(sender_id):
                return False
            
            # Check message data structure
            if not isinstance(message.data, dict):
                return False
            
            # Check required fields
            message_text = message.data.get('message')
            if not message_text or not isinstance(message_text, str):
                return False
            
            # Check message length (prevent spam)
            if len(message_text.strip()) == 0 or len(message_text) > 1000:
                return False
            
            # Verify sender ID matches message sender
            if message.sender_id != sender_id:
                return False
            
            return True
        
        except Exception as e:
            logger.error(f"Error validating chat message: {e}")
            return False
    
    def _get_client_username(self, client_id: str) -> str:
        """
        Get username for a client ID.
        
        Args:
            client_id: The client's unique ID
            
        Returns:
            str: Username or 'Unknown' if not found
        """
        client = self.session_manager.get_client(client_id)
        return client.username if client else 'Unknown'

    def _cleanup_client(self, client_id: str, client_socket: socket.socket):
        """
        Cleanup when a client disconnects.
        
        Args:
            client_id: The client's unique ID
            client_socket: The client's TCP socket
        """
        try:
            # Use graceful removal from session manager
            client = self.session_manager.get_client(client_id)
            if client:
                username = client.username
                
                # Use graceful removal which handles notifications
                self.session_manager.graceful_client_removal(client_id, "Client disconnected")
                
                # Remove client from media relay
                if self.media_relay:
                    self.media_relay.remove_client_audio_stream(client_id)
                    self.media_relay.remove_client_video_stream(client_id)
                
                # Broadcast pending notifications
                pending_broadcasts = self.session_manager.get_pending_broadcasts()
                for broadcast_message in pending_broadcasts:
                    self._broadcast_tcp_message(broadcast_message)
                
                logger.info(f"Client {username} ({client_id}) disconnected and cleaned up")
            
            # Close socket safely
            try:
                if client_socket:
                    client_socket.shutdown(socket.SHUT_RDWR)
                    client_socket.close()
            except Exception as socket_error:
                logger.debug(f"Socket cleanup error (expected): {socket_error}")
            
            # Remove from client threads tracking
            with self._lock:
                if client_id in self.client_threads:
                    del self.client_threads[client_id]
        
        except Exception as e:
            logger.error(f"Error cleaning up client {client_id}: {e}")
    
    def _send_file_to_client(self, file_id: str, sender_socket: socket.socket, sender_id: str):
        """
        Send file data to requesting client.
        
        Args:
            file_id: ID of the file to send
            sender_socket: Socket of the requesting client
            sender_id: ID of the requesting client
        """
        try:
            # Get file path from session manager
            file_path = self.session_manager.get_file_path(file_id)
            if not file_path:
                logger.warning(f"File not found for download: {file_id}")
                return
            
            # Get file metadata
            file_metadata = self.session_manager.get_file_metadata(file_id)
            if not file_metadata:
                logger.warning(f"File metadata not found: {file_id}")
                return
            
            # Send file in chunks
            chunk_size = 8192  # 8KB chunks
            total_chunks = (file_metadata.filesize + chunk_size - 1) // chunk_size
            
            with open(file_path, 'rb') as f:
                for chunk_num in range(total_chunks):
                    chunk_data = f.read(chunk_size)
                    if not chunk_data:
                        break
                    
                    # Send file chunk to requesting client
                    chunk_message = TCPMessage(
                        msg_type=MessageType.FILE_DOWNLOAD_CHUNK.value,
                        sender_id='server',
                        data={
                            'file_id': file_id,
                            'chunk_num': chunk_num,
                            'total_chunks': total_chunks,
                            'chunk_data': chunk_data.hex(),
                            'chunk_size': len(chunk_data),
                            'filename': file_metadata.filename,
                            'filesize': file_metadata.filesize
                        }
                    )
                    
                    if not self._send_tcp_message(sender_socket, chunk_message):
                        logger.error(f"Failed to send file chunk {chunk_num + 1}/{total_chunks}")
                        break
            
            logger.info(f"File download completed: {file_metadata.filename} to client {sender_id}")
        
        except Exception as e:
            logger.error(f"Error sending file to client: {e}")

    def get_session_manager(self) -> SessionManager:
        """
        Get the session manager instance.
        
        Returns:
            SessionManager: The current session manager
        """
        return self.session_manager
    
    def _heartbeat_monitor_loop(self):
        """Monitor client heartbeats and remove inactive clients."""
        logger.info("Heartbeat monitor started")
        
        while self.running:
            try:
                time.sleep(self.heartbeat_interval)
                
                if not self.running:
                    break
                
                # Check for inactive clients and remove them
                removed_clients = self.session_manager.cleanup_inactive_clients(self.heartbeat_timeout)
                
                # Broadcast disconnection notifications for removed clients
                if removed_clients:
                    pending_broadcasts = self.session_manager.get_pending_broadcasts()
                    for broadcast_message in pending_broadcasts:
                        self._broadcast_tcp_message(broadcast_message)
                        logger.info(f"Broadcasted disconnection notification: {broadcast_message.data}")
                
            except Exception as e:
                logger.error(f"Error in heartbeat monitor loop: {e}")
        
        logger.info("Heartbeat monitor stopped")
    
    def _handle_performance_update(self, quality_update: Dict, network_metrics, system_metrics):
        """
        Handle performance optimization updates.
        
        Args:
            quality_update: Updated quality settings
            network_metrics: Current network metrics
            system_metrics: Current system metrics
        """
        try:
            # Log performance changes
            logger.info(f"Performance optimization: Video={quality_update['video_quality']}, "
                       f"Audio={quality_update['audio_quality']}")
            logger.info(f"System metrics: CPU={system_metrics.cpu_usage_percent:.1f}%, "
                       f"Memory={system_metrics.memory_usage_percent:.1f}%")
            logger.info(f"Network metrics: Latency={network_metrics.latency_ms:.1f}ms, "
                       f"Loss={network_metrics.packet_loss_rate*100:.2f}%")
            
            # Broadcast quality update to all clients
            quality_message = TCPMessage(
                msg_type='quality_update',
                sender_id='server',
                data={
                    'video_settings': self.performance_monitor.compression_manager.get_current_video_settings(),
                    'audio_settings': self.performance_monitor.compression_manager.get_current_audio_settings(),
                    'reason': 'performance_optimization'
                }
            )
            
            self._broadcast_tcp_message(quality_message)
            
            # Update media relay with new settings if needed
            if self.media_relay:
                self._update_media_relay_settings(quality_update)
        
        except Exception as e:
            logger.error(f"Error handling performance update: {e}")
    
    def _update_media_relay_settings(self, quality_update: Dict):
        """
        Update media relay settings based on performance optimization.
        
        Args:
            quality_update: Updated quality settings
        """
        try:
            # Get current settings
            video_settings = self.performance_monitor.compression_manager.get_current_video_settings()
            audio_settings = self.performance_monitor.compression_manager.get_current_audio_settings()
            
            # Update audio mixer settings
            audio_mixer = self.media_relay.get_audio_mixer()
            if hasattr(audio_mixer, 'update_quality_settings'):
                audio_mixer.update_quality_settings(audio_settings)
            
            # Update video broadcaster settings
            video_broadcaster = self.media_relay.get_video_broadcaster()
            if hasattr(video_broadcaster, 'update_quality_settings'):
                video_broadcaster.update_quality_settings(video_settings)
            
            logger.info("Updated media relay settings for performance optimization")
        
        except Exception as e:
            logger.error(f"Error updating media relay settings: {e}")
    
    def get_performance_summary(self) -> Dict:
        """
        Get performance monitoring summary.
        
        Returns:
            dict: Performance metrics and statistics
        """
        if self.performance_monitor:
            return self.performance_monitor.get_performance_summary()
        return {'monitoring_active': False}
    
    def is_running(self) -> bool:
        """
        Check if the network handler is running.
        
        Returns:
            bool: True if servers are running
        """
        return self.running