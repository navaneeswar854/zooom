"""
Integration tests for client-server connection functionality.
Tests connection establishment, disconnection, and basic message exchange.
"""

import unittest
import threading
import time
import socket
from unittest.mock import Mock, patch
from server.network_handler import NetworkHandler
from client.connection_manager import ConnectionManager, ConnectionStatus
from common.messages import MessageFactory, MessageType, TCPMessage


class TestClientServerIntegration(unittest.TestCase):
    """Integration test cases for client-server communication."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        # Use different ports for testing to avoid conflicts
        self.tcp_port = 18080
        self.udp_port = 18081
        self.server_host = 'localhost'
        
        # Initialize server
        self.server = NetworkHandler(
            tcp_port=self.tcp_port,
            udp_port=self.udp_port,
            host=self.server_host
        )
        
        # Start server in background thread
        self.server_thread = threading.Thread(
            target=self._run_server,
            daemon=True
        )
        self.server_thread.start()
        
        # Wait for server to start
        time.sleep(0.5)
        
        # Initialize client
        self.client = ConnectionManager(
            server_host=self.server_host,
            tcp_port=self.tcp_port,
            udp_port=self.udp_port
        )
        
        # Track connection events
        self.connection_events = []
        self.received_messages = []
        
        # Setup client callbacks
        self.client.register_status_callback(self._on_status_change)
        self.client.register_message_callback(MessageType.CHAT.value, self._on_chat_message)
        self.client.register_message_callback('participant_joined', self._on_participant_joined)
        self.client.register_message_callback('participant_left', self._on_participant_left)
    
    def tearDown(self):
        """Clean up after each test method."""
        # Disconnect client
        if self.client:
            self.client.disconnect()
        
        # Stop server
        if self.server:
            self.server.stop_servers()
        
        # Wait for cleanup
        time.sleep(0.2)
    
    def _run_server(self):
        """Run server in background thread."""
        try:
            self.server.start_servers()
        except Exception as e:
            print(f"Server error: {e}")
    
    def _on_status_change(self, status: str):
        """Track connection status changes."""
        self.connection_events.append(('status_change', status))
    
    def _on_chat_message(self, message: TCPMessage):
        """Track received chat messages."""
        self.received_messages.append(('chat', message))
    
    def _on_participant_joined(self, message: TCPMessage):
        """Track participant join events."""
        self.received_messages.append(('participant_joined', message))
    
    def _on_participant_left(self, message: TCPMessage):
        """Track participant leave events."""
        self.received_messages.append(('participant_left', message))
    
    def test_successful_connection(self):
        """Test successful client connection to server."""
        # Attempt connection
        success = self.client.connect("TestUser")
        
        # Verify connection success
        self.assertTrue(success)
        self.assertEqual(self.client.get_status(), ConnectionStatus.CONNECTED)
        self.assertIsNotNone(self.client.get_client_id())
        
        # Verify connection events
        status_events = [event for event in self.connection_events if event[0] == 'status_change']
        self.assertGreater(len(status_events), 0)
        
        # Should have connecting and connected events
        connecting_events = [event for event in status_events if event[1] == ConnectionStatus.CONNECTING]
        connected_events = [event for event in status_events if event[1] == ConnectionStatus.CONNECTED]
        
        self.assertGreater(len(connecting_events), 0)
        self.assertGreater(len(connected_events), 0)
        
        # Verify client is in server's session
        session_manager = self.server.get_session_manager()
        client_id = self.client.get_client_id()
        server_client = session_manager.get_client(client_id)
        
        self.assertIsNotNone(server_client)
        self.assertEqual(server_client.username, "TestUser")
    
    def test_connection_failure_invalid_server(self):
        """Test connection failure with invalid server address."""
        # Create client with invalid server
        invalid_client = ConnectionManager(
            server_host='invalid_host',
            tcp_port=99999,  # Invalid port
            udp_port=99998
        )
        
        # Attempt connection
        success = invalid_client.connect("TestUser")
        
        # Verify connection failure
        self.assertFalse(success)
        self.assertNotEqual(invalid_client.get_status(), ConnectionStatus.CONNECTED)
    
    def test_graceful_disconnection(self):
        """Test graceful client disconnection."""
        # Connect first
        success = self.client.connect("TestUser")
        self.assertTrue(success)
        
        client_id = self.client.get_client_id()
        
        # Verify client is connected on server
        session_manager = self.server.get_session_manager()
        self.assertIsNotNone(session_manager.get_client(client_id))
        
        # Disconnect
        self.client.disconnect()
        
        # Wait for disconnection to process
        time.sleep(0.2)
        
        # Verify disconnection
        self.assertEqual(self.client.get_status(), ConnectionStatus.DISCONNECTED)
        
        # Verify client is removed from server
        self.assertIsNone(session_manager.get_client(client_id))
    
    def test_chat_message_exchange(self):
        """Test sending and receiving chat messages."""
        # Connect client
        success = self.client.connect("TestUser")
        self.assertTrue(success)
        
        # Clear any initial messages
        self.received_messages.clear()
        
        # Send chat message
        test_message = "Hello, this is a test message!"
        success = self.client.send_chat_message(test_message)
        self.assertTrue(success)
        
        # Wait for message processing
        time.sleep(0.2)
        
        # Verify message was added to server's chat history
        session_manager = self.server.get_session_manager()
        chat_history = session_manager.get_chat_history()
        
        chat_messages = [msg for msg in chat_history if msg.msg_type == MessageType.CHAT.value]
        self.assertGreater(len(chat_messages), 0)
        
        # Find our test message
        test_messages = [msg for msg in chat_messages 
                        if msg.data.get('message') == test_message]
        self.assertEqual(len(test_messages), 1)
        
        test_msg = test_messages[0]
        self.assertEqual(test_msg.sender_id, self.client.get_client_id())
    
    def test_multiple_client_connections(self):
        """Test multiple clients connecting simultaneously."""
        # Connect first client
        success1 = self.client.connect("User1")
        self.assertTrue(success1)
        
        # Create and connect second client
        client2 = ConnectionManager(
            server_host=self.server_host,
            tcp_port=self.tcp_port,
            udp_port=self.udp_port
        )
        
        # Track events for second client
        client2_events = []
        client2.register_status_callback(lambda status: client2_events.append(status))
        
        success2 = client2.connect("User2")
        self.assertTrue(success2)
        
        # Wait for connections to stabilize
        time.sleep(0.3)
        
        # Verify both clients are connected
        self.assertEqual(self.client.get_status(), ConnectionStatus.CONNECTED)
        self.assertEqual(client2.get_status(), ConnectionStatus.CONNECTED)
        
        # Verify both clients have different IDs
        client1_id = self.client.get_client_id()
        client2_id = client2.get_client_id()
        self.assertNotEqual(client1_id, client2_id)
        
        # Verify both clients are in server session
        session_manager = self.server.get_session_manager()
        self.assertIsNotNone(session_manager.get_client(client1_id))
        self.assertIsNotNone(session_manager.get_client(client2_id))
        
        # Verify participant lists
        participants1 = self.client.get_participants()
        participants2 = client2.get_participants()
        
        # Each client should see the other
        self.assertIn(client2_id, participants1)
        self.assertIn(client1_id, participants2)
        
        # Cleanup second client
        client2.disconnect()
        time.sleep(0.2)
    
    def test_media_status_updates(self):
        """Test media status update messages."""
        # Connect client
        success = self.client.connect("TestUser")
        self.assertTrue(success)
        
        client_id = self.client.get_client_id()
        
        # Update media status
        success = self.client.update_media_status(video_enabled=True, audio_enabled=True)
        self.assertTrue(success)
        
        # Wait for update processing
        time.sleep(0.2)
        
        # Verify status was updated on server
        session_manager = self.server.get_session_manager()
        server_client = session_manager.get_client(client_id)
        
        self.assertIsNotNone(server_client)
        self.assertTrue(server_client.video_enabled)
        self.assertTrue(server_client.audio_enabled)
        
        # Update status again
        success = self.client.update_media_status(video_enabled=False, audio_enabled=False)
        self.assertTrue(success)
        
        # Wait for update processing
        time.sleep(0.2)
        
        # Verify status was updated
        server_client = session_manager.get_client(client_id)
        self.assertFalse(server_client.video_enabled)
        self.assertFalse(server_client.audio_enabled)
    
    def test_heartbeat_mechanism(self):
        """Test heartbeat mechanism maintains connection."""
        # Connect client
        success = self.client.connect("TestUser")
        self.assertTrue(success)
        
        client_id = self.client.get_client_id()
        
        # Get initial heartbeat time
        session_manager = self.server.get_session_manager()
        server_client = session_manager.get_client(client_id)
        initial_heartbeat = server_client.last_heartbeat
        
        # Wait for heartbeat to be sent (heartbeat interval is 5 seconds)
        time.sleep(6)
        
        # Verify heartbeat was updated
        server_client = session_manager.get_client(client_id)
        self.assertGreater(server_client.last_heartbeat, initial_heartbeat)
        
        # Verify connection is still active
        self.assertEqual(self.client.get_status(), ConnectionStatus.CONNECTED)
    
    def test_screen_sharing_messages(self):
        """Test screen sharing start/stop messages."""
        # Connect client
        success = self.client.connect("TestUser")
        self.assertTrue(success)
        
        client_id = self.client.get_client_id()
        
        # Start screen sharing
        success = self.client.start_screen_sharing()
        self.assertTrue(success)
        
        # Wait for message processing
        time.sleep(0.2)
        
        # Verify presenter was set on server
        session_manager = self.server.get_session_manager()
        presenter = session_manager.get_presenter()
        
        self.assertIsNotNone(presenter)
        self.assertEqual(presenter.client_id, client_id)
        
        # Stop screen sharing
        success = self.client.stop_screen_sharing()
        self.assertTrue(success)
        
        # Wait for message processing
        time.sleep(0.2)
        
        # Verify presenter was cleared
        presenter = session_manager.get_presenter()
        self.assertIsNone(presenter)
    
    def test_udp_packet_transmission(self):
        """Test UDP packet transmission for media data."""
        # Connect client
        success = self.client.connect("TestUser")
        self.assertTrue(success)
        
        # Wait for connection to stabilize
        time.sleep(0.3)
        
        # Send audio data
        test_audio_data = b"fake_audio_data_12345"
        success = self.client.send_audio_data(test_audio_data)
        self.assertTrue(success)
        
        # Send video data
        test_video_data = b"fake_video_data_67890"
        success = self.client.send_video_data(test_video_data)
        self.assertTrue(success)
        
        # Note: In a real test, we would verify the data was received
        # by the server and potentially broadcast to other clients.
        # For this basic test, we just verify the send operations succeed.
    
    def test_connection_info_retrieval(self):
        """Test retrieving connection information."""
        # Connect client
        success = self.client.connect("TestUser")
        self.assertTrue(success)
        
        # Get connection info
        conn_info = self.client.get_connection_info()
        
        # Verify connection info structure
        self.assertIn('status', conn_info)
        self.assertIn('client_id', conn_info)
        self.assertIn('username', conn_info)
        self.assertIn('server_host', conn_info)
        self.assertIn('tcp_port', conn_info)
        self.assertIn('udp_port', conn_info)
        self.assertIn('uptime', conn_info)
        self.assertIn('participant_count', conn_info)
        
        # Verify values
        self.assertEqual(conn_info['status'], ConnectionStatus.CONNECTED)
        self.assertEqual(conn_info['client_id'], self.client.get_client_id())
        self.assertEqual(conn_info['username'], "TestUser")
        self.assertEqual(conn_info['server_host'], self.server_host)
        self.assertEqual(conn_info['tcp_port'], self.tcp_port)
        self.assertEqual(conn_info['udp_port'], self.udp_port)
        self.assertGreaterEqual(conn_info['uptime'], 0)
    
    def test_server_shutdown_handling(self):
        """Test client behavior when server shuts down."""
        # Connect client
        success = self.client.connect("TestUser")
        self.assertTrue(success)
        
        # Clear connection events
        self.connection_events.clear()
        
        # Shutdown server
        self.server.stop_servers()
        
        # Wait for client to detect disconnection
        time.sleep(2)
        
        # Verify client detected disconnection
        # Client should attempt reconnection or go to error state
        final_status = self.client.get_status()
        self.assertIn(final_status, [
            ConnectionStatus.RECONNECTING, 
            ConnectionStatus.ERROR, 
            ConnectionStatus.DISCONNECTED
        ])
    
    @patch('socket.socket')
    def test_network_error_handling(self, mock_socket):
        """Test handling of network errors during communication."""
        # Mock socket to raise exception
        mock_socket_instance = Mock()
        mock_socket_instance.connect.side_effect = socket.error("Connection refused")
        mock_socket.return_value = mock_socket_instance
        
        # Attempt connection
        success = self.client.connect("TestUser")
        
        # Verify connection failure is handled gracefully
        self.assertFalse(success)
        self.assertNotEqual(self.client.get_status(), ConnectionStatus.CONNECTED)


class TestClientServerMessageFlow(unittest.TestCase):
    """Test message flow between multiple clients through server."""
    
    def setUp(self):
        """Set up test environment with server and multiple clients."""
        # Use different ports to avoid conflicts with other tests
        self.tcp_port = 19080
        self.udp_port = 19081
        self.server_host = 'localhost'
        
        # Start server
        self.server = NetworkHandler(
            tcp_port=self.tcp_port,
            udp_port=self.udp_port,
            host=self.server_host
        )
        
        self.server_thread = threading.Thread(
            target=self.server.start_servers,
            daemon=True
        )
        self.server_thread.start()
        time.sleep(0.5)
        
        # Create multiple clients
        self.client1 = ConnectionManager(
            server_host=self.server_host,
            tcp_port=self.tcp_port,
            udp_port=self.udp_port
        )
        
        self.client2 = ConnectionManager(
            server_host=self.server_host,
            tcp_port=self.tcp_port,
            udp_port=self.udp_port
        )
        
        # Track messages for each client
        self.client1_messages = []
        self.client2_messages = []
        
        self.client1.register_message_callback(
            MessageType.CHAT.value, 
            lambda msg: self.client1_messages.append(msg)
        )
        self.client2.register_message_callback(
            MessageType.CHAT.value, 
            lambda msg: self.client2_messages.append(msg)
        )
    
    def tearDown(self):
        """Clean up test environment."""
        if self.client1:
            self.client1.disconnect()
        if self.client2:
            self.client2.disconnect()
        if self.server:
            self.server.stop_servers()
        time.sleep(0.2)
    
    def test_chat_message_broadcast(self):
        """Test chat messages are broadcast between clients."""
        # Connect both clients
        success1 = self.client1.connect("User1")
        success2 = self.client2.connect("User2")
        
        self.assertTrue(success1)
        self.assertTrue(success2)
        
        # Wait for connections to stabilize
        time.sleep(0.3)
        
        # Clear any initial messages
        self.client1_messages.clear()
        self.client2_messages.clear()
        
        # Client1 sends message
        test_message = "Hello from User1!"
        success = self.client1.send_chat_message(test_message)
        self.assertTrue(success)
        
        # Wait for message broadcast
        time.sleep(0.3)
        
        # Verify Client2 received the message
        chat_messages = [msg for msg in self.client2_messages 
                        if msg.msg_type == MessageType.CHAT.value]
        
        self.assertGreater(len(chat_messages), 0)
        
        # Find the test message
        test_messages = [msg for msg in chat_messages 
                        if msg.data.get('message') == test_message]
        
        self.assertEqual(len(test_messages), 1)
        self.assertEqual(test_messages[0].sender_id, self.client1.get_client_id())
    
    def test_participant_notifications(self):
        """Test participant join/leave notifications."""
        # Track participant events
        client1_participant_events = []
        client2_participant_events = []
        
        self.client1.register_message_callback(
            'participant_joined',
            lambda msg: client1_participant_events.append(('joined', msg))
        )
        self.client1.register_message_callback(
            'participant_left',
            lambda msg: client1_participant_events.append(('left', msg))
        )
        
        self.client2.register_message_callback(
            'participant_joined',
            lambda msg: client2_participant_events.append(('joined', msg))
        )
        self.client2.register_message_callback(
            'participant_left',
            lambda msg: client2_participant_events.append(('left', msg))
        )
        
        # Connect first client
        success1 = self.client1.connect("User1")
        self.assertTrue(success1)
        time.sleep(0.2)
        
        # Connect second client
        success2 = self.client2.connect("User2")
        self.assertTrue(success2)
        time.sleep(0.3)
        
        # Client1 should have received notification about Client2 joining
        joined_events = [event for event in client1_participant_events 
                        if event[0] == 'joined']
        self.assertGreater(len(joined_events), 0)
        
        # Disconnect Client2
        self.client2.disconnect()
        time.sleep(0.3)
        
        # Client1 should have received notification about Client2 leaving
        left_events = [event for event in client1_participant_events 
                      if event[0] == 'left']
        self.assertGreater(len(left_events), 0)


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)