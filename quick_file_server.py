#!/usr/bin/env python3
"""
Quick HTTP file server for easy file sharing.
Run this on the machine with files, access via web browser.
"""

import http.server
import socketserver
import os
import sys
from pathlib import Path

def start_file_server(port=8000, directory=None):
    """Start a simple HTTP file server."""
    
    if directory:
        os.chdir(directory)
        print(f"Serving files from: {Path(directory).absolute()}")
    else:
        print(f"Serving files from: {Path.cwd()}")
    
    # Create server
    handler = http.server.SimpleHTTPRequestHandler
    
    try:
        with socketserver.TCPServer(("", port), handler) as httpd:
            print(f"Server started at http://localhost:{port}")
            print(f"Access from other computers at http://YOUR_IP:{port}")
            print("Press Ctrl+C to stop")
            httpd.serve_forever()
    
    except KeyboardInterrupt:
        print("\nServer stopped")
    except Exception as e:
        print(f"Error starting server: {e}")

if __name__ == "__main__":
    port = 8000
    directory = None
    
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            directory = sys.argv[1]
            if len(sys.argv) > 2:
                port = int(sys.argv[2])
    
    start_file_server(port, directory)