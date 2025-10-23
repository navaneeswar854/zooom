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
        
        # Start screen playback (always ready to receive)
        self.screen_playback.start_receiving()
    
    def request_presenter_role(self):
        """Request presenter role from server."""
        if not self.connection_manager:
            logger.error("Cannot request presenter role: no connection manager")
            return
        
        with self._lock:
            if self.is_presenter:
                logger.info("Already presenter, releasing presenter role")
                self._release_presenter_role()
                return
            
            if self.presenter_request_pending:
                logger.warning("Presenter request already pending")
                return
            
            self.presenter_request_pending = True
        
        success = self.connection_manager.request_presenter_role()
        
        if success:
            logger.info("Presenter role request sent")
            # Set a timeout to reset pending flag if no response
            threading.Timer(10.0, self._reset_presenter_request_timeout).start()
        else:
            logger.error("Failed to send presenter role request")
            with self._lock:
                self.presenter_request_pending = False
    
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
        """Start screen sharing (must be presenter)."""
        with self._lock:
            if not self.is_presenter:
                logger.error("Cannot start screen sharing: not presenter")
                if self.gui_manager:
                    self.gui_manager.handle_presenter_denied("You must be the presenter to share your screen")
                return False
            
            if self.is_sharing:
                logger.warning("Screen sharing already active")
                return True
        
        # Send start message to server first
        if self.connection_manager:
            success = self.connection_manager.start_screen_sharing()
            if not success:
                logger.error("Failed to send screen sharing start message")
                return False
            
            # Wait for server confirmation before starting capture
            logger.info("Waiting for server confirmation to start screen capture...")
            return True  # Actual capture will start when server confirms
        else:
            logger.error("No connection manager available")
            return False
    
    def stop_screen_sharing(self):
        """Stop screen sharing."""
        with self._lock:
            if not self.is_sharing:
                logger.warning("Screen sharing not active")
                return
            
            self.is_sharing = False
        
        # Stop screen capture
        self.screen_capture.stop_capture()
        
        # Send stop message to server
        if self.connection_manager:
            self.connection_manager.stop_screen_sharing()
        
        # Update GUI
        if self.gui_manager:
            self.gui_manager.set_screen_sharing_status(False)
        
        logger.info("Screen sharing stopped")
    
    def handle_presenter_granted(self):
        """Handle presenter role being granted by server."""
        with self._lock:
            self.is_presenter = True
            self.presenter_request_pending = False
        
        # Update GUI
        if self.gui_manager:
            self.gui_manager.handle_presenter_granted()
        
        logger.info("Presenter role granted - you can now start screen sharing")
        
        # Automatically start screen sharing after getting presenter role
        logger.info("Auto-starting screen sharing after presenter role granted")
        self.start_screen_sharing()
    
    def handle_screen_share_confirmed(self):
        """Handle server confirmation to start screen sharing."""
        logger.info("Server confirmed screen sharing - starting capture")
        
        # Now actually start screen capture
        success = self.screen_capture.start_capture()
        
        if success:
            with self._lock:
                self.is_sharing = True
            
            # Update GUI
            if self.gui_manager:
                self.gui_manager.set_screen_sharing_status(True)
            
            logger.info("Screen capture started successfully")
        else:
            logger.error("Failed to start screen capture after server confirmation")
            # Notify server that we failed to start
            if self.connection_manager:
                self.connection_manager.stop_screen_sharing()
    
    def handle_presenter_denied(self, reason: str = ""):
        """Handle presenter role being denied by server."""
        with self._lock:
            self.presenter_request_pending = False
        
        # Update GUI
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
        """Handle incoming screen share message."""
        try:
            if message.msg_type == MessageType.SCREEN_SHARE.value:
                # Process screen frame
                self.screen_playback.process_screen_message(message)
            
            elif message.msg_type == MessageType.SCREEN_SHARE_START.value:
                # Someone started screen sharing
                presenter_id = message.sender_id
                if self.gui_manager:
                    self.gui_manager.handle_screen_share_started(f"Client {presenter_id}")
            
            elif message.msg_type == MessageType.SCREEN_SHARE_STOP.value:
                # Someone stopped screen sharing
                if self.gui_manager:
                    self.gui_manager.handle_screen_share_stopped()
            
            elif message.msg_type == MessageType.PRESENTER_GRANTED.value:
                # Presenter role granted
                presenter_id = message.data.get('presenter_id')
                if presenter_id == self.client_id:
                    self.handle_presenter_granted()
            
            elif message.msg_type == MessageType.PRESENTER_DENIED.value:
                # Presenter role denied
                reason = message.data.get('reason', '')
                self.handle_presenter_denied(reason)
        
        except Exception as e:
            logger.error(f"Error handling screen share message: {e}")
    
    def _on_screen_frame_received(self, frame_data, presenter_id: str):
        """Callback for when screen frame is received."""
        try:
            # Update GUI with screen frame
            if self.gui_manager:
                self.gui_manager.display_screen_frame(frame_data, presenter_id)
        
        except Exception as e:
            logger.error(f"Error handling received screen frame: {e}")
    
    def _on_presenter_changed(self, presenter_id: Optional[str]):
        """Callback for when presenter changes."""
        try:
            # Update GUI with presenter change
            if self.gui_manager:
                presenter_name = f"Client {presenter_id}" if presenter_id else None
                self.gui_manager.update_screen_sharing_presenter(presenter_name)
        
        except Exception as e:
            logger.error(f"Error handling presenter change: {e}")
    
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
        """Clean up screen sharing resources."""
        logger.info("Cleaning up screen sharing manager")
        
        # Stop screen sharing if active
        if self.is_sharing:
            self.stop_screen_sharing()
        
        # Stop screen capture and playback
        self.screen_capture.stop_capture()
        self.screen_playback.stop_receiving()
        
        logger.info("Screen sharing manager cleanup complete")