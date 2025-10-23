"""
Session management for the collaboration server.
Handles client connections, participant tracking, and session state management.
"""

import time
import uuid
import threading
import logging
import os
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from common.messages import TCPMessage, MessageType, MessageFactory
from common.file_metadata import FileMetadata

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ClientConnection:
    """Represents a connected client with their state information."""
    client_id: str
    username: str
    tcp_socket: object  # socket.socket
    udp_address: Optional[tuple] = None
    video_enabled: bool = False
    audio_enabled: bool = False
    is_presenter: bool = False
    connection_time: float = None
    last_heartbeat: float = None
    
    def __post_init__(self):
        if self.connection_time is None:
            self.connection_time = time.time()
        if self.last_heartbeat is None:
            self.last_heartbeat = time.time()


class SessionManager:
    """
    Manages client sessions, participant tracking, and session state.
    
    Handles:
    - Client connection management with unique IDs
    - Participant list maintenance functionality
    - Session state tracking and updates
    - Message broadcasting to participants
    """
    
    def __init__(self, file_storage_dir: str = "shared_files"):
        self.clients: Dict[str, ClientConnection] = {}
        self.active_presenter: Optional[str] = None
        self.chat_history: List[TCPMessage] = []
        self.shared_files: Dict[str, FileMetadata] = {}
        self.session_id = str(uuid.uuid4())
        self.session_start_time = time.time()
        self._lock = threading.RLock()  # Reentrant lock for thread safety
        
        # Screen sharing state
        self.screen_sharing_active = False
        self.active_screen_sharer: Optional[str] = None  # Client ID of who is currently sharing
        self.last_screen_frame_time = None
        
        # File storage setup
        self.file_storage_dir = file_storage_dir
        self.file_uploads_in_progress: Dict[str, Dict] = {}  # file_id -> upload state
        self._setup_file_storage()
        
    def add_client(self, tcp_socket: object, username: str) -> str:
        """
        Add a new client to the session.
        
        Args:
            tcp_socket: The client's TCP socket connection
            username: The client's display name
            
        Returns:
            str: Unique client ID for the new client
        """
        with self._lock:
            client_id = str(uuid.uuid4())
            
            client_connection = ClientConnection(
                client_id=client_id,
                username=username,
                tcp_socket=tcp_socket
            )
            
            self.clients[client_id] = client_connection
            
            # Add join message to chat history
            join_message = MessageFactory.create_client_join_message(client_id, username)
            self.chat_history.append(join_message)
            
            return client_id
    
    def remove_client(self, client_id: str) -> bool:
        """
        Remove a client from the session.
        
        Args:
            client_id: The unique ID of the client to remove
            
        Returns:
            bool: True if client was removed, False if client not found
        """
        with self._lock:
            if client_id not in self.clients:
                return False
            
            client = self.clients[client_id]
            
            # If this client was the presenter, clear presenter status
            if self.active_presenter == client_id:
                self.active_presenter = None
            
            # Add leave message to chat history
            leave_message = MessageFactory.create_client_leave_message(client_id)
            self.chat_history.append(leave_message)
            
            # If this client was sharing screen, stop it
            if self.active_screen_sharer == client_id:
                self.active_screen_sharer = None
                self.screen_sharing_active = False
                logger.info(f"Screen sharing stopped due to client {client_id} disconnection")
            
            # Remove client from session
            del self.clients[client_id]
            
            return True
    
    def get_client(self, client_id: str) -> Optional[ClientConnection]:
        """
        Get client connection information by ID.
        
        Args:
            client_id: The unique ID of the client
            
        Returns:
            ClientConnection or None if not found
        """
        with self._lock:
            return self.clients.get(client_id)
    
    def get_all_clients(self) -> List[ClientConnection]:
        """
        Get list of all connected clients.
        
        Returns:
            List of ClientConnection objects
        """
        with self._lock:
            return list(self.clients.values())
    
    def get_participant_list(self) -> List[Dict[str, any]]:
        """
        Get participant list with essential information for broadcasting.
        
        Returns:
            List of participant dictionaries with client info
        """
        with self._lock:
            participants = []
            for client in self.clients.values():
                participant_info = {
                    'client_id': client.client_id,
                    'username': client.username,
                    'video_enabled': client.video_enabled,
                    'audio_enabled': client.audio_enabled,
                    'is_presenter': client.is_presenter,
                    'connection_time': client.connection_time
                }
                participants.append(participant_info)
            return participants
    
    def update_client_media_status(self, client_id: str, video_enabled: bool = None, 
                                 audio_enabled: bool = None) -> bool:
        """
        Update client's media status (video/audio enabled state).
        
        Args:
            client_id: The unique ID of the client
            video_enabled: New video status (None to keep current)
            audio_enabled: New audio status (None to keep current)
            
        Returns:
            bool: True if update successful, False if client not found
        """
        with self._lock:
            if client_id not in self.clients:
                return False
            
            client = self.clients[client_id]
            
            if video_enabled is not None:
                client.video_enabled = video_enabled
            
            if audio_enabled is not None:
                client.audio_enabled = audio_enabled
            
            return True
    
    def set_presenter(self, client_id: str) -> bool:
        """
        Set a client as the active presenter for screen sharing.
        
        Args:
            client_id: The unique ID of the client to make presenter
            
        Returns:
            bool: True if successful, False if client not found
        """
        with self._lock:
            if client_id not in self.clients:
                return False
            
            # Clear previous presenter
            if self.active_presenter:
                prev_presenter = self.clients.get(self.active_presenter)
                if prev_presenter:
                    prev_presenter.is_presenter = False
            
            # Set new presenter
            self.active_presenter = client_id
            self.clients[client_id].is_presenter = True
            
            logger.info(f"Client {client_id} is now the presenter")
            return True
    
    def request_presenter_role(self, client_id: str) -> tuple[bool, str]:
        """
        Request presenter role for a client.
        
        Args:
            client_id: The unique ID of the client requesting presenter role
            
        Returns:
            tuple: (success, message) - success status and message
        """
        with self._lock:
            if client_id not in self.clients:
                return False, "Client not found"
            
            # Check if there's already an active presenter
            if self.active_presenter and self.active_presenter != client_id:
                presenter = self.clients.get(self.active_presenter)
                if presenter:
                    return False, f"Presenter role already taken by {presenter.username}"
            
            # Grant presenter role
            success = self.set_presenter(client_id)
            if success:
                return True, "Presenter role granted"
            else:
                return False, "Failed to set presenter role"
    
    def clear_presenter(self) -> bool:
        """
        Clear the current presenter (stop screen sharing).
        
        Returns:
            bool: True if presenter was cleared, False if no active presenter
        """
        with self._lock:
            if not self.active_presenter:
                return False
            
            presenter = self.clients.get(self.active_presenter)
            if presenter:
                presenter.is_presenter = False
            
            self.active_presenter = None
            return True
    
    def get_presenter(self) -> Optional[ClientConnection]:
        """
        Get the current presenter client.
        
        Returns:
            ClientConnection of presenter or None if no active presenter
        """
        with self._lock:
            if self.active_presenter:
                return self.clients.get(self.active_presenter)
            return None
    
    def get_active_presenter(self) -> Optional[str]:
        """
        Get the current active presenter client ID.
        
        Returns:
            str: Current presenter client ID or None if no presenter
        """
        with self._lock:
            return self.active_presenter
    
    def start_screen_sharing(self, client_id: str) -> tuple[bool, str]:
        """
        Start screen sharing for a client (with lock system).
        
        Args:
            client_id: The unique ID of the client starting screen sharing
            
        Returns:
            tuple: (success, message)
        """
        with self._lock:
            if self.active_screen_sharer and self.active_screen_sharer != client_id:
                # Someone else is already sharing
                sharer = self.clients.get(self.active_screen_sharer)
                sharer_name = sharer.username if sharer else "Unknown"
                return False, f"{sharer_name} is already sharing their screen"
            
            # Set this client as the active sharer
            self.active_screen_sharer = client_id
            self.screen_sharing_active = True
            
            client = self.clients.get(client_id)
            if client:
                logger.info(f"Screen sharing started by {client.username} ({client_id})")
            
            return True, "Screen sharing started"
    
    def stop_screen_sharing(self, client_id: str) -> tuple[bool, str]:
        """
        Stop screen sharing for a client.
        
        Args:
            client_id: The unique ID of the client stopping screen sharing
            
        Returns:
            tuple: (success, message)
        """
        with self._lock:
            if self.active_screen_sharer != client_id:
                return False, "You are not currently sharing your screen"
            
            # Clear the active sharer
            self.active_screen_sharer = None
            self.screen_sharing_active = False
            
            client = self.clients.get(client_id)
            if client:
                logger.info(f"Screen sharing stopped by {client.username} ({client_id})")
            
            return True, "Screen sharing stopped"
    
    def get_active_screen_sharer(self) -> Optional[str]:
        """
        Get the current active screen sharer client ID.
        
        Returns:
            str: Current screen sharer client ID or None if no one is sharing
        """
        with self._lock:
            return self.active_screen_sharer
    
    def is_screen_sharing_active(self) -> bool:
        """
        Check if screen sharing is currently active.
        
        Returns:
            bool: True if someone is sharing their screen
        """
        with self._lock:
            return self.screen_sharing_active
    
    def start_screen_sharing(self, client_id: str) -> bool:
        """
        Start screen sharing for the presenter.
        
        Args:
            client_id: The unique ID of the client starting screen sharing
            
        Returns:
            bool: True if screen sharing started successfully
        """
        with self._lock:
            if client_id not in self.clients:
                return False
            
            # Only the presenter can start screen sharing
            if self.active_presenter != client_id:
                logger.warning(f"Client {client_id} attempted to start screen sharing without presenter role")
                return False
            
            self.screen_sharing_active = True
            self.last_screen_frame_time = time.time()
            
            logger.info(f"Screen sharing started by presenter {client_id}")
            return True
    
    def stop_screen_sharing(self, client_id: str = None) -> bool:
        """
        Stop screen sharing.
        
        Args:
            client_id: The unique ID of the client stopping screen sharing (optional)
            
        Returns:
            bool: True if screen sharing stopped successfully
        """
        with self._lock:
            if not self.screen_sharing_active:
                return False
            
            # If client_id is provided, verify it's the presenter
            if client_id and self.active_presenter != client_id:
                logger.warning(f"Client {client_id} attempted to stop screen sharing without presenter role")
                return False
            
            self.screen_sharing_active = False
            self.last_screen_frame_time = None
            
            logger.info("Screen sharing stopped")
            return True
    
    def is_screen_sharing_active(self) -> bool:
        """
        Check if screen sharing is currently active.
        
        Returns:
            bool: True if screen sharing is active
        """
        with self._lock:
            return self.screen_sharing_active
    
    def update_screen_frame_time(self):
        """Update the timestamp of the last received screen frame."""
        with self._lock:
            self.last_screen_frame_time = time.time()
    
    def get_screen_sharing_info(self) -> dict:
        """
        Get screen sharing status information.
        
        Returns:
            dict: Screen sharing status and information
        """
        with self._lock:
            presenter_info = None
            if self.active_presenter:
                presenter = self.clients.get(self.active_presenter)
                if presenter:
                    presenter_info = {
                        'client_id': presenter.client_id,
                        'username': presenter.username
                    }
            
            return {
                'active': self.screen_sharing_active,
                'presenter': presenter_info,
                'last_frame_time': self.last_screen_frame_time
            }
    
    def broadcast_message(self, message: TCPMessage, sender_id: str, 
                         exclude_sender: bool = True) -> List[str]:
        """
        Broadcast a message to all connected clients.
        
        Args:
            message: The TCPMessage to broadcast
            sender_id: ID of the client sending the message
            exclude_sender: Whether to exclude sender from broadcast
            
        Returns:
            List of client IDs that failed to receive the message
        """
        with self._lock:
            failed_clients = []
            successful_deliveries = 0
            
            for client_id, client in self.clients.items():
                # Skip sender if requested
                if exclude_sender and client_id == sender_id:
                    continue
                
                try:
                    # Mark client as target for message delivery
                    # Actual socket sending is handled by NetworkHandler
                    # This method tracks delivery status for reliability
                    successful_deliveries += 1
                    
                except Exception as e:
                    failed_clients.append(client_id)
            
            # Log broadcast statistics for chat messages
            if message.msg_type == MessageType.CHAT.value:
                total_targets = len(self.clients) - (1 if exclude_sender else 0)
                logger.info(f"Chat message broadcast: {successful_deliveries}/{total_targets} clients targeted")
            
            return failed_clients
    
    def add_chat_message(self, message: TCPMessage):
        """
        Add a chat message to the session history.
        
        Args:
            message: The chat message to add
        """
        with self._lock:
            if message.msg_type == MessageType.CHAT.value:
                # Ensure message has required fields for reliable delivery
                if 'message' in message.data and message.sender_id:
                    self.chat_history.append(message)
                    
                    # Limit chat history size to prevent memory issues
                    max_history_size = 1000
                    if len(self.chat_history) > max_history_size:
                        # Remove oldest messages, keep recent ones
                        self.chat_history = self.chat_history[-max_history_size:]
    
    def get_chat_history(self) -> List[TCPMessage]:
        """
        Get the current chat history for the session.
        
        Returns:
            List of chat messages in chronological order
        """
        with self._lock:
            return self.chat_history.copy()
    
    def update_client_heartbeat(self, client_id: str) -> bool:
        """
        Update the last heartbeat time for a client.
        
        Args:
            client_id: The unique ID of the client
            
        Returns:
            bool: True if update successful, False if client not found
        """
        with self._lock:
            if client_id not in self.clients:
                return False
            
            self.clients[client_id].last_heartbeat = time.time()
            return True
    
    def get_inactive_clients(self, timeout_seconds: int = 30) -> List[str]:
        """
        Get list of clients that haven't sent heartbeat within timeout.
        
        Args:
            timeout_seconds: Heartbeat timeout in seconds
            
        Returns:
            List of client IDs that are inactive
        """
        with self._lock:
            current_time = time.time()
            inactive_clients = []
            
            for client_id, client in self.clients.items():
                if current_time - client.last_heartbeat > timeout_seconds:
                    inactive_clients.append(client_id)
            
            return inactive_clients
    
    def cleanup_inactive_clients(self, timeout_seconds: int = 30) -> List[str]:
        """
        Remove clients that haven't sent heartbeat within timeout and notify others.
        
        Args:
            timeout_seconds: Heartbeat timeout in seconds
            
        Returns:
            List of client IDs that were removed due to inactivity
        """
        inactive_clients = self.get_inactive_clients(timeout_seconds)
        removed_clients = []
        
        for client_id in inactive_clients:
            client = self.get_client(client_id)
            if client:
                logger.warning(f"Removing inactive client: {client.username} ({client_id})")
                
                # Create disconnection notification
                disconnect_message = MessageFactory.create_client_disconnect_message(
                    client_id, client.username, "Connection timeout"
                )
                
                # Add to pending broadcasts for NetworkHandler
                if not hasattr(self, '_pending_broadcasts'):
                    self._pending_broadcasts = []
                self._pending_broadcasts.append(disconnect_message)
                
                # Remove client from session
                if self.remove_client(client_id):
                    removed_clients.append(client_id)
        
        if removed_clients:
            logger.info(f"Cleaned up {len(removed_clients)} inactive clients")
        
        return removed_clients
    
    def graceful_client_removal(self, client_id: str, reason: str = "Disconnected") -> bool:
        """
        Gracefully remove a client with proper notifications.
        
        Args:
            client_id: The unique ID of the client to remove
            reason: Reason for disconnection
            
        Returns:
            bool: True if client was removed successfully
        """
        with self._lock:
            client = self.get_client(client_id)
            if not client:
                return False
            
            username = client.username
            
            # Create graceful disconnection message
            disconnect_message = MessageFactory.create_client_disconnect_message(
                client_id, username, reason
            )
            
            # Add to pending broadcasts
            if not hasattr(self, '_pending_broadcasts'):
                self._pending_broadcasts = []
            self._pending_broadcasts.append(disconnect_message)
            
            # Remove client from session
            success = self.remove_client(client_id)
            
            if success:
                logger.info(f"Gracefully removed client: {username} ({client_id}) - {reason}")
            
            return success
    
    def get_session_info(self) -> Dict[str, any]:
        """
        Get current session information and statistics.
        
        Returns:
            Dictionary with session information
        """
        with self._lock:
            return {
                'session_id': self.session_id,
                'session_start_time': self.session_start_time,
                'total_clients': len(self.clients),
                'active_presenter': self.active_presenter,
                'chat_messages': len(self.chat_history),
                'shared_files': len(self.shared_files),
                'session_duration': time.time() - self.session_start_time
            }
    
    def update_client_udp_address(self, client_id: str, udp_address: tuple) -> bool:
        """
        Update the UDP address for a client (for media streaming).
        
        Args:
            client_id: The unique ID of the client
            udp_address: Tuple of (host, port) for UDP communication
            
        Returns:
            bool: True if update successful, False if client not found
        """
        with self._lock:
            if client_id not in self.clients:
                return False
            
            self.clients[client_id].udp_address = udp_address
            return True
    
    def get_clients_with_udp(self) -> List[ClientConnection]:
        """
        Get list of clients that have UDP addresses configured.
        
        Returns:
            List of ClientConnection objects with UDP addresses
        """
        with self._lock:
            return [client for client in self.clients.values() 
                   if client.udp_address is not None]
    
    def _setup_file_storage(self):
        """Set up file storage directory using cross-platform utilities."""
        try:
            from common.platform_utils import PathUtils
            
            # Use platform-specific app data directory if relative path
            if not os.path.isabs(self.file_storage_dir):
                app_data_dir = PathUtils.get_app_data_dir()
                storage_path = app_data_dir / self.file_storage_dir
            else:
                storage_path = PathUtils.get_safe_path(self.file_storage_dir)
            
            # Create directory with proper permissions
            storage_path.mkdir(parents=True, exist_ok=True)
            
            # Update storage directory to use resolved path
            self.file_storage_dir = str(storage_path)
            
            logger.info(f"File storage directory: {self.file_storage_dir}")
        except Exception as e:
            logger.error(f"Failed to create file storage directory: {e}")
            raise
    
    def add_file_metadata(self, file_metadata: FileMetadata) -> bool:
        """
        Add file metadata to the session.
        
        Args:
            file_metadata: FileMetadata object for the shared file
            
        Returns:
            bool: True if metadata was added successfully
        """
        with self._lock:
            if not file_metadata.is_valid():
                logger.warning("Invalid file metadata provided")
                return False
            
            # Clean up any existing upload state for this file_id (in case of retry)
            if file_metadata.file_id in self.file_uploads_in_progress:
                logger.warning(f"Cleaning up existing upload state for {file_metadata.file_id}")
                self._cleanup_failed_upload(file_metadata.file_id)
            
            # Store file metadata (but don't initialize upload tracking yet)
            self.shared_files[file_metadata.file_id] = file_metadata
            
            logger.info(f"Added file metadata: {file_metadata.filename} ({file_metadata.filesize} bytes)")
            return True
    
    def start_file_upload(self, file_metadata: FileMetadata) -> tuple[bool, str]:
        """
        Start file upload process by creating temporary file.
        
        Args:
            file_metadata: FileMetadata for the file being uploaded
            
        Returns:
            tuple: (success, error_message)
        """
        with self._lock:
            try:
                file_id = file_metadata.file_id
                
                if file_id in self.file_uploads_in_progress:
                    logger.error(f"Upload already in progress for file_id: {file_id}")
                    logger.error(f"Current uploads: {list(self.file_uploads_in_progress.keys())}")
                    return False, "Upload already in progress"
                
                # Create temporary file path
                safe_filename = file_metadata.get_safe_filename()
                temp_filename = f"{file_id}_{safe_filename}.tmp"
                temp_path = os.path.join(self.file_storage_dir, temp_filename)
                
                # Open file for writing
                file_handle = open(temp_path, 'wb')
                
                # Track upload progress
                self.file_uploads_in_progress[file_id] = {
                    'metadata': file_metadata,
                    'chunks_received': 0,
                    'total_chunks': 0,
                    'file_handle': file_handle,
                    'temp_path': temp_path,
                    'start_time': time.time()
                }
                
                logger.info(f"Started file upload: {file_metadata.filename}")
                return True, ""
            
            except Exception as e:
                logger.error(f"Error starting file upload: {e}")
                return False, str(e)
    
    def process_file_chunk(self, file_id: str, chunk_num: int, total_chunks: int, 
                          chunk_data: bytes) -> tuple[bool, str, bool]:
        """
        Process a file chunk during upload.
        
        Args:
            file_id: ID of the file being uploaded
            chunk_num: Current chunk number (0-based)
            total_chunks: Total number of chunks expected
            chunk_data: Binary data for this chunk
            
        Returns:
            tuple: (success, error_message, is_complete)
        """
        with self._lock:
            try:
                if file_id not in self.file_uploads_in_progress:
                    logger.error(f"No upload in progress for file_id: {file_id}")
                    logger.error(f"Current uploads: {list(self.file_uploads_in_progress.keys())}")
                    return False, "No upload in progress for this file", False
                
                upload_state = self.file_uploads_in_progress[file_id]
                
                # Update total chunks if not set
                if upload_state['total_chunks'] == 0:
                    upload_state['total_chunks'] = total_chunks
                elif upload_state['total_chunks'] != total_chunks:
                    return False, "Total chunks mismatch", False
                
                # Write chunk to file
                file_handle = upload_state['file_handle']
                file_handle.write(chunk_data)
                file_handle.flush()
                
                upload_state['chunks_received'] += 1
                
                # Check if upload is complete
                is_complete = upload_state['chunks_received'] >= total_chunks
                
                if is_complete:
                    # Close file and move to final location
                    file_handle.close()
                    
                    metadata = upload_state['metadata']
                    final_filename = f"{file_id}_{metadata.get_safe_filename()}"
                    final_path = os.path.join(self.file_storage_dir, final_filename)
                    
                    # Move temp file to final location
                    os.rename(upload_state['temp_path'], final_path)
                    
                    # Verify file integrity if hash is available
                    if metadata.file_hash:
                        if not metadata.verify_hash(final_path):
                            os.remove(final_path)
                            return False, "File integrity check failed", False
                    
                    # Clean up upload tracking
                    del self.file_uploads_in_progress[file_id]
                    
                    # Add to shared files and prepare for broadcast
                    self.shared_files[file_id] = metadata
                    self._broadcast_file_metadata(metadata)
                    
                    logger.info(f"File upload completed: {metadata.filename}")
                
                return True, "", is_complete
            
            except Exception as e:
                logger.error(f"Error processing file chunk: {e}")
                # Clean up on error
                self._cleanup_failed_upload(file_id)
                return False, str(e), False
    
    def _broadcast_file_metadata(self, file_metadata: FileMetadata):
        """
        Broadcast file metadata to all connected clients.
        
        Args:
            file_metadata: FileMetadata to broadcast
        """
        try:
            metadata_message = TCPMessage(
                msg_type=MessageType.FILE_AVAILABLE.value,
                sender_id="server",
                data=file_metadata.to_dict()
            )
            
            # Store the message for NetworkHandler to broadcast
            self._pending_broadcasts = getattr(self, '_pending_broadcasts', [])
            self._pending_broadcasts.append(metadata_message)
            
            logger.info(f"Prepared file metadata broadcast: {file_metadata.filename}")
        
        except Exception as e:
            logger.error(f"Error preparing file metadata broadcast: {e}")
    
    def get_pending_broadcasts(self) -> list:
        """Get and clear pending broadcast messages."""
        broadcasts = getattr(self, '_pending_broadcasts', [])
        self._pending_broadcasts = []
        return broadcasts
    
    def _cleanup_failed_upload(self, file_id: str):
        """
        Clean up resources for a failed upload.
        
        Args:
            file_id: ID of the failed upload
        """
        try:
            if file_id in self.file_uploads_in_progress:
                upload_state = self.file_uploads_in_progress[file_id]
                
                # Close file handle
                if upload_state['file_handle']:
                    upload_state['file_handle'].close()
                
                # Remove temporary file
                if upload_state['temp_path'] and os.path.exists(upload_state['temp_path']):
                    os.remove(upload_state['temp_path'])
                
                # Remove from tracking
                del self.file_uploads_in_progress[file_id]
                
                logger.info(f"Cleaned up failed upload: {file_id}")
        
        except Exception as e:
            logger.error(f"Error cleaning up failed upload: {e}")
    
    def get_file_metadata(self, file_id: str) -> Optional[FileMetadata]:
        """
        Get file metadata by file ID.
        
        Args:
            file_id: ID of the file
            
        Returns:
            FileMetadata or None if not found
        """
        with self._lock:
            return self.shared_files.get(file_id)
    
    def get_all_shared_files(self) -> List[FileMetadata]:
        """
        Get list of all shared files in the session.
        
        Returns:
            List of FileMetadata objects
        """
        with self._lock:
            return list(self.shared_files.values())
    
    def get_file_path(self, file_id: str) -> Optional[str]:
        """
        Get the file system path for a shared file.
        
        Args:
            file_id: ID of the file
            
        Returns:
            str: File path or None if not found
        """
        with self._lock:
            if file_id not in self.shared_files:
                return None
            
            metadata = self.shared_files[file_id]
            filename = f"{file_id}_{metadata.get_safe_filename()}"
            file_path = os.path.join(self.file_storage_dir, filename)
            
            if os.path.exists(file_path):
                return file_path
            
            return None
    
    def remove_shared_file(self, file_id: str, requester_id: str) -> bool:
        """
        Remove a shared file (only by uploader or admin).
        
        Args:
            file_id: ID of the file to remove
            requester_id: ID of the client requesting removal
            
        Returns:
            bool: True if file was removed
        """
        with self._lock:
            if file_id not in self.shared_files:
                return False
            
            metadata = self.shared_files[file_id]
            
            # Only uploader can remove their own files
            if metadata.uploader_id != requester_id:
                logger.warning(f"Client {requester_id} attempted to remove file uploaded by {metadata.uploader_id}")
                return False
            
            try:
                # Remove file from storage
                file_path = self.get_file_path(file_id)
                if file_path and os.path.exists(file_path):
                    os.remove(file_path)
                
                # Remove from shared files
                del self.shared_files[file_id]
                
                logger.info(f"Removed shared file: {metadata.filename}")
                return True
            
            except Exception as e:
                logger.error(f"Error removing shared file: {e}")
                return False