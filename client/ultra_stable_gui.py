"""
Ultra Stable GUI System
Completely eliminates interface shaking and video flickering.
"""

import threading
import time
import logging
import tkinter as tk
from PIL import Image, ImageTk
import cv2
import numpy as np
from typing import Dict, Optional, Any
from collections import deque

logger = logging.getLogger(__name__)


class UltraStableVideoWidget:
    """
    Ultra-stable video widget that never causes interface shaking.
    """
    
    def __init__(self, parent_frame, client_id: str):
        self.parent_frame = parent_frame
        self.client_id = client_id
        
        # Widget state
        self.video_label = None
        self.name_label = None
        self.is_initialized = False
        
        # Stability controls
        self.update_lock = threading.RLock()
        self.last_update_time = 0
        self.min_update_interval = 1.0 / 20  # 20 FPS max for stability
        
        # Frame management
        self.current_photo = None
        self.pending_frame = None
        self.frame_queue = deque(maxlen=2)  # Very small queue
        
        # Error handling
        self.consecutive_errors = 0
        self.max_errors = 3
        self.is_error_state = False
        
        # Initialize widget
        self._initialize_widget()
    
    def _initialize_widget(self):
        """Initialize the video widget once."""
        try:
            with self.update_lock:
                if self.is_initialized:
                    return
                
                # Clear parent frame completely
                self._clear_parent_safely()
                
                # Create video label
                self.video_label = tk.Label(
                    self.parent_frame,
                    bg='black',
                    relief='flat',
                    borderwidth=0
                )
                self.video_label.pack(fill='both', expand=True)
                
                # Create name label
                name_text = "You (Local)" if self.client_id == 'local' else f"Client {self.client_id[:8]}"
                self.name_label = tk.Label(
                    self.parent_frame,
                    text=name_text,
                    fg='lightgreen' if self.client_id == 'local' else 'lightblue',
                    bg='black',
                    font=('Arial', 8),
                    relief='flat'
                )
                self.name_label.pack(side='bottom')
                
                self.is_initialized = True
                logger.debug(f"Initialized ultra-stable widget for {self.client_id}")
                
        except Exception as e:
            logger.error(f"Error initializing widget for {self.client_id}: {e}")
            self.is_error_state = True
    
    def update_frame(self, frame: np.ndarray) -> bool:
        """Update frame with ultra-stability."""
        try:
            current_time = time.time()
            
            # Rate limiting for stability
            if current_time - self.last_update_time < self.min_update_interval:
                # Queue frame for later processing
                self.frame_queue.append(frame.copy())
                return False
            
            with self.update_lock:
                if not self.is_initialized or self.is_error_state:
                    return False
                
                # Process frame
                photo = self._prepare_frame(frame)
                if photo is None:
                    self._handle_error("Frame preparation failed")
                    return False
                
                # Update widget - NEVER destroy, only update
                if self._widget_exists(self.video_label):
                    try:
                        self.video_label.configure(image=photo)
                        self.video_label.image = photo  # Keep reference
                        self.current_photo = photo
                        
                        self.last_update_time = current_time
                        self.consecutive_errors = 0
                        self.is_error_state = False
                        
                        return True
                        
                    except Exception as e:
                        self._handle_error(f"Widget update failed: {e}")
                        return False
                else:
                    # Widget destroyed, reinitialize
                    self._reinitialize_widget()
                    return False
                    
        except Exception as e:
            self._handle_error(f"Frame update error: {e}")
            return False
    
    def _prepare_frame(self, frame: np.ndarray) -> Optional[ImageTk.PhotoImage]:
        """Prepare frame for display with error handling."""
        try:
            if frame is None or frame.size == 0:
                return None
            
            # Convert BGR to RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Convert to PIL Image
            pil_image = Image.fromarray(rgb_frame)
            
            # Resize for display
            display_size = (200, 150)
            pil_image = pil_image.resize(display_size, Image.LANCZOS)
            
            # Convert to PhotoImage
            photo = ImageTk.PhotoImage(pil_image)
            
            return photo
            
        except Exception as e:
            logger.error(f"Frame preparation error for {self.client_id}: {e}")
            return None
    
    def _clear_parent_safely(self):
        """Clear parent frame safely without causing shaking."""
        try:
            # Only clear if there are widgets to clear
            children = self.parent_frame.winfo_children()
            if children:
                for child in children:
                    try:
                        child.destroy()
                    except:
                        pass  # Ignore destruction errors
        except Exception as e:
            logger.warning(f"Error clearing parent for {self.client_id}: {e}")
    
    def _widget_exists(self, widget) -> bool:
        """Check if widget exists safely."""
        try:
            if widget is None:
                return False
            return widget.winfo_exists()
        except (tk.TclError, AttributeError):
            return False
        except Exception:
            return False
    
    def _handle_error(self, error_msg: str):
        """Handle errors with recovery."""
        try:
            self.consecutive_errors += 1
            logger.warning(f"Widget error for {self.client_id}: {error_msg}")
            
            if self.consecutive_errors >= self.max_errors:
                self.is_error_state = True
                self._show_error_message(error_msg)
                
                # Schedule recovery
                threading.Timer(2.0, self._recover_from_error).start()
                
        except Exception as e:
            logger.error(f"Error handling error for {self.client_id}: {e}")
    
    def _show_error_message(self, error_msg: str):
        """Show error message in widget."""
        try:
            if self._widget_exists(self.video_label):
                self.video_label.configure(
                    image='',
                    text=f"Video Error\n{self.client_id}\nRecovering...",
                    fg='red',
                    compound='center'
                )
        except Exception as e:
            logger.error(f"Error showing error message for {self.client_id}: {e}")
    
    def _recover_from_error(self):
        """Recover from error state."""
        try:
            with self.update_lock:
                self.consecutive_errors = 0
                self.is_error_state = False
                
                # Try to reinitialize if needed
                if not self._widget_exists(self.video_label):
                    self.is_initialized = False
                    self._initialize_widget()
                
                logger.info(f"Recovered from error for {self.client_id}")
                
        except Exception as e:
            logger.error(f"Error recovering for {self.client_id}: {e}")
    
    def _reinitialize_widget(self):
        """Reinitialize widget if destroyed."""
        try:
            with self.update_lock:
                self.is_initialized = False
                self.video_label = None
                self.name_label = None
                self._initialize_widget()
        except Exception as e:
            logger.error(f"Error reinitializing widget for {self.client_id}: {e}")
    
    def destroy(self):
        """Destroy widget safely."""
        try:
            with self.update_lock:
                if self._widget_exists(self.video_label):
                    self.video_label.destroy()
                if self._widget_exists(self.name_label):
                    self.name_label.destroy()
                
                self.is_initialized = False
                self.video_label = None
                self.name_label = None
                
        except Exception as e:
            logger.error(f"Error destroying widget for {self.client_id}: {e}")


class UltraStableVideoManager:
    """
    Ultra-stable video manager that completely prevents interface shaking.
    """
    
    def __init__(self):
        self.video_widgets: Dict[str, UltraStableVideoWidget] = {}
        self.video_slots: Dict[str, Dict[str, Any]] = {}
        self.manager_lock = threading.RLock()
        
        # Stability settings
        self.global_update_rate = 1.0 / 15  # 15 FPS global limit
        self.last_global_update = 0
        
        # Frame processing
        self.frame_processor_thread = None
        self.frame_queue = deque(maxlen=10)
        self.processing_active = False
        
        # Start frame processor
        self._start_frame_processor()
    
    def register_video_slot(self, client_id: str, video_slot: Dict[str, Any]):
        """Register video slot for ultra-stable rendering."""
        try:
            with self.manager_lock:
                self.video_slots[client_id] = video_slot
                
                # Create ultra-stable widget
                if client_id not in self.video_widgets:
                    widget = UltraStableVideoWidget(video_slot['frame'], client_id)
                    self.video_widgets[client_id] = widget
                    
                    logger.info(f"Registered ultra-stable video for {client_id}")
                
        except Exception as e:
            logger.error(f"Error registering video slot for {client_id}: {e}")
    
    def update_video_frame(self, client_id: str, frame: np.ndarray) -> bool:
        """Update video frame with ultra-stability."""
        try:
            current_time = time.time()
            
            # Global rate limiting
            if current_time - self.last_global_update < self.global_update_rate:
                # Queue frame for processing
                self.frame_queue.append((client_id, frame.copy(), current_time))
                return False
            
            with self.manager_lock:
                if client_id not in self.video_widgets:
                    return False
                
                widget = self.video_widgets[client_id]
                success = widget.update_frame(frame)
                
                if success:
                    self.last_global_update = current_time
                
                return success
                
        except Exception as e:
            logger.error(f"Error updating video frame for {client_id}: {e}")
            return False
    
    def _start_frame_processor(self):
        """Start background frame processor."""
        try:
            self.processing_active = True
            self.frame_processor_thread = threading.Thread(
                target=self._process_frame_queue,
                daemon=True
            )
            self.frame_processor_thread.start()
            logger.info("Started ultra-stable frame processor")
        except Exception as e:
            logger.error(f"Error starting frame processor: {e}")
    
    def _process_frame_queue(self):
        """Process queued frames in background."""
        while self.processing_active:
            try:
                if self.frame_queue:
                    client_id, frame, timestamp = self.frame_queue.popleft()
                    
                    # Process frame if not too old
                    if time.time() - timestamp < 0.5:  # 500ms max age
                        self.update_video_frame(client_id, frame)
                
                time.sleep(1.0 / 30)  # 30 FPS processing rate
                
            except Exception as e:
                logger.error(f"Error in frame processor: {e}")
                time.sleep(0.1)
    
    def unregister_video_slot(self, client_id: str):
        """Unregister video slot safely."""
        try:
            with self.manager_lock:
                if client_id in self.video_widgets:
                    widget = self.video_widgets[client_id]
                    widget.destroy()
                    del self.video_widgets[client_id]
                
                if client_id in self.video_slots:
                    del self.video_slots[client_id]
                
                logger.info(f"Unregistered ultra-stable video for {client_id}")
                
        except Exception as e:
            logger.error(f"Error unregistering video slot for {client_id}: {e}")
    
    def shutdown(self):
        """Shutdown manager safely."""
        try:
            self.processing_active = False
            
            if self.frame_processor_thread and self.frame_processor_thread.is_alive():
                self.frame_processor_thread.join(timeout=1.0)
            
            # Clean up all widgets
            with self.manager_lock:
                for client_id in list(self.video_widgets.keys()):
                    self.unregister_video_slot(client_id)
            
            logger.info("Ultra-stable video manager shutdown complete")
            
        except Exception as e:
            logger.error(f"Error shutting down video manager: {e}")


# Global ultra-stable video manager
ultra_stable_manager = UltraStableVideoManager()