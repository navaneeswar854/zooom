#!/usr/bin/env python3
"""
Debug script to test video system functionality.
"""

import sys
import time
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from client.connection_manager import ConnectionManager

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def debug_video_system(server_ip="10.36.87.224"):
    """Debug video system with detailed logging."""
    logger.info("🎥 Debugging Video System")
    logger.info("=" * 50)
    
    client = ConnectionManager(server_ip, 8080, 8081)
    
    try:
        # Connect to server
        logger.info("1. Connecting to server...")
        success = client.connect("VideoDebugClient")
        
        if not success:
            logger.error("❌ Connection failed")
            return False
        
        logger.info(f"✅ Connected! Client ID: {client.get_client_id()}")
        
        # Check UDP connection
        logger.info("2. Checking UDP connection...")
        if client.udp_client and client.udp_client.connected:
            logger.info(f"✅ UDP connected on port: {client.udp_client.socket.getsockname()[1]}")
        else:
            logger.error("❌ UDP not connected")
        
        # Test sending video data
        logger.info("3. Testing video data transmission...")
        
        # Create fake video data
        fake_video_data = b"FAKE_VIDEO_FRAME_DATA_FOR_TESTING" * 100  # Make it bigger
        
        for i in range(5):
            success = client.send_video_data(fake_video_data)
            if success:
                logger.info(f"✅ Video packet {i+1} sent successfully")
            else:
                logger.error(f"❌ Video packet {i+1} failed")
            time.sleep(1)
        
        # Test media status update
        logger.info("4. Testing media status update...")
        success = client.update_media_status(video_enabled=True, audio_enabled=False)
        if success:
            logger.info("✅ Media status update sent")
        else:
            logger.error("❌ Media status update failed")
        
        # Keep connection active to see if we receive any video packets
        logger.info("5. Listening for incoming video packets...")
        
        received_video_packets = []
        def on_video_packet(packet):
            received_video_packets.append(packet)
            logger.info(f"📹 Received video packet from {packet.sender_id}, size: {len(packet.data)} bytes")
        
        client.register_message_callback('video', on_video_packet)
        
        # Wait and listen
        for i in range(15):
            logger.info(f"Listening... {i+1}/15 seconds")
            time.sleep(1)
        
        logger.info(f"📊 Total video packets received: {len(received_video_packets)}")
        
        # Check participants
        participants = client.get_participants()
        logger.info(f"👥 Current participants: {len(participants)}")
        for client_id, info in participants.items():
            username = info.get('username', 'Unknown')
            video_enabled = info.get('video_enabled', False)
            logger.info(f"  - {username} ({client_id[:8]}...) - Video: {video_enabled}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error during video debugging: {e}")
        return False
    
    finally:
        client.disconnect()
        logger.info("✅ Disconnected from server")


def main():
    """Main debug function."""
    server_ip = input("Enter server IP (default: 10.36.87.224): ").strip()
    if not server_ip:
        server_ip = "10.36.87.224"
    
    success = debug_video_system(server_ip)
    
    if success:
        print("\n🎉 Video system debug completed!")
    else:
        print("\n❌ Video system debug failed!")
    
    input("\nPress Enter to exit...")


if __name__ == "__main__":
    main()