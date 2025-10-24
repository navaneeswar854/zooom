#!/usr/bin/env python3
"""
Enhanced Frame Sequencing Test
Tests the improved frame sequencing system with better performance and chronological ordering.
"""

import sys
import os
import time
import threading
import numpy as np
import logging

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from client.frame_sequencer import FrameSequencer, frame_sequencing_manager

# Configure logging
logging.basicConfig(level=logging.WARNING)  # Reduce log noise
logger = logging.getLogger(__name__)


def test_chronological_ordering():
    """Test strict chronological ordering of frames."""
    
    print("🕒 Testing strict chronological ordering...")
    
    try:
        sequencer = FrameSequencer("chrono_test_client", max_buffer_size=15)
        
        # Create frames with precise timestamps
        base_time = time.perf_counter()
        frame_timestamps = []
        
        # Add frames with intentional out-of-order arrival
        frame_order = [0, 3, 1, 5, 2, 7, 4, 9, 6, 8]  # Mixed order
        
        for i, seq in enumerate(frame_order):
            frame_data = np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8)
            capture_time = base_time + (seq * 0.033333)  # Precise 30 FPS intervals
            network_time = capture_time + 0.002  # 2ms network delay
            
            success = sequencer.add_frame(seq, capture_time, network_time, frame_data)
            frame_timestamps.append((seq, capture_time))
            print(f"   📸 Added frame {seq} (capture: {capture_time:.6f}): {success}")
        
        # Wait for reordering
        time.sleep(0.1)
        
        # Retrieve frames and verify chronological order
        retrieved_frames = []
        retrieved_timestamps = []
        
        for i in range(len(frame_order)):
            frame = sequencer.get_next_frame()
            if frame:
                retrieved_frames.append(frame.sequence_number)
                retrieved_timestamps.append(frame.capture_timestamp)
                print(f"   🖼️  Retrieved frame {frame.sequence_number} (timestamp: {frame.capture_timestamp:.6f})")
        
        # Check chronological order
        is_chronological = all(retrieved_timestamps[i] <= retrieved_timestamps[i+1] 
                             for i in range(len(retrieved_timestamps)-1))
        
        print(f"   📊 Frames retrieved: {len(retrieved_frames)}")
        print(f"   📊 Chronological order: {is_chronological}")
        
        # Check timing accuracy
        if len(retrieved_timestamps) > 1:
            intervals = [retrieved_timestamps[i+1] - retrieved_timestamps[i] 
                        for i in range(len(retrieved_timestamps)-1)]
            avg_interval = sum(intervals) / len(intervals)
            expected_interval = 0.033333  # 30 FPS
            accuracy = (1 - abs(avg_interval - expected_interval) / expected_interval) * 100
            
            print(f"   📏 Average interval: {avg_interval:.6f}s")
            print(f"   📏 Timing accuracy: {accuracy:.1f}%")
        
        return is_chronological and len(retrieved_frames) >= 8
        
    except Exception as e:
        print(f"   ❌ Chronological ordering test error: {e}")
        return False


def test_high_performance_sequencing():
    """Test high-performance frame sequencing under load."""
    
    print("\n⚡ Testing high-performance sequencing...")
    
    try:
        sequencer = FrameSequencer("perf_test_client", max_buffer_size=25)
        
        # High frame rate simulation
        frame_count = 200
        base_time = time.perf_counter()
        
        # Add frames rapidly with some out-of-order delivery
        start_add = time.perf_counter()
        added_frames = []
        
        for i in range(frame_count):
            frame_data = np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8)
            
            # Simulate some out-of-order delivery (20% chance)
            if i > 0 and np.random.random() < 0.2:
                # Swap with previous frame occasionally
                seq = i - 1 if i % 2 == 0 else i
            else:
                seq = i
            
            capture_time = base_time + (seq * 0.016667)  # 60 FPS
            network_time = capture_time + np.random.uniform(0.001, 0.005)  # Variable delay
            
            success = sequencer.add_frame(seq, capture_time, network_time, frame_data)
            if success:
                added_frames.append(seq)
        
        end_add = time.perf_counter()
        add_time = end_add - start_add
        
        print(f"   ⚡ Added {len(added_frames)} frames in {add_time*1000:.2f}ms")
        print(f"   ⚡ Add rate: {len(added_frames)/add_time:.1f} frames/sec")
        
        # Retrieve frames rapidly
        start_get = time.perf_counter()
        retrieved_count = 0
        retrieved_timestamps = []
        
        # Process frames in batches for better performance
        while retrieved_count < len(added_frames) * 0.9:  # Expect 90% retrieval
            frame = sequencer.get_next_frame()
            if frame:
                retrieved_count += 1
                retrieved_timestamps.append(frame.capture_timestamp)
            else:
                # Small delay if no frame available
                time.sleep(0.001)
                
            # Timeout after reasonable time
            if time.perf_counter() - start_get > 2.0:
                break
        
        end_get = time.perf_counter()
        get_time = end_get - start_get
        
        print(f"   ⚡ Retrieved {retrieved_count} frames in {get_time*1000:.2f}ms")
        print(f"   ⚡ Retrieval rate: {retrieved_count/get_time:.1f} frames/sec")
        
        # Check chronological order
        is_chronological = all(retrieved_timestamps[i] <= retrieved_timestamps[i+1] 
                             for i in range(len(retrieved_timestamps)-1))
        
        # Check final statistics
        status = sequencer.get_buffer_status()
        stats = status['stats']
        
        efficiency = (stats['frames_displayed'] / stats['frames_received']) * 100
        
        print(f"   📊 Processing efficiency: {efficiency:.1f}%")
        print(f"   📊 Chronological order maintained: {is_chronological}")
        print(f"   📊 Frames reordered: {stats['frames_reordered']}")
        
        return efficiency > 80 and is_chronological
        
    except Exception as e:
        print(f"   ❌ High-performance test error: {e}")
        return False


def test_real_time_streaming_simulation():
    """Test real-time streaming simulation with network conditions."""
    
    print("\n🌐 Testing real-time streaming simulation...")
    
    try:
        sequencer = FrameSequencer("stream_test_client", max_buffer_size=20)
        
        # Simulate real-time streaming conditions
        total_frames = 150
        frames_sent = []
        
        # Simulate streaming with realistic timing
        base_time = time.perf_counter()
        
        for i in range(total_frames):
            # Simulate packet loss (5% loss rate)
            if np.random.random() < 0.05:
                continue
            
            frame_data = np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8)
            
            # Simulate network jitter (1-15ms)
            jitter = np.random.uniform(0.001, 0.015)
            capture_time = base_time + (i * 0.033333)  # 30 FPS
            network_time = capture_time + jitter
            
            # Simulate out-of-order delivery (15% chance)
            if i > 0 and np.random.random() < 0.15:
                # Small delay to simulate reordering
                time.sleep(0.002)
            
            success = sequencer.add_frame(i, capture_time, network_time, frame_data)
            if success:
                frames_sent.append(i)
        
        print(f"   📡 Sent {len(frames_sent)} frames (with {total_frames - len(frames_sent)} lost)")
        
        # Simulate real-time playback
        frames_displayed = []
        display_timestamps = []
        
        # Process frames as they become available
        start_time = time.perf_counter()
        while len(frames_displayed) < len(frames_sent) * 0.85:  # Expect 85% display rate
            frame = sequencer.get_next_frame()
            if frame:
                frames_displayed.append(frame.sequence_number)
                display_timestamps.append(frame.capture_timestamp)
            
            # Simulate 30 FPS display rate
            time.sleep(0.01)  # 10ms processing time
            
            # Timeout after reasonable time
            if time.perf_counter() - start_time > 3.0:
                break
        
        # Check results
        display_rate = len(frames_displayed) / len(frames_sent) * 100
        
        # Check chronological order
        is_chronological = all(display_timestamps[i] <= display_timestamps[i+1] 
                             for i in range(len(display_timestamps)-1))
        
        print(f"   📊 Display rate: {display_rate:.1f}%")
        print(f"   📊 Chronological order: {is_chronological}")
        print(f"   📊 Frames displayed: {len(frames_displayed)}")
        
        # Get final statistics
        status = sequencer.get_buffer_status()
        stats = status['stats']
        print(f"   📈 Final statistics:")
        print(f"      • Average jitter: {stats['average_jitter']*1000:.2f}ms")
        print(f"      • Frames reordered: {stats['frames_reordered']}")
        print(f"      • Sequence gaps: {stats['sequence_gaps']}")
        
        return display_rate > 80 and is_chronological
        
    except Exception as e:
        print(f"   ❌ Real-time streaming test error: {e}")
        return False


def test_multi_client_synchronization():
    """Test multi-client frame synchronization."""
    
    print("\n👥 Testing multi-client synchronization...")
    
    try:
        # Track displayed frames for each client
        displayed_frames = {'client_A': [], 'client_B': [], 'client_C': []}
        display_order = []
        
        def create_callback(client_id):
            def callback(frame_data):
                timestamp = time.perf_counter()
                displayed_frames[client_id].append(timestamp)
                display_order.append((client_id, timestamp))
            return callback
        
        # Register multiple clients
        clients = ['client_A', 'client_B', 'client_C']
        for client_id in clients:
            frame_sequencing_manager.register_client(
                client_id, 
                create_callback(client_id),
                max_buffer_size=12
            )
        
        # Add synchronized frames for multiple clients
        base_time = time.perf_counter()
        
        for i in range(20):
            for client_id in clients:
                frame_data = np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8)
                
                # Synchronized capture times
                capture_time = base_time + (i * 0.033333)
                
                # Variable network delays per client
                if client_id == 'client_A':
                    network_delay = 0.002  # 2ms
                elif client_id == 'client_B':
                    network_delay = 0.005  # 5ms
                else:
                    network_delay = 0.003  # 3ms
                
                network_time = capture_time + network_delay
                
                success = frame_sequencing_manager.add_frame(
                    client_id, i, capture_time, network_time, frame_data
                )
        
        # Wait for processing
        time.sleep(1.5)
        
        # Check synchronization results
        total_displayed = sum(len(frames) for frames in displayed_frames.values())
        
        print(f"   📊 Total frames displayed: {total_displayed}")
        for client_id in clients:
            count = len(displayed_frames[client_id])
            print(f"   📊 {client_id}: {count} frames")
        
        # Check temporal synchronization
        display_order.sort(key=lambda x: x[1])  # Sort by timestamp
        
        # Verify frames are reasonably interleaved (not all from one client)
        client_distribution = {}
        for client_id, _ in display_order[:30]:  # Check first 30 frames
            client_distribution[client_id] = client_distribution.get(client_id, 0) + 1
        
        is_synchronized = all(count > 5 for count in client_distribution.values())
        
        print(f"   📊 Client distribution in first 30 frames: {client_distribution}")
        print(f"   📊 Synchronized playback: {is_synchronized}")
        
        # Clean up
        for client_id in clients:
            frame_sequencing_manager.unregister_client(client_id)
        
        return total_displayed > 45 and is_synchronized
        
    except Exception as e:
        print(f"   ❌ Multi-client synchronization test error: {e}")
        return False


def main():
    """Main enhanced test function."""
    
    print("🎬 ENHANCED FRAME SEQUENCING SYSTEM TEST")
    print("Testing improved chronological frame ordering and performance")
    print("=" * 70)
    
    # Run enhanced tests
    tests = [
        ("Chronological Ordering", test_chronological_ordering),
        ("High-Performance Sequencing", test_high_performance_sequencing),
        ("Real-Time Streaming Simulation", test_real_time_streaming_simulation),
        ("Multi-Client Synchronization", test_multi_client_synchronization)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 50)
        
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
    
    print(f"\n📊 ENHANCED FRAME SEQUENCING TEST RESULTS")
    print("=" * 70)
    print(f"Tests passed: {passed}/{total} ({(passed/total)*100:.1f}%)")
    
    if passed == total:
        print("\n🎉 ALL ENHANCED FRAME SEQUENCING TESTS PASSED!")
        print("Enhanced frame sequencing system is working correctly:")
        print("• Strict chronological frame ordering ✅")
        print("• High-performance processing ✅")
        print("• Real-time streaming capability ✅")
        print("• Multi-client synchronization ✅")
        
        print(f"\n🚀 READY FOR PRODUCTION:")
        print("Frame sequencing ensures perfect chronological order with high performance!")
        
    else:
        print("\n⚠️  SOME TESTS FAILED")
        print("Please check the error messages above.")
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)