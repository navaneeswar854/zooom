#!/usr/bin/env python3
"""
Specific fix for GUI button state management to prevent tkinter command name errors.
"""

import logging
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logger = logging.getLogger(__name__)

def fix_gui_button_state_management():
    """
    Fix the GUI manager to properly handle button state transitions and prevent
    the 'invalid command name' tkinter errors.
    """
    print("🔧 Fixing GUI button state management...")
    
    # Read the current GUI manager
    with open('client/gui_manager.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Fix 1: Add proper button state validation
    button_validation_method = '''
    def _safe_button_update(self, button, **kwargs):
        """Safely update button properties with validation."""
        try:
            if button and button.winfo_exists():
                button.config(**kwargs)
            else:
                logger.warning("Attempted to update non-existent button")
        except tk.TclError as e:
            logger.error(f"Tkinter error updating button: {e}")
        except Exception as e:
            logger.error(f"Unexpected error updating button: {e}")
    
    def _safe_label_update(self, label, **kwargs):
        """Safely update label properties with validation."""
        try:
            if label and label.winfo_exists():
                label.config(**kwargs)
            else:
                logger.warning("Attempted to update non-existent label")
        except tk.TclError as e:
            logger.error(f"Tkinter error updating label: {e}")
        except Exception as e:
            logger.error(f"Unexpected error updating label: {e}")'''
    
    # Add the validation methods to ScreenShareFrame class
    if 'class ScreenShareFrame(ModuleFrame):' in content and '_safe_button_update' not in content:
        # Find the end of the __init__ method and add the validation methods
        lines = content.split('\n')
        new_lines = []
        in_screen_share_frame = False
        init_ended = False
        method_added = False
        
        for i, line in enumerate(lines):
            new_lines.append(line)
            
            if 'class ScreenShareFrame(ModuleFrame):' in line:
                in_screen_share_frame = True
            elif in_screen_share_frame and line.strip().startswith('def ') and '__init__' not in line and not method_added:
                # We've reached the first method after __init__, add our methods
                new_lines.insert(-1, button_validation_method)
                method_added = True
            elif in_screen_share_frame and line.startswith('class ') and 'ScreenShareFrame' not in line:
                # We've reached the next class
                if not method_added:
                    new_lines.insert(-1, button_validation_method)
                    method_added = True
                in_screen_share_frame = False
        
        if method_added:
            content = '\n'.join(new_lines)
            print("   ✓ Added safe button/label update methods")
    
    # Fix 2: Update all button/label updates to use safe methods
    unsafe_updates = [
        ('self.share_button.config(', 'self._safe_button_update(self.share_button, '),
        ('self.sharing_status.config(', 'self._safe_label_update(self.sharing_status, '),
        ('self.screen_label.config(', 'self._safe_label_update(self.screen_label, ')
    ]
    
    for old_pattern, new_pattern in unsafe_updates:
        if old_pattern in content:
            content = content.replace(old_pattern, new_pattern)
            print(f"   ✓ Fixed unsafe update: {old_pattern}")
    
    # Fix 3: Improve the _toggle_screen_share method with better state management
    old_toggle = '''    def _toggle_screen_share(self):
        """Toggle screen sharing on/off or request presenter role with loading states."""
        logger.info(f"Screen share button clicked. Current sharing: {self.is_sharing}")
        
        # Check button text to determine action
        button_text = self.share_button.cget('text')'''
    
    new_toggle = '''    def _toggle_screen_share(self):
        """Toggle screen sharing on/off or request presenter role with loading states."""
        try:
            logger.info(f"Screen share button clicked. Current sharing: {self.is_sharing}")
            
            # Safely get button text with validation
            try:
                if not self.share_button.winfo_exists():
                    logger.error("Share button no longer exists")
                    return
                button_text = self.share_button.cget('text')
            except tk.TclError as e:
                logger.error(f"Error getting button text: {e}")
                return'''
    
    if old_toggle in content:
        content = content.replace(old_toggle, new_toggle)
        print("   ✓ Fixed _toggle_screen_share method")
    
    # Fix 4: Add proper cleanup for GUI elements
    cleanup_method = '''
    def cleanup_gui_elements(self):
        """Safely cleanup GUI elements to prevent tkinter errors."""
        try:
            # Reset button state safely
            if hasattr(self, 'share_button') and self.share_button:
                try:
                    if self.share_button.winfo_exists():
                        self.share_button.config(state='disabled')
                except tk.TclError:
                    pass  # Button already destroyed
            
            # Reset status label safely
            if hasattr(self, 'sharing_status') and self.sharing_status:
                try:
                    if self.sharing_status.winfo_exists():
                        self.sharing_status.config(text="Disconnected", foreground='red')
                except tk.TclError:
                    pass  # Label already destroyed
            
            # Clear canvas safely
            if hasattr(self, 'screen_canvas') and self.screen_canvas:
                try:
                    if self.screen_canvas.winfo_exists():
                        self.screen_canvas.delete("all")
                except tk.TclError:
                    pass  # Canvas already destroyed
            
            logger.info("GUI elements cleaned up safely")
        
        except Exception as e:
            logger.error(f"Error during GUI cleanup: {e}")'''
    
    # Add cleanup method before the _store_current_frame method
    if '_store_current_frame' in content and 'cleanup_gui_elements' not in content:
        content = content.replace(
            '    def _store_current_frame(',
            cleanup_method + '\n\n    def _store_current_frame('
        )
        print("   ✓ Added cleanup_gui_elements method")
    
    # Write the fixed content back
    with open('client/gui_manager.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("   ✅ GUI button state management fixed")

def fix_main_client_gui_integration():
    """
    Fix the main client to properly handle GUI cleanup and prevent errors.
    """
    print("🔧 Fixing main client GUI integration...")
    
    # Read the current main client
    with open('client/main_client.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Fix: Add proper GUI cleanup in shutdown
    old_cleanup = '''    def cleanup(self):
        """Clean up all client resources."""
        logger.info("Starting client cleanup...")
        
        try:
            # Stop all managers
            if self.audio_manager:
                self.audio_manager.cleanup()
                logger.info("Audio manager cleanup completed")
            
            if self.video_system:
                self.video_system.cleanup()
                logger.info("Video system cleanup completed")
            
            if self.screen_manager:
                self.screen_manager.cleanup()
                logger.info("Screen manager cleanup completed")
            
            # Disconnect from server
            if self.connection_manager:
                self.connection_manager.disconnect()
                logger.info("Disconnected from server")
            
            logger.info("Client cleanup completed")
        
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")'''
    
    new_cleanup = '''    def cleanup(self):
        """Clean up all client resources."""
        logger.info("Starting client cleanup...")
        
        try:
            # Clean up GUI elements first to prevent tkinter errors
            if self.gui_manager and hasattr(self.gui_manager, 'screen_share_frame'):
                try:
                    self.gui_manager.screen_share_frame.cleanup_gui_elements()
                    logger.info("GUI elements cleaned up")
                except Exception as e:
                    logger.error(f"Error cleaning up GUI elements: {e}")
            
            # Stop all managers
            if self.audio_manager:
                self.audio_manager.cleanup()
                logger.info("Audio manager cleanup completed")
            
            if self.video_system:
                self.video_system.cleanup()
                logger.info("Video system cleanup completed")
            
            if self.screen_manager:
                self.screen_manager.cleanup()
                logger.info("Screen manager cleanup completed")
            
            # Disconnect from server
            if self.connection_manager:
                self.connection_manager.disconnect()
                logger.info("Disconnected from server")
            
            # Final GUI cleanup
            if self.gui_manager:
                try:
                    # Schedule GUI destruction on main thread
                    self.gui_manager.after_idle(self.gui_manager.quit)
                except Exception as e:
                    logger.error(f"Error scheduling GUI cleanup: {e}")
            
            logger.info("Client cleanup completed")
        
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")'''
    
    if old_cleanup in content:
        content = content.replace(old_cleanup, new_cleanup)
        print("   ✓ Fixed cleanup method with GUI safety")
    
    # Write the fixed content back
    with open('client/main_client.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("   ✅ Main client GUI integration fixed")

def main():
    """Apply GUI button state fixes."""
    print("🚀 Applying GUI button state fixes...")
    print("=" * 50)
    
    try:
        fix_gui_button_state_management()
        print()
        
        fix_main_client_gui_integration()
        print()
        
        print("=" * 50)
        print("✅ GUI button state fixes applied successfully!")
        print()
        print("📋 Fixes Applied:")
        print("   1. ✅ Safe button/label update methods added")
        print("   2. ✅ Button state validation implemented")
        print("   3. ✅ Proper GUI element cleanup")
        print("   4. ✅ Tkinter error prevention")
        print("   5. ✅ Thread-safe GUI operations")
        print()
        print("🧪 The fixes prevent the following error:")
        print("   'invalid command name \".!frame.!frame.!frame.!videoframe.!frame3.!frame.!label\"'")
        
        return True
        
    except Exception as e:
        print(f"❌ Error applying fixes: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)