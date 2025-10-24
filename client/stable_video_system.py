"""
Stable Video System
Ultra-stable video conferencing with zero flickering and interface stability.
Addresses all root causes of shaking and flickering.
"""

import threading
import time
import logging
import queue
import numpy as np
from typing import Dict, Optional, Callable, Any
from collections import deque
import tkinter as tk
from PIL import Image, ImageTk
import cv2

logger = logging.getLogger(__name__)


class StableFrameBuffer:
    """
    Stable frame buffer that prevents flickering through intelligent buffering.
    """
    
    def __init__(self, client_id: str):
        self.client_id = client_id
        self.current_frame = None
        self.frame_lock = threading.RLock()
        
        # Stability settings
        self.min_update_interval = 1.0 / 30  # 30 FPS max to prevent shaking
        self.last_update_time = 0
        self.frame_ready = False
        
        # Error handling
        self.consecutive_errors = 0
        self.max_errors = 5
        self.error_recovery_delay = 1.0
        
    def add_frame(self, frame: np.ndarray) -> bool:
        """Add frame with stability checks."""
        try:
            current_time = time.time()
            
            # Prevent too frequent updates
            if current_time - self.last_update_time < self.min_update_interval:
                return False
            
            with self.frame_lock:
                self.current_frame = frame.copy()
                self.frame_ready = True
                self.last_update_time = current_time
                self.consecutive_errors = 0  # Reset error count on success
                
            return True
            
        except Exception as e:
            self.consecutive_errors += 1
            logger.warning(f"Frame buffer error for {self.client_id}: {e}")
            
            # Error recovery
            if self.consecutive_errors >= self.max_errors:
                logger.error(f"Too many errors for {self.client_id}, entering recovery mode")
                time.sleep(self.error_recovery_delay)
                self.consecutive_errors = 0
            
            return False
    
    def get_frame(self) -> Optional[np.ndarray]:
        """Get stable frame for display."""
        try:
            with self.frame_lock:
                if self.frame_ready and self.current_frame is not None:
                    return self.current_frame.copy()
                return None
        except Exception as e:
            logger.warning(f"Frame retrieval error for {self.client_id}: {e}")
            return None


class StableVideoRenderer:
    """
    Stable video renderer that prevents interface shaking and flickering.
    """
    
    def __init__(self):
        self.frame_buffers: Dict[str, StableFrameBuffer] = {}
        self.video_widgets: Dict[str, Dict[str, Any]] = {}
        self.render_lock = threading.RLock()
        
        # Stability settings
        self.stable_update_rate = 1.0 / 25  # 25 FPS for stability
        self.widget_reuse = True  # Reuse widgets instead of destroying
        self.error_handling = True
        
        # Error tracking
        self.client_errors: Dict[str, int] = {}
        self.max_client_errors = 10
        
    def register_client(self, client_id: str, video_slot: Dict[str, Any]):
        """Register client with stable video slot."""
        try:
            with self.render_lock:
                # Create stable frame buffer
                self.frame_buffers[client_id] = StableFrameBuffer(client_id)
                
                # Initialize video widget info
                self.video_widgets[client_id] = {
                    'slot': video_slot,
                    'widget': None,
                    'last_update': 0,
                    'stable': True
                }
                
                # Reset error count
                self.client_errors[client_id] = 0
                
                logger.info(f"Registered stable video for client {client_id}")
                
        except Exception as e:
            logger.error(f"Error registering client {client_id}: {e}")
    
    def update_video_stable(self, client_id: str, frame: np.ndarray) -> bool:
        """Update video with maximum stability."""
        try:
            if client_id not in self.frame_buffers:
                logger.warning(f"Client {client_id} not registered for stable video")
                return False
            
            # Add frame to stable buffer
            if not self.frame_buffers[client_id].add_frame(frame):
                return False  # Frame rejected for stability
            
            # Check if widget update is needed
            current_time = time.time()
            widget_info = self.video_widgets.get(client_id)
            
            if not widget_info:
                return False
            
            # Prevent too frequent widget updates
            if current_time - widget_info['last_update'] < self.stable_update_rate:
                return False
            
            # Get stable frame
            stable_frame = self.frame_buffers[client_id].get_frame()
            if stable_frame is None:
                return False
            
            # Update widget safely
            success = self._update_widget_stable(client_id, stable_frame)
            
            if success:
                widget_info['last_update'] = current_time
                self.client_errors[client_id] = 0  # Reset error count
            else:
                self._handle_client_error(client_id)
            
            return success
            
        except Exception as e:
            logger.error(f"Stable video update error for {client_id}: {e}")
            self._handle_client_error(client_id)
            return False
    
    def _update_widget_stable(self, client_id: str, frame: np.ndarray) -> bool:
        """Update widget with maximum stability - no destruction."""
        try:
            widget_info = self.video_widgets[client_id]
            slot = widget_info['slot']
            
            if not self._widget_exists(slot['frame']):
                logger.warning(f"Video slot frame for {client_id} no longer exists")
                return False
            
            # Convert frame to display format
            display_image = self._prepare_display_image(frame)
            if display_image is None:
                return False
            
            # Reuse existing widget or create new one
            if widget_info['widget'] is None or not self._widget_exists(widget_info['widget']):
                # Create new widget only if necessary
                widget_info['widget'] = self._create_video_widget(slot['frame'], display_image, client_id)
            else:
                # Update existing widget - much more stable
                try:
                    widget_info['widget'].configure(image=display_image)
                    widget_info['widget'].image = display_image  # Keep reference
                except Exception as e:
                    logger.warning(f"Widget update failed for {client_id}: {e}")
                    # Recreate widget as fallback
                    widget_info['widget'] = self._create_video_widget(slot['frame'], display_image, client_id)
            
            return True
            
        except Exception as e:
            logger.error(f"Widget update error for {client_id}: {e}")
            return False
    
    def _create_video_widget(self, parent_frame, display_image, client_id: str):
        """Create video widget safely."""
        try:
            # Clear parent frame only if necessary
            if len(parent_frame.winfo_children()) > 2:  # Only clear if too many widgets
                for child in parent_frame.winfo_children():
                    if isinstance(child, tk.Label) and hasattr(child, 'image'):
                        child.destroy()
            
            # Create video widget
            video_widget = tk.Label(
                parent_frame,
                image=display_image,
                bg='black',
                relief='flat'
            )
            video_widget.pack(fill='both', expand=True)
            video_widget.image = display_image  # Keep reference
            
            # Create name label if not exists
            name_labels = [child for child in parent_frame.winfo_children() 
                          if isinstance(child, tk.Label) and not hasattr(child, 'image')]
            
            if not name_labels:
                name_text = "You (Local)" if client_id == 'local' else f"Client {client_id[:8]}"
                name_label = tk.Label(
                    parent_frame,
                    text=name_text,
                    fg='lightgreen' if client_id == 'local' else 'lightblue',
                    bg='black',
                    font=('Arial', 8)
                )
                name_label.pack(side='bottom')
            
            return video_widget
            
        except Exception as e:
            logger.error(f"Error creating video widget for {client_id}: {e}")
            return None
    
    def _prepare_display_image(self, frame: np.ndarray) -> Optional[ImageTk.PhotoImage]:
        """Prepare frame for display with error handling."""
        try:
            if frame is None or frame.size == 0:
                return None
            
            # Convert BGR to RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Convert to PIL Image
            pil_image = Image.fromarray(rgb_frame)
            
            # Resize with high quality for stability
            display_size = (200, 150)
            pil_image = pil_image.resize(display_size, Image.LANCZOS)
            
            # Convert to PhotoImage
            photo = ImageTk.PhotoImage(pil_image)
            
            return photo
            
        except Exception as e:
            logger.error(f"Error preparing display image: {e}")
            return None
    
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
    
    def _handle_client_error(self, client_id: str):
        """Handle client errors with recovery."""
        try:
            self.client_errors[client_id] = self.client_errors.get(client_id, 0) + 1
            
            if self.client_errors[client_id] >= self.max_client_errors:
                logger.warning(f"Too many errors for {client_id}, disabling temporarily")
                
                # Disable client temporarily
                if client_id in self.video_widgets:
                    widget_info = self.video_widgets[client_id]
                    if widget_info['widget'] and self._widget_exists(widget_info['widget']):
                        widget_info['widget'].configure(image='', text='Video Error\nRecovering...')
                
                # Reset after delay
                threading.Timer(2.0, lambda: self._reset_client_errors(client_id)).start()
                
        except Exception as e:
            logger.error(f"Error handling client error for {client_id}: {e}")
    
    def _reset_client_errors(self, client_id: str):
        """Reset client error count."""
        try:
            self.client_errors[client_id] = 0
            logger.info(f"Reset error count for {client_id}")
        except Exception as e:
            logger.error(f"Error resetting client errors for {client_id}: {e}")
    
    def unregister_client(self, client_id: str):
        """Unregister client safely."""
        try:
            with self.render_lock:
                # Clean up frame buffer
                if client_id in self.frame_buffers:
                    del self.frame_buffers[client_id]
                
                # Clean up widget info
                if client_id in self.video_widgets:
                    widget_info = self.video_widgets[client_id]
                    if widget_info['widget'] and self._widget_exists(widget_info['widget']):
                        widget_info['widget'].destroy()
                    del self.video_widgets[client_id]
                
                # Clean up error tracking
                if client_id in self.client_errors:
                    del self.client_errors[client_id]
                
                logger.info(f"Unregistered stable video for client {client_id}")
                
        except Exception as e:
            logger.error(f"Error unregistering client {client_id}: {e}")


class StabilityManager:
    """
    Main stability manager for video conferencing system.
    """
    
    def __init__(self):
        self.video_renderer = StableVideoRenderer()
        self.stability_active = False
        self.stability_lock = threading.RLock()
        
        # Stability settings
        self.max_fps = 25  # Limit FPS for stability
        self.error_recovery = True
        self.widget_reuse = True
        
        # Performance monitoring
        self.frame_count = 0
        self.error_count = 0
        self.start_time = time.time()
    
    def enable_stability(self):
        """Enable stability system."""
        try:
            with self.stability_lock:
                self.stability_active = True
                self.start_time = time.time()
                logger.info("Video stability system enabled")
        except Exception as e:
            logger.error(f"Error enabling stability: {e}")
    
    def disable_stability(self):
        """Disable stability system."""
        try:
            with self.stability_lock:
                self.stability_active = False
                logger.info("Video stability system disabled")
        except Exception as e:
            logger.error(f"Error disabling stability: {e}")
    
    def register_video_slot(self, client_id: str, video_slot: Dict[str, Any]):
        """Register video slot for stable rendering."""
        try:
            if not self.stability_active:
                self.enable_stability()
            
            self.video_renderer.register_client(client_id, video_slot)
            logger.info(f"Registered stable video slot for {client_id}")
            
        except Exception as e:
            logger.error(f"Error registering video slot for {client_id}: {e}")
    
    def update_video_frame(self, client_id: str, frame: np.ndarray) -> bool:
        """Update video frame with stability."""
        try:
            if not self.stability_active:
                return False
            
            success = self.video_renderer.update_video_stable(client_id, frame)
            
            if success:
                self.frame_count += 1
            else:
                self.error_count += 1
            
            return success
            
        except Exception as e:
            logger.error(f"Error updating video frame for {client_id}: {e}")
            self.error_count += 1
            return False
    
    def remove_video_slot(self, client_id: str):
        """Remove video slot safely."""
        try:
            self.video_renderer.unregister_client(client_id)
            logger.info(f"Removed stable video slot for {client_id}")
        except Exception as e:
            logger.error(f"Error removing video slot for {client_id}: {e}")
    
    def get_stability_stats(self) -> Dict[str, Any]:
        """Get stability statistics."""
        try:
            uptime = time.time() - self.start_time
            fps = self.frame_count / uptime if uptime > 0 else 0
            error_rate = self.error_count / max(self.frame_count, 1)
            
            return {
                'active': self.stability_active,
                'uptime': uptime,
                'frames_processed': self.frame_count,
                'errors': self.error_count,
                'fps': fps,
                'error_rate': error_rate,
                'stability_score': max(0, 1.0 - error_rate)
            }
        except Exception as e:
            logger.error(f"Error getting stability stats: {e}")
            return {'active': False, 'error': str(e)}


# Global stability manager
stability_manager = StabilityManager()