#!/usr/bin/env python3
"""
Simple file transfer script for pulling files from a friend's laptop.
Run as server on the machine with files, client on the receiving machine.
"""

import socket
import os
import sys
import threading
from pathlib import Path

class FileTransferServer:
    def __init__(self, host='0.0.0.0', port=9999):
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    def start(self):
        """Start the file transfer server."""
        try:
            self.socket.bind((self.host, self.port))
            self.socket.listen(5)
            print(f"File transfer server started on {self.host}:{self.port}")
            print("Waiting for connections...")
            
            while True:
                client_socket, address = self.socket.accept()
                print(f"Connection from {address}")
                
                # Handle client in separate thread
                client_thread = threading.Thread(
                    target=self.handle_client,
                    args=(client_socket, address)
                )
                client_thread.daemon = True
                client_thread.start()
                
        except KeyboardInterrupt:
            print("\nShutting down server...")
        finally:
            self.socket.close()
    
    def handle_client(self, client_socket, address):
        """Handle file requests from a client."""
        try:
            while True:
                # Receive command
                command = client_socket.recv(1024).decode('utf-8').strip()
                if not command:
                    break
                
                if command == "LIST":
                    self.send_file_list(client_socket)
                elif command.startswith("GET "):
                    filename = command[4:]
                    self.send_file(client_socket, filename)
                elif command == "QUIT":
                    break
                else:
                    client_socket.send(b"ERROR: Unknown command\n")
        
        except Exception as e:
            print(f"Error handling client {address}: {e}")
        finally:
            client_socket.close()
            print(f"Client {address} disconnected")
    
    def send_file_list(self, client_socket):
        """Send list of available files."""
        try:
            current_dir = Path.cwd()
            files = []
            
            for item in current_dir.iterdir():
                if item.is_file():
                    size = item.stat().st_size
                    files.append(f"{item.name} ({size} bytes)")
            
            file_list = "\n".join(files) + "\n"
            client_socket.send(file_list.encode('utf-8'))
            
        except Exception as e:
            client_socket.send(f"ERROR: {e}\n".encode('utf-8'))
    
    def send_file(self, client_socket, filename):
        """Send a specific file to the client."""
        try:
            file_path = Path(filename)
            
            if not file_path.exists() or not file_path.is_file():
                client_socket.send(b"ERROR: File not found\n")
                return
            
            # Send file size first
            file_size = file_path.stat().st_size
            client_socket.send(f"SIZE {file_size}\n".encode('utf-8'))
            
            # Send file content
            with open(file_path, 'rb') as f:
                while True:
                    chunk = f.read(8192)  # 8KB chunks
                    if not chunk:
                        break
                    client_socket.send(chunk)
            
            print(f"Sent file: {filename} ({file_size} bytes)")
            
        except Exception as e:
            client_socket.send(f"ERROR: {e}\n".encode('utf-8'))


class FileTransferClient:
    def __init__(self, host, port=9999):
        self.host = host
        self.port = port
    
    def connect(self):
        """Connect to the file transfer server."""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            print(f"Connected to {self.host}:{self.port}")
            return True
        except Exception as e:
            print(f"Failed to connect: {e}")
            return False
    
    def list_files(self):
        """List available files on the server."""
        try:
            self.socket.send(b"LIST\n")
            response = self.socket.recv(4096).decode('utf-8')
            print("Available files:")
            print(response)
        except Exception as e:
            print(f"Error listing files: {e}")
    
    def download_file(self, filename, local_path=None):
        """Download a file from the server."""
        try:
            if local_path is None:
                local_path = filename
            
            self.socket.send(f"GET {filename}\n".encode('utf-8'))
            
            # Receive response
            response = self.socket.recv(1024).decode('utf-8').strip()
            
            if response.startswith("ERROR"):
                print(response)
                return False
            
            if response.startswith("SIZE"):
                file_size = int(response.split()[1])
                print(f"Downloading {filename} ({file_size} bytes)...")
                
                # Receive file content
                with open(local_path, 'wb') as f:
                    received = 0
                    while received < file_size:
                        chunk = self.socket.recv(min(8192, file_size - received))
                        if not chunk:
                            break
                        f.write(chunk)
                        received += len(chunk)
                        
                        # Show progress
                        progress = (received / file_size) * 100
                        print(f"\rProgress: {progress:.1f}%", end='', flush=True)
                
                print(f"\nDownload completed: {local_path}")
                return True
            
        except Exception as e:
            print(f"Error downloading file: {e}")
            return False
    
    def close(self):
        """Close the connection."""
        try:
            self.socket.send(b"QUIT\n")
            self.socket.close()
        except:
            pass


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  Server mode: python simple_file_transfer.py server [port]")
        print("  Client mode: python simple_file_transfer.py client <host> [port]")
        return
    
    mode = sys.argv[1].lower()
    
    if mode == "server":
        port = int(sys.argv[2]) if len(sys.argv) > 2 else 9999
        server = FileTransferServer(port=port)
        server.start()
    
    elif mode == "client":
        if len(sys.argv) < 3:
            print("Error: Host required for client mode")
            return
        
        host = sys.argv[2]
        port = int(sys.argv[3]) if len(sys.argv) > 3 else 9999
        
        client = FileTransferClient(host, port)
        if not client.connect():
            return
        
        try:
            while True:
                print("\nCommands:")
                print("  list - List available files")
                print("  get <filename> - Download a file")
                print("  quit - Exit")
                
                command = input("\n> ").strip().lower()
                
                if command == "list":
                    client.list_files()
                elif command.startswith("get "):
                    filename = command[4:]
                    client.download_file(filename)
                elif command == "quit":
                    break
                else:
                    print("Unknown command")
        
        except KeyboardInterrupt:
            print("\nExiting...")
        finally:
            client.close()
    
    else:
        print("Error: Mode must be 'server' or 'client'")


if __name__ == "__main__":
    main()