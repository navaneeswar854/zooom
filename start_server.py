#!/usr/bin/env python3
"""
Cross-platform startup script for the LAN Collaboration Suite server.
Handles platform-specific initialization and dependency checking.
"""

import sys
import os
import logging
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_python_version():
    """Check if Python version is compatible."""
    if sys.version_info < (3, 7):
        logger.error("Python 3.7 or higher is required")
        return False
    
    logger.info(f"Python version: {sys.version}")
    return True


def check_dependencies():
    """Check if required dependencies are available."""
    missing_deps = []
    
    # Core dependencies (minimal for server)
    try:
        import socket
        import threading
        import json
        logger.info("✓ Core networking modules available")
    except ImportError as e:
        missing_deps.append(str(e))
        logger.error(f"✗ Core networking modules not available: {e}")
    
    if missing_deps:
        logger.error(f"Missing required dependencies: {', '.join(missing_deps)}")
        return False
    
    logger.info("All server dependencies available")
    return True


def setup_platform_environment():
    """Setup platform-specific environment."""
    from common.platform_utils import PLATFORM_INFO, log_platform_info, NetworkUtils
    
    # Log platform information
    log_platform_info()
    
    # Check network capabilities
    if not PLATFORM_INFO.get_capability('network_interfaces'):
        logger.error("Network interfaces not available")
        return False
    
    # Get local IP for server binding
    local_ip = NetworkUtils.get_local_ip()
    logger.info(f"Local IP address: {local_ip}")
    
    # Platform-specific setup
    if PLATFORM_INFO.is_windows():
        logger.info("Setting up Windows server environment...")
        # Windows-specific setup if needed
        
    elif PLATFORM_INFO.is_linux():
        logger.info("Setting up Linux server environment...")
        # Linux-specific setup if needed
        
    elif PLATFORM_INFO.is_macos():
        logger.info("Setting up macOS server environment...")
        # macOS-specific setup if needed
    
    return True


def get_server_config():
    """Get server configuration from user or defaults."""
    from common.platform_utils import NetworkUtils
    
    # Default configuration
    config = {
        'host': '0.0.0.0',  # Bind to all interfaces
        'tcp_port': 8080,
        'udp_port': 8081
    }
    
    # Try to find available ports
    try:
        tcp_port = NetworkUtils.get_available_port(8080)
        udp_port = NetworkUtils.get_available_port(8081)
        
        config['tcp_port'] = tcp_port
        config['udp_port'] = udp_port
        
        logger.info(f"Using ports - TCP: {tcp_port}, UDP: {udp_port}")
        
    except Exception as e:
        logger.warning(f"Could not auto-detect ports: {e}")
        logger.info("Using default ports - TCP: 8080, UDP: 8081")
    
    return config


def main():
    """Main startup function."""
    logger.info("Starting LAN Collaboration Suite Server...")
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Check dependencies
    if not check_dependencies():
        logger.error("Dependency check failed")
        input("Press Enter to exit...")
        sys.exit(1)
    
    # Setup platform environment
    if not setup_platform_environment():
        logger.error("Platform setup failed")
        sys.exit(1)
    
    # Get server configuration
    config = get_server_config()
    
    try:
        # Import and start the server
        from server.network_handler import NetworkHandler
        
        logger.info("Initializing server...")
        server = NetworkHandler(
            tcp_port=config['tcp_port'],
            udp_port=config['udp_port'],
            host=config['host']
        )
        
        logger.info(f"Starting server on {config['host']}:{config['tcp_port']} (TCP) and {config['udp_port']} (UDP)...")
        
        if server.start_servers():
            logger.info("Server started successfully!")
            logger.info("Press Ctrl+C to stop the server")
            
            # Keep server running
            try:
                while True:
                    import time
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("Server shutdown requested")
        else:
            logger.error("Failed to start server")
            sys.exit(1)
        
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
    except Exception as e:
        logger.error(f"Server startup failed: {e}")
        logger.exception("Full error details:")
        input("Press Enter to exit...")
        sys.exit(1)
    finally:
        # Cleanup
        try:
            if 'server' in locals():
                logger.info("Stopping server...")
                server.stop_servers()
                logger.info("Server stopped")
        except Exception as e:
            logger.error(f"Error during server cleanup: {e}")


if __name__ == "__main__":
    main()