"""
Core networking classes for TCP and UDP socket communication.
Provides base classes for client-server communication in the collaboration suite.
"""

import socket
import threading
import logging
from typing import Optional, Callable, Tuple, Any
from common.platform_utils import NetworkUtils, ErrorHandler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TCPSocket:
    """Base TCP socket class for reliable communication."""
    
    def __init__(self, host: str = 'localhost', port: int = 8080):
        self.host = host
        self.port = port
        self.socket: Optional[socket.socket] = None
        self.connected = False
        
    def create_socket(self) -> socket.socket:
        """Create and configure TCP socket with platform-specific options."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # Apply platform-specific socket configuration
        NetworkUtils.configure_socket_options(sock, "tcp")
        
        return sock
        
    def send_data(self, data: bytes) -> bool:
        """Send data over TCP connection."""
        if not self.connected or not self.socket:
            logger.error("Cannot send data: not connected")
            return False
            
        try:
            # Send data length first, then data
            data_length = len(data)
            length_bytes = data_length.to_bytes(4, byteorder='big')
            self.socket.sendall(length_bytes + data)
            return True
        except Exception as e:
            logger.error(f"Error sending TCP data: {e}")
            return False
            
    def receive_data(self) -> Optional[bytes]:
        """Receive data from TCP connection."""
        if not self.connected or not self.socket:
            return None
            
        try:
            # First receive the length of the data
            length_bytes = self._receive_exact(4)
            if not length_bytes:
                return None
                
            data_length = int.from_bytes(length_bytes, byteorder='big')
            
            # Then receive the actual data
            data = self._receive_exact(data_length)
            return data
        except Exception as e:
            logger.error(f"Error receiving TCP data: {e}")
            return None
            
    def _receive_exact(self, num_bytes: int) -> Optional[bytes]:
        """Receive exact number of bytes from socket."""
        data = b''
        while len(data) < num_bytes:
            chunk = self.socket.recv(num_bytes - len(data))
            if not chunk:
                return None
            data += chunk
        return data
        
    def close(self):
        """Close the TCP connection."""
        if self.socket:
            try:
                self.socket.close()
            except Exception as e:
                logger.error(f"Error closing TCP socket: {e}")
            finally:
                self.socket = None
                self.connected = False


class TCPServer(TCPSocket):
    """TCP Server class for handling multiple client connections."""
    
    def __init__(self, host: str = 'localhost', port: int = 8080):
        super().__init__(host, port)
        self.client_handler: Optional[Callable] = None
        self.running = False
        
    def start_server(self, client_handler: Callable[[socket.socket, Tuple[str, int]], None]):
        """Start the TCP server and listen for connections."""
        self.client_handler = client_handler
        self.socket = self.create_socket()
        
        try:
            self.socket.bind((self.host, self.port))
            self.socket.listen(5)
            self.running = True
            logger.info(f"TCP Server started on {self.host}:{self.port}")
            
            while self.running:
                try:
                    client_socket, client_address = self.socket.accept()
                    logger.info(f"New client connected: {client_address}")
                    
                    # Handle each client in a separate thread
                    client_thread = threading.Thread(
                        target=self.client_handler,
                        args=(client_socket, client_address),
                        daemon=True
                    )
                    client_thread.start()
                    
                except socket.error as e:
                    if self.running:
                        logger.error(f"Error accepting connection: {e}")
                        
        except Exception as e:
            logger.error(f"Error starting TCP server: {e}")
        finally:
            self.close()
            
    def stop_server(self):
        """Stop the TCP server."""
        self.running = False
        if self.socket:
            self.socket.close()


class TCPClient(TCPSocket):
    """TCP Client class for connecting to server."""
    
    def connect(self) -> bool:
        """Connect to the TCP server."""
        try:
            self.socket = self.create_socket()
            self.socket.connect((self.host, self.port))
            self.connected = True
            logger.info(f"Connected to TCP server at {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"Error connecting to TCP server: {e}")
            return False


class UDPSocket:
    """Base UDP socket class for low-latency communication."""
    
    def __init__(self, host: str = 'localhost', port: int = 8081):
        self.host = host
        self.port = port
        self.socket: Optional[socket.socket] = None
        self.bound = False
        
    def create_socket(self) -> socket.socket:
        """Create and configure UDP socket with platform-specific options."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # Set larger buffer sizes to handle video packets
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)  # 64KB receive buffer
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)  # 64KB send buffer
        except Exception as e:
            logger.warning(f"Could not set UDP buffer sizes: {e}")
        
        # Apply platform-specific socket configuration
        NetworkUtils.configure_socket_options(sock, "udp")
        
        return sock
        
    def send_data(self, data: bytes, address: Tuple[str, int]) -> bool:
        """Send data via UDP to specified address."""
        if not self.socket:
            logger.error("Cannot send data: socket not created")
            return False
            
        try:
            self.socket.sendto(data, address)
            return True
        except Exception as e:
            logger.error(f"Error sending UDP data: {e}")
            return False
            
    def receive_data(self, buffer_size: int = 65536) -> Optional[Tuple[bytes, Tuple[str, int]]]:
        """Receive data from UDP socket."""
        if not self.socket:
            return None
            
        try:
            data, address = self.socket.recvfrom(buffer_size)
            return data, address
        except Exception as e:
            logger.error(f"Error receiving UDP data: {e}")
            return None
            
    def close(self):
        """Close the UDP socket."""
        if self.socket:
            try:
                self.socket.close()
            except Exception as e:
                logger.error(f"Error closing UDP socket: {e}")
            finally:
                self.socket = None
                self.bound = False


class UDPServer(UDPSocket):
    """UDP Server class for handling datagram communication."""
    
    def __init__(self, host: str = 'localhost', port: int = 8081):
        super().__init__(host, port)
        self.running = False
        
    def start_server(self, data_handler: Callable[[bytes, Tuple[str, int]], None]):
        """Start the UDP server and listen for datagrams."""
        self.socket = self.create_socket()
        
        try:
            self.socket.bind((self.host, self.port))
            self.bound = True
            self.running = True
            logger.info(f"UDP Server started on {self.host}:{self.port}")
            
            while self.running:
                try:
                    result = self.receive_data()
                    if result:
                        data, address = result
                        # Handle each datagram in a separate thread for non-blocking processing
                        handler_thread = threading.Thread(
                            target=data_handler,
                            args=(data, address),
                            daemon=True
                        )
                        handler_thread.start()
                        
                except socket.error as e:
                    if self.running:
                        logger.error(f"Error receiving UDP data: {e}")
                        
        except Exception as e:
            logger.error(f"Error starting UDP server: {e}")
        finally:
            self.close()
            
    def stop_server(self):
        """Stop the UDP server."""
        self.running = False
        if self.socket:
            self.socket.close()


class UDPClient(UDPSocket):
    """UDP Client class for sending datagrams to server."""
    
    def __init__(self, host: str = 'localhost', port: int = 8081):
        super().__init__(host, port)
        self.socket = self.create_socket()
        self.connected = False
        
    def connect_for_receiving(self) -> bool:
        """Connect UDP socket for receiving data (Windows compatibility)."""
        try:
            if not self.socket:
                self.socket = self.create_socket()
            
            # Bind to any available local port for receiving
            self.socket.bind(('', 0))  # Bind to any available port
            self.bound = True
            self.connected = True
            
            logger.info(f"UDP client bound to local port: {self.socket.getsockname()[1]}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to bind UDP client socket: {e}")
            return False
    
    def send_to_server(self, data: bytes) -> bool:
        """Send data to the UDP server."""
        return self.send_data(data, (self.host, self.port))
    
    def disconnect(self):
        """Disconnect and cleanup UDP client."""
        self.connected = False
        self.close()