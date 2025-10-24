#!/usr/bin/env python3
"""
Verify Extreme Video Fix
Quick verification that the extreme video optimization is working correctly.
"""

import sys
import os
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def verify_optimization_active():
    """Verify that extreme optimization is active."""
    
    print("🔍 Verifying extreme video optimization...")
    
    try:
        from client.extreme_video_optimizer import extreme_video_optimizer
        
        # Check if optimizer is active
        stats = extreme_video_optimizer.get_extreme_stats()
        
        print(f"   ✅ System active: {stats['is_active']}")
        print(f"   ✅ Ultra-fast mode: {stats['ultra_fast_mode']}")
        print(f"   ✅ Zero-latency display: {stats['zero_latency_display']}")
        
        return stats['is_active'] and stats['ultra_fast_mode']
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


def test_frame_processing_speed():
    """Test frame processing speed."""
    
    print("⚡ Testing frame processing speed...")
    
    try:
        import numpy as np
        from client.extreme_video_optimizer import extreme_video_optimizer
        
        # Create test frame
        test_frame = np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8)
        frame_data = test_frame.tobytes()
        
        # Test processing time
        start_time = time.perf_counter()
        
        for i in range(10):
            extreme_video_optimizer.network_handler.process_video_packet_immediate(
                "test_client", frame_data, time.perf_counter()
            )
        
        end_time = time.perf_counter()
        avg_time = ((end_time - start_time) / 10) * 1000  # Convert to ms
        
        print(f"   ✅ Average processing time: {avg_time:.3f} ms")
        print(f"   ✅ Theoretical max FPS: {1000/avg_time:.1f}")
        
        return avg_time < 5.0  # Should be under 5ms
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


def check_anti_flicker_system():
    """Check anti-flicker system."""
    
    print("🎯 Checking anti-flicker system...")
    
    try:
        from client.extreme_video_optimizer import extreme_video_optimizer
        
        # Test flicker prevention
        client_id = "test_client"
        
        # Rapid frame updates
        prevented_count = 0
        for i in range(20):
            should_display = extreme_video_optimizer.anti_flicker.should_display_frame(client_id)
            if not should_display:
                prevented_count += 1
            time.sleep(0.001)  # 1ms intervals
        
        print(f"   ✅ Flicker events prevented: {prevented_count}/20")
        print(f"   ✅ Prevention rate: {(prevented_count/20)*100:.1f}%")
        
        return prevented_count > 0
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


def main():
    """Main verification function."""
    
    print("🧪 EXTREME VIDEO OPTIMIZATION VERIFICATION")
    print("=" * 50)
    
    tests = [
        ("Optimization Active", verify_optimization_active),
        ("Frame Processing Speed", test_frame_processing_speed),
        ("Anti-Flicker System", check_anti_flicker_system)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 30)
        
        try:
            result = test_func()
            results.append(result)
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"   {status}")
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
            results.append(False)
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    print(f"\n📊 VERIFICATION RESULTS")
    print("=" * 50)
    print(f"Tests passed: {passed}/{total} ({(passed/total)*100:.1f}%)")
    
    if passed == total:
        print("\n🎉 ALL VERIFICATIONS PASSED!")
        print("Extreme video optimization is working correctly.")
        print("\nYou can now:")
        print("• Start your video application")
        print("• Enable video in the GUI")
        print("• Experience flicker-free, ultra-fast video")
    else:
        print("\n⚠️  SOME VERIFICATIONS FAILED")
        print("Please check the error messages above.")
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)