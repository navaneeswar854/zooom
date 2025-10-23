#!/usr/bin/env python3
"""
Comprehensive multi-client functionality test for the LAN Collaboration Suite.
Tests all major features with multiple clients simultaneously.
"""

import sys
import time
import threading
import logging
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from client.connection_manager import ConnectionManager
from common.messages import MessageType

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class MultiClientTester:
    """Test multiple clients with comprehensive functionality testing."""
    
    def __init__(self, num_clients=3):
        self.num_clients = num_clients
        self.clients = []
        self.client_threads = []
        self.test_results = {}
        
    def create_test_file(self):
        """Create a test file for file sharing tests."""
        test_content = "This is a test file for the LAN Collaboration Suite.\nTesting file sharing functionality.\n"
        test_file_path = "test_shared_file.txt"
        
        with open(test_file_path, 'w') as f:
            f.write(test_content)
        
        return test_file_path
    
    def setup_client_callbacks(self, client_manager, client_name):
        """Setup callbacks for a client to track received messages."""
        received_messages = []
        received_files = []
        participants_seen = set()
        
        def on_chat_message(message):
            sender = message.data.get('sender_username', 'Unknown')
            text = message.data.get('message', '')
            received_messages.append(f"{sender}: {text}")
            logger.info(f"[{client_name}] Received chat: {sender}: {text}")
        
        def on_participant_joined(message):
            username = message.data.get('username', 'Unknown')
            participants_seen.add(username)
            logger.info(f"[{client_name}] Participant joined: {username}")
        
        def on_participant_left(message):
            username = message.data.get('username', 'Unknown')
            logger.info(f"[{client_name}] Participant left: {username}")
        
        def on_file_available(message):
            filename = message.data.get('filename', 'Unknown')
            uploader = message.data.get('uploader_id', 'Unknown')
            received_files.append(filename)
            logger.info(f"[{client_name}] File available: {filename} from {uploader}")
        
        def on_file_download_complete(filename, path):
            logger.info(f"[{client_name}] File download completed: {filename} -> {path}")
        
        # Register callbacks
        client_manager.register_message_callback(MessageType.CHAT.value, on_chat_message)
        client_manager.register_message_callback('participant_joined', on_participant_joined)
        client_manager.register_message_callback('participant_left', on_participant_left)
        client_manager.register_message_callback('file_available', on_file_available)
        client_manager.register_message_callback('file_download_complete', on_file_download_complete)
        
        return {
            'received_messages': received_messages,
            'received_files': received_files,
            'participants_seen': participants_seen
        }
    
    def test_client_connection(self, client_id):
        """Test individual client connection and basic functionality."""
        client_name = f"TestClient{client_id}"
        logger.info(f"Starting {client_name}...")
        
        try:
            # Create connection manager
            client_manager = ConnectionManager("localhost", 8080, 8081)
            
            # Setup callbacks
            callbacks = self.setup_client_callbacks(client_manager, client_name)
            
            # Connect to server
            logger.info(f"[{client_name}] Connecting to server...")
            success = client_manager.connect(client_name)
            
            if not success:
                logger.error(f"[{client_name}] Failed to connect to server")
                return False
            
            logger.info(f"[{client_name}] Connected successfully! Client ID: {client_manager.get_client_id()}")
            
            # Store client for later tests
            self.clients.append({
                'manager': client_manager,
                'name': client_name,
                'callbacks': callbacks,
                'id': client_manager.get_client_id()
            })
            
            # Wait a moment for other clients to connect
            time.sleep(2)
            
            # Test chat functionality
            logger.info(f"[{client_name}] Testing chat functionality...")
            chat_message = f"Hello from {client_name}! Testing chat functionality."
            success = client_manager.send_chat_message(chat_message)
            
            if success:
                logger.info(f"[{client_name}] ✓ Chat message sent successfully")
            else:
                logger.error(f"[{client_name}] ✗ Failed to send chat message")
            
            # Test file sharing (only first client uploads)
            if client_id == 1:
                logger.info(f"[{client_name}] Testing file upload...")
                test_file = self.create_test_file()
                
                success, message = client_manager.upload_file(test_file, f"Test file from {client_name}")
                if success:
                    logger.info(f"[{client_name}] ✓ File uploaded successfully: {message}")
                else:
                    logger.error(f"[{client_name}] ✗ File upload failed: {message}")
                
                # Clean up test file
                try:
                    os.remove(test_file)
                except:
                    pass
            
            # Keep client running for cross-client tests
            time.sleep(10)  # Allow time for all interactions
            
            # Test participant list
            participants = client_manager.get_participants()
            logger.info(f"[{client_name}] Current participants: {list(participants.keys())}")
            
            # Disconnect
            logger.info(f"[{client_name}] Disconnecting...")
            client_manager.disconnect()
            logger.info(f"[{client_name}] Disconnected successfully")
            
            return True
            
        except Exception as e:
            logger.error(f"[{client_name}] Error during testing: {e}")
            return False
    
    def run_multi_client_test(self):
        """Run comprehensive multi-client test."""
        logger.info(f"Starting multi-client test with {self.num_clients} clients...")
        
        # Start all clients in separate threads
        for i in range(1, self.num_clients + 1):
            thread = threading.Thread(
                target=self.test_client_connection,
                args=(i,),
                daemon=True
            )
            thread.start()
            self.client_threads.append(thread)
            
            # Stagger client connections
            time.sleep(1)
        
        # Wait for all clients to finish
        for thread in self.client_threads:
            thread.join(timeout=30)
        
        logger.info("Multi-client test completed!")
        
        # Analyze results
        self.analyze_results()
    
    def analyze_results(self):
        """Analyze test results and provide summary."""
        logger.info("=== TEST RESULTS SUMMARY ===")
        
        total_clients = len(self.clients)
        logger.info(f"Total clients tested: {total_clients}")
        
        if total_clients > 0:
            # Check chat message distribution
            for client in self.clients:
                received_count = len(client['callbacks']['received_messages'])
                logger.info(f"{client['name']}: Received {received_count} chat messages")
                
                participants_count = len(client['callbacks']['participants_seen'])
                logger.info(f"{client['name']}: Saw {participants_count} other participants")
                
                files_count = len(client['callbacks']['received_files'])
                logger.info(f"{client['name']}: Received {files_count} file notifications")
        
        logger.info("=== END SUMMARY ===")


def test_server_status():
    """Test if server is running and accessible."""
    logger.info("Testing server connectivity...")
    
    test_client = ConnectionManager("localhost", 8080, 8081)
    success = test_client.connect("ServerTestClient")
    
    if success:
        logger.info("✓ Server is running and accessible")
        test_client.disconnect()
        return True
    else:
        logger.error("✗ Server is not accessible")
        return False


def main():
    """Main test function."""
    logger.info("Starting comprehensive LAN Collaboration Suite functionality test...")
    
    # Test server connectivity first
    if not test_server_status():
        logger.error("Server is not running. Please start the server first.")
        return False
    
    # Run multi-client test
    tester = MultiClientTester(num_clients=3)
    tester.run_multi_client_test()
    
    logger.info("All tests completed!")
    return True


if __name__ == "__main__":
    success = main()
    if success:
        print("\n🎉 Multi-client functionality test completed!")
        sys.exit(0)
    else:
        print("\n❌ Multi-client functionality test failed!")
        sys.exit(1)