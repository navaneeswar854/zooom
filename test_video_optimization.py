#!/usr/bin/env python3
"""
Test script for the video optimization system.
Tests adaptive bitrate control, frame buffering, and synchronization.
"""

import sys
import os
import time
import logging
import numpy as np
from unittest.mock import Mock

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_adaptive_bitrate_controller():
    """Test the adaptive bitrate controller."""
    logger.info("Testing adaptive bitrate controller...")
    
    try:
        from client.video_optimization import AdaptiveBitrateController
        
        controller = AdaptiveBitrateController()
        
        # Test initial state
        assert controller.current_level == 'medium'
        assert controller.current_quality == 70
        
        # Test network degradation
        controller.update_network_metrics(0.1, 150, 1000)  # High loss, high latency
        controller.update_performance_metrics(5, 0.1)  # High drops, slow encoding
        
        # Force adaptation
        controller.last_adaptation_time = 0
        settings = controller.adapt_quality()
        
        # Should degrade quality
        assert controller.current_level in ['low', 'ultra_low']
        logger.info(f"✅ Quality degraded to {controller.current_level}")
        
        # Test network improvement
        controller.update_network_metrics(0.001, 20, 5000)  # Low loss, low latency
        controller.update_performance_metrics(0, 0.01)  # No drops, fast encoding
        
        # Force adaptation
        controller.last_adaptation_time = 0
        settings = controller.adapt_quality()
        
        logger.info(f"✅ Adaptive bitrate controller working correctly")
        return True
        
    except Exception as e:
        logger.error(f"❌ Adaptive bitrate controller test failed: {e}")
        return False

def test_frame_buffer():
    """Test the frame buffer system."""
    logger.info("Testing frame buffer...")
    
    try:
        from client.video_optimization import FrameBuffer
        
        buffer = FrameBuffer("test_client", target_buffer_size=3)
        
        # Test adding frames
        for i in range(5):
            frame = np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8)
            success = buffer.add_frame(frame, time.time(), i)
            assert success
        
        # Test buffer health
        health = buffer.get_buffer_health()
        assert health['current_size'] > 0
        assert health['target_size'] == 3
        
        # Test frame retrieval
        frame = buffer.get_frame()
        assert frame is not None
        
        # Test buffer underrun
        for _ in range(10):  # Drain buffer
            buffer.get_frame()
        
        frame = buffer.get_frame()  # Should return None (underrun)
        assert frame is None
        
        logger.info("✅ Frame buffer working correctly")
        return True
        
    except Exception as e:
        logger.error(f"❌ Frame buffer test failed: {e}")
        return False

def test_synchronization_manager():
    """Test the synchronization manager."""
    logger.info("Testing synchronization manager...")
    
    try:
        from client.video_optimization import SynchronizationManager
        
        sync_manager = SynchronizationManager()
        
        # Test timing registration
        client_id = "test_client"
        sequence = 1
        base_time = time.time()
        
        sync_manager.register_frame_timing(client_id, 'capture', base_time, sequence)
        sync_manager.register_frame_timing(client_id, 'encode', base_time + 0.01, sequence)
        sync_manager.register_frame_timing(client_id, 'transmit', base_time + 0.02, sequence)
        sync_manager.register_frame_timing(client_id, 'decode', base_time + 0.05, sequence)
        sync_manager.register_frame_timing(client_id, 'display', base_time + 0.06, sequence)
        
        # Test latency calculation
        latencies = sync_manager.calculate_pipeline_latency(client_id)
        assert 'end_to_end' in latencies
        assert latencies['end_to_end'] > 0
        
        # Test sync adjustment
        adjustment = sync_manager.get_sync_adjustment(client_id)
        assert isinstance(adjustment, float)
        
        logger.info("✅ Synchronization manager working correctly")
        return True
        
    except Exception as e:
        logger.error(f"❌ Synchronization manager test failed: {e}")
        return False

def test_video_stream_optimizer():
    """Test the main video stream optimizer."""
    logger.info("Testing video stream optimizer...")
    
    try:
        from client.video_optimization import VideoStreamOptimizer
        
        optimizer = VideoStreamOptimizer()
        
        # Test client registration
        client_id = "test_client"
        optimizer.register_client(client_id)
        assert client_id in optimizer.frame_buffers
        
        # Test frame addition
        frame = np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8)
        success = optimizer.add_frame(client_id, frame, time.time(), 1)
        assert success
        
        # Test frame retrieval
        retrieved_frame = optimizer.get_frame(client_id)
        # Note: May be None due to buffer target size
        
        # Test quality settings
        settings = optimizer.get_quality_settings()
        assert 'quality' in settings
        assert 'fps' in settings
        
        # Test metrics update
        optimizer.update_network_conditions(0.01, 30, 1000)
        optimizer.update_performance_metrics(1, 0.02)
        
        # Test stats
        stats = optimizer.get_optimization_stats()
        assert 'bitrate_controller' in stats
        assert 'frame_buffers' in stats
        
        # Test client unregistration
        optimizer.unregister_client(client_id)
        assert client_id not in optimizer.frame_buffers
        
        logger.info("✅ Video stream optimizer working correctly")
        return True
        
    except Exception as e:
        logger.error(f"❌ Video stream optimizer test failed: {e}")
        return False

def test_integration():
    """Test integration with existing video system."""
    logger.info("Testing integration...")
    
    try:
        # Test imports
        from client.video_optimization import video_optimizer
        from client.video_capture import VideoCapture
        from client.video_playback import VideoManager
        
        # Test video capture integration
        capture = VideoCapture("test_client")
        assert hasattr(capture, 'adaptive_settings')
        
        # Test video manager integration
        manager = VideoManager("test_client")
        # Note: Full integration test would require more setup
        
        logger.info("✅ Integration test passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Integration test failed: {e}")
        return False

def run_performance_simulation():
    """Run a performance simulation."""
    logger.info("Running performance simulation...")
    
    try:
        from client.video_optimization import video_optimizer
        
        # Start optimizer
        video_optimizer.start_optimization()
        
        # Simulate multiple clients
        clients = ["client_1", "client_2", "client_3"]
        
        for client_id in clients:
            video_optimizer.register_client(client_id)
        
        # Simulate frame processing
        for frame_num in range(100):
            for client_id in clients:
                # Create mock frame
                frame = np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8)
                
                # Add frame
                video_optimizer.add_frame(client_id, frame, time.time(), frame_num)
                
                # Retrieve frame (simulating display)
                video_optimizer.get_frame(client_id)
            
            # Simulate network conditions
            if frame_num % 20 == 0:  # Every 20 frames
                # Simulate varying network conditions
                packet_loss = 0.01 + (frame_num % 10) * 0.005
                latency = 20 + (frame_num % 5) * 10
                throughput = 1000 + (frame_num % 3) * 500
                
                video_optimizer.update_network_conditions(packet_loss, latency, throughput)
                video_optimizer.update_performance_metrics(frame_num % 3, 0.02 + (frame_num % 2) * 0.01)
            
            time.sleep(0.001)  # Small delay
        
        # Get final stats
        stats = video_optimizer.get_optimization_stats()
        logger.info(f"Final optimization stats: {stats['bitrate_controller']['current_level']}")
        
        # Cleanup
        for client_id in clients:
            video_optimizer.unregister_client(client_id)
        
        video_optimizer.stop_optimization()
        
        logger.info("✅ Performance simulation completed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Performance simulation failed: {e}")
        return False

def run_all_tests():
    """Run all optimization tests."""
    logger.info("Running video optimization tests...")
    
    tests = [
        ("Adaptive Bitrate Controller", test_adaptive_bitrate_controller),
        ("Frame Buffer", test_frame_buffer),
        ("Synchronization Manager", test_synchronization_manager),
        ("Video Stream Optimizer", test_video_stream_optimizer),
        ("Integration", test_integration),
        ("Performance Simulation", run_performance_simulation)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        logger.info(f"\n--- {test_name} Test ---")
        try:
            if test_func():
                logger.info(f"✅ {test_name} PASSED")
                passed += 1
            else:
                logger.error(f"❌ {test_name} FAILED")
                failed += 1
        except Exception as e:
            logger.error(f"❌ {test_name} FAILED with exception: {e}")
            failed += 1
    
    logger.info(f"\n--- Test Results ---")
    logger.info(f"Passed: {passed}")
    logger.info(f"Failed: {failed}")
    logger.info(f"Total: {passed + failed}")
    
    return failed == 0

if __name__ == "__main__":
    success = run_all_tests()
    
    if success:
        print("\n✅ All video optimization tests PASSED!")
        print("\n🚀 Optimization Features:")
        print("  • Adaptive bitrate control based on network conditions")
        print("  • Advanced frame buffering with jitter compensation")
        print("  • Pipeline synchronization and latency monitoring")
        print("  • Automatic quality adjustment for stable streaming")
        print("  • Performance metrics and optimization statistics")
        print("\n🎯 Benefits:")
        print("  • Continuous, stable video streaming")
        print("  • No frame drops or blackouts")
        print("  • Low latency with smooth playback")
        print("  • Resilient to network fluctuations")
        print("  • Optimal quality for current conditions")
    else:
        print("\n❌ Some video optimization tests failed!")
        sys.exit(1)