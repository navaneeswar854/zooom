# LAN Collaboration Suite

A complete, cross-platform communication and collaboration system for real-time interaction through video conferencing, audio chat, group messaging, screen sharing, and file transfer over local area networks.

## 🌟 Features

### Core Collaboration Features
- **Real-time Video Conferencing** - Multi-participant video calls with dynamic grid layout
- **High-Quality Audio Chat** - Low-latency audio communication with level indicators
- **Group Chat** - Persistent chat with message history and export functionality
- **Screen Sharing** - Share your screen or specific application windows
- **File Transfer** - Secure file sharing with progress tracking and integrity verification
- **Session Management** - Robust participant management with presence indicators

### Technical Highlights
- **Cross-Platform Compatibility** - Works on Windows 10/11 and Linux
- **Real-Time Performance** - Optimized for low-latency communication
- **Scalable Architecture** - Supports multiple concurrent users
- **Comprehensive Testing** - Full test coverage with automated validation
- **User-Friendly Interface** - Intuitive GUI with real-time status updates
- **Platform-Specific Optimizations** - Tailored for each operating system

## 🚀 Quick Start

### Prerequisites

**Python Requirements:**
- Python 3.7 or higher
- pip package manager

**System Requirements:**
- Windows 10/11 or Linux (Ubuntu 18.04+, CentOS 7+, etc.)
- Network connectivity (LAN/WiFi)
- Audio input/output devices (for audio features)
- Webcam (for video features)
- Display (for screen sharing)

### Installation

1. **Clone or download the project:**
   ```bash
   git clone <repository-url>
   cd lan-collaboration-suite
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

   **Platform-specific dependencies:**
   
   *Windows:*
   ```bash
   pip install pygetwindow  # For advanced screen sharing
   ```
   
   *Linux:*
   ```bash
   # Install system dependencies (Ubuntu/Debian)
   sudo apt-get update
   sudo apt-get install python3-dev portaudio19-dev
   
   # Install system dependencies (CentOS/RHEL)
   sudo yum install python3-devel portaudio-devel
   ```

3. **Verify installation:**
   ```bash
   python start_client.py --help
   python start_server.py --help
   ```

### Running the Application

#### Method 1: Using the Enhanced Startup Scripts (Recommended)

**Start the Server:**
```bash
python start_server.py
```

**Start the Client:**
```bash
python start_client.py
```

The startup scripts will:
- Check system compatibility
- Verify dependencies
- Configure platform-specific settings
- Provide helpful error messages if issues are found

#### Method 2: Direct Module Execution

**Start the Server:**
```bash
python -m server.network_handler
```

**Start the Client:**
```bash
python -m client.main_client
```

## 📖 User Guide

### Setting Up a Collaboration Session

1. **Start the Server:**
   - Run `python start_server.py` on one computer
   - Note the IP address displayed (e.g., 192.168.1.100)
   - The server will use ports 8080 (TCP) and 8081 (UDP) by default

2. **Connect Clients:**
   - Run `python start_client.py` on each participant's computer
   - Enter the server IP address and your username
   - Click "Connect"

### Using the Features

#### Video Conferencing
- Click "Enable Video" to start your camera
- Video feeds from all participants appear in a dynamic grid
- Supports up to 16 simultaneous video streams

#### Audio Chat
- Click "Enable Audio" to join voice chat
- Use "Mute/Unmute" to control your microphone
- Audio level indicator shows your input volume

#### Group Chat
- Type messages in the chat input field
- Press Enter or click "Send" to send messages
- Chat history is preserved during the session
- Export chat history to text file using "Export Chat"

#### Screen Sharing
- Click "Request Presenter" to become the presenter
- Once granted, click "Start Sharing" to share your screen
- On Windows: Choose specific application windows or full screen
- On Linux: Full screen sharing only

#### File Transfer
- Click "Share File" to upload a file to the session
- All participants can see shared files in the file list
- Double-click or select a file and click "Download Selected"
- Progress bars show upload/download status

### Interface Overview

The client interface is organized into modules:

- **Connection Panel** (top): Server connection and status
- **Video Conference** (left): Video feeds and camera controls
- **Audio Conference** (left): Audio controls and level meter
- **Group Chat** (center): Message history and input
- **Screen Share** (center): Screen sharing controls and display
- **Participants** (right): List of connected users with status
- **File Transfer** (right): Shared files and transfer controls

## 🔧 Configuration

### Server Configuration

The server automatically detects available ports and network interfaces. For custom configuration:

```python
# In start_server.py, modify the config dictionary:
config = {
    'host': '0.0.0.0',      # Bind to all interfaces
    'tcp_port': 8080,       # TCP port for control messages
    'udp_port': 8081        # UDP port for media streaming
}
```

### Client Configuration

Clients connect using the GUI, but you can also modify default settings:

```python
# In client/main_client.py, modify connection defaults:
self.server_entry.insert(0, "192.168.1.100")  # Default server
self.username_entry.insert(0, "DefaultUser")   # Default username
```

### Performance Tuning

For optimal performance:

1. **Network Settings:**
   - Use wired connections when possible
   - Ensure good WiFi signal strength
   - Close bandwidth-intensive applications

2. **System Resources:**
   - Close unnecessary applications
   - Ensure adequate RAM (4GB+ recommended)
   - Use modern CPU (dual-core+ recommended)

3. **Media Quality:**
   - Adjust video resolution in video settings
   - Use headphones to prevent audio feedback
   - Ensure good lighting for video quality

## 🧪 Testing

### Running Tests

**Run all tests:**
```bash
python run_all_tests.py
```

**Run specific test suites:**
```bash
# Cross-platform compatibility
python -m unittest tests.test_cross_platform_compatibility -v

# End-to-end workflows
python -m unittest tests.test_end_to_end_workflow -v

# System validation
python -m unittest tests.test_system_validation -v
```

### Test Coverage

The test suite includes:
- **Cross-platform compatibility tests** - Platform detection, device access, path handling
- **End-to-end workflow tests** - Complete collaboration scenarios
- **System validation tests** - Performance, reliability, edge cases
- **Integration tests** - Component interaction and data flow
- **Performance benchmarks** - Load testing and scalability

## 🛠️ Troubleshooting

### Common Issues

**"Audio capture not available"**
- Windows: Check microphone permissions in Windows Settings
- Linux: Install audio dependencies: `sudo apt-get install portaudio19-dev`
- Add user to audio group: `sudo usermod -a -G audio $USER`

**"Video capture not available"**
- Windows: Check camera permissions in Windows Settings
- Linux: Install V4L2 utilities: `sudo apt-get install v4l-utils`
- Verify camera device: `ls /dev/video*`

**"Screen capture not available"**
- Install dependencies: `pip install pyautogui`
- Windows: Install `pip install pygetwindow` for window selection
- Linux: May require X11 permissions

**Connection Issues**
- Verify server is running and accessible
- Check firewall settings (allow ports 8080, 8081)
- Ensure all devices are on the same network
- Try using IP address instead of hostname

**UDP Socket Errors (Windows)**
- If you see "WinError 10022" errors, this is usually non-critical
- The application will continue to work with TCP-only communication
- Video/audio streaming may be affected but chat and file transfer will work
- Try restarting both server and client to resolve UDP issues

**Performance Issues**
- Reduce video quality/resolution
- Close other network-intensive applications
- Use wired connection instead of WiFi
- Ensure adequate system resources

### Getting Help

1. **Check the logs** - Both client and server provide detailed logging
2. **Run diagnostics** - Use `python start_client.py` for dependency checking
3. **Review test results** - Run `python run_all_tests.py` for system validation
4. **Platform-specific help** - The application provides platform-specific error messages and suggestions

## 📁 Project Structure

```
lan-collaboration-suite/
├── client/                     # Client application
│   ├── main_client.py         # Main client application
│   ├── gui_manager.py         # GUI interface management
│   ├── connection_manager.py  # Server connection handling
│   ├── audio_capture.py       # Audio input capture
│   ├── audio_playback.py      # Audio output playback
│   ├── audio_manager.py       # Audio system coordination
│   ├── video_capture.py       # Video input capture
│   ├── video_playback.py      # Video output display
│   ├── screen_capture.py      # Screen sharing capture
│   ├── screen_manager.py      # Screen sharing management
│   └── screen_playback.py     # Screen sharing display
├── server/                     # Server application
│   ├── network_handler.py     # Network communication
│   ├── session_manager.py     # Session and participant management
│   ├── media_relay.py         # Audio/video streaming relay
│   └── performance_monitor.py # Performance monitoring
├── common/                     # Shared utilities
│   ├── networking.py          # Network communication classes
│   ├── messages.py            # Message protocol
│   ├── file_metadata.py       # File handling utilities
│   └── platform_utils.py      # Cross-platform utilities
├── tests/                      # Test suites
│   ├── test_cross_platform_compatibility.py
│   ├── test_end_to_end_workflow.py
│   ├── test_system_validation.py
│   └── [additional test files]
├── start_client.py            # Enhanced client startup
├── start_server.py            # Enhanced server startup
├── run_all_tests.py           # Comprehensive test runner
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

## 🔒 Security Considerations

- **Local Network Only** - Designed for trusted LAN environments
- **File Transfer Security** - Files are validated and hash-verified
- **No External Dependencies** - All communication stays within your network
- **Input Validation** - All user inputs are validated and sanitized

## 📋 System Requirements

### Minimum Requirements
- **OS:** Windows 10 or Linux (kernel 3.10+)
- **Python:** 3.7+
- **RAM:** 2GB
- **CPU:** Dual-core 1.5GHz
- **Network:** 100 Mbps LAN

### Recommended Requirements
- **OS:** Windows 11 or Ubuntu 20.04+
- **Python:** 3.9+
- **RAM:** 4GB+
- **CPU:** Quad-core 2.0GHz+
- **Network:** 1 Gbps LAN
- **Storage:** 1GB free space

## 📄 License

This project is provided as-is for educational and internal use purposes.

## 🤝 Contributing

This is a complete, self-contained collaboration suite. The codebase is well-documented and tested for easy understanding and modification.

---

**Ready to collaborate? Start the server, connect your clients, and enjoy seamless LAN-based communication!** 🚀#   g o o m  
 