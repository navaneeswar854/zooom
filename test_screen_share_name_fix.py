#!/usr/bin/env python3
"""
Test script to verify screen sharing displays names instead of IDs and stopping works correctly.
"""

import sys
import os
import time
from unittest.mock import Mock

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_presenter_name_resolution():
    """Test that presenter names are resolved correctly."""
    print("👤 Testing Presenter Name Resolution...")
    
    try:
        from client.screen_manager import ScreenManager
        
        # Mock connection manager with participants
        mock_connection_manager = Mock()
        mock_connection_manager.get_client_id.return_value = "local_client_123"
        mock_connection_manager.get_participants.return_value = {
            "alice_456": {"username": "Alice Johnson"},
            "bob_789": {"username": "Bob Smith"},
            "local_client_123": {"username": "You"}
        }
        
        # Mock GUI manager
        mock_gui_manager = Mock()
        
        # Create screen manager
        screen_manager = ScreenManager(
            client_id="local_client_123",
            connection_manager=mock_connection_manager,
            gui_manager=mock_gui_manager
        )
        
        print("✅ Screen manager created successfully")
        
        # Test presenter name resolution
        test_cases = [
            ("alice_456", "Alice Johnson"),
            ("bob_789", "Bob Smith"),
            ("local_client_123", "You (Presenter)"),
            ("unknown_999", "User unknown_"),
            ("", "Unknown Presenter")
        ]
        
        all_passed = True
        for presenter_id, expected_name in test_cases:
            try:
                actual_name = screen_manager._get_presenter_name(presenter_id)
                if actual_name == expected_name or (expected_name.startswith("User unknown_") and actual_name.startswith("User unknown_")):
                    print(f"✅ Presenter name for '{presenter_id}': '{actual_name}'")
                else:
                    print(f"⚠️ Presenter name for '{presenter_id}': expected '{expected_name}', got '{actual_name}'")
                    all_passed = False
            except Exception as e:
                print(f"❌ Presenter name resolution failed for '{presenter_id}': {e}")
                all_passed = False
        
        return all_passed
        
    except Exception as e:
        print(f"❌ Presenter name resolution test failed: {e}")
        return False

def test_screen_share_stopping():
    """Test that screen sharing can be stopped properly."""
    print("🛑 Testing Screen Share Stopping...")
    
    try:
        from client.gui_manager import GUIManager
        
        # Create GUI manager
        gui = GUIManager()
        
        print("✅ GUI created successfully")
        
        # Track screen share calls
        screen_share_calls = []
        def mock_screen_share_callback(enabled):
            screen_share_calls.append(enabled)
            print(f"📞 Screen share callback: {enabled}")
            
            # Simulate the state change in GUI
            gui.set_screen_sharing_status(enabled)
        
        # Set up callbacks
        gui.set_module_callbacks(
            video_callback=lambda x: None,
            audio_callback=lambda x: None,
            message_callback=lambda x: None,
            screen_share_callback=mock_screen_share_callback,
            file_upload_callback=lambda x: None,
            file_download_callback=lambda x: None
        )
        
        print("✅ Callbacks set successfully")
        
        # Test starting screen share
        try:
            gui._toggle_screen_share()
            print("✅ Screen share start works")
            
            if screen_share_calls and screen_share_calls[-1] == True:
                print("✅ Screen share started correctly")
            else:
                print("❌ Screen share start failed")
                return False
                
        except Exception as e:
            print(f"❌ Screen share start failed: {e}")
            return False
        
        # Test stopping screen share
        try:
            gui._toggle_screen_share()
            print("✅ Screen share stop works")
            
            if len(screen_share_calls) >= 2 and screen_share_calls[-1] == False:
                print("✅ Screen share stopped correctly")
            else:
                print("❌ Screen share stop failed")
                return False
                
        except Exception as e:
            print(f"❌ Screen share stop failed: {e}")
            return False
        
        # Check button state
        try:
            if hasattr(gui, 'screen_share_btn'):
                button_text = gui.screen_share_btn.cget('text')
                if "Share Screen" in button_text:
                    print("✅ Button state reset correctly after stopping")
                else:
                    print(f"⚠️ Button state may not be correct: {button_text}")
            else:
                print("⚠️ Screen share button not found")
        except Exception as e:
            print(f"⚠️ Could not check button state: {e}")
        
        # Update display
        gui.root.update()
        
        print("✅ Screen share stopping test completed")
        
        # Close after short delay
        gui.root.after(1000, gui.close)
        gui.run()
        
        return True
        
    except Exception as e:
        print(f"❌ Screen share stopping test failed: {e}")
        return False

def main():
    """Run the screen share name and stopping tests."""
    print("🚀 Starting Screen Share Name and Stopping Tests")
    print("=" * 60)
    
    tests = [
        ("Presenter Name Resolution", test_presenter_name_resolution),
        ("Screen Share Stopping", test_screen_share_stopping)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n📋 Running {test_name}...")
        try:
            result = test_func()
            results.append((test_name, result))
            if result:
                print(f"✅ {test_name} PASSED")
            else:
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            print(f"❌ {test_name} FAILED with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed!")
        print("👤 Screen sharing now displays names instead of IDs")
        print("🛑 Screen sharing stopping works correctly")
    else:
        print("⚠️ Some tests failed - please check the implementation")

if __name__ == "__main__":
    main()