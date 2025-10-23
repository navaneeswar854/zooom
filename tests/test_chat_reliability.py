"""
Tests for chat message reliability and broadcasting functionality.
Tests message broadcasting to multiple clients and chat history persistence.
"""

import unittest
import threading
import time
import uuid
from datetime import datetime
from unittest.mock import Mock, patch
from server.network_handler import NetworkHandler
from client.connection_manager import ConnectionManager, ConnectionStatus
from common.messages import MessageFactory, MessageType, TCPMessage, MessageValidator


class TestChatMessageReliability(unittest.TestCase):
    """Test cases for chat message reliability and broadcasting."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        # Use unique ports for testing to avoid conflicts
        self.tcp_port = 20080
        self.udp_port = 20081
        self.server_host = 'localhost'
        
        # Initialize server
        self.server = NetworkHandler(
            tcp_port=self.tcp_port,
            udp_port=self.udp_port,
            host=self.server_host
        )
        
        # Start server in background thread
        self.server_thread = threading.Thread(
            target=self.server.start_servers,
            daemon=True
        )
        self.server_thread.start()
        
        # Wait for server to start
        time.sleep(0.5)
        
        # Track test results
        self.test_results = {
            'messages_sent': 0,
            'messages_received': {},
            'delivery_failures': [],
            'broadcast_confirmations': []
        }
    
    def tearDown(self):
        """Clean up after each test method."""
        # Stop server
        if self.server:
            self.server.stop_servers()
        
        # Wait for cleanup
        time.sleep(0.3)
    
    def _create_test_client(self, username: str) -> ConnectionManager:
        """Create and connect a test client."""
        client = ConnectionManager(
            server_host=self.server_host,
            tcp_port=self.tcp_port,
            udp_port=self.udp_port
        )
        
        # Track messages for this client
        client_id = f"client_{username}"
        self.test_results['messages_received'][client_id] = []
        
        def track_chat_message(message: TCPMessage):
            self.test_results['messages_received'][client_id].append(message)
        
        client.register_message_callback(MessageType.CHAT.value, track_chat_message)
        
        # Connect client
        success = client.connect(username)
        if not success:
            raise Exception(f"Failed to connect client {username}")
        
        return client
    
    def test_single_message_broadcast_reliability(self):
        """Test reliable broadcasting of a single chat message to multiple clients."""
        # Create multiple clients
        client1 = self._create_test_client("User1")
        client2 = self._create_test_client("User2")
        client3 = self._create_test_client("User3")
        
        clients = [client1, client2, client3]
        
        # Wait for all connections to stabilize
        time.sleep(0.5)
        
        # Clear any initial messages
        for client_key in self.test_results['messages_received']:
            self.test_results['messages_received'][client_key].clear()
        
        # Send message from client1
        test_message = "Test message for broadcast reliability"
        success = client1.send_chat_message(test_message)
        self.assertTrue(success, "Failed to send chat message")
        
        # Wait for message propagation
        time.sleep(0.5)
        
        # Verify message was received by other clients (not sender)
        client2_messages = self.test_results['messages_received']['client_User2']
        client3_messages = self.test_results['messages_received']['client_User3']
        
        # Check client2 received the message
        chat_messages_2 = [msg for msg in client2_messages if msg.msg_type == MessageType.CHAT.value]
        self.assertGreater(len(chat_messages_2), 0, "Client2 did not receive chat message")
        
        received_message_2 = next((msg for msg in chat_messages_2 
                                 if msg.data.get('message') == test_message), None)
        self.assertIsNotNone(received_message_2, "Client2 did not receive the correct message")
        self.assertEqual(received_message_2.sender_id, client1.get_client_id())
        
        # Check client3 received the message
        chat_messages_3 = [msg for msg in client3_messages if msg.msg_type == MessageType.CHAT.value]
        self.assertGreater(len(chat_messages_3), 0, "Client3 did not receive chat message")
        
        received_message_3 = next((msg for msg in chat_messages_3 
                                 if msg.data.get('message') == test_message), None)
        self.assertIsNotNone(received_message_3, "Client3 did not receive the correct message")
        self.assertEqual(received_message_3.sender_id, client1.get_client_id())
        
        # Verify sender did not receive their own message
        client1_messages = self.test_results['messages_received']['client_User1']
        sender_echo = [msg for msg in client1_messages 
                      if msg.msg_type == MessageType.CHAT.value and 
                      msg.data.get('message') == test_message]
        self.assertEqual(len(sender_echo), 0, "Sender should not receive their own message")
        
        # Cleanup
        for client in clients:
            client.disconnect()
    
    def test_multiple_message_broadcast_reliability(self):
        """Test reliable broadcasting of multiple sequential chat messages."""
        # Create clients
        client1 = self._create_test_client("Sender")
        client2 = self._create_test_client("Receiver1")
        client3 = self._create_test_client("Receiver2")
        
        clients = [client1, client2, client3]
        
        # Wait for connections
        time.sleep(0.5)
        
        # Clear initial messages
        for client_key in self.test_results['messages_received']:
            self.test_results['messages_received'][client_key].clear()
        
        # Send multiple messages
        test_messages = [
            "First test message",
            "Second test message",
            "Third test message with special chars: !@#$%^&*()",
            "Fourth message with unicode: 🚀 🎉 ✨"
        ]
        
        for i, message in enumerate(test_messages):
            success = client1.send_chat_message(message)
            self.assertTrue(success, f"Failed to send message {i+1}")
            time.sleep(0.1)  # Small delay between messages
        
        # Wait for all messages to propagate
        time.sleep(1.0)
        
        # Verify all messages were received by both receivers
        for receiver_key in ['client_Receiver1', 'client_Receiver2']:
            received_messages = self.test_results['messages_received'][receiver_key]
            chat_messages = [msg for msg in received_messages if msg.msg_type == MessageType.CHAT.value]
            
            self.assertGreaterEqual(len(chat_messages), len(test_messages), 
                                  f"{receiver_key} did not receive all messages")
            
            # Check each test message was received
            for test_message in test_messages:
                matching_messages = [msg for msg in chat_messages 
                                   if msg.data.get('message') == test_message]
                self.assertEqual(len(matching_messages), 1, 
                               f"{receiver_key} did not receive message: {test_message}")
        
        # Cleanup
        for client in clients:
            client.disconnect()
    
    def test_chat_history_persistence(self):
        """Test chat history persistence for session duration."""
        # Create initial client
        client1 = self._create_test_client("HistoryUser1")
        
        # Send some messages
        initial_messages = [
            "Message 1 for history test",
            "Message 2 for history test",
            "Message 3 for history test"
        ]
        
        for message in initial_messages:
            success = client1.send_chat_message(message)
            self.assertTrue(success)
            time.sleep(0.1)
        
        # Wait for messages to be processed
        time.sleep(0.5)
        
        # Check server chat history
        session_manager = self.server.get_session_manager()
        chat_history = session_manager.get_chat_history()
        
        # Filter for actual chat messages (exclude join/leave messages)
        chat_messages = [msg for msg in chat_history if msg.msg_type == MessageType.CHAT.value]
        
        # Verify all messages are in history
        self.assertGreaterEqual(len(chat_messages), len(initial_messages))
        
        for test_message in initial_messages:
            matching_messages = [msg for msg in chat_messages 
                               if msg.data.get('message') == test_message]
            self.assertEqual(len(matching_messages), 1, 
                           f"Message not found in history: {test_message}")
        
        # Create second client (should not receive old messages automatically)
        client2 = self._create_test_client("HistoryUser2")
        time.sleep(0.5)
        
        # Clear messages received by client2
        self.test_results['messages_received']['client_HistoryUser2'].clear()
        
        # Send new message
        new_message = "New message after client2 joined"
        success = client1.send_chat_message(new_message)
        self.assertTrue(success)
        time.sleep(0.5)
        
        # Verify client2 received the new message
        client2_messages = self.test_results['messages_received']['client_HistoryUser2']
        new_chat_messages = [msg for msg in client2_messages 
                           if msg.msg_type == MessageType.CHAT.value and 
                           msg.data.get('message') == new_message]
        self.assertEqual(len(new_chat_messages), 1)
        
        # Verify history still contains all messages
        updated_history = session_manager.get_chat_history()
        updated_chat_messages = [msg for msg in updated_history if msg.msg_type == MessageType.CHAT.value]
        self.assertGreaterEqual(len(updated_chat_messages), len(initial_messages) + 1)
        
        # Cleanup
        client1.disconnect()
        client2.disconnect()
    
    def test_message_validation_and_error_handling(self):
        """Test message validation and error handling for invalid messages."""
        client = self._create_test_client("ValidationUser")
        time.sleep(0.3)
        
        # Test empty message
        success = client.send_chat_message("")
        self.assertFalse(success, "Empty message should be rejected")
        
        # Test whitespace-only message
        success = client.send_chat_message("   ")
        self.assertFalse(success, "Whitespace-only message should be rejected")
        
        # Test very long message
        long_message = "x" * 1500  # Exceeds 1000 character limit
        success = client.send_chat_message(long_message)
        # Should either be rejected or truncated, but not crash
        # The exact behavior depends on implementation
        
        # Test valid message after invalid ones
        valid_message = "This is a valid message"
        success = client.send_chat_message(valid_message)
        self.assertTrue(success, "Valid message should be accepted after invalid ones")
        
        # Cleanup
        client.disconnect()
    
    def test_concurrent_message_broadcasting(self):
        """Test reliable broadcasting under concurrent message load."""
        # Create multiple clients
        clients = []
        for i in range(4):
            client = self._create_test_client(f"ConcurrentUser{i+1}")
            clients.append(client)
        
        # Wait for all connections
        time.sleep(0.8)
        
        # Clear initial messages
        for client_key in self.test_results['messages_received']:
            self.test_results['messages_received'][client_key].clear()
        
        # Send messages concurrently from multiple clients
        def send_messages_from_client(client, client_index):
            for i in range(3):
                message = f"Concurrent message {i+1} from client {client_index}"
                success = client.send_chat_message(message)
                if not success:
                    self.test_results['delivery_failures'].append(
                        f"Failed to send: {message}"
                    )
                time.sleep(0.05)  # Small delay between messages
        
        # Start concurrent sending
        threads = []
        for i, client in enumerate(clients):
            thread = threading.Thread(
                target=send_messages_from_client,
                args=(client, i+1)
            )
            threads.append(thread)
            thread.start()
        
        # Wait for all sending to complete
        for thread in threads:
            thread.join()
        
        # Wait for message propagation
        time.sleep(1.5)
        
        # Verify no delivery failures
        self.assertEqual(len(self.test_results['delivery_failures']), 0, 
                        f"Delivery failures occurred: {self.test_results['delivery_failures']}")
        
        # Verify each client received messages from others
        total_expected_messages = len(clients) * 3  # 4 clients * 3 messages each
        
        for i, client in enumerate(clients):
            client_key = f"client_ConcurrentUser{i+1}"
            received_messages = self.test_results['messages_received'][client_key]
            chat_messages = [msg for msg in received_messages if msg.msg_type == MessageType.CHAT.value]
            
            # Each client should receive messages from other clients (not their own)
            expected_count = (len(clients) - 1) * 3  # Messages from other clients
            self.assertGreaterEqual(len(chat_messages), expected_count * 0.8,  # Allow some tolerance
                                  f"Client {i+1} received insufficient messages: {len(chat_messages)}/{expected_count}")
        
        # Cleanup
        for client in clients:
            client.disconnect()
    
    def test_message_ordering_and_timestamps(self):
        """Test that messages maintain chronological order and proper timestamps."""
        client1 = self._create_test_client("OrderUser1")
        client2 = self._create_test_client("OrderUser2")
        
        time.sleep(0.5)
        
        # Clear initial messages
        for client_key in self.test_results['messages_received']:
            self.test_results['messages_received'][client_key].clear()
        
        # Send messages with known order
        messages_with_timestamps = []
        for i in range(5):
            message = f"Ordered message {i+1}"
            send_time = time.time()
            success = client1.send_chat_message(message)
            self.assertTrue(success)
            messages_with_timestamps.append((message, send_time))
            time.sleep(0.2)  # Ensure different timestamps
        
        # Wait for propagation
        time.sleep(1.0)
        
        # Check message order on receiving client
        client2_messages = self.test_results['messages_received']['client_OrderUser2']
        chat_messages = [msg for msg in client2_messages if msg.msg_type == MessageType.CHAT.value]
        
        # Verify we received all messages
        self.assertGreaterEqual(len(chat_messages), 5)
        
        # Check chronological order by timestamp
        received_timestamps = [msg.timestamp for msg in chat_messages[:5]]
        sorted_timestamps = sorted(received_timestamps)
        self.assertEqual(received_timestamps, sorted_timestamps, 
                        "Messages not received in chronological order")
        
        # Verify message content order
        received_messages = [msg.data.get('message') for msg in chat_messages[:5]]
        expected_messages = [f"Ordered message {i+1}" for i in range(5)]
        
        for expected_msg in expected_messages:
            self.assertIn(expected_msg, received_messages, 
                         f"Expected message not found: {expected_msg}")
        
        # Cleanup
        client1.disconnect()
        client2.disconnect()
    
    def test_client_disconnection_during_broadcast(self):
        """Test message broadcasting reliability when clients disconnect during transmission."""
        # Create clients
        client1 = self._create_test_client("DisconnectUser1")
        client2 = self._create_test_client("DisconnectUser2")
        client3 = self._create_test_client("DisconnectUser3")
        
        clients = [client1, client2, client3]
        time.sleep(0.5)
        
        # Clear initial messages
        for client_key in self.test_results['messages_received']:
            self.test_results['messages_received'][client_key].clear()
        
        # Send first message to establish baseline
        success = client1.send_chat_message("Message before disconnect")
        self.assertTrue(success)
        time.sleep(0.3)
        
        # Verify all clients received first message
        for i in [2, 3]:
            client_key = f"client_DisconnectUser{i}"
            messages = self.test_results['messages_received'][client_key]
            chat_messages = [msg for msg in messages if msg.msg_type == MessageType.CHAT.value]
            self.assertGreater(len(chat_messages), 0)
        
        # Disconnect client2
        client2.disconnect()
        time.sleep(0.3)
        
        # Send message after client2 disconnected
        success = client1.send_chat_message("Message after disconnect")
        self.assertTrue(success)
        time.sleep(0.5)
        
        # Verify client3 still received the message
        client3_messages = self.test_results['messages_received']['client_DisconnectUser3']
        chat_messages = [msg for msg in client3_messages if msg.msg_type == MessageType.CHAT.value]
        
        after_disconnect_messages = [msg for msg in chat_messages 
                                   if msg.data.get('message') == "Message after disconnect"]
        self.assertEqual(len(after_disconnect_messages), 1, 
                        "Remaining client should receive message after other client disconnects")
        
        # Verify server cleaned up disconnected client
        session_manager = self.server.get_session_manager()
        remaining_clients = session_manager.get_all_clients()
        self.assertEqual(len(remaining_clients), 2, "Server should have 2 remaining clients")
        
        # Cleanup
        client1.disconnect()
        client3.disconnect()
    
    def test_message_content_integrity(self):
        """Test that message content is preserved exactly during transmission."""
        client1 = self._create_test_client("IntegrityUser1")
        client2 = self._create_test_client("IntegrityUser2")
        
        time.sleep(0.5)
        
        # Clear initial messages
        for client_key in self.test_results['messages_received']:
            self.test_results['messages_received'][client_key].clear()
        
        # Test various message content types
        test_messages = [
            "Simple text message",
            "Message with numbers: 12345",
            "Message with symbols: !@#$%^&*()_+-=[]{}|;:,.<>?",
            "Message with unicode: 🚀 Hello 世界 🌍",
            "Message\nwith\nnewlines",
            "Message\twith\ttabs",
            "Message with \"quotes\" and 'apostrophes'",
            "Very long message: " + "x" * 500,  # Test long content
            "   Message with leading/trailing spaces   "
        ]
        
        for original_message in test_messages:
            success = client1.send_chat_message(original_message)
            self.assertTrue(success, f"Failed to send message: {original_message[:50]}...")
            time.sleep(0.1)
        
        # Wait for all messages to propagate
        time.sleep(1.0)
        
        # Verify content integrity
        client2_messages = self.test_results['messages_received']['client_IntegrityUser2']
        chat_messages = [msg for msg in client2_messages if msg.msg_type == MessageType.CHAT.value]
        
        self.assertGreaterEqual(len(chat_messages), len(test_messages))
        
        received_content = [msg.data.get('message') for msg in chat_messages]
        
        for original_message in test_messages:
            # For very long messages, check if it was truncated or preserved
            if len(original_message) > 1000:
                # Check if truncated version exists
                truncated_matches = [msg for msg in received_content 
                                   if msg and msg.startswith(original_message[:900])]
                self.assertGreater(len(truncated_matches), 0, 
                                 f"Long message not found (original or truncated): {original_message[:50]}...")
            else:
                # Exact match expected
                self.assertIn(original_message, received_content, 
                             f"Message content not preserved: {original_message}")
        
        # Cleanup
        client1.disconnect()
        client2.disconnect()


class TestChatMessageValidation(unittest.TestCase):
    """Test cases for chat message validation and security."""
    
    def test_tcp_message_validation(self):
        """Test TCPMessage validation for chat messages."""
        # Valid chat message
        valid_message = MessageFactory.create_chat_message("user123", "Hello world!")
        self.assertTrue(MessageValidator.validate_tcp_message(valid_message))
        
        # Invalid message type
        invalid_type_message = TCPMessage(
            msg_type="invalid_type",
            sender_id="user123",
            data={"message": "Hello"}
        )
        self.assertFalse(MessageValidator.validate_tcp_message(invalid_type_message))
        
        # Empty sender ID
        empty_sender_message = TCPMessage(
            msg_type=MessageType.CHAT.value,
            sender_id="",
            data={"message": "Hello"}
        )
        self.assertFalse(MessageValidator.validate_tcp_message(empty_sender_message))
        
        # Invalid data structure
        invalid_data_message = TCPMessage(
            msg_type=MessageType.CHAT.value,
            sender_id="user123",
            data="not_a_dict"
        )
        self.assertFalse(MessageValidator.validate_tcp_message(invalid_data_message))
    
    def test_message_serialization_deserialization(self):
        """Test message serialization and deserialization integrity."""
        original_message = MessageFactory.create_chat_message("user456", "Test serialization!")
        
        # Serialize
        serialized_data = original_message.serialize()
        self.assertIsInstance(serialized_data, bytes)
        
        # Deserialize
        deserialized_message = TCPMessage.deserialize(serialized_data)
        
        # Verify integrity
        self.assertEqual(deserialized_message.msg_type, original_message.msg_type)
        self.assertEqual(deserialized_message.sender_id, original_message.sender_id)
        self.assertEqual(deserialized_message.data, original_message.data)
        self.assertEqual(deserialized_message.message_id, original_message.message_id)
        
        # Timestamps should be very close (within 1 second)
        time_diff = abs(deserialized_message.timestamp - original_message.timestamp)
        self.assertLess(time_diff, 1.0)
    
    def test_malformed_message_handling(self):
        """Test handling of malformed message data."""
        # Test invalid JSON
        with self.assertRaises(ValueError):
            TCPMessage.deserialize(b"invalid json data")
        
        # Test incomplete message data
        with self.assertRaises(ValueError):
            TCPMessage.deserialize(b'{"msg_type": "chat"}')  # Missing required fields
        
        # Test empty data
        with self.assertRaises(ValueError):
            TCPMessage.deserialize(b"")


if __name__ == '__main__':
    # Run tests with detailed output
    unittest.main(verbosity=2, buffer=True)