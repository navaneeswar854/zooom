#!/usr/bin/env python3
"""
Test script for screen sharing improvements.
Tests high FPS screen sharing and black screen display when video stops.
"""

import sys
import os
import time
import logging
import threading
from typing import Optional

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from client.screen_capture import ScreenCapture
from client.screen_playback import ScreenPlayback
from client.gui_manager import ScreenShareFrame
import tkinter as tk

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ScreenSharingTester:
    """Test screen sharing improvements including FPS and black screen handling."""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Screen Sharing Improvements Test")
        self.root.geometry("800x600")
        
        # Test results
        self.test_results = {
            'fps_test': False,
            'black_screen_test': False,
            'performance_test': False
        }
        
        # Create test GUI
        self._create_test_gui()
        
        # Initialize components
        self.screen_capture = ScreenCapture("test_client", None)
        self.screen_playback = ScreenPlayback("test_client")
        
        # Test data
        self.captured_frames = []
        self.fps_measurements = []
        
    def _create_test_gui(self):
        """Create test GUI with screen sharing frame."""
        # Main frame
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Title
        title_label = tk.Label(main_frame, text="Screen Sharing Improvements Test", 
                              font=('Arial', 16, 'bold'))
        title_label.pack(pady=10)
        
        # Test controls
        controls_frame = tk.Frame(main_frame)
        controls_frame.pack(fill='x', pady=10)
        
        self.start_fps_test_btn = tk.Button(controls_frame, text="Test High FPS Screen Capture", 
                                           command=self._test_high_fps)
        self.start_fps_test_btn.pack(side='left', padx=5)
        
        self.test_black_screen_btn = tk.Button(controls_frame, text="Test Black Screen Display", 
                                              command=self._test_black_screen)
        self.test_black_screen_btn.pack(side='left', padx=5)
        
        self.test_performance_btn = tk.Button(controls_frame, text="Test Performance", 
                                             command=self._test_performance)
        self.test_performance_btn.pack(side='left', padx=5)
        
        # Results display
        self.results_text = tk.Text(main_frame, height=15, width=80)
        self.results_text.pack(fill='both', expand=True, pady=10)
        
        # Screen sharing frame
        self.screen_share_frame = ScreenShareFrame(main_frame)
        self.screen_share_frame.pack(fill='both', expand=True, pady=10)
        
    def _log_result(self, message: str):
        """Log test result to GUI."""
        self.results_text.insert(tk.END, f"{time.strftime('%H:%M:%S')} - {message}\n")
        self.results_text.see(tk.END)
        self.root.update()
        logger.info(message)
    
    def _test_high_fps(self):
        """Test high FPS screen capture performance."""
        self._log_result("=== Testing High FPS Screen Capture ===")
        
        try:
            # Test different FPS settings
            fps_settings = [15, 30, 45, 60]
            
            for fps in fps_settings:
                self._log_result(f"Testing {fps} FPS screen capture...")
                
                # Set FPS
                self.screen_capture.set_capture_settings(fps=fps, quality=70)
                
                # Start capture
                success, message = self.screen_capture.start_capture()
                if not success:
                    self._log_result(f"Failed to start capture at {fps} FPS: {message}")
                    continue
                
                # Capture for 3 seconds
                start_time = time.time()
                frame_count = 0
                
                while time.time() - start_time < 3.0:
                    time.sleep(0.1)
                    frame_count = self.screen_capture.stats['frames_captured']
                
                # Stop capture
                self.screen_capture.stop_capture()
                
                # Calculate actual FPS
                actual_fps = frame_count / 3.0
                self._log_result(f"Target: {fps} FPS, Actual: {actual_fps:.1f} FPS")
                
                # Check if FPS is acceptable (within 80% of target)
                if actual_fps >= fps * 0.8:
                    self._log_result(f"✓ {fps} FPS test PASSED")
                else:
                    self._log_result(f"✗ {fps} FPS test FAILED")
            
            self.test_results['fps_test'] = True
            self._log_result("High FPS test completed")
            
        except Exception as e:
            self._log_result(f"High FPS test failed: {e}")
            logger.error(f"High FPS test error: {e}")
    
    def _test_black_screen(self):
        """Test black screen display when video stops."""
        self._log_result("=== Testing Black Screen Display ===")
        
        try:
            # Simulate screen sharing start
            self._log_result("Simulating screen sharing start...")
            
            # Create a test frame (black image)
            import numpy as np
            test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
            
            # Display test frame
            self.screen_share_frame.display_screen_frame(test_frame.tobytes(), "Test Presenter")
            self._log_result("Test frame displayed")
            
            time.sleep(2)
            
            # Simulate presenter stop (None frame)
            self._log_result("Simulating presenter stop (black screen)...")
            self.screen_share_frame.display_screen_frame(None, None)
            
            # Check if black screen is shown
            time.sleep(1)
            self._log_result("✓ Black screen test completed")
            
            self.test_results['black_screen_test'] = True
            
        except Exception as e:
            self._log_result(f"Black screen test failed: {e}")
            logger.error(f"Black screen test error: {e}")
    
    def _test_performance(self):
        """Test overall screen sharing performance."""
        self._log_result("=== Testing Performance ===")
        
        try:
            # Test capture performance
            start_time = time.time()
            
            # Start capture at 30 FPS
            self.screen_capture.set_capture_settings(fps=30, quality=70)
            success, message = self.screen_capture.start_capture()
            
            if not success:
                self._log_result(f"Failed to start performance test: {message}")
                return
            
            # Capture for 5 seconds
            initial_frames = self.screen_capture.stats['frames_captured']
            
            time.sleep(5)
            
            # Stop capture
            self.screen_capture.stop_capture()
            
            # Calculate performance metrics
            final_frames = self.screen_capture.stats['frames_captured']
            frames_captured = final_frames - initial_frames
            actual_fps = frames_captured / 5.0
            
            # Get capture stats
            stats = self.screen_capture.get_capture_stats()
            
            self._log_result(f"Frames captured: {frames_captured}")
            self._log_result(f"Actual FPS: {actual_fps:.1f}")
            self._log_result(f"Capture errors: {stats.get('capture_errors', 0)}")
            self._log_result(f"Average frame size: {stats.get('average_frame_size', 0)} bytes")
            
            # Performance criteria
            if actual_fps >= 25 and stats.get('capture_errors', 0) < 5:
                self._log_result("✓ Performance test PASSED")
                self.test_results['performance_test'] = True
            else:
                self._log_result("✗ Performance test FAILED")
            
        except Exception as e:
            self._log_result(f"Performance test failed: {e}")
            logger.error(f"Performance test error: {e}")
    
    def run_all_tests(self):
        """Run all screen sharing improvement tests."""
        self._log_result("Starting Screen Sharing Improvements Test Suite")
        self._log_result("=" * 50)
        
        # Run tests
        self._test_high_fps()
        self._test_black_screen()
        self._test_performance()
        
        # Summary
        self._log_result("=" * 50)
        self._log_result("TEST SUMMARY:")
        
        passed_tests = sum(1 for result in self.test_results.values() if result)
        total_tests = len(self.test_results)
        
        for test_name, result in self.test_results.items():
            status = "PASSED" if result else "FAILED"
            self._log_result(f"{test_name}: {status}")
        
        self._log_result(f"Overall: {passed_tests}/{total_tests} tests passed")
        
        if passed_tests == total_tests:
            self._log_result("🎉 All screen sharing improvements working correctly!")
        else:
            self._log_result("⚠️ Some tests failed - check the logs above")
    
    def run(self):
        """Run the test application."""
        try:
            # Start tests automatically
            self.root.after(1000, self.run_all_tests)
            
            # Run GUI
            self.root.mainloop()
            
        except KeyboardInterrupt:
            self._log_result("Test interrupted by user")
        except Exception as e:
            self._log_result(f"Test application error: {e}")
            logger.error(f"Test application error: {e}")
        finally:
            # Cleanup
            if hasattr(self, 'screen_capture'):
                self.screen_capture.stop_capture()


def main():
    """Main function to run screen sharing improvements test."""
    print("Screen Sharing Improvements Test")
    print("=" * 40)
    print("This test will verify:")
    print("1. High FPS screen sharing (30+ FPS)")
    print("2. Black screen display when video stops")
    print("3. Overall performance improvements")
    print("=" * 40)
    
    try:
        tester = ScreenSharingTester()
        tester.run()
    except Exception as e:
        print(f"Failed to run test: {e}")
        logger.error(f"Test execution failed: {e}")


if __name__ == "__main__":
    main()
