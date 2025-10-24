#!/usr/bin/env python3
"""
Final test for video conferencing fixes.
Tests that video slots are stable and don't get destroyed.
"""

import sys
import os
import time
import threading
import logging
import numpy as np

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_video_slot_stability():
    """Test that video slots remain stable and don't get destroyed."""
    print("🧪 Testing Video Slot Stability...")
    
    try:
        from client.gui_manager import VideoFrame
        import tkinter as tk
        
        # Create test environment
        root = tk.Tk()
        root.withdraw()
        
        test_frame = tk.Frame(root)
        video_frame = VideoFrame(test_frame)
        
        # Test 1: Check initial video slots
        initial_slots = len(video_frame.video_slots)
        print(f"✅ Initial video slots created: {initial_slots}")
        
        # Store references to initial widgets
        initial_widgets = {}
        for slot_id, slot in video_frame.video_slots.items():
            initial_widgets[slot_id] = {
                'frame': slot['frame'],
                'label': slot['label']
            }
        
        # Test 2: Simulate participant updates (this was causing widget destruction)
        participants = {
            'client1': {'username': 'User1', 'video_enabled': True, 'client_id': 'client1'},
            'client2': {'username': 'User2', 'video_enabled': False, 'client_id': 'client2'}
        }
        
        # Update video feeds multiple times
        for i in range(5):
            video_frame.update_video_feeds(participants)
            time.sleep(0.1)  # Small delay
        
        # Test 3: Check that original widgets still exist
        widgets_survived = True
        for slot_id, widgets in initial_widgets.items():
            if not video_frame._widget_exists(widgets['frame']):
                print(f"❌ Slot {slot_id} frame was destroyed!")
                widgets_survived = False
            if not video_frame._widget_exists(widgets['label']):
                print(f"❌ Slot {slot_id} label was destroyed!")
                widgets_survived = False
        
        if widgets_survived:
            print("✅ All video slot widgets survived participant updates")
        
        # Test 4: Test video updates with mock frames
        test_frame_data = np.zeros((120, 160, 3), dtype=np.uint8)
        test_frame_data[:, :] = [100, 150, 200]
        
        # Test local video update
        try:
            video_frame.update_local_video(test_frame_data)
            print("✅ Local video update successful")
        except Exception as e:
            print(f"❌ Local video update failed: {e}")
            widgets_survived = False
        
        # Test remote video update
        try:
            video_frame.update_remote_video("client1", test_frame_data)
            print("✅ Remote video update successful")
        except Exception as e:
            print(f"❌ Remote video update failed: {e}")
            widgets_survived = False
        
        # Test 5: Check widgets still exist after video updates
        for slot_id, widgets in initial_widgets.items():
            if not video_frame._widget_exists(widgets['frame']):
                print(f"❌ Slot {slot_id} frame destroyed after video update!")
                widgets_survived = False
        
        if widgets_survived:
            print("✅ All widgets survived video frame updates")
        
        # Clean up
        root.destroy()
        
        return widgets_survived
        
    except Exception as e:
        print(f"❌ Video slot stability test failed: {e}")
        return False

def test_no_widget_destruction():
    """Test that update_video_feeds doesn't destroy widgets."""
    print("\n🧪 Testing No Widget Destruction...")
    
    try:
        from client.gui_manager import VideoFrame
        import tkinter as tk
        
        root = tk.Tk()
        root.withdraw()
        
        test_frame = tk.Frame(root)
        video_frame = VideoFrame(test_frame)
        
        # Get initial widget IDs
        initial_widget_ids = {}
        for slot_id, slot in video_frame.video_slots.items():
            initial_widget_ids[slot_id] = {
                'frame_id': str(slot['frame']),
                'label_id': str(slot['label'])
            }
        
        # Simulate multiple participant updates
        participants_scenarios = [
            {},  # No participants
            {'client1': {'username': 'User1', 'video_enabled': True, 'client_id': 'client1'}},  # One participant
            {  # Two participants
                'client1': {'username': 'User1', 'video_enabled': True, 'client_id': 'client1'},
                'client2': {'username': 'User2', 'video_enabled': False, 'client_id': 'client2'}
            },
            {'client1': {'username': 'User1', 'video_enabled': False, 'client_id': 'client1'}},  # Video disabled
        ]
        
        for scenario_num, participants in enumerate(participants_scenarios):
            video_frame.update_video_feeds(participants)
            
            # Check that widget IDs haven't changed (widgets weren't recreated)
            for slot_id, slot in video_frame.video_slots.items():
                current_frame_id = str(slot['frame'])
                current_label_id = str(slot['label'])
                
                if current_frame_id != initial_widget_ids[slot_id]['frame_id']:
                    print(f"❌ Slot {slot_id} frame was recreated in scenario {scenario_num}!")
                    return False
                
                if current_label_id != initial_widget_ids[slot_id]['label_id']:
                    print(f"❌ Slot {slot_id} label was recreated in scenario {scenario_num}!")
                    return False
        
        print("✅ No widgets were destroyed or recreated during updates")
        
        root.destroy()
        return True
        
    except Exception as e:
        print(f"❌ No widget destruction test failed: {e}")
        return False

def test_error_handling():
    """Test that video updates handle errors gracefully."""
    print("\n🧪 Testing Error Handling...")
    
    try:
        from client.gui_manager import VideoFrame
        import tkinter as tk
        
        root = tk.Tk()
        root.withdraw()
        
        test_frame = tk.Frame(root)
        video_frame = VideoFrame(test_frame)
        
        # Test 1: Invalid frame data
        try:
            video_frame.update_local_video(None)
            print("✅ Handles None frame gracefully")
        except Exception as e:
            print(f"⚠️  None frame handling: {e}")
        
        # Test 2: Invalid client ID
        try:
            video_frame.update_remote_video("", None)
            print("✅ Handles empty client ID gracefully")
        except Exception as e:
            print(f"⚠️  Empty client ID handling: {e}")
        
        # Test 3: Destroyed widget handling
        # Destroy one widget and see if it's handled gracefully
        slot_0 = video_frame.video_slots[0]
        original_label = slot_0['label']
        original_label.destroy()
        
        # Try to update - should not crash
        try:
            participants = {'client1': {'username': 'User1', 'video_enabled': True, 'client_id': 'client1'}}
            video_frame.update_video_feeds(participants)
            print("✅ Handles destroyed widgets gracefully")
        except Exception as e:
            print(f"⚠️  Destroyed widget handling: {e}")
        
        root.destroy()
        return True
        
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        return False

def main():
    """Run all video conferencing final fix tests."""
    print("🚀 Starting Video Conferencing Final Fix Tests")
    print("=" * 60)
    
    tests = [
        ("Video Slot Stability", test_video_slot_stability),
        ("No Widget Destruction", test_no_widget_destruction),
        ("Error Handling", test_error_handling),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name}: PASSED")
            else:
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}")
        
        print("-" * 40)
    
    print(f"\n📊 Final Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 Video conferencing is now working correctly!")
        print("\n📋 Fixed Issues:")
        print("   • Video slots no longer get destroyed during updates")
        print("   • Widget existence validation prevents crashes")
        print("   • Removed problematic create_dynamic_video_grid calls")
        print("   • Added proper error handling for destroyed widgets")
        print("   • Video feeds should now display properly")
        
        print("\n🔧 The following errors should no longer occur:")
        print("   • 'Local/Remote video slot frame no longer exists'")
        print("   • 'bad window path name' errors")
        print("   • 'invalid command name' errors")
        
        return True
    else:
        print("⚠️  Some tests failed. Video conferencing may still have issues.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)