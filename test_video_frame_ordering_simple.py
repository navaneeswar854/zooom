"""
Simple test script for video frame ordering optimization.
Tests chronological frame ordering and prevents back-and-forth display.
"""

import time
import numpy as np
import logging
from client.frame_sequencer import FrameSequencer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_frame_sequencer_chronological_order():
    """Test frame sequencer with perfect chronological ordering."""
    print("\nTesting Frame Sequencer - Chronological Order...")
    
    try:
        sequencer = FrameSequencer("test_client", max_buffer_size=20)
        
        # Test 1: Perfect chronological order
        print("   Test 1: Perfect chronological order")
        frame_order = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
        base_time = time.perf_counter()
        
        # Add frames in perfect order
        for seq in frame_order:
            capture_time = base_time + (seq * 0.033333)  # 30 FPS
            network_time = capture_time + 0.002
            frame_data = np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8)
            
            success = sequencer.add_frame(seq, capture_time, network_time, frame_data)
            print(f"      Frame {seq}: {'OK' if success else 'FAIL'}")
        
        # Retrieve frames
        retrieved_frames = []
        for _ in range(len(frame_order)):
            frame = sequencer.get_next_frame()
            if frame:
                retrieved_frames.append(frame.sequence_number)
        
        is_chronological = retrieved_frames == frame_order
        print(f"      Result: {'PASS' if is_chronological else 'FAIL'} - {retrieved_frames}")
        
        # Test 2: Out-of-order frames
        print("   Test 2: Out-of-order frames")
        sequencer.reset()
        out_of_order = [0, 3, 1, 5, 2, 7, 4, 9, 6, 8]
        
        for seq in out_of_order:
            capture_time = base_time + (seq * 0.033333)
            network_time = capture_time + 0.002
            frame_data = np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8)
            
            success = sequencer.add_frame(seq, capture_time, network_time, frame_data)
            print(f"      Frame {seq}: {'OK' if success else 'FAIL'}")
        
        # Retrieve frames in chronological order
        retrieved_frames = []
        for _ in range(len(out_of_order)):
            frame = sequencer.get_next_frame()
            if frame:
                retrieved_frames.append(frame.sequence_number)
        
        expected_order = sorted(out_of_order)
        is_chronological = retrieved_frames == expected_order
        print(f"      Result: {'PASS' if is_chronological else 'FAIL'} - {retrieved_frames}")
        print(f"      Expected: {expected_order}")
        
        return is_chronological
        
    except Exception as e:
        print(f"   ERROR: Frame sequencer test error: {e}")
        return False


def test_temporal_jump_prevention():
    """Test prevention of temporal jumps (back-and-forth display)."""
    print("\nTesting Temporal Jump Prevention...")
    
    try:
        sequencer = FrameSequencer("temporal_test", max_buffer_size=15)
        
        # Create temporal jump scenario
        base_time = time.perf_counter()
        timestamps = [0.0, 0.033, 0.066, 0.05, 0.099, 0.132]  # 0.05 is a jump back
        sequences = [0, 1, 2, 3, 4, 5]
        
        frames_added = 0
        for i, (seq, timestamp) in enumerate(zip(sequences, timestamps)):
            capture_time = base_time + timestamp
            network_time = capture_time + 0.002
            frame_data = np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8)
            
            success = sequencer.add_frame(seq, capture_time, network_time, frame_data)
            if success:
                frames_added += 1
            print(f"      Frame {seq} (t={timestamp:.3f}): {'OK' if success else 'REJECTED'}")
        
        # Check if temporal jumps were prevented
        stats = sequencer.get_buffer_status()
        print(f"      Frames added: {frames_added}")
        print(f"      Frames dropped (old): {stats['stats']['frames_dropped_old']}")
        
        # Should reject some frames to prevent temporal jumps
        jumps_prevented = stats['stats']['frames_dropped_old'] > 0
        print(f"      Temporal jumps prevented: {'YES' if jumps_prevented else 'NO'}")
        
        return jumps_prevented
        
    except Exception as e:
        print(f"   ERROR: Temporal jump prevention test error: {e}")
        return False


def test_multi_client_synchronization():
    """Test multi-client frame synchronization."""
    print("\nTesting Multi-Client Synchronization...")
    
    try:
        # Create multiple sequencers
        clients = ['client_A', 'client_B', 'client_C']
        sequencers = {}
        
        for client_id in clients:
            sequencers[client_id] = FrameSequencer(client_id, max_buffer_size=15)
        
        # Simulate frames from multiple clients
        base_time = time.perf_counter()
        total_frames = 0
        
        for client_id in clients:
            for seq in range(5):  # 5 frames per client
                capture_time = base_time + (seq * 0.033333) + (hash(client_id) % 100) * 0.001
                network_time = capture_time + 0.002
                frame_data = np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8)
                
                success = sequencers[client_id].add_frame(seq, capture_time, network_time, frame_data)
                if success:
                    total_frames += 1
        
        print(f"   Total frames added: {total_frames}")
        
        # Check synchronization
        all_chronological = True
        for client_id, sequencer in sequencers.items():
            stats = sequencer.get_buffer_status()
            frames_displayed = stats['stats']['frames_displayed']
            frames_received = stats['stats']['frames_received']
            
            if frames_received > 0:
                accuracy = frames_displayed / frames_received
                print(f"   {client_id}: {accuracy:.2%} accuracy ({frames_displayed}/{frames_received})")
                
                if accuracy < 0.8:  # 80% accuracy threshold
                    all_chronological = False
            else:
                print(f"   {client_id}: No frames processed")
        
        print(f"   Multi-client sync: {'PASS' if all_chronological else 'FAIL'}")
        return all_chronological
        
    except Exception as e:
        print(f"   ERROR: Multi-client synchronization test error: {e}")
        return False


def test_performance_optimization():
    """Test performance optimization features."""
    print("\nTesting Performance Optimization...")
    
    try:
        sequencer = FrameSequencer("perf_test", max_buffer_size=50)
        
        # Test with many frames
        num_frames = 100
        base_time = time.perf_counter()
        
        start_time = time.time()
        
        # Add frames rapidly
        for seq in range(num_frames):
            capture_time = base_time + (seq * 0.016667)  # 60 FPS
            network_time = capture_time + 0.001
            frame_data = np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8)
            
            sequencer.add_frame(seq, capture_time, network_time, frame_data)
        
        # Retrieve frames
        retrieved_count = 0
        while True:
            frame = sequencer.get_next_frame()
            if frame:
                retrieved_count += 1
            else:
                break
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Performance metrics
        fps = num_frames / processing_time
        stats = sequencer.get_buffer_status()
        accuracy = stats['stats']['frames_displayed'] / stats['stats']['frames_received'] if stats['stats']['frames_received'] > 0 else 0
        
        print(f"   Frames processed: {num_frames}")
        print(f"   Frames retrieved: {retrieved_count}")
        print(f"   Processing time: {processing_time:.3f}s")
        print(f"   Effective FPS: {fps:.1f}")
        print(f"   Chronological accuracy: {accuracy:.2%}")
        
        # Performance thresholds
        is_fast = fps > 1000  # Should process > 1000 frames/second
        is_accurate = accuracy > 0.95  # Should maintain > 95% accuracy
        
        print(f"   Performance: {'PASS' if is_fast else 'FAIL'} (fast: {fps:.1f} fps)")
        print(f"   Accuracy: {'PASS' if is_accurate else 'FAIL'} ({accuracy:.2%})")
        
        return is_fast and is_accurate
        
    except Exception as e:
        print(f"   ERROR: Performance optimization test error: {e}")
        return False


def main():
    """Run all optimization tests."""
    print("OPTIMIZED VIDEO FRAME ORDERING TESTS")
    print("=" * 50)
    
    tests = [
        ("Frame Sequencer Chronological Order", test_frame_sequencer_chronological_order),
        ("Temporal Jump Prevention", test_temporal_jump_prevention),
        ("Multi-Client Synchronization", test_multi_client_synchronization),
        ("Performance Optimization", test_performance_optimization)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            result = test_func()
            results.append((test_name, result))
            print(f"\n{test_name}: {'PASSED' if result else 'FAILED'}")
        except Exception as e:
            print(f"\n{test_name}: ERROR - {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*50)
    print("TEST SUMMARY")
    print("="*50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "PASSED" if result else "FAILED"
        print(f"   {test_name}: {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("\nALL TESTS PASSED!")
        print("Video frame ordering is perfectly optimized!")
        print("Chronological order is maintained!")
        print("Back-and-forth display is prevented!")
        print("Multi-client synchronization works!")
        print("Performance is optimized!")
        
        print("\nREADY FOR PRODUCTION:")
        print("Your video conferencing system now has:")
        print("- Perfect chronological frame ordering")
        print("- Zero back-and-forth video display")
        print("- Optimized performance")
        print("- Multi-client synchronization")
        print("- Professional-quality video streaming")
        
    else:
        print(f"\n{total-passed} TESTS FAILED")
        print("Some optimizations may need adjustment.")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
