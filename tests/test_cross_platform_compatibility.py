"""
Cross-platform compatibility tests for the LAN Collaboration Suite.
Tests platform-specific functionality and compatibility across Windows and Linux.
"""

import unittest
import sys
import os
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.platform_utils import (
    PlatformInfo, PathUtils, NetworkUtils, DeviceUtils, 
    ErrorHandler, is_windows, is_linux
)


class TestPlatformDetection(unittest.TestCase):
    """Test platform detection and capability checking."""
    
    def setUp(self):
        self.platform_info = PlatformInfo()
    
    def test_platform_detection(self):
        """Test basic platform detection."""
        # Should detect current platform correctly
        self.assertIsInstance(self.platform_info.system, str)
        self.assertIn(self.platform_info.system, ['Windows', 'Linux', 'Darwin'])
        
        # Test convenience functions
        if sys.platform.startswith('win'):
            self.assertTrue(is_windows())
            self.assertFalse(is_linux())
        elif sys.platform.startswith('linux'):
            self.assertTrue(is_linux())
            self.assertFalse(is_windows())
    
    def test_capability_detection(self):
        """Test capability detection."""
        capabilities = self.platform_info.capabilities
        
        # Should have all expected capabilities
        expected_capabilities = [
            'audio_capture', 'video_capture', 'screen_capture',
            'gui_framework', 'file_permissions', 'network_interfaces'
        ]
        
        for capability in expected_capabilities:
            self.assertIn(capability, capabilities)
            self.assertIsInstance(capabilities[capability], bool)
    
    def test_platform_summary(self):
        """Test platform summary generation."""
        summary = self.platform_info.get_platform_summary()
        
        required_keys = ['system', 'version', 'architecture', 'python_version', 'capabilities']
        for key in required_keys:
            self.assertIn(key, summary)


class TestCrossPlatformPaths(unittest.TestCase):
    """Test cross-platform path handling."""
    
    def test_safe_path_creation(self):
        """Test safe path creation."""
        test_path = "test/path/file.txt"
        safe_path = PathUtils.get_safe_path(test_path)
        
        self.assertIsInstance(safe_path, Path)
        self.assertTrue(safe_path.is_absolute())
    
    def test_downloads_directory(self):
        """Test downloads directory detection."""
        downloads_dir = PathUtils.get_downloads_dir()
        
        self.assertIsInstance(downloads_dir, Path)
        self.assertTrue(downloads_dir.exists())
        self.assertTrue(downloads_dir.is_dir())
    
    def test_app_data_directory(self):
        """Test application data directory creation."""
        app_name = "TestApp"
        app_dir = PathUtils.get_app_data_dir(app_name)
        
        self.assertIsInstance(app_dir, Path)
        self.assertTrue(app_dir.exists())
        self.assertTrue(app_dir.is_dir())
        self.assertIn(app_name, str(app_dir))
        
        # Cleanup
        try:
            app_dir.rmdir()
        except:
            pass
    
    def test_path_safety_validation(self):
        """Test path safety validation."""
        # Safe paths
        safe_paths = [
            "file.txt",
            "folder/file.txt",
            "valid_filename.pdf"
        ]
        
        for path in safe_paths:
            self.assertTrue(PathUtils.is_path_safe(path), f"Path should be safe: {path}")
        
        # Unsafe paths
        unsafe_paths = [
            "../../../etc/passwd",
            "..\\..\\windows\\system32",
            "folder/../../../file.txt"
        ]
        
        for path in unsafe_paths:
            self.assertFalse(PathUtils.is_path_safe(path), f"Path should be unsafe: {path}")
    
    def test_path_normalization(self):
        """Test path separator normalization."""
        test_paths = [
            "folder/subfolder/file.txt",
            "folder\\subfolder\\file.txt",
            "folder/subfolder\\file.txt"
        ]
        
        for path in test_paths:
            normalized = PathUtils.normalize_path_separators(path)
            self.assertIsInstance(normalized, str)
            # Should not contain mixed separators
            if os.sep == '/':
                self.assertNotIn('\\', normalized)
            else:
                self.assertNotIn('/', normalized)


class TestNetworkCompatibility(unittest.TestCase):
    """Test cross-platform networking functionality."""
    
    def test_local_ip_detection(self):
        """Test local IP address detection."""
        local_ip = NetworkUtils.get_local_ip()
        
        self.assertIsInstance(local_ip, str)
        # Should be a valid IP format
        parts = local_ip.split('.')
        self.assertEqual(len(parts), 4)
        for part in parts:
            self.assertTrue(0 <= int(part) <= 255)
    
    def test_available_port_detection(self):
        """Test available port detection."""
        port = NetworkUtils.get_available_port(8080)
        
        self.assertIsInstance(port, int)
        self.assertTrue(1024 <= port <= 65535)
    
    def test_socket_configuration(self):
        """Test socket configuration."""
        import socket
        
        # Test TCP socket configuration
        tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            NetworkUtils.configure_socket_options(tcp_sock, "tcp")
            # Should not raise an exception
        finally:
            tcp_sock.close()
        
        # Test UDP socket configuration
        udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            NetworkUtils.configure_socket_options(udp_sock, "udp")
            # Should not raise an exception
        finally:
            udp_sock.close()


class TestDeviceAccess(unittest.TestCase):
    """Test cross-platform device access."""
    
    def test_device_access_testing(self):
        """Test device access testing functionality."""
        device_status = DeviceUtils.test_device_access()
        
        expected_devices = ['audio_input', 'video_input', 'screen_capture']
        for device in expected_devices:
            self.assertIn(device, device_status)
            self.assertIsInstance(device_status[device], bool)
    
    @patch('pyaudio.PyAudio')
    def test_audio_device_enumeration(self, mock_pyaudio):
        """Test audio device enumeration."""
        # Mock PyAudio
        mock_pa_instance = Mock()
        mock_pa_instance.get_device_count.return_value = 2
        mock_pa_instance.get_device_info_by_index.side_effect = [
            {
                'name': 'Test Microphone',
                'maxInputChannels': 2,
                'defaultSampleRate': 44100
            },
            {
                'name': 'Test Speaker',
                'maxInputChannels': 0,
                'defaultSampleRate': 44100
            }
        ]
        mock_pyaudio.return_value = mock_pa_instance
        
        devices = DeviceUtils.get_audio_devices()
        
        # Should return only input devices
        self.assertEqual(len(devices), 1)
        self.assertEqual(devices[0]['name'], 'Test Microphone')
        self.assertEqual(devices[0]['channels'], 2)
    
    @patch('cv2.VideoCapture')
    def test_video_device_enumeration(self, mock_video_capture):
        """Test video device enumeration."""
        # Mock OpenCV VideoCapture
        mock_cap = Mock()
        mock_cap.isOpened.return_value = True
        mock_cap.get.side_effect = lambda prop: {
            3: 640,  # CAP_PROP_FRAME_WIDTH
            4: 480,  # CAP_PROP_FRAME_HEIGHT
            5: 30    # CAP_PROP_FPS
        }.get(prop, 0)
        
        mock_video_capture.return_value = mock_cap
        
        devices = DeviceUtils.get_video_devices()
        
        # Should detect available cameras
        self.assertGreaterEqual(len(devices), 0)
        if devices:
            device = devices[0]
            self.assertIn('index', device)
            self.assertIn('name', device)
            self.assertIn('width', device)
            self.assertIn('height', device)


class TestErrorHandling(unittest.TestCase):
    """Test cross-platform error handling."""
    
    def test_platform_specific_error_messages(self):
        """Test platform-specific error message generation."""
        # Test different error types
        test_errors = [
            PermissionError("Access denied"),
            FileNotFoundError("No such file or directory"),
            ConnectionError("Connection refused"),
            Exception("Generic error")
        ]
        
        for error in test_errors:
            message = ErrorHandler.get_platform_specific_error_message(error)
            self.assertIsInstance(message, str)
            self.assertGreater(len(message), 0)
    
    def test_platform_fix_suggestions(self):
        """Test platform-specific fix suggestions."""
        # Test permission errors
        permission_error = PermissionError("Permission denied")
        suggestion = ErrorHandler.suggest_platform_fix(permission_error)
        
        if suggestion:
            self.assertIsInstance(suggestion, str)
            self.assertGreater(len(suggestion), 0)
    
    def test_error_message_formatting(self):
        """Test error message formatting."""
        test_error = ValueError("Test error message")
        formatted_message = ErrorHandler.get_platform_specific_error_message(test_error)
        
        self.assertIn("ValueError", formatted_message)
        self.assertIn("Test error message", formatted_message)


class TestFileSystemCompatibility(unittest.TestCase):
    """Test cross-platform file system operations."""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
    
    def tearDown(self):
        # Cleanup temporary directory
        import shutil
        try:
            shutil.rmtree(self.temp_dir)
        except:
            pass
    
    def test_file_creation_and_access(self):
        """Test cross-platform file creation and access."""
        test_file = self.temp_path / "test_file.txt"
        test_content = "Test content for cross-platform compatibility"
        
        # Create file
        test_file.write_text(test_content, encoding='utf-8')
        
        # Verify file exists and content is correct
        self.assertTrue(test_file.exists())
        self.assertEqual(test_file.read_text(encoding='utf-8'), test_content)
    
    def test_directory_operations(self):
        """Test cross-platform directory operations."""
        test_dir = self.temp_path / "test_directory"
        
        # Create directory
        test_dir.mkdir(parents=True, exist_ok=True)
        
        # Verify directory exists
        self.assertTrue(test_dir.exists())
        self.assertTrue(test_dir.is_dir())
        
        # Create subdirectory
        sub_dir = test_dir / "subdirectory"
        sub_dir.mkdir()
        
        self.assertTrue(sub_dir.exists())
        self.assertTrue(sub_dir.is_dir())
    
    def test_file_permissions(self):
        """Test file permission handling."""
        test_file = self.temp_path / "permission_test.txt"
        test_file.write_text("test")
        
        # Test read access
        self.assertTrue(os.access(test_file, os.R_OK))
        
        # Test write access
        self.assertTrue(os.access(test_file, os.W_OK))


class TestIntegrationScenarios(unittest.TestCase):
    """Test integration scenarios across platforms."""
    
    def test_complete_platform_initialization(self):
        """Test complete platform initialization sequence."""
        # This simulates the startup sequence
        platform_info = PlatformInfo()
        
        # Check all capabilities
        capabilities = platform_info.get_platform_summary()
        self.assertIsInstance(capabilities, dict)
        
        # Test path utilities
        downloads_dir = PathUtils.get_downloads_dir()
        self.assertTrue(downloads_dir.exists())
        
        # Test network utilities
        local_ip = NetworkUtils.get_local_ip()
        self.assertIsInstance(local_ip, str)
        
        # Test device access
        device_status = DeviceUtils.test_device_access()
        self.assertIsInstance(device_status, dict)
    
    def test_error_recovery_scenarios(self):
        """Test error recovery in various scenarios."""
        # Test handling of missing dependencies
        with patch('builtins.__import__', side_effect=ImportError("Module not found")):
            # Should handle gracefully
            try:
                device_status = DeviceUtils.test_device_access()
                # Should return False for all devices
                for device, available in device_status.items():
                    self.assertFalse(available)
            except Exception as e:
                self.fail(f"Should handle missing dependencies gracefully: {e}")
    
    def test_concurrent_operations(self):
        """Test concurrent operations across platform utilities."""
        results = {}
        
        def test_network_operations():
            results['network'] = NetworkUtils.get_local_ip()
        
        def test_path_operations():
            results['path'] = PathUtils.get_downloads_dir()
        
        def test_device_operations():
            results['devices'] = DeviceUtils.test_device_access()
        
        # Run operations concurrently
        threads = [
            threading.Thread(target=test_network_operations),
            threading.Thread(target=test_path_operations),
            threading.Thread(target=test_device_operations)
        ]
        
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join(timeout=10)
        
        # Verify all operations completed
        self.assertIn('network', results)
        self.assertIn('path', results)
        self.assertIn('devices', results)


if __name__ == '__main__':
    # Configure test runner
    unittest.main(verbosity=2, buffer=True)