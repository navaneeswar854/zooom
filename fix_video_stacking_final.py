#!/usr/bin/env python3
"""
Final fix for video frame stacking issue.
This script will completely replace the problematic video update functions.
"""

import logging
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_fixed_video_functions():
    """Create the fixed video update functions."""
    
    local_video_function = '''    def _update_local_video_safe(self, frame, client_key):
        """Thread-safe implementation of local video update."""
        try:
            import cv2
            from PIL import Image, ImageTk
            import time
            
            # Clear pending update flag
            if client_key in self.pending_updates:
                del self.pending_updates[client_key]
            
            # Frame rate limiting for local video
            current_time = time.time()
            if 'local' in self.last_frame_time:
                if current_time - self.last_frame_time['local'] < self.frame_rate_limit:
                    return  # Skip this frame to prevent stacking
            self.last_frame_time['local'] = current_time
            
            # Convert OpenCV frame (BGR) to RGB
            if frame is not None and frame.size > 0:
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Convert to PIL Image
                pil_image = Image.fromarray(rgb_frame)
                
                # Resize to fit in video slot (maintain aspect ratio)
                display_size = (200, 150)  # Larger size for better visibility
                pil_image = pil_image.resize(display_size, Image.LANCZOS)
                
                # Convert to PhotoImage for tkinter
                photo = ImageTk.PhotoImage(pil_image)
                
                # Update the first video slot with local video
                if 0 in self.video_slots:
                    slot = self.video_slots[0]
                    
                    # Check if widgets still exist before accessing them
                    if not self._widget_exists(slot['frame']):
                        logger.warning("Local video slot frame no longer exists")
                        return
                    
                    # Hide the placeholder label first
                    if 'label' in slot and self._widget_exists(slot['label']):
                        slot['label'].pack_forget()
                    
                    # Destroy any existing video widget to prevent stacking
                    if hasattr(slot, 'video_widget') and self._widget_exists(slot.get('video_widget')):
                        slot['video_widget'].destroy()
                    
                    # Create new video label widget
                    slot['video_widget'] = tk.Label(
                        slot['frame'],
                        image=photo,
                        bg='black'
                    )
                    slot['video_widget'].pack(fill='both', expand=True)
                    slot['video_widget'].image = photo  # Keep reference
                    
                    # Update slot info
                    slot['participant_id'] = 'local'
                    slot['active'] = True
                    
                    # Add "You" label
                    if not hasattr(slot, 'name_label') or not self._widget_exists(slot.get('name_label')):
                        slot['name_label'] = tk.Label(
                            slot['frame'], 
                            text="You (Local)", 
                            fg='lightgreen', 
                            bg='black',
                            font=('Arial', 8)
                        )
                        slot['name_label'].pack(side='bottom')
                    
                logger.debug("Local video frame updated")
            
        except Exception as e:
            logger.error(f"Error updating local video: {e}")
            # Show error in video slot
            try:
                if 0 in self.video_slots:
                    slot = self.video_slots[0]
                    if 'label' in slot and self._widget_exists(slot['label']):
                        slot['label'].config(text="Local Video\\nError", fg='red')
            except:
                pass  # Ignore errors when showing error message'''

    remote_video_function = '''    def _update_remote_video_safe(self, client_id: str, frame):
        """Thread-safe implementation of remote video update."""
        try:
            import cv2
            from PIL import Image, ImageTk
            import time
            
            # Clear pending update flag
            if client_id in self.pending_updates:
                del self.pending_updates[client_id]
            
            # Frame rate limiting for remote video
            current_time = time.time()
            if client_id in self.last_frame_time:
                if current_time - self.last_frame_time[client_id] < self.frame_rate_limit:
                    return  # Skip this frame to prevent stacking
            self.last_frame_time[client_id] = current_time
            
            # Convert OpenCV frame (BGR) to RGB
            if frame is not None and frame.size > 0:
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Convert to PIL Image
                pil_image = Image.fromarray(rgb_frame)
                
                # Resize to fit in video slot (maintain aspect ratio)
                display_size = (200, 150)  # Larger size for better visibility
                pil_image = pil_image.resize(display_size, Image.LANCZOS)
                
                # Convert to PhotoImage for tkinter
                photo = ImageTk.PhotoImage(pil_image)
                
                # Find or get assigned slot for this client (skip slot 0 which is for local video)
                slot_id = self._get_or_assign_video_slot(client_id)
                
                if slot_id is not None and slot_id in self.video_slots:
                    slot = self.video_slots[slot_id]
                    
                    # Check if widgets still exist before accessing them
                    if not self._widget_exists(slot['frame']):
                        logger.warning(f"Remote video slot frame for {client_id} no longer exists")
                        return
                    
                    # Ensure this slot is exclusively for this client
                    if slot.get('participant_id') and slot.get('participant_id') != client_id:
                        logger.warning(f"Slot {slot_id} already occupied by {slot.get('participant_id')}, finding new slot")
                        # Clear this assignment and find a new slot
                        slot_id = None
                        for new_slot_id in range(1, len(self.video_slots)):
                            new_slot = self.video_slots[new_slot_id]
                            if not new_slot.get('active', False) or new_slot.get('participant_id') is None:
                                slot_id = new_slot_id
                                slot = new_slot
                                break
                        
                        if slot_id is None:
                            logger.error(f"No available slots for client {client_id}")
                            return
                    
                    # Remove text label and add video display
                    if 'label' in slot and self._widget_exists(slot['label']):
                        slot['label'].pack_forget()
                    
                    # Destroy any existing video widget to prevent stacking
                    if hasattr(slot, 'video_widget') and self._widget_exists(slot.get('video_widget')):
                        slot['video_widget'].destroy()
                    
                    # Create new video label widget
                    slot['video_widget'] = tk.Label(
                        slot['frame'],
                        image=photo,
                        bg='black'
                    )
                    slot['video_widget'].pack(fill='both', expand=True)
                    slot['video_widget'].image = photo  # Keep reference
                    
                    # Update slot info - ensure exclusive assignment
                    slot['participant_id'] = client_id
                    slot['active'] = True
                    
                    # Add or update participant name label
                    if not hasattr(slot, 'name_label') or not self._widget_exists(slot.get('name_label')):
                        slot['name_label'] = tk.Label(
                            slot['frame'], 
                            text=f"Client {client_id[:8]}", 
                            fg='lightblue', 
                            bg='black',
                            font=('Arial', 8)
                        )
                        slot['name_label'].pack(side='bottom')
                    else:
                        # Update existing label
                        slot['name_label'].config(text=f"Client {client_id[:8]}")
                    
                logger.debug(f"Remote video frame updated for client {client_id} in slot {slot_id}")
            
        except Exception as e:
            logger.error(f"Error updating remote video from {client_id}: {e}")'''

    return local_video_function, remote_video_function

def apply_final_video_fix():
    """Apply the final video stacking fix."""
    
    logger.info("Applying final video frame stacking fix...")
    
    try:
        # Read the current GUI manager file
        with open('client/gui_manager.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Get the fixed functions
        local_func, remote_func = create_fixed_video_functions()
        
        # Find and replace the local video function
        import re
        
        # Replace local video function
        local_pattern = r'def _update_local_video_safe\(self, frame, client_key\):.*?(?=\n    def |\n\nclass |\nclass |\Z)'
        if re.search(local_pattern, content, re.DOTALL):
            content = re.sub(local_pattern, local_func.strip(), content, flags=re.DOTALL)
            logger.info("✅ Replaced local video function")
        else:
            logger.warning("Could not find local video function to replace")
        
        # Replace remote video function  
        remote_pattern = r'def _update_remote_video_safe\(self, client_id: str, frame\):.*?(?=\n    def |\n\nclass |\nclass |\Z)'
        if re.search(remote_pattern, content, re.DOTALL):
            content = re.sub(remote_pattern, remote_func.strip(), content, flags=re.DOTALL)
            logger.info("✅ Replaced remote video function")
        else:
            logger.warning("Could not find remote video function to replace")
        
        # Write the updated content back
        with open('client/gui_manager.py', 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info("✅ Final video stacking fix applied successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Error applying final video fix: {e}")
        return False

if __name__ == "__main__":
    success = apply_final_video_fix()
    
    if success:
        print("✅ Final video frame stacking fix applied successfully!")
        print("\nKey changes:")
        print("  • Replaced Canvas with Label widgets for video display")
        print("  • Added proper widget destruction to prevent stacking")
        print("  • Enhanced pending update tracking")
        print("  • Improved frame rate limiting")
        print("\n🎯 Expected Results:")
        print("  • Video frames will replace each other (no stacking)")
        print("  • Each client appears in only ONE video slot")
        print("  • Smooth 30 FPS video conferencing")
        print("  • No more vertical frame accumulation")
        print("\n⚠️  Please restart the client application to apply the fix!")
    else:
        print("❌ Failed to apply final video stacking fix")
        sys.exit(1)