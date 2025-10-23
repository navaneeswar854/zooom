"""
Message serialization and deserialization utilities for the collaboration suite.
Handles TCP and UDP message protocols with proper encoding/decoding.
"""

import json
import time
import uuid
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass, asdict
from enum import Enum


class MessageType(Enum):
    """Enumeration of message types for the collaboration system."""
    # TCP Message Types
    CHAT = "chat"
    FILE_UPLOAD = "file_upload"
    FILE_REQUEST = "file_request"
    FILE_METADATA = "file_metadata"
    FILE_AVAILABLE = "file_available"
    FILE_DOWNLOAD_CHUNK = "file_download_chunk"
    SCREEN_SHARE = "screen_share"
    SCREEN_SHARE_START = "screen_share_start"
    SCREEN_SHARE_STOP = "screen_share_stop"
    PRESENTER_REQUEST = "presenter_request"
    PRESENTER_GRANTED = "presenter_granted"
    PRESENTER_DENIED = "presenter_denied"
    CLIENT_JOIN = "client_join"
    CLIENT_LEAVE = "client_leave"
    HEARTBEAT = "heartbeat"
    
    # Server System Messages
    WELCOME = "welcome"
    PARTICIPANT_JOINED = "participant_joined"
    PARTICIPANT_LEFT = "participant_left"
    PARTICIPANT_STATUS_UPDATE = "participant_status_update"
    HEARTBEAT_ACK = "heartbeat_ack"
    MEDIA_STATUS_UPDATE = "media_status_update"
    UDP_ADDRESS_UPDATE = "udp_address_update"
    SERVER_SHUTDOWN = "server_shutdown"
    QUALITY_UPDATE = "quality_update"
    SCREEN_SHARE_ERROR = "screen_share_error"
    
    # UDP Packet Types
    AUDIO = "audio"
    VIDEO = "video"


@dataclass
class TCPMessage:
    """TCP message structure for reliable communication."""
    msg_type: str
    sender_id: str
    data: Dict[str, Any]
    timestamp: float = None
    message_id: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()
        if self.message_id is None:
            self.message_id = str(uuid.uuid4())
    
    def serialize(self) -> bytes:
        """Serialize the TCP message to bytes."""
        try:
            message_dict = asdict(self)
            json_str = json.dumps(message_dict, separators=(',', ':'))
            return json_str.encode('utf-8')
        except Exception as e:
            raise ValueError(f"Failed to serialize TCP message: {e}")
    
    @classmethod
    def deserialize(cls, data: bytes) -> 'TCPMessage':
        """Deserialize bytes to TCP message."""
        try:
            json_str = data.decode('utf-8')
            message_dict = json.loads(json_str)
            return cls(**message_dict)
        except Exception as e:
            raise ValueError(f"Failed to deserialize TCP message: {e}")
    
    def is_valid(self) -> bool:
        """Validate the TCP message structure."""
        required_fields = ['msg_type', 'sender_id', 'data', 'timestamp', 'message_id']
        return all(hasattr(self, field) and getattr(self, field) is not None 
                  for field in required_fields)


@dataclass
class UDPPacket:
    """UDP packet structure for low-latency streaming."""
    packet_type: str
    sender_id: str
    sequence_num: int
    data: bytes
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()
    
    def serialize(self) -> bytes:
        """Serialize the UDP packet to bytes."""
        try:
            # Create header with metadata
            header = {
                'packet_type': self.packet_type,
                'sender_id': self.sender_id,
                'sequence_num': self.sequence_num,
                'timestamp': self.timestamp,
                'data_length': len(self.data)
            }
            
            # Serialize header to JSON and encode
            header_json = json.dumps(header, separators=(',', ':')).encode('utf-8')
            header_length = len(header_json)
            
            # Pack: header_length (4 bytes) + header + data
            packet = (
                header_length.to_bytes(4, byteorder='big') +
                header_json +
                self.data
            )
            
            return packet
        except Exception as e:
            raise ValueError(f"Failed to serialize UDP packet: {e}")
    
    @classmethod
    def deserialize(cls, data: bytes) -> 'UDPPacket':
        """Deserialize bytes to UDP packet."""
        try:
            # Extract header length
            if len(data) < 4:
                raise ValueError("Packet too short")
                
            header_length = int.from_bytes(data[:4], byteorder='big')
            
            # Extract header
            if len(data) < 4 + header_length:
                raise ValueError("Invalid header length")
                
            header_json = data[4:4 + header_length].decode('utf-8')
            header = json.loads(header_json)
            
            # Extract payload data
            payload_data = data[4 + header_length:]
            
            # Validate data length
            expected_length = header.get('data_length', 0)
            if len(payload_data) != expected_length:
                raise ValueError("Data length mismatch")
            
            return cls(
                packet_type=header['packet_type'],
                sender_id=header['sender_id'],
                sequence_num=header['sequence_num'],
                data=payload_data,
                timestamp=header['timestamp']
            )
        except Exception as e:
            raise ValueError(f"Failed to deserialize UDP packet: {e}")
    
    def is_valid(self) -> bool:
        """Validate the UDP packet structure."""
        required_fields = ['packet_type', 'sender_id', 'sequence_num', 'data', 'timestamp']
        return all(hasattr(self, field) and getattr(self, field) is not None 
                  for field in required_fields)


class MessageFactory:
    """Factory class for creating common message types."""
    
    @staticmethod
    def create_chat_message(sender_id: str, message_text: str) -> TCPMessage:
        """Create a chat message."""
        return TCPMessage(
            msg_type=MessageType.CHAT.value,
            sender_id=sender_id,
            data={'message': message_text}
        )
    
    @staticmethod
    def create_heartbeat_message(sender_id: str) -> TCPMessage:
        """Create a heartbeat message."""
        return TCPMessage(
            msg_type=MessageType.HEARTBEAT.value,
            sender_id=sender_id,
            data={'status': 'alive'}
        )
    
    @staticmethod
    def create_client_join_message(sender_id: str, username: str) -> TCPMessage:
        """Create a client join message."""
        return TCPMessage(
            msg_type=MessageType.CLIENT_JOIN.value,
            sender_id=sender_id,
            data={'username': username}
        )
    
    @staticmethod
    def create_client_leave_message(sender_id: str) -> TCPMessage:
        """Create a client leave message."""
        return TCPMessage(
            msg_type=MessageType.CLIENT_LEAVE.value,
            sender_id=sender_id,
            data={}
        )
    
    @staticmethod
    def create_client_disconnect_message(client_id: str, username: str, reason: str) -> TCPMessage:
        """Create a client disconnect notification message."""
        return TCPMessage(
            msg_type=MessageType.PARTICIPANT_LEFT.value,
            sender_id="server",
            data={
                'client_id': client_id,
                'username': username,
                'reason': reason
            }
        )
    
    @staticmethod
    def create_file_metadata_message(sender_id: str, filename: str, filesize: int, file_id: str) -> TCPMessage:
        """Create a file metadata message."""
        return TCPMessage(
            msg_type=MessageType.FILE_METADATA.value,
            sender_id=sender_id,
            data={
                'filename': filename,
                'filesize': filesize,
                'file_id': file_id
            }
        )
    
    @staticmethod
    def create_audio_packet(sender_id: str, sequence_num: int, audio_data: bytes) -> UDPPacket:
        """Create an audio UDP packet."""
        return UDPPacket(
            packet_type=MessageType.AUDIO.value,
            sender_id=sender_id,
            sequence_num=sequence_num,
            data=audio_data
        )
    
    @staticmethod
    def create_video_packet(sender_id: str, sequence_num: int, video_data: bytes) -> UDPPacket:
        """Create a video UDP packet."""
        return UDPPacket(
            packet_type=MessageType.VIDEO.value,
            sender_id=sender_id,
            sequence_num=sequence_num,
            data=video_data
        )
    
    @staticmethod
    def create_presenter_request_message(sender_id: str) -> TCPMessage:
        """Create a presenter request message."""
        return TCPMessage(
            msg_type=MessageType.PRESENTER_REQUEST.value,
            sender_id=sender_id,
            data={}
        )
    
    @staticmethod
    def create_presenter_granted_message(sender_id: str, presenter_id: str) -> TCPMessage:
        """Create a presenter granted message."""
        return TCPMessage(
            msg_type=MessageType.PRESENTER_GRANTED.value,
            sender_id=sender_id,
            data={'presenter_id': presenter_id}
        )
    
    @staticmethod
    def create_presenter_denied_message(sender_id: str, reason: str = "") -> TCPMessage:
        """Create a presenter denied message."""
        return TCPMessage(
            msg_type=MessageType.PRESENTER_DENIED.value,
            sender_id=sender_id,
            data={'reason': reason}
        )
    
    @staticmethod
    def create_screen_share_start_message(sender_id: str) -> TCPMessage:
        """Create a screen share start message."""
        return TCPMessage(
            msg_type=MessageType.SCREEN_SHARE_START.value,
            sender_id=sender_id,
            data={}
        )
    
    @staticmethod
    def create_screen_share_stop_message(sender_id: str) -> TCPMessage:
        """Create a screen share stop message."""
        return TCPMessage(
            msg_type=MessageType.SCREEN_SHARE_STOP.value,
            sender_id=sender_id,
            data={}
        )


class MessageValidator:
    """Utility class for validating messages and packets."""
    
    @staticmethod
    def validate_tcp_message(message: TCPMessage) -> bool:
        """Validate TCP message structure and content."""
        if not message.is_valid():
            return False
        
        # Check if message type is valid
        valid_types = [msg_type.value for msg_type in MessageType if msg_type.name not in ['AUDIO', 'VIDEO']]
        if message.msg_type not in valid_types:
            return False
        
        # Check sender_id format
        if not message.sender_id or len(message.sender_id.strip()) == 0:
            return False
        
        # Check data is a dictionary
        if not isinstance(message.data, dict):
            return False
        
        return True
    
    @staticmethod
    def validate_udp_packet(packet: UDPPacket) -> bool:
        """Validate UDP packet structure and content."""
        if not packet.is_valid():
            return False
        
        # Check if packet type is valid
        valid_types = [MessageType.AUDIO.value, MessageType.VIDEO.value]
        if packet.packet_type not in valid_types:
            return False
        
        # Check sender_id format
        if not packet.sender_id or len(packet.sender_id.strip()) == 0:
            return False
        
        # Check sequence number is non-negative
        if packet.sequence_num < 0:
            return False
        
        # Check data is bytes
        if not isinstance(packet.data, bytes):
            return False
        
        return True


# Utility functions for common operations
def serialize_message(message: Union[TCPMessage, UDPPacket]) -> bytes:
    """Generic function to serialize any message type."""
    return message.serialize()


def deserialize_tcp_message(data: bytes) -> TCPMessage:
    """Deserialize TCP message with validation."""
    message = TCPMessage.deserialize(data)
    if not MessageValidator.validate_tcp_message(message):
        raise ValueError("Invalid TCP message structure")
    return message


def deserialize_udp_packet(data: bytes) -> UDPPacket:
    """Deserialize UDP packet with validation."""
    packet = UDPPacket.deserialize(data)
    if not MessageValidator.validate_udp_packet(packet):
        raise ValueError("Invalid UDP packet structure")
    return packet