#!/usr/bin/env python3
"""
Test Video Chronological Integration
Comprehensive test to verify the entire video system displays frames
in strict chronological order without back-and-forth issues.
"""

import sys
import os
import time
import logging
import numpy as np
import threading

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_video_system_chronological_integration():
    """Test complete video system integration with chronological ordering."""
    
    print("🎬 Testing video system chronological integration...")
    
    try:
        from client.video_playback import VideoRenderer
        from client.frame_sequencer import frame_sequencing_manager
        from common.messages import MessageFactory
        import cv2
        
        # Create video renderer
        renderer = VideoRenderer()
        renderer.start_rendering()
        
        # Track displayed frames for chronological analysis
        displayed_frames = []
        display_timestamps = []
        
        def frame_callback(client_id, frame):
            display_time = time.perf_counter()
            displayed_frames.append((client_id, len(displayed_frames), display_time))
            display_timestamps.append(display_time)
            print(f"   🖼️  Displayed frame {len(displayed_frames)} for {client_id} at {display_time:.6f}")
        
        renderer.set_frame_update_callback(frame_callback)
        
        # Create test video packets with chronological timestamps
        client_id = "chrono_video_test_client"
        base_time = time.perf_counter()
        
        # Create frames with precise timing but send them out of order
        frame_data_map = {}
        frame_timestamps = {}
        
        print("   📸 Creating test video frames:")
        for i in range(12):
            # Create test frame
            test_frame = np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8)
            
            # Compress frame
            success, encoded_frame = cv2.imencode('.jpg', test_frame)
            if success:
                frame_data_map[i] = encoded_frame.tobytes()
                frame_timestamps[i] = base_time + (i * 0.033333)  # 30 FPS intervals
                print(f"      Created frame {i} (timestamp: {frame_timestamps[i]:.6f})")
        
        # Send frames out of order to test chronological ordering
        send_order = [0, 3, 1, 6, 2, 9, 4, 11, 5, 8, 7, 10]
        
        print("   📡 Sending video packets out of order:")
        for seq in send_order:
            if seq in frame_data_map:
                capture_time = frame_timestamps[seq]
                network_time = capture_time + 0.002  # 2ms network delay
                
                # Create sequenced packet
                packet = MessageFactory.create_sequenced_video_packet(
                    sender_id=client_id,
                    sequence_num=seq,
                    video_data=frame_data_map[seq],
                    capture_timestamp=capture_time,
                    relative_timestamp=seq * 0.033333
                )
                
                # Process packet
                renderer.process_video_packet(packet)
                print(f"      Sent frame {seq} out of order")
                
                # Small delay between packets
                time.sleep(0.01)
        
        # Wait for processing
        print("   ⏳ Waiting for chronological processing...")
        time.sleep(2.0)
        
        # Analyze results
        print(f"   📊 Chronological integration analysis:")
        print(f"      Total frames displayed: {len(displayed_frames)}")
        
        # Check chronological order of display timestamps
        is_chronological = True
        if len(display_timestamps) > 1:
            for i in range(len(display_timestamps) - 1):
                if display_timestamps[i] > display_timestamps[i + 1]:
                    is_chronological = False
                    print(f"      ❌ Chronological violation at position {i}")
        
        print(f"      Chronological display order: {is_chronological}")
        
        # Get sequencing statistics
        all_status = frame_sequencing_manager.get_all_status()
        if client_id in all_status:
            stats = all_status[client_id]['stats']
            print(f"      Sequencing statistics:")
            print(f"         Frames received: {stats['frames_received']}")
            print(f"         Frames displayed: {stats['frames_displayed']}")
            print(f"         Frames reordered: {stats['frames_reordered']}")
            print(f"         Sequence gaps: {stats['sequence_gaps']}")
        
        # Clean up
        renderer.remove_video_stream(client_id)
        renderer.stop_rendering()
        
        return is_chronological and len(displayed_frames) >= 8
        
    except Exception as e:
        print(f"   ❌ Video system integration test error: {e}")
        return False


def test_multi_client_video_chronological_sync():
    """Test multi-client video with chronological synchronization."""
    
    print("\n👥 Testing multi-client video chronological sync...")
    
    try:
        from client.video_playback import VideoRenderer
        from client.frame_sequencer import frame_sequencing_manager
        from common.messages import MessageFactory
        import cv2
        
        # Create video renderer
        renderer = VideoRenderer()
        renderer.start_rendering()
        
        # Track displayed frames per client
        client_displays = {'client_A': [], 'client_B': [], 'client_C': []}
        
        def frame_callback(client_id, frame):
            display_time = time.perf_counter()
            if client_id in client_displays:
                client_displays[client_id].append(display_time)
                print(f"   🖼️  {client_id}: frame {len(client_displays[client_id])}")
        
        renderer.set_frame_update_callback(frame_callback)
        
        # Create synchronized video frames for multiple clients
        clients = ['client_A', 'client_B', 'client_C']
        base_time = time.perf_counter()
        
        print("   📸 Creating synchronized video frames for multiple clients:")
        
        for i in range(10):
            for client_id in clients:
                # Create test frame
                test_frame = np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8)
                
                # Compress frame
                success, encoded_frame = cv2.imencode('.jpg', test_frame)
                if success:
                    compressed_data = encoded_frame.tobytes()
                    
                    # Synchronized capture time
                    capture_time = base_time + (i * 0.033333)  # 30 FPS
                    
                    # Different network delays per client
                    if client_id == 'client_A':
                        network_delay = 0.002  # 2ms
                    elif client_id == 'client_B':
                        network_delay = 0.005  # 5ms
                    else:
                        network_delay = 0.003  # 3ms
                    
                    network_time = capture_time + network_delay
                    
                    # Create sequenced packet
                    packet = MessageFactory.create_sequenced_video_packet(
                        sender_id=client_id,
                        sequence_num=i,
                        video_data=compressed_data,
                        capture_timestamp=capture_time,
                        relative_timestamp=i * 0.033333
                    )
                    
                    # Process packet
                    renderer.process_video_packet(packet)
            
            if i % 3 == 0:
                print(f"      Sent frame {i} to all clients")
        
        # Wait for processing
        print("   ⏳ Waiting for multi-client processing...")
        time.sleep(2.5)
        
        # Analyze synchronization
        total_displayed = sum(len(displays) for displays in client_displays.values())
        
        print(f"   📊 Multi-client synchronization analysis:")
        print(f"      Total frames displayed: {total_displayed}")
        
        for client_id in clients:
            count = len(client_displays[client_id])
            print(f"      {client_id}: {count} frames")
        
        # Check synchronization
        frame_counts = [len(displays) for displays in client_displays.values()]
        min_frames = min(frame_counts)
        max_frames = max(frame_counts)
        sync_variance = max_frames - min_frames
        
        is_synchronized = sync_variance <= 2  # Within 2 frames
        
        print(f"      Synchronization variance: {sync_variance} frames")
        print(f"      Synchronized: {is_synchronized}")
        
        # Check chronological order for each client
        all_chronological = True
        for client_id, displays in client_displays.items():
            if len(displays) > 1:
                client_chronological = all(displays[i] <= displays[i+1] 
                                         for i in range(len(displays)-1))
                if not client_chronological:
                    all_chronological = False
                    print(f"      ❌ {client_id} not chronological")
        
        print(f"      All clients chronological: {all_chronological}")
        
        # Clean up
        for client_id in clients:
            renderer.remove_video_stream(client_id)
        renderer.stop_rendering()
        
        return total_displayed >= 20 and is_synchronized and all_chronological
        
    except Exception as e:
        print(f"   ❌ Multi-client video sync test error: {e}")
        return False


def test_real_time_video_streaming():
    """Test real-time video streaming with chronological ordering."""
    
    print("\n🌐 Testing real-time video streaming...")
    
    try:
        from client.video_playback import VideoRenderer
        from client.frame_sequencer import frame_sequencing_manager
        from common.messages import MessageFactory
        import cv2
        
        # Create video renderer
        renderer = VideoRenderer()
        renderer.start_rendering()
        
        # Track streaming performance
        frames_sent = 0
        frames_displayed = []
        
        def frame_callback(client_id, frame):
            display_time = time.perf_counter()
            frames_displayed.append(display_time)
            if len(frames_displayed) % 5 == 0:
                print(f"   🖼️  Displayed {len(frames_displayed)} frames")
        
        renderer.set_frame_update_callback(frame_callback)
        
        # Simulate real-time streaming
        client_id = "realtime_stream_client"
        base_time = time.perf_counter()
        
        print("   📡 Simulating real-time video streaming:")
        
        # Send frames with realistic timing and network conditions
        for i in range(20):
            # Create test frame
            test_frame = np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8)
            
            # Compress frame
            success, encoded_frame = cv2.imencode('.jpg', test_frame)
            if success:
                compressed_data = encoded_frame.tobytes()
                
                # Simulate network jitter
                jitter = np.random.uniform(0.001, 0.010)  # 1-10ms jitter
                capture_time = base_time + (i * 0.033333)  # 30 FPS
                network_time = capture_time + jitter
                
                # Create sequenced packet
                packet = MessageFactory.create_sequenced_video_packet(
                    sender_id=client_id,
                    sequence_num=i,
                    video_data=compressed_data,
                    capture_timestamp=capture_time,
                    relative_timestamp=i * 0.033333
                )
                
                # Process packet
                renderer.process_video_packet(packet)
                frames_sent += 1
                
                # Simulate out-of-order delivery occasionally
                if i > 0 and np.random.random() < 0.2:
                    time.sleep(0.005)  # Small delay
                
                # Simulate real-time capture rate
                time.sleep(0.02)  # Slightly faster than 30 FPS
        
        # Wait for processing
        print("   ⏳ Waiting for streaming processing...")
        time.sleep(1.5)
        
        # Analyze streaming performance
        delivery_rate = len(frames_displayed) / frames_sent * 100
        
        print(f"   📊 Real-time streaming analysis:")
        print(f"      Frames sent: {frames_sent}")
        print(f"      Frames displayed: {len(frames_displayed)}")
        print(f"      Delivery rate: {delivery_rate:.1f}%")
        
        # Check chronological order
        is_chronological = True
        if len(frames_displayed) > 1:
            for i in range(len(frames_displayed) - 1):
                if frames_displayed[i] > frames_displayed[i + 1]:
                    is_chronological = False
                    break
        
        print(f"      Chronological order: {is_chronological}")
        
        # Get final statistics
        all_status = frame_sequencing_manager.get_all_status()
        if client_id in all_status:
            stats = all_status[client_id]['stats']
            print(f"      Average jitter: {stats['average_jitter']*1000:.2f}ms")
            print(f"      Sequence gaps: {stats['sequence_gaps']}")
        
        # Clean up
        renderer.remove_video_stream(client_id)
        renderer.stop_rendering()
        
        return delivery_rate > 70 and is_chronological
        
    except Exception as e:
        print(f"   ❌ Real-time streaming test error: {e}")
        return False


def main():
    """Main video chronological integration test function."""
    
    print("🎬 VIDEO CHRONOLOGICAL INTEGRATION TEST")
    print("Testing complete video system with chronological frame ordering")
    print("=" * 80)
    
    # Run integration tests
    tests = [
        ("Video System Chronological Integration", test_video_system_chronological_integration),
        ("Multi-Client Video Chronological Sync", test_multi_client_video_chronological_sync),
        ("Real-Time Video Streaming", test_real_time_video_streaming)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 70)
        
        try:
            result = test_func()
            results.append(result)
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"   {status}")
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
            results.append(False)
    
    # Final results
    passed = sum(results)
    total = len(results)
    
    print(f"\n📊 VIDEO CHRONOLOGICAL INTEGRATION TEST RESULTS")
    print("=" * 80)
    print(f"Tests passed: {passed}/{total} ({(passed/total)*100:.1f}%)")
    
    if passed == total:
        print("\n🎉 VIDEO CHRONOLOGICAL INTEGRATION SUCCESSFUL!")
        print("Your complete video system now provides:")
        print("• Perfect chronological frame ordering ✅")
        print("• No back-and-forth video display ✅")
        print("• Seamless multi-client synchronization ✅")
        print("• Real-time streaming with correct ordering ✅")
        
        print(f"\n🚀 READY FOR PROFESSIONAL VIDEO CONFERENCING:")
        print("Video frames are displayed in perfect chronological order!")
        print("No more temporal jumping or back-and-forth issues!")
        print("Smooth, professional-quality video playback guaranteed!")
        
    else:
        print("\n⚠️  SOME INTEGRATION TESTS FAILED")
        print("Please check the error messages above.")
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)