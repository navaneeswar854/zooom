#!/usr/bin/env python3
"""
Comprehensive test for audio and screen sharing fixes.
"""

import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_fixes():
    """Test both audio and screen sharing fixes."""
    print("🔧 Audio & Screen Sharing Fixes Test v2")
    print("=" * 50)
    
    from client.gui_manager import GUIManager
    
    # Create GUI manager
    gui = GUIManager()
    
    # Test audio callbacks
    def test_audio_callback(enabled):
        print(f"🔊 Audio callback: enabled={enabled}")
        if enabled:
            print("✅ Audio system should start (regardless of mute state)")
        else:
            print("❌ Audio system should stop")
    
    def test_mute_callback(muted):
        print(f"🔇 Mute callback: muted={muted}")
        print(f"   Audio system stays running, just {'muted' if muted else 'unmuted'}")
    
    # Set up callbacks
    if gui.audio_frame:
        gui.audio_frame.set_audio_callback(test_audio_callback)
        gui.audio_frame.set_mute_callback(test_mute_callback)
        print("✅ Audio callbacks set up")
    
    # Add test instructions to chat
    if gui.chat_frame:
        gui.chat_frame.add_system_message("🧪 Audio & Screen Sharing Fixes Test")
        gui.chat_frame.add_system_message("")
        gui.chat_frame.add_system_message("📋 Audio Test Instructions:")
        gui.chat_frame.add_system_message("1. Go to Video Conference tab")
        gui.chat_frame.add_system_message("2. Click 'Enable Audio' - should work")
        gui.chat_frame.add_system_message("3. Click 'Mute' - should mute but keep audio running")
        gui.chat_frame.add_system_message("4. Click 'Unmute' - should restore audio")
        gui.chat_frame.add_system_message("")
        gui.chat_frame.add_system_message("🖥️ Screen Share Test Instructions:")
        gui.chat_frame.add_system_message("1. Go to Screen Share tab")
        gui.chat_frame.add_system_message("2. Request presenter role")
        gui.chat_frame.add_system_message("3. Start screen sharing")
        gui.chat_frame.add_system_message("4. You should see your own screen!")
        gui.chat_frame.add_system_message("5. Status should show 'you can see your own share'")
    
    print("🎯 Test Instructions:")
    print()
    print("Audio Testing:")
    print("1. Switch to 'Video Conference' tab")
    print("2. Click 'Enable Audio' button")
    print("   → Should work regardless of mute state")
    print("   → Console shows: 'Audio callback: enabled=True'")
    print("3. Click 'Mute' button")
    print("   → Should mute but keep audio system running")
    print("   → Console shows: 'Mute callback: muted=True'")
    print("4. Click 'Unmute' button")
    print("   → Should restore audio")
    print("   → Console shows: 'Mute callback: muted=False'")
    print()
    print("Screen Sharing Testing:")
    print("1. Switch to 'Screen Share' tab")
    print("2. Click 'Request Presenter Role'")
    print("3. Click 'Start Screen Share'")
    print("4. You should see your own screen in the display area")
    print("5. Status should show 'Sharing your screen (you can see your own share)'")
    print()
    print("Expected Results:")
    print("✅ Audio starts even when muted")
    print("✅ Mute/unmute works independently")
    print("✅ Presenter sees their own screen share")
    print("✅ Clear visual feedback for all states")
    
    # Start GUI
    gui.run()

if __name__ == "__main__":
    test_fixes()