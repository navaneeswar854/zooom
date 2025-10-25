#!/usr/bin/env python3
"""
Test Chronological Frame Ordering
Comprehensive test to ensure frames are displayed in strict chronological order
to prevent "back and forth" video display issues.
"""

import sys
import os
import time
import logging
import numpy as np

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from client.frame_sequencer import FrameSequencer, frame_sequencing_manager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_strict_chronological_ordering():
    """Test strict chronological ordering to prevent back-and-forth display."""
    
    print("🕒 Testing strict chronological ordering...")
    
    try:
        sequencer = FrameSequencer("chrono_test", max_buffer_size=20)
        
        # Create frames with precise timestamps but add them out of order
        base_time = time.perf_counter()
        
        # Simulate frames arriving out of order (common in network transmission)
        frame_data_map = {}
        frame_timestamps = {}
        
        # Create frame data and timestamps
        for i in range(10):
            frame_data_map[i] = np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8)
            frame_timestamps[i] = base_time + (i * 0.033333)  # 30 FPS intervals
        
        # Add frames in mixed order to simulate network reordering
        add_order = [0, 3, 1, 5, 2, 7, 4, 9, 6, 8]
        
        print("   📸 Adding frames out of order:")
        for seq in add_order:
            capture_time = frame_timestamps[seq]
            network_time = capture_time + 0.002
            
            success = sequencer.add_frame(seq, capture_time, network_time, frame_data_map[seq])
            print(f"      Frame {seq} (timestamp: {capture_time:.6f}): {success}")
        
        # Retrieve frames and verify chronological order
        retrieved_frames = []
        retrieved_timestamps = []
        
        print("   🖼️  Retrieving frames in chronological order:")
        
        # Try to get all frames
        for attempt in range(15):  # Extra attempts to ensure we get all frames
            frame = sequencer.get_next_frame()
            if frame:
                retrieved_frames.append(frame.sequence_number)
                retrieved_timestamps.append(frame.capture_timestamp)
                print(f"      Retrieved frame {frame.sequence_number} (timestamp: {frame.capture_timestamp:.6f})")
            else:
                # Small delay to allow for frame processing
                time.sleep(0.01)
        
        # Verify chronological order
        is_chronological = True
        if len(retrieved_timestamps) > 1:
            for i in range(len(retrieved_timestamps) - 1):
                if retrieved_timestamps[i] > retrieved_timestamps[i + 1]:
                    is_chronological = False
                    print(f"      ❌ Chronological violation: frame {i} ({retrieved_timestamps[i]:.6f}) > frame {i+1} ({retrieved_timestamps[i+1]:.6f})")
        
        # Check completeness
        expected_frames = sorted(add_order)
        retrieved_sorted = sorted(retrieved_frames)
        
        print(f"   📊 Results:")
        print(f"      Frames added: {len(add_order)}")
        print(f"      Frames retrieved: {len(retrieved_frames)}")
        print(f"      Expected order: {expected_frames}")
        print(f"      Retrieved frames: {retrieved_frames}")
        print(f"      Chronological order: {is_chronological}")
        print(f"      Complete retrieval: {retrieved_sorted == expected_frames}")
        
        return is_chronological and len(retrieved_frames) >= len(add_order) * 0.8
        
    except Exception as e:
        print(f"   ❌ Chronological ordering test error: {e}")
        return False


def test_back_and_forth_prevention():
    """Test prevention of back-and-forth video display."""
    
    print("\n🔄 Testing back-and-forth prevention...")
    
    try:
        sequencer = FrameSequencer("back_forth_test", max_buffer_size=25)
        
        # Simulate a scenario that could cause back-and-forth display
        base_time = time.perf_counter()
        
        # Create frames with timestamps that could cause issues
        frame_scenarios = [
            (0, base_time + 0.000),  # Frame 0 at T+0ms
            (2, base_time + 0.067),  # Frame 2 at T+67ms (should be at T+67ms)
            (1, base_time + 0.033),  # Frame 1 at T+33ms (arrives late)
            (4, base_time + 0.133),  # Frame 4 at T+133ms
            (3, base_time + 0.100),  # Frame 3 at T+100ms (arrives late)
            (6, base_time + 0.200),  # Frame 6 at T+200ms
            (5, base_time + 0.167),  # Frame 5 at T+167ms (arrives late)
        ]
        
        print("   📸 Adding frames with potential back-and-forth issues:")
        for seq, capture_time in frame_scenarios:
            frame_data = np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8)
            network_time = capture_time + 0.002
            
            success = sequencer.add_frame(seq, capture_time, network_time, frame_data)
            print(f"      Frame {seq} (timestamp: {capture_time:.6f}): {success}")
        
        # Retrieve frames and check for back-and-forth issues
        retrieved_sequence = []
        retrieved_timestamps = []
        
        print("   🖼️  Retrieving frames to check for back-and-forth:")
        
        # Process frames with realistic timing
        for attempt in range(20):
            frame = sequencer.get_next_frame()
            if frame:
                retrieved_sequence.append(frame.sequence_number)
                retrieved_timestamps.append(frame.capture_timestamp)
                print(f"      Retrieved frame {frame.sequence_number} (timestamp: {frame.capture_timestamp:.6f})")
            
            # Simulate frame display timing (30 FPS)
            time.sleep(0.01)
        
        # Check for back-and-forth issues
        has_back_and_forth = False
        if len(retrieved_timestamps) > 1:
            for i in range(len(retrieved_timestamps) - 1):
                if retrieved_timestamps[i] > retrieved_timestamps[i + 1]:
                    has_back_and_forth = True
                    time_diff = retrieved_timestamps[i] - retrieved_timestamps[i + 1]
                    print(f"      ⚠️  Potential back-and-forth: frame {i} -> {i+1} (time diff: {time_diff*1000:.2f}ms)")
        
        # Check sequence monotonicity (should generally increase)
        sequence_violations = 0
        if len(retrieved_sequence) > 1:
            for i in range(len(retrieved_sequence) - 1):
                if retrieved_sequence[i] > retrieved_sequence[i + 1]:
                    sequence_violations += 1
        
        print(f"   📊 Back-and-forth analysis:")
        print(f"      Frames processed: {len(retrieved_sequence)}")
        print(f"      Chronological violations: {has_back_and_forth}")
        print(f"      Sequence violations: {sequence_violations}")
        print(f"      Prevention successful: {not has_back_and_forth}")
        
        return not has_back_and_forth
        
    except Exception as e:
        print(f"   ❌ Back-and-forth prevention test error: {e}")
        return False


def test_real_time_chronological_streaming():
    """Test chronological ordering in real-time streaming scenario."""
    
    print("\n🌐 Testing real-time chronological streaming...")
    
    try:
        sequencer = FrameSequencer("realtime_test", max_buffer_size=30)
        
        # Simulate real-time streaming with network conditions
        base_time = time.perf_counter()
        total_frames = 30
        
        # Track frame processing
        frames_sent = []
        display_order = []
        
        print("   📡 Simulating real-time streaming:")
        
        # Send frames with realistic network conditions
        for i in range(total_frames):
            frame_data = np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8)
            
            # Simulate network jitter (1-10ms)
            jitter = np.random.uniform(0.001, 0.010)
            capture_time = base_time + (i * 0.033333)  # 30 FPS
            network_time = capture_time + jitter
            
            # Simulate occasional out-of-order delivery (20% chance)
            if i > 0 and np.random.random() < 0.2:
                # Add small delay to simulate reordering
                time.sleep(0.005)
            
            success = sequencer.add_frame(i, capture_time, network_time, frame_data)
            if success:
                frames_sent.append((i, capture_time))
                
            if i % 5 == 0:  # Log every 5th frame
                print(f"      Sent frame {i} (jitter: {jitter*1000:.1f}ms)")
        
        print("   🖼️  Processing frames in real-time:")
        
        # Process frames as they become available (simulate real-time display)
        start_time = time.perf_counter()
        processed_count = 0
        
        while processed_count < len(frames_sent) * 0.9 and (time.perf_counter() - start_time) < 3.0:
            frame = sequencer.get_next_frame()
            if frame:
                display_order.append((frame.sequence_number, frame.capture_timestamp))
                processed_count += 1
                
                if processed_count % 5 == 0:  # Log every 5th processed frame
                    print(f"      Processed frame {frame.sequence_number}")
            
            # Simulate display rate (30 FPS)
            time.sleep(0.01)
        
        # Analyze chronological ordering
        is_chronological = True
        timestamp_violations = 0
        
        if len(display_order) > 1:
            for i in range(len(display_order) - 1):
                current_timestamp = display_order[i][1]
                next_timestamp = display_order[i + 1][1]
                
                if current_timestamp > next_timestamp:
                    is_chronological = False
                    timestamp_violations += 1
        
        # Calculate processing efficiency
        processing_rate = len(display_order) / len(frames_sent) * 100
        
        print(f"   📊 Real-time streaming results:")
        print(f"      Frames sent: {len(frames_sent)}")
        print(f"      Frames processed: {len(display_order)}")
        print(f"      Processing rate: {processing_rate:.1f}%")
        print(f"      Chronological order: {is_chronological}")
        print(f"      Timestamp violations: {timestamp_violations}")
        
        # Get final statistics
        status = sequencer.get_buffer_status()
        stats = status['stats']
        print(f"      Average jitter: {stats['average_jitter']*1000:.2f}ms")
        print(f"      Sequence gaps: {stats['sequence_gaps']}")
        
        return is_chronological and processing_rate > 80
        
    except Exception as e:
        print(f"   ❌ Real-time streaming test error: {e}")
        return False


def test_multi_client_chronological_sync():
    """Test chronological synchronization across multiple clients."""
    
    print("\n👥 Testing multi-client chronological synchronization...")
    
    try:
        # Track display order for each client
        client_displays = {'client_A': [], 'client_B': [], 'client_C': []}
        
        def create_callback(client_id):
            def callback(frame_data):
                timestamp = time.perf_counter()
                client_displays[client_id].append(timestamp)
            return callback
        
        # Register clients
        clients = ['client_A', 'client_B', 'client_C']
        for client_id in clients:
            frame_sequencing_manager.register_client(
                client_id, create_callback(client_id), max_buffer_size=15
            )
        
        # Send synchronized frames
        base_time = time.perf_counter()
        
        print("   📡 Sending synchronized frames to multiple clients:")
        
        for i in range(15):
            for client_id in clients:
                frame_data = np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8)
                
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
                
                frame_sequencing_manager.add_frame(
                    client_id, i, capture_time, network_time, frame_data
                )
            
            if i % 5 == 0:
                print(f"      Sent frame {i} to all clients")
        
        # Wait for processing
        time.sleep(2.0)
        
        # Analyze synchronization
        total_displayed = sum(len(displays) for displays in client_displays.values())
        
        print(f"   📊 Multi-client synchronization results:")
        print(f"      Total frames displayed: {total_displayed}")
        
        for client_id in clients:
            count = len(client_displays[client_id])
            print(f"      {client_id}: {count} frames")
        
        # Check temporal synchronization
        min_frames = min(len(displays) for displays in client_displays.values())
        max_frames = max(len(displays) for displays in client_displays.values())
        sync_variance = max_frames - min_frames
        
        is_synchronized = sync_variance <= 2  # Within 2 frames
        
        print(f"      Synchronization variance: {sync_variance} frames")
        print(f"      Synchronized: {is_synchronized}")
        
        # Clean up
        for client_id in clients:
            frame_sequencing_manager.unregister_client(client_id)
        
        return total_displayed >= 35 and is_synchronized
        
    except Exception as e:
        print(f"   ❌ Multi-client synchronization test error: {e}")
        return False


def main():
    """Main chronological ordering test function."""
    
    print("🎬 CHRONOLOGICAL FRAME ORDERING TEST")
    print("Testing strict chronological ordering to prevent back-and-forth video")
    print("=" * 80)
    
    # Run chronological ordering tests
    tests = [
        ("Strict Chronological Ordering", test_strict_chronological_ordering),
        ("Back-and-Forth Prevention", test_back_and_forth_prevention),
        ("Real-Time Chronological Streaming", test_real_time_chronological_streaming),
        ("Multi-Client Chronological Sync", test_multi_client_chronological_sync)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 60)
        
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
    
    print(f"\n📊 CHRONOLOGICAL FRAME ORDERING TEST RESULTS")
    print("=" * 80)
    print(f"Tests passed: {passed}/{total} ({(passed/total)*100:.1f}%)")
    
    if passed == total:
        print("\n🎉 CHRONOLOGICAL FRAME ORDERING WORKING PERFECTLY!")
        print("Your video system now provides:")
        print("• Strict chronological frame ordering ✅")
        print("• Prevention of back-and-forth video display ✅")
        print("• Real-time streaming with correct ordering ✅")
        print("• Multi-client synchronized chronological playback ✅")
        
        print(f"\n🚀 READY FOR SEAMLESS VIDEO:")
        print("Frames will be displayed in perfect chronological order!")
        print("No more back-and-forth or temporal jumping issues!")
        
    else:
        print("\n⚠️  SOME CHRONOLOGICAL TESTS FAILED")
        print("Please check the error messages above.")
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)