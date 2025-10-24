#!/usr/bin/env python3
"""
Test Extreme Video Optimization
Comprehensive testing for ultra-fast, flicker-free video system.
"""

import sys
import os
import time
import threading
import numpy as np
import logging

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from client.extreme_video_optimizer import extreme_video_optimizer
from client.video_optimization import video_optimizer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_zero_latency_processing():
    """Test zero-latency frame processing."""
    print("🚀 Testing zero-latency frame processing...")
    
    # Create test frame data
    test_frame = np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8)
    frame_data = test_frame.tobytes()
    
    # Test processing times
    times = []
    for i in range(100):
        start = time.perf_counter()
        extreme_video_optimizer.network_handler.process_video_packet_immediate(
            f"test_client_{i%5}", frame_data, time.perf_counter()
        )
        end = time.perf_counter()
        times.append((end - start) * 1000)  # Convert to ms
    
    avg_time = sum(times) / len(times)
    max_fps = 1000 / avg_time if avg_time > 0 else 0
    
    print(f"   ✅ Average processing: {avg_time:.3f} ms")
    print(f"   ✅ Theoretical max FPS: {max_fps:.1f}")
    print(f"   ✅ Min/Max time: {min(times):.3f}/{max(times):.3f} ms")
    
    return avg_time < 5.0  # Should be under 5ms for extreme performance


def test_anti_flicker_system():
    """Test anti-flicker system."""
    print("🎯 Testing anti-flicker system...")
    
    client_id = "flicker_test_client"
    
    # Test rapid frame updates
    flicker_prevented = 0
    frames_processed = 0
    
    for i in range(50):
        should_display = extreme_video_optimizer.anti_flicker.should_display_frame(client_id)
        if should_display:
            frames_processed += 1
        else:
            flicker_prevented += 1
        
        # Simulate very rapid updates
        time.sleep(0.001)  # 1ms intervals
    
    print(f"   ✅ Frames processed: {frames_processed}")
    print(f"   ✅ Flicker events prevented: {flicker_prevented}")
    print(f"   ✅ Flicker prevention rate: {(flicker_prevented/50)*100:.1f}%")
    
    return flicker_prevented > 0  # Should prevent some flicker


def test_extreme_network_handling():
    """Test extreme network packet handling."""
    print("🌐 Testing extreme network handling...")
    
    # Start network processing
    extreme_video_optimizer.network_handler.start_processing()
    
    # Test large packet processing
    large_packet = b"x" * 500000  # 500KB packet
    
    start_time = time.perf_counter()
    extreme_video_optimizer.network_handler.process_video_packet_immediate(
        "large_packet_test", large_packet, time.perf_counter()
    )
    end_time = time.perf_counter()
    
    processing_time = (end_time - start_time) * 1000
    
    print(f"   ✅ Large packet (500KB) processed in: {processing_time:.3f} ms")
    
    # Test throughput
    packet_count = 100
    small_packet = b"x" * 50000  # 50KB packets
    
    start_time = time.perf_counter()
    for i in range(packet_count):
        extreme_video_optimizer.network_handler.process_video_packet_immediate(
            f"throughput_test_{i}", small_packet, time.perf_counter()
        )
    end_time = time.perf_counter()
    
    total_time = end_time - start_time
    throughput = (packet_count * 50000) / (total_time * 1024 * 1024)  # MB/s
    
    print(f"   ✅ Throughput: {throughput:.1f} MB/s")
    print(f"   ✅ Packets per second: {packet_count/total_time:.1f}")
    
    return processing_time < 10.0 and throughput > 10.0  # Good performance thresholds


def test_gui_integration():
    """Test GUI integration with extreme optimization."""
    print("🖥️  Testing GUI integration...")
    
    try:
        import tkinter as tk
        from client.gui_manager import VideoFrame
        
        # Create test GUI
        root = tk.Tk()
        root.withdraw()  # Hide window
        
        video_frame = VideoFrame(root)
        
        # Test local video update
        test_frame = np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8)
        
        start_time = time.perf_counter()
        video_frame.update_local_video(test_frame)
        end_time = time.perf_counter()
        
        local_update_time = (end_time - start_time) * 1000
        
        # Test remote video update
        start_time = time.perf_counter()
        video_frame.update_remote_video("test_client", test_frame)
        end_time = time.perf_counter()
        
        remote_update_time = (end_time - start_time) * 1000
        
        print(f"   ✅ Local video update: {local_update_time:.3f} ms")
        print(f"   ✅ Remote video update: {remote_update_time:.3f} ms")
        
        root.destroy()
        
        return local_update_time < 20.0 and remote_update_time < 20.0
        
    except Exception as e:
        print(f"   ❌ GUI test failed: {e}")
        return False


def test_memory_efficiency():
    """Test memory efficiency of extreme optimization."""
    print("💾 Testing memory efficiency...")
    
    import psutil
    import gc
    
    # Get initial memory usage
    process = psutil.Process()
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB
    
    # Process many frames
    test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    frame_data = test_frame.tobytes()
    
    for i in range(1000):
        extreme_video_optimizer.network_handler.process_video_packet_immediate(
            f"memory_test_{i%10}", frame_data, time.perf_counter()
        )
    
    # Force garbage collection
    gc.collect()
    
    # Get final memory usage
    final_memory = process.memory_info().rss / 1024 / 1024  # MB
    memory_increase = final_memory - initial_memory
    
    print(f"   ✅ Initial memory: {initial_memory:.1f} MB")
    print(f"   ✅ Final memory: {final_memory:.1f} MB")
    print(f"   ✅ Memory increase: {memory_increase:.1f} MB")
    
    return memory_increase < 100.0  # Should not increase by more than 100MB


def run_comprehensive_test():
    """Run comprehensive test suite."""
    print("🧪 COMPREHENSIVE EXTREME VIDEO OPTIMIZATION TEST")
    print("=" * 60)
    
    # Enable extreme optimization
    print("🚀 Enabling extreme optimization...")
    extreme_video_optimizer.start_optimization()
    extreme_video_optimizer.enable_ultra_fast_mode()
    extreme_video_optimizer.enable_anti_flicker_mode()
    
    # Run tests
    tests = [
        ("Zero-Latency Processing", test_zero_latency_processing),
        ("Anti-Flicker System", test_anti_flicker_system),
        ("Network Handling", test_extreme_network_handling),
        ("GUI Integration", test_gui_integration),
        ("Memory Efficiency", test_memory_efficiency)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 40)
        
        try:
            result = test_func()
            results.append((test_name, result))
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"   {status}")
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
            results.append((test_name, False))
    
    # Display results
    print(f"\n📊 TEST RESULTS")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {status} {test_name}")
    
    print(f"\n🎯 SUMMARY: {passed}/{total} tests passed ({(passed/total)*100:.1f}%)")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED - EXTREME OPTIMIZATION READY!")
    else:
        print("⚠️  SOME TESTS FAILED - CHECK CONFIGURATION")
    
    return passed == total


if __name__ == "__main__":
    success = run_comprehensive_test()
    sys.exit(0 if success else 1)