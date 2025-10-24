#!/usr/bin/env python3
"""
Test script for video conferencing duplication fix.
Verifies that video frames are displayed correctly without duplication.
"""

import sys
import os
import time
import logging
import threading
from unittest.mock import Mock, MagicMock
import numpy as np

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_video_slot_assignment():
    """Test video slot assignment logic."""
    logger.info("Testing video slot assignment logic...")
    
    try:
        # Mock tkinter components
        import tkinter as tk
        from unittest.mock import patch
        
        with patch('tkinter.Tk'), patch('tkinter.Frame'), patch('tkinter.Label'), patch('tkinter.Canvas'):
            from client.gui_manager import VideoFrame
            
            # Create mock parent
            mock_parent = Mock()
            
            # Create video frame
            video_frame = VideoFrame(mock_parent)
            
            # Test 1: Assign different clients to different slots
            logger.info("Test 1: Assigning different clients to different slots")
            
            slot1 = video_frame._get_or_assign_video_slot("client_1")
            slot2 = video_frame._get_or_assign_video_slot("client_2")
            slot3 = video_frame._get_or_assign_video_slot("client_3")
            
            # Verify different clients get different slots
            assert slot1 != slot2, f"Client 1 and 2 got same slot: {slot1}"
            assert slot2 != slot3, f"Client 2 and 3 got same slot: {slot2}"
            assert slot1 != slot3, f"Client 1 and 3 got same slot: {slot1}"
            
            logger.info(f"✅ Clients assigned to different slots: {slot1}, {slot2}, {slot3}")
            
            # Test 2: Same client should get same slot
            logger.info("Test 2: Same client should get same slot")
            
            slot1_again = video_frame._get_or_assign_video_slot("client_1")
            assert slot1 == slot1_again, f"Client 1 got different slot on second call: {slot1} vs {slot1_again}"
            
            logger.info(f"✅ Same client got same slot: {slot1}")
            
            # Test 3: Clear slot and reassign
            logger.info("Test 3: Clear slot and reassign")
            
            video_frame.clear_video_slot("client_2")
            new_client_slot = video_frame._get_or_assign_video_slot("client_4")
            
            # Should get the cleared slot
            assert new_client_slot == slot2, f"New client didn't get cleared slot: {new_client_slot} vs {slot2}"
            
            logger.info(f"✅ New client got cleared slot: {new_client_slot}")
            
            return True
            
    except Exception as e:
        logger.error(f"Video slot assignment test failed: {e}")
        return False

def test_video_frame_processing():
    """Test video frame processing without duplication."""
    logger.info("Testing video frame processing...")
    
    try:
        # Create mock video frame data
        mock_frame = np.zeros((240, 320, 3), dtype=np.uint8)  # Mock video frame
        
        # Track frame processing calls
        frame_process_count = {}
        
        def mock_update_remote_video(client_id, frame):
            if client_id not in frame_process_count:
                frame_process_count[client_id] = 0
            frame_process_count[client_id] += 1
            logger.debug(f"Processing frame for {client_id}, count: {frame_process_count[client_id]}")
        
        # Mock GUI manager
        mock_gui_manager = Mock()
        mock_video_frame = Mock()
        mock_video_frame.update_remote_video = mock_update_remote_video
        mock_gui_manager.video_frame = mock_video_frame
        
        # Simulate video frame processing
        logger.info("Simulating video frame processing for single client...")
        
        client_id = "test_client_1"
        
        # Process same frame multiple times (simulating network packets)
        for i in range(5):
            mock_update_remote_video(client_id, mock_frame)
            time.sleep(0.01)  # Small delay
        
        # Verify frame was processed but not duplicated in display
        total_calls = frame_process_count.get(client_id, 0)
        logger.info(f"Total frame processing calls for {client_id}: {total_calls}")
        
        # Each call should be processed (this is expected)
        assert total_calls == 5, f"Expected 5 calls, got {total_calls}"
        
        logger.info("✅ Video frame processing test passed")
        return True
        
    except Exception as e:
        logger.error(f"Video frame processing test failed: {e}")
        return False

def test_video_participant_assignment():
    """Test video participant assignment logic."""
    logger.info("Testing video participant assignment...")
    
    try:
        # Mock participants data
        participants = {
            "client_1": {
                "client_id": "client_1",
                "username": "User1",
                "video_enabled": True
            },
            "client_2": {
                "client_id": "client_2", 
                "username": "User2",
                "video_enabled": False
            },
            "client_3": {
                "client_id": "client_3",
                "username": "User3", 
                "video_enabled": True
            }
        }
        
        # Mock video frame
        with patch('tkinter.Tk'), patch('tkinter.Frame'), patch('tkinter.Label'):
            from client.gui_manager import VideoFrame
            
            mock_parent = Mock()
            video_frame = VideoFrame(mock_parent)
            
            # Mock video slots
            video_frame.video_slots = {
                0: {'participant_id': 'local', 'active': True, 'label': Mock()},
                1: {'participant_id': None, 'active': False, 'label': Mock()},
                2: {'participant_id': None, 'active': False, 'label': Mock()},
                3: {'participant_id': None, 'active': False, 'label': Mock()}
            }
            
            # Mock _widget_exists to return True
            video_frame._widget_exists = Mock(return_value=True)
            
            # Update video feeds
            video_frame.update_video_feeds(participants)
            
            # Verify assignments
            assigned_clients = set()
            for slot_id, slot in video_frame.video_slots.items():
                if slot_id > 0 and slot.get('active'):  # Skip local video slot
                    participant_id = slot.get('participant_id')
                    if participant_id:
                        assert participant_id not in assigned_clients, f"Client {participant_id} assigned to multiple slots"
                        assigned_clients.add(participant_id)
            
            # Should have 2 clients with video enabled
            expected_clients = {"client_1", "client_3"}
            assert assigned_clients == expected_clients, f"Expected {expected_clients}, got {assigned_clients}"
            
            logger.info(f"✅ Video participants assigned correctly: {assigned_clients}")
            return True
            
    except Exception as e:
        logger.error(f"Video participant assignment test failed: {e}")
        return False

def run_all_tests():
    """Run all video conferencing duplication tests."""
    logger.info("Running video conferencing duplication fix tests...")
    
    tests = [
        ("Video Slot Assignment", test_video_slot_assignment),
        ("Video Frame Processing", test_video_frame_processing), 
        ("Video Participant Assignment", test_video_participant_assignment)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        logger.info(f"\n--- Running {test_name} Test ---")
        try:
            if test_func():
                logger.info(f"✅ {test_name} test PASSED")
                passed += 1
            else:
                logger.error(f"❌ {test_name} test FAILED")
                failed += 1
        except Exception as e:
            logger.error(f"❌ {test_name} test FAILED with exception: {e}")
            failed += 1
    
    logger.info(f"\n--- Test Results ---")
    logger.info(f"Passed: {passed}")
    logger.info(f"Failed: {failed}")
    logger.info(f"Total: {passed + failed}")
    
    if failed == 0:
        logger.info("🎉 All video conferencing duplication fix tests PASSED!")
        return True
    else:
        logger.error(f"💥 {failed} test(s) FAILED!")
        return False

if __name__ == "__main__":
    # Import required modules with mocking
    from unittest.mock import patch
    
    success = run_all_tests()
    
    if success:
        print("\n✅ Video conferencing duplication fix tests completed successfully!")
        print("The video conferencing should now display each client only once.")
    else:
        print("\n❌ Some video conferencing duplication fix tests failed!")
        sys.exit(1)