"""
Audio quality and latency tests for the collaboration suite.
Tests audio capture, encoding, mixing, playback, and latency measurements.
"""

import unittest
import time
import threading
import struct
from unittest.mock import Mock, MagicMock, patch
from client.audio_capture import AudioCapture, AudioEncoder
from client.audio_playback import AudioPlayback, AudioDecoder
from client.audio_manager import AudioManager
from server.media_relay import AudioMixer, MediaRelay
from common.messages import UDPPacket, MessageFactory


class TestAudioCapture(unittest.TestCase):
    """Test cases for audio capture functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.client_id = "test_client_123"
    
    @patch('client.audio_capture.pyaudio.PyAudio')
    def test_audio_capture_initialization(self, mock_pyaudio):
        """Test audio capture initialization."""
        # Mock PyAudio
        mock_instance = Mock()
        mock_pyaudio.return_value = mock_instance
        mock_instance.get_device_count.return_value = 2
        mock_instance.get_default_input_device_info.return_value = {'name': 'Test Mic'}
        
        # Initialize audio capture
        capture = AudioCapture(self.client_id)
        
        # Verify initialization
        self.assertEqual(capture.client_id, self.client_id)
        self.assertFalse(capture.is_capturing)
        self.assertFalse(capture.is_muted)
        self.assertEqual(capture.sequence_number, 0)
        
        # Verify PyAudio was initialized
        mock_pyaudio.assert_called_once()
        mock_instance.get_device_count.assert_called_once()
        mock_instance.get_default_input_device_info.assert_called_once()
    
    @patch('client.audio_capture.pyaudio.PyAudio')
    def test_audio_capture_start_stop(self, mock_pyaudio):
        """Test starting and stopping audio capture."""
        # Mock PyAudio and stream
        mock_instance = Mock()
        mock_stream = Mock()
        mock_pyaudio.return_value = mock_instance
        mock_instance.get_device_count.return_value = 1
        mock_instance.get_default_input_device_info.return_value = {'name': 'Test Mic'}
        mock_instance.open.return_value = mock_stream
        
        capture = AudioCapture(self.client_id)
        
        # Test start capture
        success = capture.start_capture()
        self.assertTrue(success)
        self.assertTrue(capture.is_capturing)
        
        # Verify stream was opened
        mock_instance.open.assert_called_once()
        
        # Test stop capture
        capture.stop_capture()
        self.assertFalse(capture.is_capturing)
        
        # Verify stream was closed
        mock_stream.stop_stream.assert_called_once()
        mock_stream.close.assert_called_once()
    
    def test_audio_encoding_pcm(self):
        """Test PCM audio encoding."""
        # Test data
        test_audio = b'\x00\x01\x02\x03\x04\x05'
        
        # Test PCM encoding (should return data as-is)
        encoded = AudioEncoder.encode_pcm(test_audio)
        self.assertEqual(encoded, test_audio)
        
        # Test codec info
        codec_info = AudioEncoder.get_codec_info('PCM')
        self.assertEqual(codec_info['name'], 'PCM')
        self.assertEqual(codec_info['compression_ratio'], 1.0)
        
        # Test supported codecs
        codecs = AudioEncoder.get_supported_codecs()
        self.assertIn('PCM', codecs)


class TestAudioPlayback(unittest.TestCase):
    """Test cases for audio playback functionality."""
    
    @patch('client.audio_playback.pyaudio.PyAudio')
    def test_audio_playback_initialization(self, mock_pyaudio):
        """Test audio playback initialization."""
        # Mock PyAudio
        mock_instance = Mock()
        mock_pyaudio.return_value = mock_instance
        mock_instance.get_device_count.return_value = 2
        mock_instance.get_default_output_device_info.return_value = {'name': 'Test Speaker'}
        
        # Initialize audio playback
        playback = AudioPlayback()
        
        # Verify initialization
        self.assertFalse(playback.is_playing)
        self.assertFalse(playback.is_muted)
        self.assertEqual(len(playback.audio_buffer), 0)
        
        # Verify PyAudio was initialized
        mock_pyaudio.assert_called_once()
        mock_instance.get_device_count.assert_called_once()
        mock_instance.get_default_output_device_info.assert_called_once()
    
    @patch('client.audio_playback.pyaudio.PyAudio')
    def test_audio_playback_start_stop(self, mock_pyaudio):
        """Test starting and stopping audio playback."""
        # Mock PyAudio and stream
        mock_instance = Mock()
        mock_stream = Mock()
        mock_pyaudio.return_value = mock_instance
        mock_instance.get_device_count.return_value = 1
        mock_instance.get_default_output_device_info.return_value = {'name': 'Test Speaker'}
        mock_instance.open.return_value = mock_stream
        
        playback = AudioPlayback()
        
        # Test start playback
        success = playback.start_playback()
        self.assertTrue(success)
        self.assertTrue(playback.is_playing)
        
        # Verify stream was opened
        mock_instance.open.assert_called_once()
        
        # Test stop playback
        playback.stop_playback()
        self.assertFalse(playback.is_playing)
        
        # Verify stream was closed
        mock_stream.stop_stream.assert_called_once()
        mock_stream.close.assert_called_once()
    
    def test_audio_packet_buffering(self):
        """Test audio packet buffering."""
        with patch('client.audio_playback.pyaudio.PyAudio'):
            playback = AudioPlayback()
            
            # Create test audio packet
            test_audio_data = b'\x00\x01' * 512  # 1024 bytes of test data
            audio_packet = MessageFactory.create_audio_packet(
                sender_id="test_sender",
                sequence_num=1,
                audio_data=test_audio_data
            )
            
            # Start playback to enable buffering
            with patch.object(playback, 'stream', Mock()):
                playback.is_playing = True
                
                # Add packet to buffer
                playback.add_audio_packet(audio_packet)
                
                # Verify packet was buffered
                self.assertEqual(len(playback.audio_buffer), 1)
                self.assertEqual(playback.stats['packets_received'], 1)
    
    def test_audio_decoding_pcm(self):
        """Test PCM audio decoding."""
        # Test data
        test_audio = b'\x00\x01\x02\x03\x04\x05'
        
        # Test PCM decoding (should return data as-is)
        decoded = AudioDecoder.decode_pcm(test_audio)
        self.assertEqual(decoded, test_audio)
        
        # Test codec info
        codec_info = AudioDecoder.get_codec_info('PCM')
        self.assertEqual(codec_info['name'], 'PCM')
        
        # Test supported codecs
        codecs = AudioDecoder.get_supported_codecs()
        self.assertIn('PCM', codecs)


class TestAudioMixer(unittest.TestCase):
    """Test cases for server-side audio mixing."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mixer = AudioMixer()
    
    def test_mixer_initialization(self):
        """Test audio mixer initialization."""
        self.assertFalse(self.mixer.is_mixing)
        self.assertEqual(len(self.mixer.client_buffers), 0)
        self.assertIsNone(self.mixer.mixed_audio_callback)
    
    def test_mixer_start_stop(self):
        """Test starting and stopping audio mixer."""
        # Test start mixing
        success = self.mixer.start_mixing()
        self.assertTrue(success)
        self.assertTrue(self.mixer.is_mixing)
        
        # Test stop mixing
        self.mixer.stop_mixing()
        self.assertFalse(self.mixer.is_mixing)
    
    def test_audio_stream_management(self):
        """Test adding and removing audio streams."""
        client_id = "test_client_1"
        
        # Create test audio packet
        test_audio_data = self._generate_test_audio_data(1024)
        audio_packet = MessageFactory.create_audio_packet(
            sender_id=client_id,
            sequence_num=1,
            audio_data=test_audio_data
        )
        
        # Add audio stream
        self.mixer.add_audio_stream(client_id, audio_packet)
        
        # Verify stream was added
        self.assertIn(client_id, self.mixer.client_buffers)
        self.assertEqual(len(self.mixer.client_buffers[client_id]), 1)
        
        # Remove audio stream
        self.mixer.remove_audio_stream(client_id)
        
        # Verify stream was removed
        self.assertNotIn(client_id, self.mixer.client_buffers)
    
    def test_audio_mixing_quality(self):
        """Test audio mixing quality with multiple streams."""
        # Create test audio data for multiple clients
        client1_data = self._generate_sine_wave(440, 0.1, 1024)  # 440Hz tone
        client2_data = self._generate_sine_wave(880, 0.1, 1024)  # 880Hz tone
        
        # Create audio packets
        packet1 = MessageFactory.create_audio_packet("client1", 1, client1_data)
        packet2 = MessageFactory.create_audio_packet("client2", 1, client2_data)
        
        # Add streams to mixer
        self.mixer.add_audio_stream("client1", packet1)
        self.mixer.add_audio_stream("client2", packet2)
        
        # Test mixing
        mixed_audio = self.mixer._mix_audio_buffers()
        
        # Verify mixed audio was generated
        self.assertIsNotNone(mixed_audio)
        self.assertGreater(len(mixed_audio), 0)
        
        # Verify mixed audio length matches input
        expected_length = min(len(client1_data), len(client2_data))
        self.assertEqual(len(mixed_audio), expected_length)
    
    def test_mixing_statistics(self):
        """Test audio mixing statistics."""
        # Start mixing
        self.mixer.start_mixing()
        
        # Get initial stats
        stats = self.mixer.get_mixing_stats()
        
        # Verify stats structure
        self.assertIn('total_mixed_packets', stats)
        self.assertIn('active_audio_clients', stats)
        self.assertIn('is_mixing', stats)
        self.assertIn('mixing_start_time', stats)
        
        # Verify initial values
        self.assertTrue(stats['is_mixing'])
        self.assertEqual(stats['total_mixed_packets'], 0)
        self.assertIsNotNone(stats['mixing_start_time'])
        
        # Stop mixing
        self.mixer.stop_mixing()
    
    def _generate_test_audio_data(self, size: int) -> bytes:
        """Generate test audio data."""
        # Generate simple test pattern
        data = []
        for i in range(size // 2):  # 2 bytes per sample for 16-bit
            sample = int((i % 1000) * 32)  # Simple sawtooth pattern
            data.append(sample)
        
        return struct.pack(f'<{len(data)}h', *data)
    
    def _generate_sine_wave(self, frequency: float, amplitude: float, size: int) -> bytes:
        """Generate sine wave audio data for testing."""
        import math
        
        sample_rate = 16000
        samples = []
        
        for i in range(size // 2):  # 2 bytes per sample
            t = i / sample_rate
            sample = int(amplitude * 32767 * math.sin(2 * math.pi * frequency * t))
            samples.append(sample)
        
        return struct.pack(f'<{len(samples)}h', *samples)


class TestAudioLatency(unittest.TestCase):
    """Test cases for audio latency measurements."""
    
    def test_audio_packet_timing(self):
        """Test audio packet timing and latency."""
        # Create audio packet with timestamp
        start_time = time.time()
        audio_data = b'\x00\x01' * 512
        
        packet = MessageFactory.create_audio_packet(
            sender_id="test_client",
            sequence_num=1,
            audio_data=audio_data
        )
        
        # Verify timestamp is recent
        packet_time = packet.timestamp
        time_diff = abs(packet_time - start_time)
        self.assertLess(time_diff, 0.1)  # Should be within 100ms
    
    def test_buffer_latency(self):
        """Test audio buffer latency characteristics."""
        with patch('client.audio_playback.pyaudio.PyAudio'):
            playback = AudioPlayback()
            
            # Simulate adding packets with timing
            packet_times = []
            for i in range(5):
                packet_time = time.time()
                packet_times.append(packet_time)
                
                audio_packet = MessageFactory.create_audio_packet(
                    sender_id="test_sender",
                    sequence_num=i,
                    audio_data=b'\x00\x01' * 512
                )
                audio_packet.timestamp = packet_time
                
                with patch.object(playback, 'stream', Mock()):
                    playback.is_playing = True
                    playback.add_audio_packet(audio_packet)
                
                time.sleep(0.01)  # 10ms between packets
            
            # Verify buffer contains packets
            self.assertEqual(len(playback.audio_buffer), 5)
            
            # Check buffer status
            buffer_status = playback.get_buffer_status()
            self.assertEqual(buffer_status['current_size'], 5)
            self.assertIn('health', buffer_status)
    
    def test_mixing_latency(self):
        """Test audio mixing latency."""
        mixer = AudioMixer()
        
        # Measure mixing time for multiple streams
        start_time = time.time()
        
        # Add multiple audio streams
        for i in range(3):
            client_id = f"client_{i}"
            audio_data = self._generate_test_audio(1024)
            
            packet = MessageFactory.create_audio_packet(
                sender_id=client_id,
                sequence_num=1,
                audio_data=audio_data
            )
            
            mixer.add_audio_stream(client_id, packet)
        
        # Perform mixing
        mixed_audio = mixer._mix_audio_buffers()
        
        mixing_time = time.time() - start_time
        
        # Verify mixing completed quickly (should be under 10ms for 3 streams)
        self.assertLess(mixing_time, 0.01)
        self.assertIsNotNone(mixed_audio)
    
    def _generate_test_audio(self, size: int) -> bytes:
        """Generate test audio data."""
        data = []
        for i in range(size // 2):
            sample = int((i % 100) * 300)  # Simple pattern
            data.append(sample)
        
        return struct.pack(f'<{len(data)}h', *data)


class TestAudioIntegration(unittest.TestCase):
    """Integration tests for complete audio system."""
    
    @patch('client.audio_capture.pyaudio.PyAudio')
    @patch('client.audio_playback.pyaudio.PyAudio')
    def test_audio_manager_integration(self, mock_playback_pyaudio, mock_capture_pyaudio):
        """Test complete audio manager integration."""
        # Mock PyAudio for both capture and playback
        mock_capture_instance = Mock()
        mock_playback_instance = Mock()
        mock_capture_pyaudio.return_value = mock_capture_instance
        mock_playback_pyaudio.return_value = mock_playback_instance
        
        # Mock device info
        mock_capture_instance.get_device_count.return_value = 1
        mock_capture_instance.get_default_input_device_info.return_value = {'name': 'Test Mic'}
        mock_playback_instance.get_device_count.return_value = 1
        mock_playback_instance.get_default_output_device_info.return_value = {'name': 'Test Speaker'}
        
        # Mock streams
        mock_capture_stream = Mock()
        mock_playback_stream = Mock()
        mock_capture_instance.open.return_value = mock_capture_stream
        mock_playback_instance.open.return_value = mock_playback_stream
        
        # Mock connection manager
        mock_connection = Mock()
        mock_connection.send_audio_data.return_value = True
        mock_connection.update_media_status.return_value = True
        
        # Create audio manager
        audio_manager = AudioManager("test_client", mock_connection)
        
        # Test starting audio
        success = audio_manager.start_audio()
        self.assertTrue(success)
        self.assertTrue(audio_manager.is_enabled())
        
        # Test muting
        audio_manager.set_muted(True)
        self.assertTrue(audio_manager.is_capture_muted_state())
        
        # Test unmuting
        audio_manager.set_muted(False)
        self.assertFalse(audio_manager.is_capture_muted_state())
        
        # Test stopping audio
        audio_manager.stop_audio()
        self.assertFalse(audio_manager.is_enabled())
        
        # Verify connection manager calls
        mock_connection.update_media_status.assert_called()
    
    def test_end_to_end_audio_flow(self):
        """Test end-to-end audio flow simulation."""
        # This test simulates the complete audio flow without actual hardware
        
        # 1. Create audio packet (simulating capture)
        test_audio_data = b'\x00\x01' * 512
        audio_packet = MessageFactory.create_audio_packet(
            sender_id="sender_client",
            sequence_num=1,
            audio_data=test_audio_data
        )
        
        # 2. Process through mixer (simulating server)
        mixer = AudioMixer()
        mixer.add_audio_stream("sender_client", audio_packet)
        mixed_audio = mixer._mix_audio_buffers()
        
        # 3. Create mixed packet for playback
        mixed_packet = MessageFactory.create_audio_packet(
            sender_id="server_mixer",
            sequence_num=1,
            audio_data=mixed_audio
        )
        
        # 4. Simulate playback reception
        with patch('client.audio_playback.pyaudio.PyAudio'):
            playback = AudioPlayback()
            
            with patch.object(playback, 'stream', Mock()):
                playback.is_playing = True
                playback.add_audio_packet(mixed_packet)
            
            # Verify packet was received
            self.assertEqual(len(playback.audio_buffer), 1)
            self.assertEqual(playback.stats['packets_received'], 1)


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)