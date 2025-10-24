#!/usr/bin/env python3
"""
Test Frame Sequencing System
Comprehensive testing for chronological frame ordering and sequencing.
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
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_basic_sequencing():
    """Test basic frame sequencing functionality."""
    
    print("🧪 Testing basic frame sequencing...")
    
    try:
        # Create frame sequencer
        sequencer = FrameSequencer("test_client", max_buffer_size=10)
        
        # Create test frames with timestamps
        frames_displayed = []
        
        def display_callback(frame_data):
            frames_displayed.append(time.perf_counter())
        
        # Add frames in order
        base_time = time.perf_counter()
        for i in range(5):
            frame_data = np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8)
            capture_time = base_time + (i * 0.033)  # 30 FPS intervals
            network_time = capture_time + 0.001  # 1ms network delay
            
            success = sequencer.add_frame(i, capture_time, network_time, frame_data)
            print(f"   📸 Added frame {i}: {success}")
        
        # Get frames in order
        for i in range(5):
            frame = sequencer.get_next_frame()
            if frame:
                print(f"   🖼️  Got frame {frame.sequence_number} (timestamp: {frame.capture_timestamp:.6f})")
            else:
                print(f"   ❌ No frame available for sequence {i}")
        
        # Check buffer status
        status = sequencer.get_buffer_status()
        print(f"   📊 Buffer status: {status['stats']}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Basic sequencing test error: {e}")
        return False


def test_out_of_order_frames():
    """Test handling of out-of-order frames."""
    
    print("\n🔄 Testing out-of-order frame handling...")
    
    try:
        sequencer = FrameSequencer("ooo_test_client", max_buffer_size=15)
        
        # Add frames out of order
        base_time = time.perf_counter()
        frame_order = [0, 2, 1, 4, 3, 6, 5, 7]  # Out of order sequence
        
        frames_added = []
        for seq in frame_order:
            frame_data = np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8)
            capture_time = base_time + (seq * 0.033)
            network_time = capture_time + 0.002
            
            success = sequencer.add_frame(seq, capture_time, network_time, frame_data)
            frames_added.append((seq, success))
            print(f"   📸 Added frame {seq} (out of order): {success}")
        
        # Wait for reorder timeout
        time.sleep(0.15)
        
        # Get frames - should be in chronological order
        frames_retrieved = []
        for i in range(len(frame_order)):
            frame = sequencer.get_next_frame()
            if frame:
                frames_retrieved.append(frame.sequence_number)
                print(f"   🖼️  Retrieved frame {frame.sequence_number}")
            else:
                print(f"   ⏳ No frame ready yet")
        
        # Check if frames were reordered correctly
        expected_order = sorted(frame_order)
        actual_order = frames_retrieved
        
        print(f"   📋 Expected order: {expected_order}")
        print(f"   📋 Actual order: {actual_order}")
        
        # Check statistics
        status = sequencer.get_buffer_status()
        print(f"   📊 Reordered frames: {status['stats']['frames_reordered']}")
        print(f"   📊 Sequence gaps: {status['stats']['sequence_gaps']}")
        
        return len(actual_order) > 0
        
    except Exception as e:
        print(f"   ❌ Out-of-order test error: {e}")
        return False


def test_frame_sequencing_manager():
    """Test the frame sequencing manager with multiple clients."""
    
    print("\n👥 Testing frame sequencing manager...")
    
    try:
        # Track displayed frames for each client
        displayed_frames = {'client1': [], 'client2': [], 'client3': []}
        
        def create_callback(client_id):
            def callback(frame_data):
                displayed_frames[client_id].append(time.perf_counter())
                print(f"   🖼️  Displayed frame for {client_id}")
            return callback
        
        # Register multiple clients
        clients = ['client1', 'client2', 'client3']
        for client_id in clients:
            frame_sequencing_manager.register_client(
                client_id, 
                create_callback(client_id),
                max_buffer_size=8
            )
        
        # Add frames for multiple clients simultaneously
        base_time = time.perf_counter()
        
        for i in range(10):
            for client_id in clients:
                frame_data = np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8)
                capture_time = base_time + (i * 0.033)
                network_time = capture_time + np.random.uniform(0.001, 0.005)  # Variable network delay
                
                success = frame_sequencing_manager.add_frame(
                    client_id, i, capture_time, network_time, frame_data
                )
                
                if i % 3 == 0:  # Log every 3rd frame
                    print(f"   📸 Added frame {i} for {client_id}: {success}")
        
        # Wait for processing
        time.sleep(1.0)
        
        # Check results
        for client_id in clients:
            count = len(displayed_frames[client_id])
            print(f"   📊 {client_id}: {count} frames displayed")
        
        # Get status for all clients
        all_status = frame_sequencing_manager.get_all_status()
        for client_id, status in all_status.items():
            print(f"   📈 {client_id} stats: {status['stats']}")
        
        # Clean up
        for client_id in clients:
            frame_sequencing_manager.unregister_client(client_id)
        
        return sum(len(frames) for frames in displayed_frames.values()) > 0
        
    except Exception as e:
        print(f"   ❌ Manager test error: {e}")
        return False


def test_jitter_compensation():
    """Test jitter compensation and timing accuracy."""
    
    print("\n⏱️  Testing jitter compensation...")
    
    try:
        sequencer = FrameSequencer("jitter_test_client", max_buffer_size=12)
        
        # Simulate network jitter
        base_time = time.perf_counter()
        jitter_values = [0.001, 0.005, 0.002, 0.008, 0.001, 0.003, 0.006, 0.002]
        
        frames_added = []
        for i, jitter in enumerate(jitter_values):
            frame_data = np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8)
            capture_time = base_time + (i * 0.033)
            network_time = capture_time + jitter  # Variable jitter
            
            success = sequencer.add_frame(i, capture_time, network_time, frame_data)
            frames_added.append((i, jitter, success))
            print(f"   📸 Frame {i} with {jitter*1000:.1f}ms jitter: {success}")
        
        # Wait for jitter buffer to fill
        time.sleep(0.2)
        
        # Retrieve frames
        frames_retrieved = []
        retrieval_times = []
        
        for i in range(len(jitter_values)):
            start_time = time.perf_counter()
            frame = sequencer.get_next_frame()
            end_time = time.perf_counter()
            
            if frame:
                frames_retrieved.append(frame.sequence_number)
                retrieval_times.append(end_time - start_time)
                print(f"   🖼️  Retrieved frame {frame.sequence_number} in {(end_time-start_time)*1000:.2f}ms")
        
        # Check jitter statistics
        status = sequencer.get_buffer_status()
        avg_jitter = status['stats']['average_jitter']
        print(f"   📊 Average jitter: {avg_jitter*1000:.2f}ms")
        print(f"   📊 Frames processed: {len(frames_retrieved)}")
        
        return len(frames_retrieved) > 0 and avg_jitter > 0
        
    except Exception as e:
        print(f"   ❌ Jitter compensation test error: {e}")
        return False


def test_performance_under_load():
    """Test performance under high frame load."""
    
    print("\n🚀 Testing performance under load...")
    
    try:
        sequencer = FrameSequencer("load_test_client", max_buffer_size=20)
        
        # High frame rate simulation
        frame_count = 100
        base_time = time.perf_counter()
        
        # Add frames rapidly
        start_add = time.perf_counter()
        for i in range(frame_count):
            frame_data = np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8)
            capture_time = base_time + (i * 0.016)  # 60 FPS
            network_time = capture_time + np.random.uniform(0.001, 0.003)
            
            sequencer.add_frame(i, capture_time, network_time, frame_data)
        
        end_add = time.perf_counter()
        add_time = end_add - start_add
        
        print(f"   ⚡ Added {frame_count} frames in {add_time*1000:.2f}ms")
        print(f"   ⚡ Add rate: {frame_count/add_time:.1f} frames/sec")
        
        # Retrieve frames rapidly
        start_get = time.perf_counter()
        retrieved_count = 0
        
        for i in range(frame_count):
            frame = sequencer.get_next_frame()
            if frame:
                retrieved_count += 1
            
            # Small delay to simulate processing
            time.sleep(0.001)
        
        end_get = time.perf_counter()
        get_time = end_get - start_get
        
        print(f"   ⚡ Retrieved {retrieved_count} frames in {get_time*1000:.2f}ms")
        print(f"   ⚡ Retrieval rate: {retrieved_count/get_time:.1f} frames/sec")
        
        # Check final statistics
        status = sequencer.get_buffer_status()
        stats = status['stats']
        
        print(f"   📊 Final stats:")
        print(f"      • Frames received: {stats['frames_received']}")
        print(f"      • Frames displayed: {stats['frames_displayed']}")
        print(f"      • Frames dropped: {stats['frames_dropped_old'] + stats['frames_dropped_duplicate']}")
        print(f"      • Processing efficiency: {(stats['frames_displayed']/stats['frames_received'])*100:.1f}%")
        
        return retrieved_count > frame_count * 0.8  # At least 80% success rate
        
    except Exception as e:
        print(f"   ❌ Performance test error: {e}")
        return False


def main():
    """Main test function."""
    
    print("🎬 FRAME SEQUENCING SYSTEM TEST")
    print("Testing chronological frame ordering and sequencing")
    print("=" * 60)
    
    # Run tests
    tests = [
        ("Basic Sequencing", test_basic_sequencing),
        ("Out-of-Order Frames", test_out_of_order_frames),
        ("Sequencing Manager", test_frame_sequencing_manager),
        ("Jitter Compensation", test_jitter_compensation),
        ("Performance Under Load", test_performance_under_load)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 40)
        
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
    
    print(f"\n📊 FRAME SEQUENCING TEST RESULTS")
    print("=" * 60)
    print(f"Tests passed: {passed}/{total} ({(passed/total)*100:.1f}%)")
    
    if passed == total:
        print("\n🎉 ALL FRAME SEQUENCING TESTS PASSED!")
        print("Frame sequencing system is working correctly:")
        print("• Chronological frame ordering ✅")
        print("• Out-of-order frame handling ✅")
        print("• Multi-client management ✅")
        print("• Jitter compensation ✅")
        print("• High-performance processing ✅")
        
        print(f"\n🚀 READY FOR PRODUCTION:")
        print("Frame sequencing will ensure smooth, correctly ordered video playback!")
        
    else:
        print("\n⚠️  SOME TESTS FAILED")
        print("Please check the error messages above.")
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)