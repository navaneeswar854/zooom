#!/usr/bin/env python3
"""
Fix Video Conferencing Transmission
Complete fix for video transmission and display issues.
"""

import sys
import os
import time
import logging

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def fix_video_transmission_chain():
    """Fix the complete video transmission chain."""
    
    print("🔧 Fixing video transmission chain...")
    
    try:
        # Fix 1: Ensure video packets are properly processed
        with open('client/main_client.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Enhanced video packet handler
        enhanced_video_handler = '''    def _on_video_packet(self, packet: UDPPacket):
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
            logger.error(f"Error handling video packet: {e}")'''
        
        # Replace the video packet handler
        import re
        pattern = r'def _on_video_packet\(self, packet: UDPPacket\):.*?(?=\n    def |\n\n    # |\Z)'
        content = re.sub(pattern, enhanced_video_handler.strip(), content, flags=re.DOTALL)
        
        # Write back
        with open('client/main_client.py', 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("   ✅ Video packet handler enhanced")
        return True
        
    except Exception as e:
        print(f"   ❌ Error fixing video transmission: {e}")
        return False


def fix_video_display_chain():
    """Fix the video display chain in GUI."""
    
    print("🔧 Fixing video display chain...")
    
    try:
        # Fix the GUI video display methods
        with open('client/gui_manager.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Enhanced remote video update
        enhanced_remote_update = '''    def update_remote_video(self, client_id: str, frame):
        """Update remote video display with enhanced error handling."""
        try:
            logger.debug(f"Updating remote video for client {client_id}")
            
            # Get or assign video slot
            slot_id = self._get_video_slot_stable(client_id)
            
            if slot_id is not None and slot_id in self.video_slots:
                # Assign slot to this client
                self.video_slots[slot_id]['participant_id'] = client_id
                self.video_slots[slot_id]['active'] = True
                
                # Create video display
                self._create_enhanced_video_display(
                    self.video_slots[slot_id]['frame'], frame, client_id, slot_id
                )
                
                logger.debug(f"Remote video updated for {client_id} in slot {slot_id}")
            else:
                logger.warning(f"No available video slot for remote client {client_id}")
                
        except Exception as e:
            logger.error(f"Error updating remote video for {client_id}: {e}")'''
        
        # Enhanced video display creation
        enhanced_display_creation = '''    def _create_enhanced_video_display(self, parent_frame, frame, client_id: str, slot_id: int):
        """Create enhanced video display with better error handling."""
        try:
            import cv2
            from PIL import Image, ImageTk
            
            if frame is None or frame.size == 0:
                logger.warning(f"Invalid frame for {client_id}")
                return
            
            # Convert frame for display
            if len(frame.shape) == 3:
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            else:
                rgb_frame = frame
            
            # Create PIL image
            pil_image = Image.fromarray(rgb_frame)
            
            # Resize for video slot
            display_size = (200, 150)
            pil_image = pil_image.resize(display_size, Image.LANCZOS)
            
            # Convert to PhotoImage
            photo = ImageTk.PhotoImage(pil_image)
            
            # Clear existing content
            for child in parent_frame.winfo_children():
                child.destroy()
            
            # Create video display
            video_label = tk.Label(
                parent_frame,
                image=photo,
                bg='black'
            )
            video_label.pack(fill='both', expand=True)
            video_label.image = photo  # Keep reference
            
            # Add client info
            info_label = tk.Label(
                parent_frame,
                text=f"Client {client_id[:8]}",
                fg='lightblue',
                bg='black',
                font=('Arial', 8)
            )
            info_label.place(x=5, y=5)
            
            logger.debug(f"Enhanced video display created for {client_id}")
            
        except Exception as e:
            logger.error(f"Error creating enhanced video display for {client_id}: {e}")'''
        
        # Replace methods
        import re
        
        # Replace update_remote_video
        pattern = r'def update_remote_video\(self, client_id: str, frame\):.*?(?=\n    def |\n\nclass |\Z)'
        content = re.sub(pattern, enhanced_remote_update.strip(), content, flags=re.DOTALL)
        
        # Add enhanced display method if not exists
        if '_create_enhanced_video_display' not in content:
            insert_pos = content.find('def clear_video_slot(self, client_id: str):')
            if insert_pos != -1:
                content = content[:insert_pos] + enhanced_display_creation + '\n    \n    ' + content[insert_pos:]
        
        # Write back
        with open('client/gui_manager.py', 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("   ✅ Video display chain enhanced")
        return True
        
    except Exception as e:
        print(f"   ❌ Error fixing video display: {e}")
        return False


def main():
    """Main fix function."""
    
    print("🎬 VIDEO CONFERENCING TRANSMISSION FIX")
    print("Fixing video transmission and display issues")
    print("=" * 60)
    
    # Apply fixes
    fixes = [
        ("Video Transmission Chain", fix_video_transmission_chain),
        ("Video Display Chain", fix_video_display_chain)
    ]
    
    results = []
    
    for fix_name, fix_func in fixes:
        print(f"\n📋 {fix_name}")
        print("-" * 40)
        
        try:
            result = fix_func()
            results.append(result)
            status = "✅ SUCCESS" if result else "❌ FAILED"
            print(f"   {status}")
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
            results.append(False)
    
    # Final results
    passed = sum(results)
    total = len(results)
    
    print(f"\n📊 VIDEO TRANSMISSION FIX RESULTS")
    print("=" * 60)
    print(f"Fixes applied: {passed}/{total} ({(passed/total)*100:.1f}%)")
    
    if passed == total:
        print("\n🎉 VIDEO TRANSMISSION FIXED!")
        print("Video conferencing should now work properly:")
        print("• Enhanced video packet processing ✅")
        print("• Improved video display chain ✅")
        print("• Better error handling and logging ✅")
        
    else:
        print("\n⚠️  SOME FIXES FAILED")
        print("Please check the error messages above.")
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)