"""
Main client application for the LAN Collaboration Suite.
Integrates ConnectionManager and GUIManager to provide the complete client experience.
"""

import logging
import threading
import time
import os
from datetime import datetime
from typing import Optional, Dict, Any
from client.connection_manager import ConnectionManager, ConnectionStatus
from client.gui_manager import GUIManager
from client.audio_manager import AudioManager
from client.video_capture import VideoCapture
from client.video_playback import VideoManager
from client.screen_manager import ScreenManager
from client.extreme_video_optimizer import extreme_video_optimizer
from common.messages import TCPMessage, UDPPacket, MessageType
from common.platform_utils import PLATFORM_INFO, log_platform_info, DeviceUtils, ErrorHandler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CollaborationClient:
    """
    Main client application that coordinates GUI and network communication.
    
    Integrates:
    - ConnectionManager for server communication
    - GUIManager for user interface
    - Message handling and routing
    - Media capture and playback (placeholder for future implementation)
    """
    
    def __init__(self):
        # Log platform information for debugging
        log_platform_info()
        
        # Check platform capabilities
        self._check_platform_capabilities()
        
        # Core components
        self.connection_manager: Optional[ConnectionManager] = None
        self.gui_manager = GUIManager()
        self.audio_manager: Optional[AudioManager] = None
        self.video_capture: Optional[VideoCapture] = None
        self.video_manager: Optional[VideoManager] = None
        self.screen_manager: Optional[ScreenManager] = None
        
        # Application state
        self.running = False
        self.current_username = ""
        
        # Media state
        self.video_enabled = False
        self.audio_enabled = False
        self.screen_sharing = False
        
        # Setup callbacks
        self._setup_gui_callbacks()
        
        logger.info("Collaboration client initialized")
    
    def _check_platform_capabilities(self):
        """Check and log platform capabilities."""
        capabilities = PLATFORM_INFO.get_platform_summary()
        
        logger.info(f"Platform capabilities:")
        for capability, available in capabilities['capabilities'].items():
            status = "✓" if available else "✗"
            logger.info(f"  {status} {capability}: {available}")
        
        # Test device access
        device_status = DeviceUtils.test_device_access()
        logger.info("Device access test:")
        for device, available in device_status.items():
            status = "✓" if available else "✗"
            logger.info(f"  {status} {device}: {available}")
        
        # Warn about missing capabilities
        if not PLATFORM_INFO.get_capability('audio_capture'):
            logger.warning("Audio capture not available - audio features will be disabled")
        
        if not PLATFORM_INFO.get_capability('video_capture'):
            logger.warning("Video capture not available - video features will be disabled")
        
        if not PLATFORM_INFO.get_capability('screen_capture'):
            logger.warning("Screen capture not available - screen sharing will be disabled")
    
    def _setup_gui_callbacks(self):
        """Setup callbacks between GUI and connection manager."""
        # Connection callbacks
        self.gui_manager.set_connection_callbacks(
            connect_callback=self._handle_connect,
            disconnect_callback=self._handle_disconnect
        )
        
        # Module callbacks with enhanced error handling
        self.gui_manager.set_module_callbacks(
            video_callback=self._handle_video_toggle,
            audio_callback=self._handle_audio_toggle,
            message_callback=self._handle_send_message,
            screen_share_callback=self._handle_screen_share_toggle,
            file_upload_callback=self._handle_file_upload,
            file_download_callback=self._handle_file_download
        )
    
    def _handle_connect(self, username: str):
        """Handle connection request from GUI."""
        try:
            self.current_username = username
            
            # Create connection manager
            server_host = self.gui_manager.server_entry.get().strip() or "localhost"
            self.connection_manager = ConnectionManager(server_host=server_host)
            
            # Note: Screen manager will be initialized after successful connection
            # when we have a valid client_id
            
            # Setup connection callbacks
            self.connection_manager.register_status_callback(self._on_connection_status_changed)
            self.connection_manager.register_message_callback(
                MessageType.CHAT.value, self._on_chat_message
            )
            self.connection_manager.register_message_callback(
                'participant_joined', self._on_participant_joined
            )
            self.connection_manager.register_message_callback(
                'participant_left', self._on_participant_left
            )
            self.connection_manager.register_message_callback(
                'participant_status_update', self._on_participant_status_update
            )
            self.connection_manager.register_message_callback(
                MessageType.SCREEN_SHARE_START.value, self._on_screen_share_start
            )
            self.connection_manager.register_message_callback(
                MessageType.SCREEN_SHARE_STOP.value, self._on_screen_share_stop
            )
            self.connection_manager.register_message_callback(
                MessageType.SCREEN_SHARE.value, self._on_screen_share_frame
            )
            self.connection_manager.register_message_callback(
                MessageType.SCREEN_SHARE_ERROR.value, self._on_screen_share_error
            )
            self.connection_manager.register_message_callback(
                MessageType.SCREEN_SHARE_CONFIRMED.value, self._on_screen_share_confirmed
            )
            self.connection_manager.register_message_callback(
                MessageType.PRESENTER_GRANTED.value, self._on_presenter_granted
            )
            self.connection_manager.register_message_callback(
                MessageType.PRESENTER_DENIED.value, self._on_presenter_denied
            )
            self.connection_manager.register_message_callback(
                MessageType.FILE_AVAILABLE.value, self._on_file_available
            )
            self.connection_manager.register_message_callback(
                'file_download_progress', self._on_file_download_progress
            )
            self.connection_manager.register_message_callback(
                'file_download_complete', self._on_file_download_complete
            )
            self.connection_manager.register_message_callback(
                'file_download_error', self._on_file_download_error
            )
            self.connection_manager.register_message_callback(
                MessageType.AUDIO.value, self._on_audio_packet
            )
            self.connection_manager.register_message_callback(
                MessageType.VIDEO.value, self._on_video_packet
            )
            
            # Attempt connection in separate thread to avoid blocking GUI
            connect_thread = threading.Thread(
                target=self._connect_to_server,
                args=(username,),
                daemon=True
            )
            connect_thread.start()
        
        except Exception as e:
            logger.error(f"Error initiating connection: {e}")
            self.gui_manager.show_error("Connection Error", f"Failed to connect: {e}")
    
    def _connect_to_server(self, username: str):
        """Connect to server in background thread."""
        try:
            success = self.connection_manager.connect(username)
            if success:
                # Initialize media managers after successful connection
                client_id = self.connection_manager.get_client_id()
                if client_id:
                    # Initialize audio manager
                    self.audio_manager = AudioManager(client_id, self.connection_manager)
                    
                    # Setup audio level callback for GUI
                    self.audio_manager.set_audio_level_callback(self._on_audio_level_update)
                    
                    # Setup audio mute callback for GUI
                    self.gui_manager.audio_frame.set_mute_callback(self._handle_audio_mute)
                    
                    logger.info("Audio manager initialized")
                    
                    # Initialize video capture (but don't start it yet)
                    self.video_capture = VideoCapture(client_id, self.connection_manager)
                    self.video_capture.set_frame_callback(self._on_video_frame_captured)
                    
                    # Initialize video manager for incoming video
                    self.video_manager = VideoManager(client_id, self.connection_manager)
                    self.video_manager.set_gui_callbacks(
                        self._on_incoming_video_frame,
                        self._on_video_stream_status_change
                    )
                    
                    # Start video system for receiving video
                    # Enable extreme video optimization
                    extreme_video_optimizer.start_optimization()
                    extreme_video_optimizer.enable_ultra_fast_mode()
                    extreme_video_optimizer.enable_anti_flicker_mode()
                    
                    self.video_manager.start_video_system()
                    
                    logger.info("Video system initialized")
                    
                    # Initialize screen manager after successful connection with proper client ID
                    self._initialize_screen_manager()
            else:
                self.gui_manager.show_error(
                    "Connection Failed", 
                    "Could not connect to server. Please check server address and try again."
                )
        except Exception as e:
            logger.error(f"Connection error: {e}")
            self.gui_manager.show_error("Connection Error", f"Connection failed: {e}")
    
    def _handle_disconnect(self):
        """Handle disconnection request from GUI."""
        try:
            # Cleanup media managers
            if self.audio_manager:
                self.audio_manager.cleanup()
                self.audio_manager = None
            
            if self.video_capture:
                self.video_capture.stop_capture()
                self.video_capture = None
            
            if self.video_manager:
                self.video_manager.stop_video_system()
                self.video_manager = None
            
            if self.screen_manager:
                self.screen_manager.cleanup()
                self.screen_manager = None
            
            if self.connection_manager:
                self.connection_manager.disconnect()
                self.connection_manager = None
            
            # Reset media states
            self.video_enabled = False
            self.audio_enabled = False
            self.screen_sharing = False
            
            logger.info("Disconnected from server")
        
        except Exception as e:
            logger.error(f"Error during disconnect: {e}")
    
    def _initialize_screen_manager(self):
        """Initialize screen manager after successful connection with proper client ID."""
        try:
            # Validate that connection manager exists
            if not self.connection_manager:
                logger.error("Cannot initialize screen manager: no connection manager")
                return False
            
            # Validate that we have a successful connection
            if not self.connection_manager._is_connected():
                logger.error("Cannot initialize screen manager: not connected to server")
                return False
            
            # Validate that client ID is available before creating screen manager
            client_id = self.connection_manager.get_client_id()
            if not client_id:
                logger.error("Cannot initialize screen manager: no client ID available")
                return False
            
            # Ensure we don't create duplicate screen managers
            if self.screen_manager:
                logger.warning("Screen manager already exists, cleaning up old instance")
                self.screen_manager.cleanup()
                self.screen_manager = None
            
            # Create screen manager with proper client ID
            self.screen_manager = ScreenManager(
                client_id=client_id,
                connection_manager=self.connection_manager,
                gui_manager=self.gui_manager
            )
            
            logger.info(f"Screen manager initialized successfully with client ID: {client_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing screen manager: {e}")
            self.screen_manager = None
            return False
    
    def _handle_video_toggle(self, enabled: bool):
        """Handle video enable/disable from GUI."""
        try:
            self.video_enabled = enabled
            
            # Immediately update local video display
            if not enabled:
                # Show blank screen for local video immediately
                if hasattr(self.gui_manager, 'video_frame') and self.gui_manager.video_frame:
                    self.gui_manager.video_frame._show_blank_screen_for_local()
            
            if self.connection_manager:
                # Update server with media status
                self.connection_manager.update_media_status(
                    video_enabled=self.video_enabled,
                    audio_enabled=self.audio_enabled
                )
            
            logger.info(f"Video {'enabled' if enabled else 'disabled'}")
            
            # Start/stop video capture
            if enabled:
                self._start_video_capture()
            else:
                self._stop_video_capture()
        
        except Exception as e:
            logger.error(f"Error toggling video: {e}")
            self.gui_manager.show_error("Video Error", f"Video toggle failed: {e}")
    
    def _handle_audio_toggle(self, enabled: bool):
        """Handle audio enable/disable from GUI."""
        try:
            self.audio_enabled = enabled
            
            if self.audio_manager:
                if enabled:
                    success = self.audio_manager.start_audio()
                    if not success:
                        self.gui_manager.show_error("Audio Error", "Failed to start audio system")
                        return
                else:
                    self.audio_manager.stop_audio()
            
            logger.info(f"Audio {'enabled' if enabled else 'disabled'}")
        
        except Exception as e:
            logger.error(f"Error toggling audio: {e}")
            self.gui_manager.show_error("Audio Error", f"Audio toggle failed: {e}")
    
    def _handle_audio_mute(self, muted: bool):
        """Handle audio mute/unmute from GUI."""
        try:
            if self.audio_manager:
                self.audio_manager.set_muted(muted)
            
            logger.info(f"Audio {'muted' if muted else 'unmuted'}")
        
        except Exception as e:
            logger.error(f"Error toggling audio mute: {e}")
    
    def _on_audio_level_update(self, level: float):
        """Handle audio level updates from audio manager."""
        try:
            # Update GUI audio level indicator
            self.gui_manager.audio_frame.update_audio_level(level)
        
        except Exception as e:
            logger.error(f"Error updating audio level: {e}")
    
    def _handle_send_message(self, message_text: str):
        """Handle sending chat message from GUI with enhanced functionality."""
        try:
            if not self.connection_manager or not self.connection_manager.get_client_id():
                if hasattr(self.gui_manager, 'chat_frame') and self.gui_manager.chat_frame:
                    self.gui_manager.chat_frame.add_error_message("Not connected to server")
                return
            
            success = self.connection_manager.send_chat_message(message_text)
            if success:
                # Add own message to chat display with proper formatting
                if hasattr(self.gui_manager, 'chat_frame') and self.gui_manager.chat_frame:
                    self.gui_manager.chat_frame.add_message(
                        username=self.current_username,
                        message=message_text,
                        timestamp=datetime.now(),
                        is_own_message=True,
                        message_type='chat'
                    )
            else:
                if hasattr(self.gui_manager, 'chat_frame') and self.gui_manager.chat_frame:
                    self.gui_manager.chat_frame.add_error_message("Failed to send message")
        
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            if hasattr(self.gui_manager, 'chat_frame') and self.gui_manager.chat_frame:
                self.gui_manager.chat_frame.add_error_message(f"Send error: {e}")
    
    def _handle_screen_share_toggle(self, enabled: bool):
        """Handle screen sharing toggle from GUI."""
        try:
            # Check if screen manager exists before calling methods
            if not self.screen_manager:
                # Try to initialize screen manager if not available
                if not self._initialize_screen_manager():
                    self.gui_manager.show_error("Screen Share Error", "Screen sharing not available - connection required")
                    # Reset GUI button state since we failed
                    if hasattr(self.gui_manager, 'screen_share_frame'):
                        self.gui_manager.screen_share_frame.set_screen_sharing_status(False)
                    return
            
            if enabled:
                # Check if we're already presenter
                if self.screen_manager.is_presenter:
                    # Start screen sharing directly
                    success = self.screen_manager.start_screen_sharing()
                    if not success:
                        self.gui_manager.show_error("Screen Share Error", "Failed to start screen sharing")
                        # Reset GUI button state since we failed
                        if hasattr(self.gui_manager, 'screen_share_frame'):
                            self.gui_manager.screen_share_frame.set_screen_sharing_status(False)
                        return
                else:
                    # Request presenter role first - screen sharing will start automatically when granted
                    logger.info("Requesting presenter role for screen sharing")
                    self.screen_manager.request_presenter_role()
                    
                    # Show user feedback that request is pending
                    if hasattr(self.gui_manager, 'chat_frame') and self.gui_manager.chat_frame:
                        self.gui_manager.chat_frame.add_system_message("Requesting presenter role...")
            else:
                # Stop screen sharing
                self.screen_manager.stop_screen_sharing()
            
            # Update local state
            self.screen_sharing = enabled
        
        except Exception as e:
            logger.error(f"Error toggling screen share: {e}")
            # Provide detailed error feedback to user
            error_msg = f"Screen sharing error: {str(e)}"
            self.gui_manager.show_error("Screen Share Error", error_msg)
            
            # Reset GUI button state since we failed
            if hasattr(self.gui_manager, 'screen_share_frame'):
                self.gui_manager.screen_share_frame.set_screen_sharing_status(False)
            
            # Reset local state
            self.screen_sharing = False
    
    def _handle_file_upload(self, file_path: str):
        """Handle file upload request from GUI."""
        try:
            if not self.connection_manager or not self.connection_manager.get_client_id():
                self.gui_manager.show_error("Upload Error", "Not connected to server")
                return
            
            logger.info(f"Starting file upload: {file_path}")
            
            # Show progress in GUI
            filename = file_path.split('/')[-1] if '/' in file_path else file_path.split('\\')[-1]
            self.gui_manager.show_file_transfer_progress(filename, 0.0)
            
            # Upload file in background thread to avoid blocking GUI
            upload_thread = threading.Thread(
                target=self._upload_file_background,
                args=(file_path,),
                daemon=True
            )
            upload_thread.start()
        
        except Exception as e:
            logger.error(f"Error initiating file upload: {e}")
            self.gui_manager.show_error("Upload Error", f"Error uploading file: {e}")
            self.gui_manager.hide_file_transfer_progress()
    
    def _upload_file_background(self, file_path: str):
        """Upload file in background thread."""
        try:
            success, message = self.connection_manager.upload_file(file_path)
            
            # Update GUI on main thread
            if success:
                self.gui_manager.show_info("Upload Complete", message)
            else:
                self.gui_manager.show_error("Upload Failed", message)
            
            self.gui_manager.hide_file_transfer_progress()
        
        except Exception as e:
            logger.error(f"Error in background file upload: {e}")
            self.gui_manager.show_error("Upload Error", f"Upload failed: {e}")
            self.gui_manager.hide_file_transfer_progress()
    
    def _handle_file_download(self, file_id: str):
        """Handle file download request from GUI with enhanced user experience."""
        try:
            if not self.connection_manager or not self.connection_manager.get_client_id():
                self.gui_manager.show_error("Download Error", "Not connected to server")
                return
            
            logger.info(f"Starting file download: {file_id}")
            
            # Get filename from shared files list
            if hasattr(self.gui_manager.file_transfer_frame, 'shared_files'):
                file_info = self.gui_manager.file_transfer_frame.shared_files.get(file_id)
                if not file_info:
                    self.gui_manager.show_error("Download Error", "File not found or no longer available")
                    return
                
                filename = file_info['filename']
                filesize = file_info.get('filesize', 0)
                
                # Check if download is already in progress
                active_downloads = self.connection_manager.get_active_downloads()
                if file_id in active_downloads:
                    self.gui_manager.show_info("Download In Progress", f"'{filename}' is already being downloaded.")
                    return
                
                # For large files (>50MB), ask user for save location
                save_path = None
                if filesize > 50 * 1024 * 1024:  # 50MB threshold
                    from tkinter import filedialog
                    save_path = filedialog.asksaveasfilename(
                        title=f"Save {filename} ({filesize / (1024*1024):.1f} MB)",
                        initialname=filename,
                        defaultextension=os.path.splitext(filename)[1],
                        filetypes=[
                            ("All files", "*.*"),
                            ("Documents", "*.pdf;*.doc;*.docx;*.txt"),
                            ("Images", "*.jpg;*.jpeg;*.png;*.gif;*.bmp"),
                            ("Archives", "*.zip;*.rar;*.7z;*.tar;*.gz")
                        ]
                    )
                    
                    if not save_path:
                        return  # User cancelled
                
                # Show initial progress
                self.gui_manager.show_file_transfer_progress(filename, 0.0, "Starting download")
                
                # Request download (will use default downloads directory if save_path is None)
                success = self.connection_manager.request_file_download(file_id, save_path)
                
                if success:
                    logger.info(f"Started download request for: {filename}")
                else:
                    self.gui_manager.show_error("Download Error", "Failed to start file download")
                    self.gui_manager.hide_file_transfer_progress()
            else:
                self.gui_manager.show_error("Download Error", "No files available")
        
        except Exception as e:
            logger.error(f"Error downloading file: {e}")
            self.gui_manager.show_error("Download Error", f"Error downloading file: {e}")
            self.gui_manager.hide_file_transfer_progress()
    
    def _on_connection_status_changed(self, status: str):
        """Handle connection status changes."""
        try:
            logger.info(f"Connection status changed to: {status}")
            
            # Update GUI status
            self.gui_manager.update_connection_status(status)
            
            # Handle specific status changes
            if status == ConnectionStatus.CONNECTED:
                # Update participant list
                if self.connection_manager:
                    participants = self.connection_manager.get_participants()
                    client_id = self.connection_manager.get_client_id()
                    self.gui_manager.update_participants(participants, client_id)
            
            elif status in [ConnectionStatus.DISCONNECTED, ConnectionStatus.ERROR]:
                # Clear participant list
                self.gui_manager.update_participants({}, "")
        
        except Exception as e:
            logger.error(f"Error handling status change: {e}")
    
    def _on_chat_message(self, message: TCPMessage):
        """Handle incoming chat messages with enhanced display."""
        try:
            # Extract message information
            message_text = message.data.get('message', '')
            sender_username = message.data.get('sender_username', 'Unknown')
            
            # Fallback to participant list if sender_username not in message
            if sender_username == 'Unknown' and self.connection_manager:
                participants = self.connection_manager.get_participants()
                participant = participants.get(message.sender_id, {})
                sender_username = participant.get('username', message.sender_id)
            
            # Convert timestamp
            timestamp = datetime.fromtimestamp(message.timestamp) if message.timestamp else datetime.now()
            
            # Check if this is our own message (shouldn't happen, but handle gracefully)
            is_own_message = (message.sender_id == self.connection_manager.get_client_id()) if self.connection_manager else False
            
            # Add to chat display with enhanced formatting
            if hasattr(self.gui_manager, 'chat_frame') and self.gui_manager.chat_frame:
                self.gui_manager.chat_frame.add_message(
                    username=sender_username,
                    message=message_text,
                    timestamp=timestamp,
                    is_own_message=is_own_message,
                    message_type='chat'
                )
            
            logger.info(f"Received chat message from {sender_username}: {message_text}")
        
        except Exception as e:
            logger.error(f"Error handling chat message: {e}")
            if hasattr(self.gui_manager, 'chat_frame') and self.gui_manager.chat_frame:
                self.gui_manager.chat_frame.add_error_message("Error receiving message")
    
    def _on_participant_joined(self, message: TCPMessage):
        """Handle participant joined notification with chat system message."""
        try:
            username = message.data.get('username', 'Unknown')
            
            # Update participant list
            if self.connection_manager:
                participants = self.connection_manager.get_participants()
                client_id = self.connection_manager.get_client_id()
                self.gui_manager.update_participants(participants, client_id)
            
            # Add system message to chat
            if hasattr(self.gui_manager, 'chat_frame') and self.gui_manager.chat_frame:
                self.gui_manager.chat_frame.add_system_message(f"{username} joined the session")
            
            logger.info(f"Participant joined: {username}")
        
        except Exception as e:
            logger.error(f"Error handling participant joined: {e}")
    
    def _on_participant_left(self, message: TCPMessage):
        """Handle participant left notification with chat system message."""
        try:
            username = message.data.get('username', 'Unknown')
            left_client_id = message.data.get('client_id')
            
            # Remove video stream for disconnected client
            if self.video_manager and left_client_id:
                self.video_manager.remove_client_video(left_client_id)
            
            # Clear video slot in GUI for disconnected client
            if hasattr(self.gui_manager, 'video_frame') and self.gui_manager.video_frame and left_client_id:
                self.gui_manager.video_frame.clear_video_slot(left_client_id)
            
            # Update participant list
            if self.connection_manager:
                participants = self.connection_manager.get_participants()
                client_id = self.connection_manager.get_client_id()
                self.gui_manager.update_participants(participants, client_id)
            
            # Add system message to chat
            if hasattr(self.gui_manager, 'chat_frame') and self.gui_manager.chat_frame:
                self.gui_manager.chat_frame.add_system_message(f"{username} left the session")
            
            logger.info(f"Participant left: {username}")
        
        except Exception as e:
            logger.error(f"Error handling participant left: {e}")
    
    def _on_participant_status_update(self, message: TCPMessage):
        """Handle participant status updates."""
        try:
            if self.connection_manager:
                # Get the updated client info
                updated_client_id = message.data.get('client_id')
                video_enabled = message.data.get('video_enabled')
                audio_enabled = message.data.get('audio_enabled')
                
                # Update participants list
                participants = self.connection_manager.get_participants()
                
                # Update GUI participant list (this will handle video status changes via update_video_feeds)
                current_client_id = self.connection_manager.get_client_id()
                self.gui_manager.update_participants(participants, current_client_id)
                
                # Log the status change for debugging (only for significant changes)
                if updated_client_id and updated_client_id in participants:
                    username = participants[updated_client_id].get('username', f'User {updated_client_id[:8]}')
                    status = "enabled" if video_enabled else "disabled"
                    logger.debug(f"Participant status update: Video {status} for {username}")
        
        except Exception as e:
            logger.error(f"Error handling participant status update: {e}")
    
    def _on_screen_share_start(self, message: TCPMessage):
        """Handle screen sharing start messages from other clients."""
        try:
            # Get presenter username from participants list
            presenter_id = message.sender_id
            presenter_name = "Unknown"
            
            if self.connection_manager:
                participants = self.connection_manager.get_participants()
                participant = participants.get(presenter_id, {})
                presenter_name = participant.get('username', f"Client {presenter_id}")
            
            # Add presenter name to message data for screen manager
            if 'data' not in message.__dict__ or message.data is None:
                message.data = {}
            message.data['presenter_name'] = presenter_name
            
            if self.screen_manager:
                self.screen_manager.handle_screen_share_message(message)
                
            # Add system message to chat
            if hasattr(self.gui_manager, 'chat_frame') and self.gui_manager.chat_frame:
                self.gui_manager.chat_frame.add_system_message(f"{presenter_name} started screen sharing")
                
        except Exception as e:
            logger.error(f"Error handling screen share start: {e}")
    
    def _on_screen_share_stop(self, message: TCPMessage):
        """Handle screen sharing stop messages."""
        try:
            # Get presenter username from participants list
            presenter_id = message.sender_id
            presenter_name = "Unknown"
            
            if self.connection_manager:
                participants = self.connection_manager.get_participants()
                participant = participants.get(presenter_id, {})
                presenter_name = participant.get('username', f"Client {presenter_id}")
            
            if self.screen_manager:
                self.screen_manager.handle_screen_share_message(message)
                
            # Add system message to chat
            if hasattr(self.gui_manager, 'chat_frame') and self.gui_manager.chat_frame:
                self.gui_manager.chat_frame.add_system_message(f"{presenter_name} stopped screen sharing")
                
        except Exception as e:
            logger.error(f"Error handling screen share stop: {e}")
    
    def _on_screen_share_frame(self, message: TCPMessage):
        """Handle screen sharing frame data."""
        try:
            if self.screen_manager:
                self.screen_manager.handle_screen_share_message(message)
        except Exception as e:
            logger.error(f"Error handling screen share frame: {e}")
    
    def _on_screen_share_error(self, message: TCPMessage):
        """Handle screen share error messages with enhanced feedback."""
        try:
            error_msg = message.data.get('error', 'Unknown error')
            error_type = message.data.get('error_type', 'general')
            logger.warning(f"Screen share error: {error_msg}")
            
            # Show detailed error to user with suggestions
            detailed_msg = error_msg
            if error_type == 'permission':
                detailed_msg += "\n\nPlease check your screen recording permissions in system settings."
            elif error_type == 'capture':
                detailed_msg += "\n\nTry closing other applications that might be using screen capture."
            elif error_type == 'network':
                detailed_msg += "\n\nCheck your network connection and try again."
            
            self.gui_manager.show_error("Screen Share Error", detailed_msg)
            
            # Stop screen sharing via screen manager
            if self.screen_manager:
                self.screen_manager.stop_screen_sharing()
            
            # Update GUI to show stopped status with error indication
            if hasattr(self.gui_manager, 'screen_share_frame'):
                self.gui_manager.screen_share_frame.sharing_status.config(
                    text="Screen sharing failed", foreground='red'
                )
                # Reset after delay
                self.gui_manager.root.after(5000, lambda: 
                    self.gui_manager.screen_share_frame.sharing_status.config(
                        text="Ready to share", foreground='black'
                    )
                )
            
            # Add error message to chat
            if hasattr(self.gui_manager, 'chat_frame') and self.gui_manager.chat_frame:
                self.gui_manager.chat_frame.add_error_message(f"Screen sharing error: {error_msg}")
            
        except Exception as e:
            logger.error(f"Error handling screen share error: {e}")
    
    def _on_screen_share_confirmed(self, message: TCPMessage):
        """Handle screen share confirmation from server."""
        try:
            status = message.data.get('status')
            if status == 'started':
                logger.info("Server confirmed screen sharing start - beginning capture")
                if hasattr(self, 'screen_manager'):
                    self.screen_manager.handle_screen_share_confirmed()
                else:
                    logger.error("Screen manager not available")
            
        except Exception as e:
            logger.error(f"Error handling screen share confirmation: {e}")
    
    def _on_presenter_granted(self, message: TCPMessage):
        """Handle presenter role granted message with enhanced feedback."""
        try:
            if self.screen_manager:
                self.screen_manager.handle_presenter_granted()
                
            # Add system message to chat
            if hasattr(self.gui_manager, 'chat_frame') and self.gui_manager.chat_frame:
                self.gui_manager.chat_frame.add_system_message("You are now the presenter!")
                
        except Exception as e:
            logger.error(f"Error handling presenter granted: {e}")
            self.gui_manager.show_error("Screen Share Error", f"Error handling presenter role: {e}")
    
    def _on_presenter_denied(self, message: TCPMessage):
        """Handle presenter role denied message with detailed feedback."""
        try:
            reason = message.data.get('reason', 'Another user is already presenting')
            if self.screen_manager:
                self.screen_manager.handle_presenter_denied(reason)
                
            # Add system message to chat with denial reason
            if hasattr(self.gui_manager, 'chat_frame') and self.gui_manager.chat_frame:
                self.gui_manager.chat_frame.add_system_message(f"Presenter request denied: {reason}")
                
        except Exception as e:
            logger.error(f"Error handling presenter denied: {e}")
            self.gui_manager.show_error("Screen Share Error", f"Error handling presenter denial: {e}")
    
    def _on_file_available(self, message: TCPMessage):
        """Handle file available notifications."""
        try:
            filename = message.data.get('filename')
            filesize = message.data.get('filesize')
            file_id = message.data.get('file_id')
            uploader_id = message.data.get('uploader_id')
            
            if self.connection_manager:
                participants = self.connection_manager.get_participants()
                participant = participants.get(uploader_id, {})
                uploader = participant.get('username', uploader_id)
                
                self.gui_manager.add_shared_file(file_id, filename, filesize, uploader)
                
                # Add system message to chat
                if hasattr(self.gui_manager, 'chat_frame') and self.gui_manager.chat_frame:
                    self.gui_manager.chat_frame.add_system_message(
                        f"{uploader} shared a file: {filename}"
                    )
        
        except Exception as e:
            logger.error(f"Error handling file available: {e}")
    
    def _on_file_download_progress(self, filename: str, progress: float):
        """Handle file download progress updates with enhanced display."""
        try:
            # Update progress bar with download-specific text
            self.gui_manager.show_file_transfer_progress(filename, progress, "Downloading")
            
            # Log progress for debugging (every 25%)
            if progress in [0.25, 0.5, 0.75]:
                logger.info(f"Download progress: {filename} - {progress*100:.0f}%")
                
        except Exception as e:
            logger.error(f"Error handling download progress: {e}")
    
    def _on_file_download_complete(self, filename: str, file_path: str):
        """Handle file download completion with user notification."""
        try:
            # Show completion progress briefly
            self.gui_manager.show_file_transfer_progress(filename, 1.0, "Download complete")
            
            # Hide progress after a short delay
            self.gui_manager.root.after(2000, self.gui_manager.hide_file_transfer_progress)
            
            # Show success notification
            self.gui_manager.show_info(
                "Download Complete", 
                f"File '{filename}' downloaded successfully!\n\nSaved to: {file_path}"
            )
            
            # Add system message to chat
            if hasattr(self.gui_manager, 'chat_frame') and self.gui_manager.chat_frame:
                self.gui_manager.chat_frame.add_system_message(
                    f"Downloaded file: {filename}"
                )
            
            logger.info(f"File download completed: {filename} -> {file_path}")
            
        except Exception as e:
            logger.error(f"Error handling download completion: {e}")
    
    def _on_file_download_error(self, filename: str, error_message: str):
        """Handle file download errors."""
        try:
            self.gui_manager.hide_file_transfer_progress()
            self.gui_manager.show_error(
                "Download Failed", 
                f"Failed to download '{filename}':\n{error_message}"
            )
            
            # Add error message to chat
            if hasattr(self.gui_manager, 'chat_frame') and self.gui_manager.chat_frame:
                self.gui_manager.chat_frame.add_error_message(
                    f"Download failed: {filename} - {error_message}"
                )
            
            logger.error(f"File download failed: {filename} - {error_message}")
            
        except Exception as e:
            logger.error(f"Error handling download error: {e}")
    
    def _on_audio_packet(self, packet: UDPPacket):
        """Handle incoming audio packets."""
        try:
            # TODO: Implement audio playback
            pass
        
        except Exception as e:
            logger.error(f"Error handling audio packet: {e}")
    
    def _on_video_packet(self, packet: UDPPacket):
        """Handle incoming video packets with enhanced processing."""
        try:
            logger.debug(f"Received video packet from {packet.sender_id}, seq: {packet.sequence_num}")
            
            if self.video_manager:
                # Process video packet
                self.video_manager.process_incoming_video(packet)
                logger.debug(f"Video packet processed by video manager")
            else:
                logger.warning("Video manager not available for packet processing")
        
        except Exception as e:
            logger.error(f"Error handling video packet: {e}")
    def _start_video_capture(self):
        """Start video capture using OpenCV."""
        try:
            if not self.connection_manager or not self.connection_manager.get_client_id():
                logger.error("Cannot start video capture: not connected")
                return False
            
            # Initialize video capture if not already created
            if not self.video_capture:
                client_id = self.connection_manager.get_client_id()
                self.video_capture = VideoCapture(client_id, self.connection_manager)
                
                # Set frame callback for local video display
                self.video_capture.set_frame_callback(self._on_video_frame_captured)
            
            # Start video capture
            success = self.video_capture.start_capture()
            if success:
                logger.info("Video capture started successfully")
            else:
                logger.error("Failed to start video capture")
                self.gui_manager.show_error("Video Error", "Failed to start video capture. Please check your camera.")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error starting video capture: {e}")
            self.gui_manager.show_error("Video Error", f"Failed to start video: {e}")
            return False
    
    def _stop_video_capture(self):
        """Stop video capture."""
        try:
            if self.video_capture:
                self.video_capture.stop_capture()
                logger.info("Video capture stopped")
        
        except Exception as e:
            logger.error(f"Error stopping video capture: {e}")
    
    def _on_video_frame_captured(self, frame):
        """Handle captured video frame for local display."""
        try:
            # Validate frame
            if frame is None:
                logger.warning("Received None frame from video capture")
                return
            
            # Update GUI with local video frame
            if hasattr(self.gui_manager, 'video_frame') and self.gui_manager.video_frame:
                self.gui_manager.video_frame.update_local_video(frame)
                logger.debug("Local video frame sent to GUI")
            else:
                logger.warning("GUI video frame not available for local video display")
        
        except Exception as e:
            logger.error(f"Error handling local video frame: {e}")
    
    def _on_incoming_video_frame(self, client_id: str, frame):
        """Handle incoming video frame from other participants with username display."""
        try:
            # Validate frame and client_id
            if not client_id:
                logger.warning("Received video frame with empty client_id")
                return
            
            if frame is None:
                logger.warning(f"Received None frame from client {client_id}")
                return
            
            # Update GUI with incoming video frame
            if hasattr(self.gui_manager, 'video_frame') and self.gui_manager.video_frame:
                self.gui_manager.video_frame.update_remote_video(client_id, frame)
                
                # Update participant name if we have connection manager
                if self.connection_manager:
                    participants = self.connection_manager.get_participants()
                    participant = participants.get(client_id, {})
                    username = participant.get('username', f'Client {client_id[:8]}')
                    self.gui_manager.video_frame.update_participant_name(client_id, username)
                
                logger.debug(f"Remote video frame from {client_id} sent to GUI")
            else:
                logger.warning("GUI video frame not available for remote video display")
        
        except Exception as e:
            logger.error(f"Error handling incoming video frame from {client_id}: {e}")
    
    def _on_video_stream_status_change(self, client_id: str, active: bool):
        """Handle video stream status changes from video manager."""
        try:
            # This method handles video stream events from the video manager
            # The actual UI updates are handled by _on_participant_status_update
            # which receives server-broadcasted status updates
            
            # Update local participant data
            if self.connection_manager:
                participants = self.connection_manager.get_participants()
                if client_id in participants:
                    participants[client_id]['video_enabled'] = active
                    logger.info(f"Video stream status updated for {client_id}: {'active' if active else 'inactive'}")
        
        except Exception as e:
            logger.error(f"Error handling video stream status change: {e}")
    

    
    def _start_audio_capture(self):
        """Start audio capture (placeholder)."""
        logger.info("Audio capture started (placeholder)")
        # TODO: Implement audio capture using PyAudio
    
    def _stop_audio_capture(self):
        """Stop audio capture (placeholder)."""
        logger.info("Audio capture stopped (placeholder)")
    
    def _start_screen_capture(self):
        """Start screen capture."""
        try:
            import traceback
            logger.info("Starting screen capture...")
            logger.info(f"Screen capture called from: {traceback.format_stack()[-2].strip()}")
            
            if not hasattr(self, 'screen_capture') or self.screen_capture is None:
                # Import and initialize screen capture
                from client.screen_capture import ScreenCapture
                client_id = self.connection_manager.get_client_id() if self.connection_manager else "unknown"
                logger.info(f"Initializing screen capture for client {client_id}")
                
                self.screen_capture = ScreenCapture(
                    client_id=client_id,
                    connection_manager=self.connection_manager
                )
                
                # Don't set local frame callback - let clients only see others' screens
            
            success = self.screen_capture.start_capture()
            if success:
                logger.info("Screen capture started successfully")
                self.gui_manager.show_info("Screen Share", "Screen sharing started successfully")
            else:
                logger.error("Failed to start screen capture")
                self.gui_manager.show_error("Screen Share Error", "Failed to start screen capture")
                
        except Exception as e:
            logger.error(f"Error starting screen capture: {e}")
            self.gui_manager.show_error("Screen Share Error", f"Error starting screen capture: {e}")
    
    def _stop_screen_capture(self):
        """Stop screen capture."""
        try:
            if hasattr(self, 'screen_capture') and self.screen_capture is not None:
                self.screen_capture.stop_capture()
                logger.info("Screen capture stopped successfully")
            else:
                logger.warning("No screen capture instance to stop")
                
        except Exception as e:
            logger.error(f"Error stopping screen capture: {e}")
    
    def run(self):
        """Start the client application."""
        try:
            self.running = True
            logger.info("Starting collaboration client...")
            
            # Start GUI main loop
            self.gui_manager.run()
        
        except KeyboardInterrupt:
            logger.info("Client interrupted by user")
        except Exception as e:
            logger.error(f"Client error: {e}")
        finally:
            self.shutdown()
    
    def shutdown(self):
        """Shutdown the client application."""
        try:
            self.running = False
            
            # Disconnect from server
            if self.connection_manager:
                self.connection_manager.disconnect()
            
            # Close GUI
            self.gui_manager.close()
            
            logger.info("Client shutdown complete")
        
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")


def main():
    """Main entry point for the client application."""
    try:
        client = CollaborationClient()
        client.run()
    except Exception as e:
        logger.error(f"Failed to start client: {e}")


if __name__ == "__main__":
    main()