"""
GUI Manager for the collaboration client.
Creates and manages the unified dashboard with all collaboration modules.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import threading
import logging
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ModuleFrame(ttk.Frame):
    """Base class for module frames in the dashboard."""
    
    def __init__(self, parent, title: str):
        super().__init__(parent, relief='ridge', borderwidth=2)
        self.title = title
        self.enabled = False
        
        # Create title label
        self.title_label = ttk.Label(self, text=title, font=('Arial', 12, 'bold'))
        self.title_label.pack(pady=5)
        
        # Status indicator
        self.status_frame = ttk.Frame(self)
        self.status_frame.pack(fill='x', padx=5)
        
        self.status_indicator = tk.Canvas(self.status_frame, width=12, height=12)
        self.status_indicator.pack(side='left')
        
        self.status_label = ttk.Label(self.status_frame, text="Inactive")
        self.status_label.pack(side='left', padx=(5, 0))
        
        self._update_status_indicator()
    
    def set_enabled(self, enabled: bool):
        """Set module enabled state."""
        self.enabled = enabled
        self._update_status_indicator()
    
    def _update_status_indicator(self):
        """Update the visual status indicator."""
        self.status_indicator.delete("all")
        color = "green" if self.enabled else "red"
        self.status_indicator.create_oval(2, 2, 10, 10, fill=color, outline=color)
        
        status_text = "Active" if self.enabled else "Inactive"
        self.status_label.config(text=status_text)


class VideoFrame(ModuleFrame):
    """Video conferencing module frame with large grid layout."""
    
    def __init__(self, parent):
        super().__init__(parent, "Video Conference")
        
        # Video controls at top
        self.controls_frame = ttk.Frame(self)
        self.controls_frame.pack(fill='x', padx=5, pady=5)
        
        self.video_button = ttk.Button(
            self.controls_frame, 
            text="Enable Video", 
            command=self._toggle_video
        )
        self.video_button.pack(side='left', padx=2)
        
        # Video quality indicator
        self.quality_label = ttk.Label(self.controls_frame, text="Quality: Auto")
        self.quality_label.pack(side='right', padx=5)
        
        # Large video display area with grid layout
        self.video_display = tk.Frame(self, bg='#2c2c2c')
        self.video_display.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Configure grid for responsive video layout
        for i in range(2):  # 2x2 grid for up to 4 participants
            self.video_display.rowconfigure(i, weight=1)
            self.video_display.columnconfigure(i, weight=1)
        
        # Create video slots
        self.video_slots = {}
        self._create_video_slots()
        
        # Callbacks
        self.video_callback: Optional[Callable[[bool], None]] = None
        self.participant_videos = {}  # Track participant video states
    
    def set_video_callback(self, callback: Callable[[bool], None]):
        """Set callback for video toggle events."""
        self.video_callback = callback
    
    def _toggle_video(self):
        """Toggle video on/off."""
        self.enabled = not self.enabled
        self._update_status_indicator()
        
        button_text = "Disable Video" if self.enabled else "Enable Video"
        self.video_button.config(text=button_text)
        
        if self.video_callback:
            self.video_callback(self.enabled)
    
    def _create_video_slots(self):
        """Create video slots in a 2x2 grid."""
        positions = [(0, 0), (0, 1), (1, 0), (1, 1)]
        
        for i, (row, col) in enumerate(positions):
            slot_frame = tk.Frame(self.video_display, bg='black', relief='solid', borderwidth=1)
            slot_frame.grid(row=row, column=col, sticky='nsew', padx=2, pady=2)
            
            # Placeholder content
            placeholder_label = tk.Label(
                slot_frame, 
                text=f"Video Slot {i+1}\nNo participant", 
                fg='white', 
                bg='black',
                font=('Arial', 12)
            )
            placeholder_label.pack(expand=True)
            
            self.video_slots[i] = {
                'frame': slot_frame,
                'label': placeholder_label,
                'participant_id': None,
                'active': False
            }
    
    def update_video_feeds(self, participants: Dict[str, Any]):
        """Update video feed display with participant information."""
        # Update video slots with participant information
        active_participants = [p for p in participants.values() 
                             if p.get('video_enabled', False)]
        
        # Update each slot
        for slot_id, slot in self.video_slots.items():
            if slot_id < len(active_participants):
                participant = active_participants[slot_id]
                participant_name = participant.get('username', 'Unknown')
                
                # Update slot with participant info
                slot['label'].config(
                    text=f"{participant_name}\n{'🎥 Video Active' if participant.get('video_enabled') else '📷 Video Off'}",
                    fg='lightgreen' if participant.get('video_enabled') else 'lightgray'
                )
                slot['participant_id'] = participant.get('client_id')
                slot['active'] = True
            else:
                # Empty slot
                slot['label'].config(
                    text=f"Video Slot {slot_id+1}\nNo participant",
                    fg='white'
                )
                slot['participant_id'] = None
                slot['active'] = False
        # Get list of clients with active video
        active_video_clients = [client_id for client_id, participant in participants.items() 
                               if participant.get('video_enabled', False)]
        
        # Create dynamic grid layout
        self.create_dynamic_video_grid(active_video_clients)
    
    def update_local_video(self, frame):
        """Update local video display with captured frame."""
        try:
            # This is a placeholder for local video display
            # In a full implementation, you would convert the OpenCV frame
            # to a format suitable for tkinter display (PIL Image -> PhotoImage)
            # For now, we'll just indicate that video is active
            pass
        except Exception as e:
            logger.error(f"Error updating local video: {e}")
    
    def update_remote_video(self, client_id: str, frame):
        """Update remote video display with incoming frame."""
        try:
            # This is a placeholder for remote video display
            # In a full implementation, you would:
            # 1. Convert OpenCV frame to PIL Image
            # 2. Resize frame to fit in grid layout
            # 3. Convert to PhotoImage for tkinter
            # 4. Update the appropriate video feed widget
            # For now, we'll just log that video is being received
            logger.debug(f"Received video frame from client {client_id}")
        except Exception as e:
            logger.error(f"Error updating remote video: {e}")
    
    def create_dynamic_video_grid(self, active_video_clients: list):
        """Create dynamic grid layout for multiple video feeds."""
        try:
            # Clear existing display
            for widget in self.video_display.winfo_children():
                widget.destroy()
            
            if not active_video_clients:
                self.video_label = ttk.Label(self.video_display, text="No active video feeds")
                self.video_label.pack(expand=True)
                return
            
            # Calculate grid dimensions based on number of clients
            num_clients = len(active_video_clients)
            if num_clients == 1:
                rows, cols = 1, 1
            elif num_clients <= 4:
                rows, cols = 2, 2
            elif num_clients <= 6:
                rows, cols = 2, 3
            elif num_clients <= 9:
                rows, cols = 3, 3
            else:
                rows, cols = 4, 4  # Maximum 16 video feeds
            
            # Create grid of video feed frames
            for i, client_id in enumerate(active_video_clients[:16]):  # Limit to 16 feeds
                row = i // cols
                col = i % cols
                
                # Create frame for this video feed
                feed_frame = tk.Frame(self.video_display, bg='black', relief='sunken', bd=1)
                feed_frame.grid(row=row, column=col, sticky='nsew', padx=1, pady=1)
                
                # Configure grid weights for proper resizing
                self.video_display.grid_rowconfigure(row, weight=1)
                self.video_display.grid_columnconfigure(col, weight=1)
                
                # Add client identifier label
                client_label = ttk.Label(feed_frame, text=f"Client {client_id}", 
                                       background='black', foreground='white')
                client_label.pack(side='bottom')
                
                # Add placeholder for video content
                video_placeholder = tk.Label(feed_frame, text="Video Feed", 
                                           bg='gray', fg='white')
                video_placeholder.pack(fill='both', expand=True)
        
        except Exception as e:
            logger.error(f"Error creating video grid: {e}")


class AudioFrame(ModuleFrame):
    """Audio conferencing module frame."""
    
    def __init__(self, parent):
        super().__init__(parent, "Audio Conference")
        
        # Audio controls
        self.controls_frame = ttk.Frame(self)
        self.controls_frame.pack(fill='x', padx=5, pady=5)
        
        self.audio_button = ttk.Button(
            self.controls_frame, 
            text="Enable Audio", 
            command=self._toggle_audio
        )
        self.audio_button.pack(side='left', padx=2)
        
        self.mute_button = ttk.Button(
            self.controls_frame, 
            text="Mute", 
            command=self._toggle_mute,
            state='disabled'
        )
        self.mute_button.pack(side='left', padx=2)
        
        # Audio level indicator
        self.level_frame = ttk.Frame(self)
        self.level_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(self.level_frame, text="Audio Level:").pack(side='left')
        
        self.level_bar = ttk.Progressbar(
            self.level_frame, 
            length=100, 
            mode='determinate'
        )
        self.level_bar.pack(side='left', padx=(5, 0), fill='x', expand=True)
        
        # Audio status
        self.audio_status = ttk.Label(self, text="Audio inactive")
        self.audio_status.pack(pady=5)
        
        # State
        self.muted = False
        
        # Callbacks
        self.audio_callback: Optional[Callable[[bool], None]] = None
        self.mute_callback: Optional[Callable[[bool], None]] = None
    
    def set_audio_callback(self, callback: Callable[[bool], None]):
        """Set callback for audio toggle events."""
        self.audio_callback = callback
    
    def set_mute_callback(self, callback: Callable[[bool], None]):
        """Set callback for mute toggle events."""
        self.mute_callback = callback
    
    def _toggle_audio(self):
        """Toggle audio on/off."""
        self.enabled = not self.enabled
        self._update_status_indicator()
        
        button_text = "Disable Audio" if self.enabled else "Enable Audio"
        self.audio_button.config(text=button_text)
        
        # Enable/disable mute button
        mute_state = 'normal' if self.enabled else 'disabled'
        self.mute_button.config(state=mute_state)
        
        # Update status
        if self.enabled:
            status_text = "Muted" if self.muted else "Active"
        else:
            status_text = "Inactive"
        self.audio_status.config(text=f"Audio {status_text}")
        
        if self.audio_callback:
            self.audio_callback(self.enabled and not self.muted)
    
    def _toggle_mute(self):
        """Toggle mute on/off."""
        self.muted = not self.muted
        
        button_text = "Unmute" if self.muted else "Mute"
        self.mute_button.config(text=button_text)
        
        status_text = "Muted" if self.muted else "Active"
        self.audio_status.config(text=f"Audio {status_text}")
        
        # Call separate mute callback if available
        if self.mute_callback:
            self.mute_callback(self.muted)
        
        # Also call audio callback for overall state
        if self.audio_callback:
            self.audio_callback(self.enabled and not self.muted)
    
    def update_audio_level(self, level: float):
        """Update audio level indicator (0.0 to 1.0)."""
        self.level_bar['value'] = level * 100


class ChatFrame(ModuleFrame):
    """Group chat module frame with chronological message ordering and history."""
    
    def __init__(self, parent):
        super().__init__(parent, "Group Chat")
        self.set_enabled(True)  # Chat is always enabled
        
        # Chat history storage for session duration
        self.chat_history: List[Dict[str, Any]] = []
        self.max_history_size = 500  # Limit history to prevent memory issues
        
        # Chat display area with improved formatting
        self.chat_display = scrolledtext.ScrolledText(
            self, 
            height=12, 
            state='disabled',
            wrap='word',
            font=('Consolas', 9),
            bg='#f8f9fa',
            fg='#212529'
        )
        self.chat_display.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Configure text tags for different message types
        self._configure_message_tags()
        
        # Message input area
        self.input_frame = ttk.Frame(self)
        self.input_frame.pack(fill='x', padx=5, pady=5)
        
        # Character counter
        self.char_counter = ttk.Label(self.input_frame, text="0/1000", font=('Arial', 8))
        self.char_counter.pack(side='right', padx=(5, 0))
        
        self.send_button = ttk.Button(
            self.input_frame, 
            text="Send", 
            command=self._send_message
        )
        self.send_button.pack(side='right', padx=(5, 0))
        
        self.message_entry = ttk.Entry(self.input_frame)
        self.message_entry.pack(side='left', fill='x', expand=True)
        self.message_entry.bind('<Return>', self._send_message)
        self.message_entry.bind('<KeyRelease>', self._update_char_counter)
        
        # Chat controls
        self.controls_frame = ttk.Frame(self)
        self.controls_frame.pack(fill='x', padx=5, pady=(0, 5))
        
        self.clear_button = ttk.Button(
            self.controls_frame, 
            text="Clear History", 
            command=self._clear_chat_history
        )
        self.clear_button.pack(side='left')
        
        self.export_button = ttk.Button(
            self.controls_frame, 
            text="Export Chat", 
            command=self._export_chat_history
        )
        self.export_button.pack(side='left', padx=(5, 0))
        
        # Status label
        self.status_label = ttk.Label(self.controls_frame, text="Ready", font=('Arial', 8))
        self.status_label.pack(side='right')
        
        # Callbacks
        self.message_callback: Optional[Callable[[str], None]] = None
    
    def _configure_message_tags(self):
        """Configure text tags for different message types and formatting."""
        self.chat_display.tag_configure('timestamp', foreground='#6c757d', font=('Consolas', 8))
        self.chat_display.tag_configure('username', foreground='#0d6efd', font=('Consolas', 9, 'bold'))
        self.chat_display.tag_configure('message', foreground='#212529', font=('Consolas', 9))
        self.chat_display.tag_configure('system', foreground='#198754', font=('Consolas', 8, 'italic'))
        self.chat_display.tag_configure('error', foreground='#dc3545', font=('Consolas', 8, 'italic'))
        self.chat_display.tag_configure('own_message', foreground='#6f42c1', font=('Consolas', 9))
    
    def set_message_callback(self, callback: Callable[[str], None]):
        """Set callback for sending messages."""
        self.message_callback = callback
    
    def _send_message(self, event=None):
        """Send a chat message with validation."""
        message_text = self.message_entry.get().strip()
        
        if not message_text:
            self._show_status("Cannot send empty message", is_error=True)
            return
        
        if len(message_text) > 1000:
            self._show_status("Message too long (max 1000 characters)", is_error=True)
            return
        
        if self.message_callback:
            try:
                self.message_callback(message_text)
                self.message_entry.delete(0, tk.END)
                self._update_char_counter()
                self._show_status("Message sent")
            except Exception as e:
                self._show_status(f"Failed to send message: {e}", is_error=True)
        else:
            self._show_status("Not connected", is_error=True)
    
    def _update_char_counter(self, event=None):
        """Update character counter display."""
        current_length = len(self.message_entry.get())
        self.char_counter.config(text=f"{current_length}/1000")
        
        # Change color based on length
        if current_length > 900:
            self.char_counter.config(foreground='red')
        elif current_length > 800:
            self.char_counter.config(foreground='orange')
        else:
            self.char_counter.config(foreground='black')
    
    def _show_status(self, message: str, is_error: bool = False):
        """Show status message with auto-clear."""
        color = 'red' if is_error else 'green'
        self.status_label.config(text=message, foreground=color)
        
        # Clear status after 3 seconds
        self.after(3000, lambda: self.status_label.config(text="Ready", foreground='black'))
    
    def add_message(self, username: str, message: str, timestamp: Optional[datetime] = None, 
                   is_own_message: bool = False, message_type: str = 'chat'):
        """
        Add a message to the chat display with chronological ordering and sender information.
        
        Args:
            username: Name of the message sender
            message: Message content
            timestamp: Message timestamp (defaults to current time)
            is_own_message: Whether this is the current user's message
            message_type: Type of message ('chat', 'system', 'error')
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        # Add to chat history for session duration
        message_entry = {
            'username': username,
            'message': message,
            'timestamp': timestamp,
            'is_own_message': is_own_message,
            'message_type': message_type
        }
        
        self.chat_history.append(message_entry)
        
        # Limit history size
        if len(self.chat_history) > self.max_history_size:
            self.chat_history = self.chat_history[-self.max_history_size:]
        
        # Format and display message
        self._display_message(message_entry)
    
    def _display_message(self, message_entry: Dict[str, Any]):
        """
        Display a message in the chat area with proper formatting.
        
        Args:
            message_entry: Dictionary containing message information
        """
        username = message_entry['username']
        message = message_entry['message']
        timestamp = message_entry['timestamp']
        is_own_message = message_entry.get('is_own_message', False)
        message_type = message_entry.get('message_type', 'chat')
        
        # Format timestamp
        time_str = timestamp.strftime("%H:%M:%S")
        
        # Enable editing
        self.chat_display.config(state='normal')
        
        # Insert timestamp
        self.chat_display.insert(tk.END, f"[{time_str}] ", 'timestamp')
        
        if message_type == 'system':
            # System message (join/leave notifications)
            self.chat_display.insert(tk.END, f"* {message}\n", 'system')
        elif message_type == 'error':
            # Error message
            self.chat_display.insert(tk.END, f"! {message}\n", 'error')
        else:
            # Regular chat message
            username_tag = 'own_message' if is_own_message else 'username'
            message_tag = 'own_message' if is_own_message else 'message'
            
            self.chat_display.insert(tk.END, f"{username}: ", username_tag)
            self.chat_display.insert(tk.END, f"{message}\n", message_tag)
        
        # Disable editing and scroll to bottom
        self.chat_display.config(state='disabled')
        self.chat_display.see(tk.END)
    
    def add_system_message(self, message: str, timestamp: Optional[datetime] = None):
        """Add a system message (e.g., user joined/left)."""
        self.add_message("System", message, timestamp, False, 'system')
    
    def add_error_message(self, message: str, timestamp: Optional[datetime] = None):
        """Add an error message."""
        self.add_message("Error", message, timestamp, False, 'error')
    
    def _clear_chat_history(self):
        """Clear chat history and display."""
        if messagebox.askyesno("Clear Chat", "Are you sure you want to clear the chat history?"):
            self.chat_history.clear()
            self.chat_display.config(state='normal')
            self.chat_display.delete(1.0, tk.END)
            self.chat_display.config(state='disabled')
            self._show_status("Chat history cleared")
    
    def _export_chat_history(self):
        """Export chat history to a text file."""
        if not self.chat_history:
            self._show_status("No chat history to export", is_error=True)
            return
        
        try:
            from tkinter import filedialog
            filename = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
                title="Export Chat History"
            )
            
            if filename:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write("LAN Collaboration Suite - Chat History\n")
                    f.write("=" * 50 + "\n\n")
                    
                    for entry in self.chat_history:
                        timestamp = entry['timestamp'].strftime("%Y-%m-%d %H:%M:%S")
                        username = entry['username']
                        message = entry['message']
                        message_type = entry.get('message_type', 'chat')
                        
                        if message_type == 'system':
                            f.write(f"[{timestamp}] * {message}\n")
                        elif message_type == 'error':
                            f.write(f"[{timestamp}] ! {message}\n")
                        else:
                            f.write(f"[{timestamp}] {username}: {message}\n")
                
                self._show_status(f"Chat exported to {filename}")
        
        except Exception as e:
            self._show_status(f"Export failed: {e}", is_error=True)
    
    def get_chat_history(self) -> List[Dict[str, Any]]:
        """
        Get the current chat history for the session.
        
        Returns:
            List of message dictionaries in chronological order
        """
        return self.chat_history.copy()
    
    def load_chat_history(self, history: List[Dict[str, Any]]):
        """
        Load chat history (e.g., when reconnecting to session).
        
        Args:
            history: List of message dictionaries to load
        """
        # Clear current display
        self.chat_display.config(state='normal')
        self.chat_display.delete(1.0, tk.END)
        self.chat_display.config(state='disabled')
        
        # Clear current history
        self.chat_history.clear()
        
        # Sort messages by timestamp to ensure chronological order
        sorted_history = sorted(history, key=lambda x: x.get('timestamp', datetime.min))
        
        # Display each message
        for message_entry in sorted_history:
            self._display_message(message_entry)
            self.chat_history.append(message_entry)
        
        self._show_status(f"Loaded {len(history)} messages from history")


class ScreenShareFrame(ModuleFrame):
    """Screen sharing module frame with presenter controls and display."""
    
    def __init__(self, parent):
        super().__init__(parent, "Screen Share")
        
        # Screen sharing state
        self.is_presenter = False
        self.is_sharing = False
        self.current_presenter_name = None
        
        # Screen share controls
        self.controls_frame = ttk.Frame(self)
        self.controls_frame.pack(fill='x', padx=5, pady=5)
        
        # Request presenter button
        self.presenter_button = ttk.Button(
            self.controls_frame, 
            text="Request Presenter", 
            command=self._request_presenter
        )
        self.presenter_button.pack(side='left', padx=2)
        
        # Start/stop sharing button
        self.share_button = ttk.Button(
            self.controls_frame, 
            text="Start Sharing", 
            command=self._toggle_screen_share,
            state='disabled'
        )
        self.share_button.pack(side='left', padx=2)
        
        # Screen sharing status
        self.status_frame = ttk.Frame(self)
        self.status_frame.pack(fill='x', padx=5, pady=2)
        
        self.presenter_label = ttk.Label(self.status_frame, text="No presenter")
        self.presenter_label.pack(side='left')
        
        self.sharing_status = ttk.Label(self.status_frame, text="")
        self.sharing_status.pack(side='right')
        
        # Screen display area
        self.screen_display = tk.Frame(self, bg='black', height=120)
        self.screen_display.pack(fill='both', expand=True, padx=5, pady=5)
        
        self.screen_label = ttk.Label(self.screen_display, text="No screen sharing active", 
                                    background='black', foreground='white')
        self.screen_label.pack(expand=True)
        
        # Screen frame display (for actual screen content)
        self.screen_canvas = tk.Canvas(self.screen_display, bg='black')
        self.screen_canvas.pack(fill='both', expand=True)
        self.screen_canvas.pack_forget()  # Initially hidden
        
        # Callbacks
        self.presenter_request_callback: Optional[Callable[[], None]] = None
        self.screen_share_start_callback: Optional[Callable[[], None]] = None
        self.screen_share_stop_callback: Optional[Callable[[], None]] = None
    
    def set_presenter_request_callback(self, callback: Callable[[], None]):
        """Set callback for presenter role requests."""
        self.presenter_request_callback = callback
    
    def set_screen_share_callbacks(self, start_callback: Callable[[], None], 
                                 stop_callback: Callable[[], None]):
        """Set callbacks for screen sharing start/stop events."""
        self.screen_share_start_callback = start_callback
        self.screen_share_stop_callback = stop_callback
    
    def _request_presenter(self):
        """Request presenter role."""
        if self.presenter_request_callback:
            self.presenter_request_callback()
    
    def _toggle_screen_share(self):
        """Toggle screen sharing on/off."""
        if not self.is_presenter:
            messagebox.showwarning("Screen Share", "You must be the presenter to share your screen")
            return
        
        if self.is_sharing:
            # Stop sharing
            if self.screen_share_stop_callback:
                self.screen_share_stop_callback()
        else:
            # Start sharing
            if self.screen_share_start_callback:
                self.screen_share_start_callback()
    
    def set_presenter_status(self, is_presenter: bool, presenter_name: str = None):
        """Update presenter status."""
        self.is_presenter = is_presenter
        
        if is_presenter:
            self.presenter_label.config(text="You are the presenter")
            self.share_button.config(state='normal')
            self.presenter_button.config(text="Release Presenter", state='normal')
        else:
            if presenter_name:
                self.presenter_label.config(text=f"Presenter: {presenter_name}")
            else:
                self.presenter_label.config(text="No presenter")
            self.share_button.config(state='disabled')
            self.presenter_button.config(text="Request Presenter", state='normal')
            
            # Stop sharing if we were sharing
            if self.is_sharing:
                self.set_sharing_status(False)
    
    def set_sharing_status(self, is_sharing: bool):
        """Update screen sharing status."""
        self.is_sharing = is_sharing
        self.enabled = is_sharing
        self._update_status_indicator()
        
        if is_sharing:
            self.share_button.config(text="Stop Sharing")
            self.sharing_status.config(text="Sharing active", foreground='green')
            self.screen_label.pack_forget()
            self.screen_canvas.pack(fill='both', expand=True)
        else:
            self.share_button.config(text="Start Sharing")
            self.sharing_status.config(text="", foreground='black')
            self.screen_canvas.pack_forget()
            self.screen_label.pack(expand=True)
            
            if self.current_presenter_name:
                self.screen_label.config(text=f"Waiting for {self.current_presenter_name} to share")
            else:
                self.screen_label.config(text="No screen sharing active")
    
    def update_presenter(self, presenter_name: Optional[str]):
        """Update the current presenter information."""
        self.current_presenter_name = presenter_name
        
        if presenter_name:
            if not self.is_presenter:
                self.presenter_label.config(text=f"Presenter: {presenter_name}")
                if not self.is_sharing:
                    self.screen_label.config(text=f"Waiting for {presenter_name} to share")
        else:
            self.presenter_label.config(text="No presenter")
            self.screen_label.config(text="No screen sharing active")
    
    def display_screen_frame(self, frame_data, presenter_name: str):
        """Display a screen frame from the presenter."""
        try:
            # This would be implemented to display the actual screen frame
            # For now, just update the label
            if self.current_presenter_name != presenter_name:
                self.update_presenter(presenter_name)
            
            # Show that we're receiving frames
            if not self.is_sharing:  # Only show if we're not the one sharing
                self.screen_label.config(text=f"Receiving screen from {presenter_name}")
                
        except Exception as e:
            logger.error(f"Error displaying screen frame: {e}")
    
    def handle_presenter_granted(self):
        """Handle presenter role being granted."""
        self.set_presenter_status(True)
        messagebox.showinfo("Screen Share", "You are now the presenter! You can start screen sharing.")
    
    def handle_presenter_denied(self, reason: str = ""):
        """Handle presenter role being denied."""
        message = "Presenter request denied"
        if reason:
            message += f": {reason}"
        messagebox.showwarning("Screen Share", message)
    
    def handle_screen_share_started(self, presenter_name: str):
        """Handle screen sharing being started by presenter."""
        if presenter_name != "You":
            self.update_presenter(presenter_name)
            self.screen_label.config(text=f"{presenter_name} is sharing their screen")
    
    def handle_screen_share_stopped(self):
        """Handle screen sharing being stopped."""
        self.set_sharing_status(False)


class FileTransferFrame(ModuleFrame):
    """Compact file transfer module frame."""
    
    def __init__(self, parent):
        super().__init__(parent, "File Transfer")
        self.set_enabled(True)  # File transfer is always enabled
        
        # Compact upload controls
        self.upload_frame = ttk.Frame(self)
        self.upload_frame.pack(fill='x', padx=3, pady=2)
        
        self.upload_button = ttk.Button(
            self.upload_frame, 
            text="Share File", 
            command=self._select_file
        )
        self.upload_button.pack(fill='x')
        
        # Compact file list
        ttk.Label(self, text="Shared Files:", font=('Arial', 9)).pack(anchor='w', padx=3)
        
        self.file_listbox = tk.Listbox(self, height=3, font=('Arial', 8))
        self.file_listbox.pack(fill='both', expand=True, padx=3, pady=2)
        self.file_listbox.bind('<Double-Button-1>', self._download_file)
        
        # Compact download controls
        download_frame = ttk.Frame(self)
        download_frame.pack(fill='x', padx=3, pady=2)
        
        self.download_button = ttk.Button(
            download_frame, 
            text="Download", 
            command=self._download_file
        )
        self.download_button.pack(fill='x')
        
        # Compact progress display
        self.progress_label = ttk.Label(self, text="", font=('Arial', 8))
        self.progress_label.pack(padx=3)
        
        self.progress_bar = ttk.Progressbar(self, mode='determinate')
        # Progress bar will be packed only when needed
        
        # Cancel button for downloads
        self.cancel_button = ttk.Button(
            self, 
            text="Cancel Download", 
            command=self._cancel_download,
            state='disabled'
        )
        # Cancel button will be packed only when needed
        
        # File data
        self.shared_files: Dict[str, Dict[str, Any]] = {}
        
        # Callbacks
        self.file_upload_callback: Optional[Callable[[str], None]] = None
        self.file_download_callback: Optional[Callable[[str], None]] = None
        self.cancel_download_callback: Optional[Callable[[], None]] = None
        
        # Track current download
        self.current_download_file_id: Optional[str] = None
    
    def set_file_callbacks(self, upload_callback: Callable[[str], None], 
                          download_callback: Callable[[str], None],
                          cancel_download_callback: Optional[Callable[[], None]] = None):
        """Set callbacks for file operations."""
        self.file_upload_callback = upload_callback
        self.file_download_callback = download_callback
        self.cancel_download_callback = cancel_download_callback
    
    def _select_file(self):
        """Open file dialog to select file for sharing."""
        file_path = filedialog.askopenfilename(
            title="Select file to share",
            filetypes=[("All files", "*.*")]
        )
        
        if file_path and self.file_upload_callback:
            self.file_upload_callback(file_path)
    
    def _download_file(self, event=None):
        """Download selected file with validation and user feedback."""
        selection = self.file_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a file to download.")
            return
        
        if not self.file_download_callback:
            messagebox.showerror("Error", "Download functionality not available.")
            return
        
        try:
            file_index = selection[0]
            file_items = list(self.shared_files.items())
            
            if file_index >= len(file_items):
                messagebox.showerror("Error", "Invalid file selection.")
                return
            
            file_id, file_info = file_items[file_index]
            filename = file_info['filename']
            filesize = file_info['filesize']
            
            # Confirm download with user
            size_mb = filesize / (1024 * 1024)
            if size_mb > 10:  # Warn for files larger than 10MB
                result = messagebox.askyesno(
                    "Large File Download", 
                    f"Download '{filename}' ({size_mb:.1f} MB)?\n\nThis may take some time."
                )
                if not result:
                    return
            
            # Start download
            self.file_download_callback(file_id)
            
        except Exception as e:
            messagebox.showerror("Download Error", f"Failed to start download: {e}")
    
    def _cancel_download(self):
        """Cancel current download."""
        if self.cancel_download_callback:
            self.cancel_download_callback()
        else:
            messagebox.showwarning("Cancel Download", "No download to cancel.")
    
    def add_shared_file(self, file_id: str, filename: str, filesize: int, uploader: str):
        """Add a file to the shared files list."""
        self.shared_files[file_id] = {
            'filename': filename,
            'filesize': filesize,
            'uploader': uploader
        }
        
        # Update listbox
        self._update_file_list()
    
    def _update_file_list(self):
        """Update the file list display."""
        self.file_listbox.delete(0, tk.END)
        
        for file_id, file_info in self.shared_files.items():
            filename = file_info['filename']
            filesize = file_info['filesize']
            uploader = file_info['uploader']
            
            # Format file size
            if filesize < 1024:
                size_str = f"{filesize} B"
            elif filesize < 1024 * 1024:
                size_str = f"{filesize / 1024:.1f} KB"
            else:
                size_str = f"{filesize / (1024 * 1024):.1f} MB"
            
            display_text = f"{filename} ({size_str}) - {uploader}"
            self.file_listbox.insert(tk.END, display_text)
    
    def show_transfer_progress(self, filename: str, progress: float, transfer_type: str = "Downloading"):
        """Show file transfer progress with enhanced display."""
        # Update progress label with more detailed information
        progress_percent = int(progress * 100)
        self.progress_label.config(text=f"{transfer_type}: {filename} ({progress_percent}%)")
        
        # Update progress bar
        self.progress_bar['value'] = progress * 100
        self.progress_bar.pack(fill='x', pady=(2, 0))
        
        # Show and enable cancel button during download
        if progress < 1.0 and transfer_type == "Downloading":
            self.cancel_button.pack(fill='x', pady=(2, 0))
            self.cancel_button.config(state='normal')
        else:
            self.cancel_button.config(state='disabled')
        
        # Change progress bar color based on progress
        if progress >= 1.0:
            # Complete - green
            self.progress_bar.configure(style="Complete.Horizontal.TProgressbar")
        elif progress >= 0.5:
            # More than half - default blue
            self.progress_bar.configure(style="TProgressbar")
        else:
            # Less than half - default
            self.progress_bar.configure(style="TProgressbar")
    
    def hide_transfer_progress(self):
        """Hide file transfer progress."""
        self.progress_label.config(text="")
        self.progress_bar.pack_forget()
        self.cancel_button.pack_forget()
        # Reset progress bar style and disable cancel button
        self.progress_bar.configure(style="TProgressbar")
        self.cancel_button.config(state='disabled')
        self.current_download_file_id = None


class ParticipantListFrame(ttk.Frame):
    """Compact participant list display frame."""
    
    def __init__(self, parent):
        super().__init__(parent, relief='ridge', borderwidth=1)
        
        # Compact title
        title_label = ttk.Label(self, text="Participants", font=('Arial', 10, 'bold'))
        title_label.pack(pady=2)
        
        # Compact participant list
        self.participant_listbox = tk.Listbox(self, height=4, font=('Arial', 9))
        self.participant_listbox.pack(fill='both', expand=True, padx=3, pady=2)
        
        # Compact connection info
        self.connection_info = ttk.Label(self, text="Not connected", font=('Arial', 8))
        self.connection_info.pack(pady=1)
    
    def update_participants(self, participants: Dict[str, Dict[str, Any]], current_client_id: str):
        """Update the participant list display."""
        self.participant_listbox.delete(0, tk.END)
        
        for client_id, participant in participants.items():
            username = participant.get('username', 'Unknown')
            video_status = "📹" if participant.get('video_enabled', False) else "📹❌"
            audio_status = "🎤" if participant.get('audio_enabled', False) else "🎤❌"
            
            if client_id == current_client_id:
                username += " (You)"
            
            display_text = f"{username} {video_status} {audio_status}"
            self.participant_listbox.insert(tk.END, display_text)
    
    def update_connection_info(self, status: str, participant_count: int):
        """Update connection information display."""
        info_text = f"Status: {status} | Participants: {participant_count}"
        self.connection_info.config(text=info_text)


class GUIManager:
    """
    Main GUI manager for the collaboration client.
    
    Creates and manages the unified dashboard with all collaboration modules.
    """
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("LAN Collaboration Suite")
        
        # Get screen dimensions for responsive sizing
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # Set window size based on screen size (80% of screen)
        window_width = int(screen_width * 0.8)
        window_height = int(screen_height * 0.8)
        
        # Center the window
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        self.root.minsize(1000, 700)  # Increased minimum size
        
        # Make window resizable and responsive
        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)
        
        # Set application icon and styling
        self._setup_styling()
        
        # Connection callbacks
        self.connect_callback: Optional[Callable[[str], None]] = None
        self.disconnect_callback: Optional[Callable[[], None]] = None
        
        # Module frames
        self.video_frame: Optional[VideoFrame] = None
        self.audio_frame: Optional[AudioFrame] = None
        self.chat_frame: Optional[ChatFrame] = None
        self.screen_share_frame: Optional[ScreenShareFrame] = None
        self.file_transfer_frame: Optional[FileTransferFrame] = None
        self.participant_frame: Optional[ParticipantListFrame] = None
        
        # Connection state
        self.connected = False
        
        # Real-time update tracking
        self.last_update_time = None
        
        self._create_interface()
        self.setup_enhanced_callbacks()
        
        # Start real-time updates
        self.start_real_time_updates()
        
        # Handle window closing
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
    
    def _setup_styling(self):
        """Setup GUI styling and theming."""
        try:
            # Configure ttk styles for better appearance
            style = ttk.Style()
            
            # Try to use a modern theme if available
            available_themes = style.theme_names()
            if 'clam' in available_themes:
                style.theme_use('clam')
            elif 'alt' in available_themes:
                style.theme_use('alt')
            
            # Configure custom styles for progress bars
            style.configure("Complete.Horizontal.TProgressbar", 
                          foreground='green', background='green')
            
            # Set window icon if available
            try:
                # This would set a custom icon if we had one
                # self.root.iconbitmap('icon.ico')
                pass
            except:
                pass
                
        except Exception as e:
            logger.warning(f"Could not setup advanced styling: {e}")
    
    def _on_closing(self):
        """Handle application closing."""
        try:
            if self.connected and self.disconnect_callback:
                # Attempt graceful disconnect
                self.disconnect_callback()
            
            # Close the application
            self.root.quit()
            self.root.destroy()
            
        except Exception as e:
            logger.error(f"Error during application shutdown: {e}")
            # Force close if graceful shutdown fails
            self.root.destroy()
    
    def _create_interface(self):
        """Create the main interface layout."""
        # Main container
        main_container = ttk.Frame(self.root)
        main_container.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Top section: Connection controls
        self._create_connection_section(main_container)
        
        # Middle section: Main collaboration modules
        self._create_modules_section(main_container)
        
        # Right section: Participant list
        self._create_participant_section(main_container)
    
    def _create_connection_section(self, parent):
        """Create compact connection controls section."""
        connection_frame = ttk.LabelFrame(parent, text="Connection", padding=5)
        connection_frame.pack(fill='x', pady=(0, 5))
        
        # Main connection row
        main_row = ttk.Frame(connection_frame)
        main_row.pack(fill='x')
        
        # Server input (more compact)
        ttk.Label(main_row, text="Server:").pack(side='left')
        self.server_entry = ttk.Entry(main_row, width=12)
        self.server_entry.pack(side='left', padx=(2, 8))
        self.server_entry.insert(0, "localhost")
        
        # Username input
        ttk.Label(main_row, text="Username:").pack(side='left')
        self.username_entry = ttk.Entry(main_row, width=12)
        self.username_entry.pack(side='left', padx=(2, 8))
        self.username_entry.insert(0, "User")
        
        # Connection buttons
        self.connect_button = ttk.Button(
            main_row, 
            text="Connect", 
            command=self._connect_clicked
        )
        self.connect_button.pack(side='left', padx=2)
        
        self.disconnect_button = ttk.Button(
            main_row, 
            text="Disconnect", 
            command=self._disconnect_clicked,
            state='disabled'
        )
        self.disconnect_button.pack(side='left', padx=2)
        
        # Status display (more compact)
        self.status_label = ttk.Label(main_row, text="Status: Disconnected", font=('Arial', 9))
        self.status_label.pack(side='right', padx=5)
    
    def _create_modules_section(self, parent):
        """Create the main collaboration modules section with responsive layout."""
        modules_frame = ttk.Frame(parent)
        modules_frame.pack(fill='both', expand=True)
        
        # Configure grid weights for responsive layout
        modules_frame.columnconfigure(0, weight=1)  # Left half (video)
        modules_frame.columnconfigure(1, weight=1)  # Right half (chat/controls)
        modules_frame.rowconfigure(0, weight=1)
        
        # LEFT HALF: Large Video Grid
        left_half = ttk.Frame(modules_frame)
        left_half.grid(row=0, column=0, sticky='nsew', padx=(0, 5))
        left_half.rowconfigure(0, weight=1)
        left_half.columnconfigure(0, weight=1)
        
        # Large video frame taking up most of left half
        self.video_frame = VideoFrame(left_half)
        self.video_frame.grid(row=0, column=0, sticky='nsew', pady=(0, 5))
        
        # Audio controls at bottom of left half
        self.audio_frame = AudioFrame(left_half)
        self.audio_frame.grid(row=1, column=0, sticky='ew')
        
        # RIGHT HALF: Chat, Controls, and Participants
        right_half = ttk.Frame(modules_frame)
        right_half.grid(row=0, column=1, sticky='nsew', padx=(5, 0))
        right_half.rowconfigure(0, weight=1)  # Chat takes most space
        right_half.columnconfigure(0, weight=1)
        
        # Chat frame (top priority for space)
        self.chat_frame = ChatFrame(right_half)
        self.chat_frame.grid(row=0, column=0, sticky='nsew', pady=(0, 5))
        
        # Screen share controls
        self.screen_share_frame = ScreenShareFrame(right_half)
        self.screen_share_frame.grid(row=1, column=0, sticky='ew', pady=(0, 5))
        
        # Participants and file transfer in bottom section
        bottom_right_frame = ttk.Frame(right_half)
        bottom_right_frame.grid(row=2, column=0, sticky='ew')
        bottom_right_frame.columnconfigure(0, weight=1)
        bottom_right_frame.columnconfigure(1, weight=1)
        
        # Participant list (left side of bottom)
        self.participant_frame = ParticipantListFrame(bottom_right_frame)
        self.participant_frame.grid(row=0, column=0, sticky='nsew', padx=(0, 2))
        
        # File transfer (right side of bottom)
        self.file_transfer_frame = FileTransferFrame(bottom_right_frame)
        self.file_transfer_frame.grid(row=0, column=1, sticky='nsew', padx=(2, 0))
    
    def _create_participant_section(self, parent):
        """Participant section is now integrated into the right half layout."""
        # This method is now handled in _create_modules_section
        pass
    
    def _connect_clicked(self):
        """Handle connect button click."""
        server = self.server_entry.get().strip()
        username = self.username_entry.get().strip()
        
        if not server or not username:
            messagebox.showerror("Error", "Please enter server address and username")
            return
        
        if self.connect_callback:
            self.connect_callback(username)
    
    def _disconnect_clicked(self):
        """Handle disconnect button click."""
        if self.disconnect_callback:
            self.disconnect_callback()
    
    def set_connection_callbacks(self, connect_callback: Callable[[str], None], 
                               disconnect_callback: Callable[[], None]):
        """Set callbacks for connection events."""
        self.connect_callback = connect_callback
        self.disconnect_callback = disconnect_callback
    
    def set_module_callbacks(self, video_callback: Callable[[bool], None],
                           audio_callback: Callable[[bool], None],
                           message_callback: Callable[[str], None],
                           screen_share_callback: Callable[[bool], None],
                           file_upload_callback: Callable[[str], None],
                           file_download_callback: Callable[[str], None]):
        """Set callbacks for module events with enhanced error handling."""
        try:
            if self.video_frame:
                self.video_frame.set_video_callback(video_callback)
            
            if self.audio_frame:
                self.audio_frame.set_audio_callback(audio_callback)
            
            if self.chat_frame:
                self.chat_frame.set_message_callback(message_callback)
            
            if self.screen_share_frame:
                # Use a unified screen share callback
                def screen_share_wrapper():
                    try:
                        screen_share_callback(not self.screen_share_frame.is_sharing)
                    except Exception as e:
                        self.handle_platform_specific_error(e, "Screen Sharing")
                
                self.screen_share_frame.set_presenter_request_callback(screen_share_wrapper)
                self.screen_share_frame.set_screen_share_callbacks(screen_share_wrapper, screen_share_wrapper)
            
            if self.file_transfer_frame:
                # Wrap file callbacks with error handling
                def safe_file_upload(file_path):
                    try:
                        file_upload_callback(file_path)
                    except Exception as e:
                        self.handle_platform_specific_error(e, "File Upload")
                
                def safe_file_download(file_id):
                    try:
                        file_download_callback(file_id)
                    except Exception as e:
                        self.handle_platform_specific_error(e, "File Download")
                
                self.file_transfer_frame.set_file_callbacks(safe_file_upload, safe_file_download)
                
        except Exception as e:
            logger.error(f"Error setting module callbacks: {e}")
            self.show_error("Configuration Error", f"Failed to setup module callbacks: {e}")
    
    def update_connection_status(self, status: str):
        """Update connection status display and button states."""
        self.status_label.config(text=f"Status: {status}")
        
        # Update button states based on connection status
        if status.lower() == "connected":
            self.connected = True
            self.connect_button.config(state='disabled')
            self.disconnect_button.config(state='normal')
            self.server_entry.config(state='disabled')
            self.username_entry.config(state='disabled')
        else:
            self.connected = False
            self.connect_button.config(state='normal')
            self.disconnect_button.config(state='disabled')
            self.server_entry.config(state='normal')
            self.username_entry.config(state='normal')
    
    def update_screen_sharing_presenter(self, presenter_name: Optional[str]):
        """Update screen sharing presenter information."""
        if self.screen_share_frame:
            self.screen_share_frame.update_presenter(presenter_name)
    
    def set_presenter_status(self, is_presenter: bool, presenter_name: str = None):
        """Set presenter status for screen sharing."""
        if self.screen_share_frame:
            self.screen_share_frame.set_presenter_status(is_presenter, presenter_name)
    
    def set_screen_sharing_status(self, is_sharing: bool):
        """Set screen sharing active status."""
        if self.screen_share_frame:
            self.screen_share_frame.set_sharing_status(is_sharing)
    
    def display_screen_frame(self, frame_data, presenter_name: str):
        """Display screen frame from presenter."""
        if self.screen_share_frame:
            self.screen_share_frame.display_screen_frame(frame_data, presenter_name)
    
    def handle_presenter_granted(self):
        """Handle presenter role being granted."""
        if self.screen_share_frame:
            self.screen_share_frame.handle_presenter_granted()
    
    def handle_presenter_denied(self, reason: str = ""):
        """Handle presenter role being denied."""
        if self.screen_share_frame:
            self.screen_share_frame.handle_presenter_denied(reason)
    
    def handle_screen_share_started(self, presenter_name: str):
        """Handle screen sharing being started."""
        if self.screen_share_frame:
            self.screen_share_frame.handle_screen_share_started(presenter_name)
    
    def handle_screen_share_stopped(self):
        """Handle screen sharing being stopped."""
        if self.screen_share_frame:
            self.screen_share_frame.handle_screen_share_stopped()
    
    def update_participants(self, participants: Dict[str, Dict[str, Any]], current_client_id: str):
        """Update participant list and video feeds."""
        if self.participant_frame:
            self.participant_frame.update_participants(participants, current_client_id)
            self.participant_frame.update_connection_info("Connected", len(participants))
        
        if self.video_frame:
            self.video_frame.update_video_feeds(participants)
    
    def add_chat_message(self, username: str, message: str, timestamp: Optional[datetime] = None, 
                        is_own_message: bool = False, message_type: str = 'chat'):
        """Add a message to the chat display with enhanced formatting."""
        if self.chat_frame:
            self.chat_frame.add_message(username, message, timestamp, is_own_message, message_type)
    
    def update_presenter(self, presenter_name: Optional[str]):
        """Update screen sharing presenter information."""
        if self.screen_share_frame:
            self.screen_share_frame.update_presenter(presenter_name)
    
    def add_shared_file(self, file_id: str, filename: str, filesize: int, uploader: str):
        """Add a file to the shared files list."""
        if self.file_transfer_frame:
            self.file_transfer_frame.add_shared_file(file_id, filename, filesize, uploader)
    
    def show_file_transfer_progress(self, filename: str, progress: float, transfer_type: str = "Downloading"):
        """Show file transfer progress with enhanced display."""
        if self.file_transfer_frame:
            self.file_transfer_frame.show_transfer_progress(filename, progress, transfer_type)
    
    def hide_file_transfer_progress(self):
        """Hide file transfer progress."""
        if self.file_transfer_frame:
            self.file_transfer_frame.hide_transfer_progress()
    
    def update_audio_level(self, level: float):
        """Update audio level indicator."""
        if self.audio_frame:
            self.audio_frame.update_audio_level(level)
    
    def show_error(self, title: str, message: str):
        """Show error message dialog with platform-specific error handling."""
        try:
            from common.platform_utils import ErrorHandler
            
            # Try to provide platform-specific error suggestions
            if "Error:" in message:
                error_part = message.split("Error:")[-1].strip()
                suggestion = ErrorHandler.suggest_platform_fix(Exception(error_part))
                if suggestion:
                    message += f"\n\nSuggested fix: {suggestion}"
            
            messagebox.showerror(title, message)
        except Exception as e:
            # Fallback to basic error display
            messagebox.showerror(title, message)
    
    def show_info(self, title: str, message: str):
        """Show information message dialog."""
        messagebox.showinfo(title, message)
    
    def show_warning(self, title: str, message: str):
        """Show warning message dialog."""
        messagebox.showwarning(title, message)
    
    def show_status_message(self, message: str, duration: int = 3000, is_error: bool = False):
        """Show temporary status message in the status bar."""
        original_text = self.status_label.cget("text")
        color = "red" if is_error else "green"
        
        # Update status with temporary message
        self.status_label.config(text=f"Status: {message}", foreground=color)
        
        # Restore original status after duration
        def restore_status():
            self.status_label.config(text=original_text, foreground="black")
        
        self.root.after(duration, restore_status)
    
    def update_real_time_status(self):
        """Update real-time status indicators across all modules."""
        try:
            # Update connection indicator
            if self.connected:
                self.show_status_message("Connected", 1000, False)
            
            # Update module status indicators
            if self.video_frame and self.video_frame.enabled:
                self.video_frame._update_status_indicator()
            
            if self.audio_frame and self.audio_frame.enabled:
                self.audio_frame._update_status_indicator()
            
            if self.screen_share_frame and self.screen_share_frame.enabled:
                self.screen_share_frame._update_status_indicator()
            
            # Schedule next update
            self.root.after(5000, self.update_real_time_status)  # Update every 5 seconds
            
        except Exception as e:
            logger.error(f"Error updating real-time status: {e}")
    
    def start_real_time_updates(self):
        """Start real-time status updates."""
        self.update_real_time_status()
    
    def handle_platform_specific_error(self, error: Exception, context: str = ""):
        """Handle platform-specific errors with appropriate user feedback."""
        try:
            from common.platform_utils import ErrorHandler
            
            error_msg = ErrorHandler.get_platform_specific_error_message(error)
            suggestion = ErrorHandler.suggest_platform_fix(error)
            
            title = f"Error in {context}" if context else "Application Error"
            message = error_msg
            
            if suggestion:
                message += f"\n\nSuggested solution:\n{suggestion}"
            
            self.show_error(title, message)
            
        except Exception as e:
            # Fallback error handling
            self.show_error("Error", f"An error occurred: {error}")
    
    def validate_user_input(self, input_type: str, value: str) -> tuple[bool, str]:
        """Validate user input with helpful error messages."""
        if input_type == "username":
            if not value or not value.strip():
                return False, "Username cannot be empty"
            if len(value.strip()) < 2:
                return False, "Username must be at least 2 characters long"
            if len(value.strip()) > 50:
                return False, "Username must be less than 50 characters"
            if not value.replace("_", "").replace("-", "").isalnum():
                return False, "Username can only contain letters, numbers, hyphens, and underscores"
            return True, ""
        
        elif input_type == "server":
            if not value or not value.strip():
                return False, "Server address cannot be empty"
            # Basic validation for IP or hostname
            value = value.strip()
            if not (value.replace(".", "").replace(":", "").replace("-", "").isalnum() or value == "localhost"):
                return False, "Invalid server address format"
            return True, ""
        
        return True, ""
    
    def enhanced_connect_clicked(self):
        """Enhanced connect button handler with validation and feedback."""
        server = self.server_entry.get().strip()
        username = self.username_entry.get().strip()
        
        # Validate inputs
        server_valid, server_error = self.validate_user_input("server", server)
        if not server_valid:
            self.show_error("Invalid Server", server_error)
            self.server_entry.focus()
            return
        
        username_valid, username_error = self.validate_user_input("username", username)
        if not username_valid:
            self.show_error("Invalid Username", username_error)
            self.username_entry.focus()
            return
        
        # Show connecting status
        self.show_status_message("Connecting...", 10000, False)
        
        if self.connect_callback:
            try:
                self.connect_callback(username)
            except Exception as e:
                self.handle_platform_specific_error(e, "Connection")
    
    def setup_enhanced_callbacks(self):
        """Setup enhanced callback handling with error management."""
        # Replace the basic connect callback with enhanced version
        self.connect_button.config(command=self.enhanced_connect_clicked)
    
    def run(self):
        """Start the GUI main loop."""
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            logger.info("GUI interrupted by user")
        except Exception as e:
            logger.error(f"GUI error: {e}")
    
    def close(self):
        """Close the GUI application."""
        self.root.quit()
        self.root.destroy()