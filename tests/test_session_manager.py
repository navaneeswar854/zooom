"""
Unit tests for SessionManager class.
Tests client addition/removal functionality and session state management.
"""

import unittest
import time
from unittest.mock import Mock, MagicMock
from server.session_manager import SessionManager, ClientConnection
from common.messages import TCPMessage, MessageType, MessageFactory


class TestSessionManager(unittest.TestCase):
    """Test cases for SessionManager functionality."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.session_manager = SessionManager()
        self.mock_socket1 = Mock()
        self.mock_socket2 = Mock()
        self.mock_socket3 = Mock()
    
    def test_add_client_success(self):
        """Test successful client addition."""
        # Add a client
        client_id = self.session_manager.add_client(self.mock_socket1, "TestUser1")
        
        # Verify client was added
        self.assertIsNotNone(client_id)
        self.assertIn(client_id, self.session_manager.clients)
        
        # Verify client details
        client = self.session_manager.get_client(client_id)
        self.assertIsNotNone(client)
        self.assertEqual(client.username, "TestUser1")
        self.assertEqual(client.tcp_socket, self.mock_socket1)
        self.assertFalse(client.video_enabled)
        self.assertFalse(client.audio_enabled)
        self.assertFalse(client.is_presenter)
        
        # Verify join message was added to chat history
        self.assertEqual(len(self.session_manager.chat_history), 1)
        join_message = self.session_manager.chat_history[0]
        self.assertEqual(join_message.msg_type, MessageType.CLIENT_JOIN.value)
        self.assertEqual(join_message.sender_id, client_id)
    
    def test_add_multiple_clients(self):
        """Test adding multiple clients."""
        # Add multiple clients
        client_id1 = self.session_manager.add_client(self.mock_socket1, "User1")
        client_id2 = self.session_manager.add_client(self.mock_socket2, "User2")
        client_id3 = self.session_manager.add_client(self.mock_socket3, "User3")
        
        # Verify all clients were added
        self.assertEqual(len(self.session_manager.clients), 3)
        self.assertIn(client_id1, self.session_manager.clients)
        self.assertIn(client_id2, self.session_manager.clients)
        self.assertIn(client_id3, self.session_manager.clients)
        
        # Verify unique client IDs
        self.assertNotEqual(client_id1, client_id2)
        self.assertNotEqual(client_id2, client_id3)
        self.assertNotEqual(client_id1, client_id3)
    
    def test_remove_client_success(self):
        """Test successful client removal."""
        # Add a client
        client_id = self.session_manager.add_client(self.mock_socket1, "TestUser")
        
        # Verify client exists
        self.assertIsNotNone(self.session_manager.get_client(client_id))
        
        # Remove the client
        result = self.session_manager.remove_client(client_id)
        
        # Verify removal was successful
        self.assertTrue(result)
        self.assertIsNone(self.session_manager.get_client(client_id))
        self.assertNotIn(client_id, self.session_manager.clients)
        
        # Verify leave message was added to chat history
        leave_messages = [msg for msg in self.session_manager.chat_history 
                         if msg.msg_type == MessageType.CLIENT_LEAVE.value]
        self.assertEqual(len(leave_messages), 1)
        self.assertEqual(leave_messages[0].sender_id, client_id)
    
    def test_remove_nonexistent_client(self):
        """Test removing a client that doesn't exist."""
        result = self.session_manager.remove_client("nonexistent_id")
        self.assertFalse(result)
    
    def test_remove_presenter_client(self):
        """Test removing a client who is the current presenter."""
        # Add client and set as presenter
        client_id = self.session_manager.add_client(self.mock_socket1, "Presenter")
        self.session_manager.set_presenter(client_id)
        
        # Verify client is presenter
        self.assertEqual(self.session_manager.active_presenter, client_id)
        
        # Remove the presenter client
        result = self.session_manager.remove_client(client_id)
        
        # Verify removal and presenter status cleared
        self.assertTrue(result)
        self.assertIsNone(self.session_manager.active_presenter)
        self.assertIsNone(self.session_manager.get_client(client_id))
    
    def test_get_participant_list(self):
        """Test getting participant list."""
        # Add multiple clients
        client_id1 = self.session_manager.add_client(self.mock_socket1, "User1")
        client_id2 = self.session_manager.add_client(self.mock_socket2, "User2")
        
        # Update media status for one client
        self.session_manager.update_client_media_status(client_id1, video_enabled=True, audio_enabled=True)
        
        # Get participant list
        participants = self.session_manager.get_participant_list()
        
        # Verify participant list
        self.assertEqual(len(participants), 2)
        
        # Find participants by client_id
        user1_info = next(p for p in participants if p['client_id'] == client_id1)
        user2_info = next(p for p in participants if p['client_id'] == client_id2)
        
        # Verify User1 info
        self.assertEqual(user1_info['username'], "User1")
        self.assertTrue(user1_info['video_enabled'])
        self.assertTrue(user1_info['audio_enabled'])
        self.assertFalse(user1_info['is_presenter'])
        
        # Verify User2 info
        self.assertEqual(user2_info['username'], "User2")
        self.assertFalse(user2_info['video_enabled'])
        self.assertFalse(user2_info['audio_enabled'])
        self.assertFalse(user2_info['is_presenter'])
    
    def test_update_client_media_status(self):
        """Test updating client media status."""
        # Add a client
        client_id = self.session_manager.add_client(self.mock_socket1, "TestUser")
        
        # Update video status
        result = self.session_manager.update_client_media_status(client_id, video_enabled=True)
        self.assertTrue(result)
        
        client = self.session_manager.get_client(client_id)
        self.assertTrue(client.video_enabled)
        self.assertFalse(client.audio_enabled)  # Should remain unchanged
        
        # Update audio status
        result = self.session_manager.update_client_media_status(client_id, audio_enabled=True)
        self.assertTrue(result)
        
        client = self.session_manager.get_client(client_id)
        self.assertTrue(client.video_enabled)  # Should remain unchanged
        self.assertTrue(client.audio_enabled)
        
        # Update both statuses
        result = self.session_manager.update_client_media_status(client_id, video_enabled=False, audio_enabled=False)
        self.assertTrue(result)
        
        client = self.session_manager.get_client(client_id)
        self.assertFalse(client.video_enabled)
        self.assertFalse(client.audio_enabled)
    
    def test_update_nonexistent_client_media_status(self):
        """Test updating media status for nonexistent client."""
        result = self.session_manager.update_client_media_status("nonexistent", video_enabled=True)
        self.assertFalse(result)
    
    def test_set_presenter(self):
        """Test setting a client as presenter."""
        # Add clients
        client_id1 = self.session_manager.add_client(self.mock_socket1, "User1")
        client_id2 = self.session_manager.add_client(self.mock_socket2, "User2")
        
        # Set first client as presenter
        result = self.session_manager.set_presenter(client_id1)
        self.assertTrue(result)
        
        # Verify presenter status
        self.assertEqual(self.session_manager.active_presenter, client_id1)
        client1 = self.session_manager.get_client(client_id1)
        self.assertTrue(client1.is_presenter)
        
        # Verify other client is not presenter
        client2 = self.session_manager.get_client(client_id2)
        self.assertFalse(client2.is_presenter)
        
        # Change presenter to second client
        result = self.session_manager.set_presenter(client_id2)
        self.assertTrue(result)
        
        # Verify presenter change
        self.assertEqual(self.session_manager.active_presenter, client_id2)
        
        # Verify first client is no longer presenter
        client1 = self.session_manager.get_client(client_id1)
        self.assertFalse(client1.is_presenter)
        
        # Verify second client is now presenter
        client2 = self.session_manager.get_client(client_id2)
        self.assertTrue(client2.is_presenter)
    
    def test_set_nonexistent_presenter(self):
        """Test setting nonexistent client as presenter."""
        result = self.session_manager.set_presenter("nonexistent")
        self.assertFalse(result)
        self.assertIsNone(self.session_manager.active_presenter)
    
    def test_clear_presenter(self):
        """Test clearing the current presenter."""
        # Add client and set as presenter
        client_id = self.session_manager.add_client(self.mock_socket1, "Presenter")
        self.session_manager.set_presenter(client_id)
        
        # Verify presenter is set
        self.assertEqual(self.session_manager.active_presenter, client_id)
        
        # Clear presenter
        result = self.session_manager.clear_presenter()
        self.assertTrue(result)
        
        # Verify presenter is cleared
        self.assertIsNone(self.session_manager.active_presenter)
        client = self.session_manager.get_client(client_id)
        self.assertFalse(client.is_presenter)
    
    def test_clear_presenter_when_none(self):
        """Test clearing presenter when no presenter is set."""
        result = self.session_manager.clear_presenter()
        self.assertFalse(result)
    
    def test_get_presenter(self):
        """Test getting the current presenter."""
        # Initially no presenter
        presenter = self.session_manager.get_presenter()
        self.assertIsNone(presenter)
        
        # Add client and set as presenter
        client_id = self.session_manager.add_client(self.mock_socket1, "Presenter")
        self.session_manager.set_presenter(client_id)
        
        # Get presenter
        presenter = self.session_manager.get_presenter()
        self.assertIsNotNone(presenter)
        self.assertEqual(presenter.client_id, client_id)
        self.assertEqual(presenter.username, "Presenter")
    
    def test_add_chat_message(self):
        """Test adding chat messages to session history."""
        # Create chat message
        chat_message = MessageFactory.create_chat_message("user123", "Hello everyone!")
        
        # Add to session
        self.session_manager.add_chat_message(chat_message)
        
        # Verify message was added
        chat_history = self.session_manager.get_chat_history()
        chat_messages = [msg for msg in chat_history if msg.msg_type == MessageType.CHAT.value]
        self.assertEqual(len(chat_messages), 1)
        self.assertEqual(chat_messages[0].data['message'], "Hello everyone!")
    
    def test_update_client_heartbeat(self):
        """Test updating client heartbeat timestamp."""
        # Add a client
        client_id = self.session_manager.add_client(self.mock_socket1, "TestUser")
        
        # Get initial heartbeat time
        client = self.session_manager.get_client(client_id)
        initial_heartbeat = client.last_heartbeat
        
        # Wait a small amount and update heartbeat
        time.sleep(0.01)
        result = self.session_manager.update_client_heartbeat(client_id)
        self.assertTrue(result)
        
        # Verify heartbeat was updated
        client = self.session_manager.get_client(client_id)
        self.assertGreater(client.last_heartbeat, initial_heartbeat)
    
    def test_get_inactive_clients(self):
        """Test getting list of inactive clients."""
        # Add clients
        client_id1 = self.session_manager.add_client(self.mock_socket1, "User1")
        client_id2 = self.session_manager.add_client(self.mock_socket2, "User2")
        
        # Manually set old heartbeat for one client
        client1 = self.session_manager.get_client(client_id1)
        client1.last_heartbeat = time.time() - 60  # 60 seconds ago
        
        # Get inactive clients with 30 second timeout
        inactive_clients = self.session_manager.get_inactive_clients(timeout_seconds=30)
        
        # Verify only client1 is inactive
        self.assertEqual(len(inactive_clients), 1)
        self.assertIn(client_id1, inactive_clients)
        self.assertNotIn(client_id2, inactive_clients)
    
    def test_get_session_info(self):
        """Test getting session information."""
        # Add some clients and data
        client_id1 = self.session_manager.add_client(self.mock_socket1, "User1")
        client_id2 = self.session_manager.add_client(self.mock_socket2, "User2")
        self.session_manager.set_presenter(client_id1)
        
        # Add a chat message
        chat_message = MessageFactory.create_chat_message(client_id1, "Test message")
        self.session_manager.add_chat_message(chat_message)
        
        # Get session info
        session_info = self.session_manager.get_session_info()
        
        # Verify session info
        self.assertIn('session_id', session_info)
        self.assertIn('session_start_time', session_info)
        self.assertEqual(session_info['total_clients'], 2)
        self.assertEqual(session_info['active_presenter'], client_id1)
        self.assertGreaterEqual(session_info['chat_messages'], 3)  # 2 join + 1 chat
        self.assertEqual(session_info['shared_files'], 0)
        self.assertGreater(session_info['session_duration'], 0)
    
    def test_update_client_udp_address(self):
        """Test updating client UDP address."""
        # Add a client
        client_id = self.session_manager.add_client(self.mock_socket1, "TestUser")
        
        # Update UDP address
        udp_address = ("192.168.1.100", 9000)
        result = self.session_manager.update_client_udp_address(client_id, udp_address)
        self.assertTrue(result)
        
        # Verify UDP address was updated
        client = self.session_manager.get_client(client_id)
        self.assertEqual(client.udp_address, udp_address)
    
    def test_get_clients_with_udp(self):
        """Test getting clients with UDP addresses configured."""
        # Add clients
        client_id1 = self.session_manager.add_client(self.mock_socket1, "User1")
        client_id2 = self.session_manager.add_client(self.mock_socket2, "User2")
        client_id3 = self.session_manager.add_client(self.mock_socket3, "User3")
        
        # Set UDP addresses for some clients
        self.session_manager.update_client_udp_address(client_id1, ("192.168.1.100", 9000))
        self.session_manager.update_client_udp_address(client_id3, ("192.168.1.102", 9002))
        
        # Get clients with UDP
        clients_with_udp = self.session_manager.get_clients_with_udp()
        
        # Verify only clients with UDP addresses are returned
        self.assertEqual(len(clients_with_udp), 2)
        client_ids_with_udp = [client.client_id for client in clients_with_udp]
        self.assertIn(client_id1, client_ids_with_udp)
        self.assertIn(client_id3, client_ids_with_udp)
        self.assertNotIn(client_id2, client_ids_with_udp)


if __name__ == '__main__':
    unittest.main()