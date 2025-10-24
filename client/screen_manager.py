"""
Screen sharing manager for the collaboration client.
Integrates screen capture, playback, and GUI controls for screen sharing functionality.
"""

import logging
import threading
import time
from typing import Optional, Callable
from client.screen_capture import ScreenCapture
from client.screen_playback import ScreenPlayback
from common.messages import TCPMessage, MessageType

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ScreenManager:
    """
    Screen sharing manager that coordinates capture, playback, and controls.
    
    Handles:
    - Screen capture for sharing own screen
    - Screen playback for viewing shared screens
    - Presenter role management
    - Integration with GUI controls and connection manager
    """
    
    def __init__(self, client_id: str, connection_manager=None, gui_manager=None):
        """
        Initialize the screen sharing manager.
        
        Args:
            client_id: Unique identifier for this client
            connection_manager: Connection manager for network communication
            gui_manager: GUI manager for user interface updates
        """
        self.client_id = client_id
        self.connection_manager = connection_manager
        self.gui_manager = gui_manager
        
        # Screen sharing components
        self.screen_capture = ScreenCapture(client_id, connection_manager)
        self.screen_playback = ScreenPlayback(client_id)
        
        # Screen sharing state
        self.is_presenter = False
        self.is_sharing = False
        self.presenter_request_pending = False
        
        # Threading
        self._lock = threading.RLock()
        
        # Setup callbacks
        self._setup_callbacks()
        
        logger.info("Screen sharing manager initialized")
    
    def _setup_callbacks(self):
        """Setup callbacks between components."""
        # Screen playback callbacks
        self.screen_playback.set_frame_callback(self._on_screen_frame_received)
        self.screen_playback.set_presenter_change_callback(self._on_presenter_changed)
        
        # Connection manager callbacks for network error handling
        if self.connection_manager:
            self.connection_manager.register_message_callback('screen_sharing_connection_lost', self._on_connection_lost)
            self.connection_manager.register_message_callback('screen_sharing_reconnected', self._on_connection_restored)
            self.connection_manager.register_message_callback('screen_sharing_connection_failed', self._on_connection_failed)
        
        # Start screen playback (always ready to receive)
        self.screen_playback.start_receiving()
    
    def request_presenter_role(self):
        """Request presenter role from server with comprehensive error handling."""
        try:
            if not self.connection_manager:
                error_msg = "Cannot request presenter role: no connection manager available"
                logger.error(error_msg)
                if self.gui_manager:
                    self.gui_manager.show_error("Screen Sharing Error", error_msg)
                return
            
            with self._lock:
                if self.is_presenter:
                    logger.info("Already presenter, releasing presenter role")
                    self._release_presenter_role()
                    return
                
                if self.presenter_request_pending:
                    logger.warning("Presenter request already pending")
                    if self.gui_manager:
                        self.gui_manager.show_error("Screen Sharing", "Presenter request already in progress")
                    return
                
                self.presenter_request_pending = True
            
            # Use enhanced connection manager method that returns detailed error info
            success, message = self.connection_manager.request_presenter_role()
            
            if success:
                logger.info(f"Presenter role request sent: {message}")
                # Set a timeout to reset pending flag if no response
                threading.Timer(10.0, self._reset_presenter_request_timeout).start()
            else:
                logger.error(f"Failed to send presenter role request: {message}")
                with self._lock:
                    self.presenter_request_pending = False
                
                # Show detailed error to user
                if self.gui_manager:
                    self.gui_manager.show_error("Screen Sharing Error", f"Failed to request presenter role: {message}")
        
        except Exception as e:
            error_msg = f"Unexpected error requesting presenter role: {e}"
            logger.error(error_msg)
            
            with self._lock:
                self.presenter_request_pending = False
            
            if self.gui_manager:
                self.gui_manager.show_error("Screen Sharing Error", error_msg)
    
    def _release_presenter_role(self):
        """Release presenter role (stop sharing and notify server)."""
        with self._lock:
            if self.is_sharing:
                self.stop_screen_sharing()
            
            self.is_presenter = False
            
            # Update GUI
            if self.gui_manager:
                self.gui_manager.set_presenter_status(False)
        
        # Note: In a full implementation, we might send a release message to server
        logger.info("Released presenter role")
    
    def start_screen_sharing(self):
        """Start screen sharing with comprehensive error handling."""
        try:
            with self._lock:
                if not self.is_presenter:
                    error_msg = "Cannot start screen sharing: not presenter"
                    logger.error(error_msg)
                    if self.gui_manager:
                        self.gui_manager.handle_presenter_denied("You must be the presenter to share your screen")
                    return False
                
                if self.is_sharing:
                    logger.warning("Screen sharing already active")
                    return True
            
            # Check connection manager availability
            if not self.connection_manager:
                error_msg = "Cannot start screen sharing: no connection manager available"
                logger.error(error_msg)
                if self.gui_manager:
                    self.gui_manager.show_error("Screen Sharing Error", error_msg)
                return False
            
            # Send start message to server first with detailed error handling
            success, message = self.connection_manager.start_screen_sharing()
            if not success:
                error_msg = f"Failed to send screen sharing start message: {message}"
                logger.error(error_msg)
                if self.gui_manager:
                    self.gui_manager.show_error("Screen Sharing Error", error_msg)
                return False
            
            # Wait for server confirmation before starting capture
            logger.info(f"Screen sharing start message sent: {message}")
            logger.info("Waiting for server confirmation to start screen capture...")
            return True  # Actual capture will start when server confirms
        
        except Exception as e:
            error_msg = f"Unexpected error starting screen sharing: {e}"
            logger.error(error_msg)
            if self.gui_manager:
                self.gui_manager.show_error("Screen Sharing Error", error_msg)
            return False
    
    def stop_screen_sharing(self):
        """Stop screen sharing with comprehensive error handling and cleanup."""
        try:
            with self._lock:
                if not self.is_sharing:
                    logger.warning("Screen sharing not active")
                    return
                
                self.is_sharing = False
            
            # Stop screen capture with error handling
            try:
                self.screen_capture.stop_capture()
                logger.info("Screen capture stopped successfully")
            except Exception as e:
                logger.error(f"Error stopping screen capture: {e}")
                # Continue with cleanup even if capture stop fails
            
            # Send stop message to server with error handling
            if self.connection_manager:
                try:
                    success, message = self.connection_manager.stop_screen_sharing()
                    if success:
                        logger.info(f"Screen sharing stop message sent: {message}")
                    else:
                        logger.warning(f"Failed to send stop message to server: {message}")
                        # Continue with local cleanup even if server notification fails
                except Exception as e:
                    logger.error(f"Error sending stop message to server: {e}")
            else:
                logger.warning("No connection manager available to notify server of stop")
            
            # Update GUI with error handling
            try:
                if self.gui_manager:
                    self.gui_manager.set_screen_sharing_status(False)
                    logger.info("GUI updated for screen sharing stop")
            except Exception as e:
                logger.error(f"Error updating GUI for screen sharing stop: {e}")
            
            logger.info("Screen sharing stopped and cleaned up")
        
        except Exception as e:
            error_msg = f"Unexpected error stopping screen sharing: {e}"
            logger.error(error_msg)
            
            # Force cleanup even on error
            try:
                with self._lock:
                    self.is_sharing = False
                self.screen_capture.stop_capture()
                if self.gui_manager:
                    self.gui_manager.set_screen_sharing_status(False)
            except Exception as cleanup_error:
                logger.error(f"Error during forced cleanup: {cleanup_error}")
            
            if self.gui_manager:
                self.gui_manager.show_error("Screen Sharing Error", f"Error stopping screen sharing: {e}")
    
    def handle_presenter_granted(self):
        """Handle presenter role being granted by server with enhanced feedback."""
        with self._lock:
            self.is_presenter = True
            self.presenter_request_pending = False
        
        # Update GUI with enhanced feedback
        if self.gui_manager:
            self.gui_manager.handle_presenter_granted()
        
        logger.info("Presenter role granted - you can now start screen sharing")
        
        # Automatically start screen sharing after getting presenter role
        logger.info("Auto-starting screen sharing after presenter role granted")
        self.start_screen_sharing()
    
    def handle_screen_share_confirmed(self):
        """Handle server confirmation to start screen sharing with comprehensive error handling."""
        try:
            logger.info("Server confirmed screen sharing - starting capture")
            
            # Check if screen capture is available before attempting to start
            try:
                capability_info = self.screen_capture.get_capability_info()
                logger.info(f"Screen capture capability info: {capability_info}")
                
                available = capability_info.get('available', False)
                logger.info(f"Screen capture available: {available}")
                
                if not available:
                    # Get detailed error information
                    capabilities = capability_info.get('capabilities', {})
                    permissions = capability_info.get('permissions', {})
                    dependencies = capability_info.get('dependencies', {})
                    
                    logger.error(f"Screen capture capabilities: {capabilities}")
                    logger.error(f"Screen capture permissions: {permissions}")
                    logger.error(f"Screen capture dependencies: {dependencies}")
                    
                    # Try to get a more specific error message
                    error_msg = capability_info.get('error_message')
                    if not error_msg:
                        if not capabilities.get('available', True):
                            error_msg = capabilities.get('message', 'Platform capabilities not available')
                        elif not permissions.get('available', True):
                            error_msg = permissions.get('message', 'Screen capture permissions denied')
                        else:
                            error_msg = 'Screen capture not available'
                    
                    logger.error(f"Screen capture not available: {error_msg}")
                    
                    if self.gui_manager:
                        self.gui_manager.show_error("Screen Capture Error", error_msg)
                        # Provide setup instructions if available
                        try:
                            instructions = self.screen_capture.get_setup_instructions()
                            if instructions:
                                instruction_text = "\n".join(instructions)
                                self.gui_manager.show_error("Setup Instructions", instruction_text)
                        except Exception as inst_e:
                            logger.error(f"Error getting setup instructions: {inst_e}")
                    
                    # Notify server that we failed to start
                    self._notify_server_capture_failed(error_msg)
                    return
            except Exception as e:
                logger.error(f"Error checking screen capture capability: {e}")
                import traceback
                logger.error(f"Capability check traceback: {traceback.format_exc()}")
                # Continue with attempt, but log the error
            
            # Now actually start screen capture
            logger.info("Attempting to start screen capture...")
            try:
                success, message = self.screen_capture.start_capture()
                logger.info(f"Screen capture start result: success={success}, message='{message}'")
                
                if success:
                    with self._lock:
                        self.is_sharing = True
                    
                    # Update GUI
                    try:
                        if self.gui_manager:
                            self.gui_manager.set_screen_sharing_status(True)
                            logger.info("GUI updated for screen sharing start")
                    except Exception as e:
                        logger.error(f"Error updating GUI for screen sharing start: {e}")
                        # Continue even if GUI update fails
                    
                    logger.info(f"Screen capture started successfully: {message}")
                else:
                    logger.error(f"Failed to start screen capture after server confirmation: {message}")
                    
                    # Show detailed error to user
                    if self.gui_manager:
                        self.gui_manager.show_error("Screen Capture Error", message)
                    
                    # Notify server that we failed to start
                    self._notify_server_capture_failed(message)
            except Exception as start_e:
                error_msg = f"Exception during screen capture start: {start_e}"
                logger.error(error_msg)
                if self.gui_manager:
                    self.gui_manager.show_error("Screen Capture Error", error_msg)
                self._notify_server_capture_failed(error_msg)
        
        except Exception as e:
            error_msg = f"Unexpected error handling screen share confirmation: {e}"
            logger.error(error_msg)
            
            if self.gui_manager:
                self.gui_manager.show_error("Screen Sharing Error", error_msg)
            
            # Notify server of failure
            self._notify_server_capture_failed(f"Unexpected error: {e}")
    
    def _notify_server_capture_failed(self, error_message: str):
        """Notify server that screen capture failed to start."""
        try:
            if self.connection_manager:
                success, message = self.connection_manager.stop_screen_sharing()
                if success:
                    logger.info(f"Notified server of capture failure: {message}")
                else:
                    logger.warning(f"Failed to notify server of capture failure: {message}")
            else:
                logger.warning("No connection manager available to notify server of capture failure")
        except Exception as e:
            logger.error(f"Error notifying server of capture failure: {e}")
    
    def handle_presenter_denied(self, reason: str = ""):
        """Handle presenter role being denied by server with detailed feedback."""
        with self._lock:
            self.presenter_request_pending = False
        
        # Update GUI with detailed error feedback
        if self.gui_manager:
            self.gui_manager.handle_presenter_denied(reason)
        
        logger.info(f"Presenter role denied: {reason}")
    
    def _reset_presenter_request_timeout(self):
        """Reset presenter request pending flag after timeout."""
        with self._lock:
            if self.presenter_request_pending:
                logger.warning("Presenter request timed out - resetting pending flag")
                self.presenter_request_pending = False
    
    def handle_screen_share_message(self, message: TCPMessage):
        """Handle incoming screen share message with comprehensive error handling."""
        try:
            # Validate message structure
            if not message or not hasattr(message, 'msg_type'):
                logger.error("Invalid screen share message received: missing message type")
                return
            
            if message.msg_type == MessageType.SCREEN_SHARE.value:
                # Process screen frame with error handling
                try:
                    self.screen_playback.process_screen_message(message)
                except Exception as e:
                    logger.error(f"Error processing screen frame: {e}")
                    if self.gui_manager:
                        self.gui_manager.show_error("Screen Playback Error", f"Error displaying screen frame: {e}")
            
            elif message.msg_type == MessageType.SCREEN_SHARE_START.value:
                # Someone started screen sharing
                try:
                    presenter_id = message.sender_id
                    presenter_name = message.data.get('presenter_name', f"Client {presenter_id}") if message.data else f"Client {presenter_id}"
                    
                    if self.gui_manager:
                        # Update presenter info and status message
                        self.gui_manager.update_presenter(presenter_name)
                        self.gui_manager.handle_screen_share_started(presenter_name)
                    
                    logger.info(f"Screen sharing started by {presenter_name}")
                except Exception as e:
                    logger.error(f"Error handling screen share start: {e}")
            
            elif message.msg_type == MessageType.SCREEN_SHARE_STOP.value:
                # Someone stopped screen sharing
                try:
                    if self.gui_manager:
                        # Clear presenter and reset status
                        self.gui_manager.update_presenter(None)
                        self.gui_manager.handle_screen_share_stopped()
                    
                    logger.info("Screen sharing stopped by presenter")
                except Exception as e:
                    logger.error(f"Error handling screen share stop: {e}")
            
            elif message.msg_type == MessageType.PRESENTER_GRANTED.value:
                # Presenter role granted
                try:
                    presenter_id = message.data.get('presenter_id') if message.data else None
                    if presenter_id == self.client_id:
                        self.handle_presenter_granted()
                    else:
                        logger.warning(f"Received presenter granted for different client: {presenter_id}")
                except Exception as e:
                    logger.error(f"Error handling presenter granted: {e}")
                    if self.gui_manager:
                        self.gui_manager.show_error("Screen Sharing Error", f"Error processing presenter role: {e}")
            
            elif message.msg_type == MessageType.PRESENTER_DENIED.value:
                # Presenter role denied
                try:
                    reason = message.data.get('reason', 'Unknown reason') if message.data else 'Unknown reason'
                    self.handle_presenter_denied(reason)
                except Exception as e:
                    logger.error(f"Error handling presenter denied: {e}")
                    if self.gui_manager:
                        self.gui_manager.show_error("Screen Sharing Error", f"Error processing presenter denial: {e}")
            
            else:
                logger.warning(f"Unknown screen share message type: {message.msg_type}")
        
        except Exception as e:
            error_msg = f"Unexpected error handling screen share message: {e}"
            logger.error(error_msg)
            if self.gui_manager:
                self.gui_manager.show_error("Screen Sharing Error", error_msg)
    
    def _on_screen_frame_received(self, frame_data, presenter_id: str):
        """Callback for when screen frame is received with comprehensive error handling."""
        try:
            # Validate frame data
            if frame_data is None or (hasattr(frame_data, 'size') and frame_data.size == 0) or (isinstance(frame_data, (str, bytes)) and len(frame_data) == 0):
                logger.warning("Received empty screen frame data")
                return
            
            if not presenter_id:
                logger.warning("Received screen frame without presenter ID")
                return
            
            # Update GUI with screen frame
            if self.gui_manager:
                try:
                    self.gui_manager.display_screen_frame(frame_data, presenter_id)
                except Exception as gui_error:
                    logger.error(f"Error updating GUI with screen frame: {gui_error}")
                    # Show error to user but don't crash
                    self.gui_manager.show_error("Display Error", f"Error displaying screen frame: {gui_error}")
            else:
                logger.warning("No GUI manager available to display screen frame")
        
        except Exception as e:
            error_msg = f"Unexpected error handling received screen frame: {e}"
            logger.error(error_msg)
            if self.gui_manager:
                self.gui_manager.show_error("Screen Playback Error", error_msg)
    
    def _on_presenter_changed(self, presenter_id: Optional[str]):
        """Callback for when presenter changes with comprehensive error handling."""
        try:
            # Update GUI with presenter change
            if self.gui_manager:
                try:
                    presenter_name = f"Client {presenter_id}" if presenter_id else None
                    self.gui_manager.update_screen_sharing_presenter(presenter_name)
                    logger.info(f"Updated presenter to: {presenter_name}")
                except Exception as gui_error:
                    logger.error(f"Error updating GUI with presenter change: {gui_error}")
                    # Continue operation but log the error
            else:
                logger.warning("No GUI manager available to update presenter")
        
        except Exception as e:
            error_msg = f"Unexpected error handling presenter change: {e}"
            logger.error(error_msg)
            if self.gui_manager:
                self.gui_manager.show_error("Screen Sharing Error", error_msg)
    
    def _on_connection_lost(self):
        """Handle connection loss during screen sharing."""
        try:
            logger.warning("Connection lost during screen sharing session")
            
            # Pause screen capture if we're sharing
            if self.is_sharing:
                try:
                    # Don't fully stop capture, just pause it
                    logger.info("Pausing screen capture due to connection loss")
                    # Note: We don't call stop_screen_sharing() here as that would clean up everything
                    # Instead we just pause and wait for reconnection
                except Exception as e:
                    logger.error(f"Error pausing screen capture: {e}")
            
            # Notify user about connection issues
            if self.gui_manager:
                self.gui_manager.show_error("Connection Lost", 
                    "Network connection lost during screen sharing. Attempting to reconnect...")
        
        except Exception as e:
            logger.error(f"Error handling connection loss: {e}")
    
    def _on_connection_restored(self):
        """Handle connection restoration during screen sharing."""
        try:
            logger.info("Connection restored during screen sharing session")
            
            # Resume screen sharing if we were sharing before
            if self.is_presenter and self.is_sharing:
                try:
                    logger.info("Attempting to resume screen sharing after reconnection")
                    # Re-request presenter role and restart sharing
                    self.request_presenter_role()
                except Exception as e:
                    logger.error(f"Error resuming screen sharing after reconnection: {e}")
                    if self.gui_manager:
                        self.gui_manager.show_error("Screen Sharing Error", 
                            f"Failed to resume screen sharing after reconnection: {e}")
            
            # Notify user about successful reconnection
            if self.gui_manager:
                self.gui_manager.show_error("Connection Restored", 
                    "Network connection restored. Screen sharing may resume automatically.")
        
        except Exception as e:
            logger.error(f"Error handling connection restoration: {e}")
    
    def _on_connection_failed(self):
        """Handle permanent connection failure during screen sharing."""
        try:
            logger.error("Permanent connection failure during screen sharing")
            
            # Stop screen sharing completely
            if self.is_sharing:
                try:
                    logger.info("Stopping screen sharing due to permanent connection failure")
                    # Force local cleanup without trying to notify server
                    with self._lock:
                        self.is_sharing = False
                        self.is_presenter = False
                        self.presenter_request_pending = False
                    
                    self.screen_capture.stop_capture()
                    
                    if self.gui_manager:
                        self.gui_manager.set_screen_sharing_status(False)
                        self.gui_manager.set_presenter_status(False)
                
                except Exception as e:
                    logger.error(f"Error stopping screen sharing after connection failure: {e}")
            
            # Notify user about permanent failure
            if self.gui_manager:
                self.gui_manager.show_error("Connection Failed", 
                    "Unable to reconnect to server. Screen sharing has been stopped. Please check your network connection and try again.")
        
        except Exception as e:
            logger.error(f"Error handling connection failure: {e}")
    
    def get_screen_sharing_status(self) -> dict:
        """
        Get current screen sharing status.
        
        Returns:
            dict: Screen sharing status information
        """
        with self._lock:
            capture_stats = self.screen_capture.get_capture_stats()
            playback_stats = self.screen_playback.get_playback_stats()
            
            return {
                'is_presenter': self.is_presenter,
                'is_sharing': self.is_sharing,
                'presenter_request_pending': self.presenter_request_pending,
                'current_presenter': self.screen_playback.get_current_presenter(),
                'is_receiving_screen': self.screen_playback.is_screen_sharing_active(),
                'capture_stats': capture_stats,
                'playback_stats': playback_stats
            }
    
    def get_screen_capture_capability_info(self) -> dict:
        """
        Get screen capture capability and permission information.
        
        Returns:
            dict: Capability and permission details
        """
        return self.screen_capture.get_capability_info()
    
    def get_screen_capture_setup_instructions(self) -> list:
        """
        Get setup instructions for screen capture.
        
        Returns:
            list: List of setup instruction strings
        """
        return self.screen_capture.get_setup_instructions()
    
    def set_screen_capture_settings(self, fps: int = None, quality: int = None):
        """
        Update screen capture settings.
        
        Args:
            fps: Frames per second for screen capture
            quality: JPEG compression quality (0-100)
        """
        self.screen_capture.set_capture_settings(fps=fps, quality=quality)
    
    def get_available_windows(self) -> list:
        """
        Get list of available windows for capture.
        
        Returns:
            list: List of window information dictionaries
        """
        return self.screen_capture.get_available_windows()
    
    def set_capture_window(self, window_title: str = None) -> bool:
        """
        Set window to capture (None for full screen).
        
        Args:
            window_title: Title of window to capture, None for full screen
            
        Returns:
            bool: True if window was set successfully
        """
        return self.screen_capture.set_capture_window(window_title)
    
    def cleanup(self):
        """Clean up screen sharing resources with comprehensive error handling."""
        logger.info("Cleaning up screen sharing manager")
        
        try:
            # Stop screen sharing if active
            if self.is_sharing:
                try:
                    self.stop_screen_sharing()
                    logger.info("Screen sharing stopped during cleanup")
                except Exception as e:
                    logger.error(f"Error stopping screen sharing during cleanup: {e}")
            
            # Stop screen capture with error handling
            try:
                self.screen_capture.stop_capture()
                logger.info("Screen capture stopped during cleanup")
            except Exception as e:
                logger.error(f"Error stopping screen capture during cleanup: {e}")
            
            # Stop screen playback with error handling
            try:
                self.screen_playback.stop_receiving()
                logger.info("Screen playback stopped during cleanup")
            except Exception as e:
                logger.error(f"Error stopping screen playback during cleanup: {e}")
            
            # Reset state variables
            try:
                with self._lock:
                    self.is_presenter = False
                    self.is_sharing = False
                    self.presenter_request_pending = False
                logger.info("Screen manager state reset during cleanup")
            except Exception as e:
                logger.error(f"Error resetting state during cleanup: {e}")
            
            logger.info("Screen sharing manager cleanup complete")
        
        except Exception as e:
            error_msg = f"Unexpected error during screen sharing manager cleanup: {e}"
            logger.error(error_msg)
            
            # Force reset critical state even on error
            try:
                with self._lock:
                    self.is_presenter = False
                    self.is_sharing = False
                    self.presenter_request_pending = False
            except Exception as force_error:
                logger.error(f"Error during forced state reset: {force_error}")
            
            if self.gui_manager:
                self.gui_manager.show_error("Cleanup Error", f"Error cleaning up screen sharing: {e}")