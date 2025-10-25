# Goom - Advanced Video Conferencing & Screen Sharing Platform

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![OpenCV](https://img.shields.io/badge/OpenCV-4.0+-green.svg)](https://opencv.org)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A high-performance, real-time video conferencing and screen sharing platform with advanced features including 60 FPS video streaming, ultra-low latency, and seamless screen sharing capabilities.

## 🚀 Features

### Video Conferencing
- **60 FPS Ultra-Low Latency Video**: Smooth, high-quality video streaming
- **Multi-Client Support**: Connect multiple participants simultaneously
- **Adaptive Quality**: Dynamic quality adjustment based on network conditions
- **Frame Sequencing**: Perfect chronological frame ordering
- **Real-time Audio**: Synchronized audio with video

### Screen Sharing
- **High FPS Screen Capture**: Up to 60 FPS screen sharing
- **Professional Quality**: High-resolution screen sharing with optimized compression
- **Presenter Controls**: Easy presenter role management
- **Black Screen Handling**: Clean transitions when sharing stops
- **Cross-Platform**: Windows, Linux, and macOS support

### Advanced Features
- **Ultra-Stable GUI**: Zero-flicker video display system
- **Network Optimization**: TCP/UDP hybrid communication
- **Error Recovery**: Robust error handling and recovery
- **Performance Monitoring**: Real-time performance statistics
- **Modular Architecture**: Extensible and maintainable codebase

## 📋 Requirements

### System Requirements
- **Python**: 3.8 or higher
- **Operating System**: Windows 10+, Linux (Ubuntu 18.04+), macOS 10.14+
- **RAM**: 4GB minimum, 8GB recommended
- **Network**: Stable internet connection for optimal performance

### Python Dependencies
```bash
pip install -r requirements.txt
```

Key dependencies:
- `opencv-python` - Video processing and computer vision
- `numpy` - Numerical computing
- `PIL` (Pillow) - Image processing
- `pyautogui` - Screen capture
- `tkinter` - GUI framework (included with Python)
- `threading` - Multi-threading support

## 🛠️ Installation

### 1. Clone the Repository
```bash
git clone https://github.com/Ganapathi-G2005/goom.git
cd goom
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Platform-Specific Setup

#### Windows
```bash
# Install additional Windows dependencies
pip install pygetwindow
```

#### Linux
```bash
# Install system packages
sudo apt-get update
sudo apt-get install python3-tk python3-dev scrot xvfb

# Install Python packages
pip install pyautogui pillow opencv-python
```

#### macOS
```bash
# Install Python packages
pip install pyautogui pillow opencv-python

# Grant screen recording permissions in System Preferences
# System Preferences > Security & Privacy > Privacy > Screen Recording
```

## 🚀 Quick Start

### Start the Server
```bash
python start_server.py
```

### Start a Client
```bash
python start_client.py
```

### Run Tests
```bash
# Test screen sharing improvements
python test_screen_sharing_improvements.py

# Test video conferencing
python test_video_conferencing.py

# Run all tests
python run_all_tests.py
```

## 📁 Project Structure

```
goom/
├── client/                     # Client-side components
│   ├── gui_manager.py         # GUI management and display
│   ├── screen_capture.py      # Screen capture functionality
│   ├── screen_playback.py     # Screen playback and display
│   ├── video_capture.py       # Video capture from camera
│   ├── video_playback.py     # Video playback and rendering
│   ├── frame_sequencer.py    # Frame sequencing for smooth playback
│   └── main_client.py         # Main client application
├── server/                     # Server-side components
│   ├── session_manager.py     # Session and participant management
│   ├── network_handler.py     # Network communication handling
│   └── media_relay.py         # Media streaming and relay
├── common/                     # Shared utilities
│   ├── messages.py            # Message types and protocols
│   └── platform_utils.py      # Platform-specific utilities
├── tests/                      # Test suites
├── docs/                      # Documentation
└── requirements.txt           # Python dependencies
```

## 🎯 Key Components

### Video Conferencing System
- **High-Performance Capture**: Optimized camera capture with 60 FPS support
- **Ultra-Low Latency**: Minimal delay video transmission
- **Frame Sequencing**: Perfect chronological ordering of video frames
- **Adaptive Quality**: Dynamic quality adjustment based on network conditions

### Screen Sharing System
- **High FPS Capture**: Up to 60 FPS screen sharing
- **Professional Quality**: High-resolution sharing with optimized compression
- **Cross-Platform**: Windows, Linux, and macOS support
- **Black Screen Handling**: Clean transitions when sharing stops

### Network Architecture
- **TCP/UDP Hybrid**: Reliable TCP for control, fast UDP for media
- **Optimized Packets**: Efficient packet sizing and compression
- **Error Recovery**: Robust error handling and recovery mechanisms
- **Performance Monitoring**: Real-time statistics and monitoring

## 🔧 Configuration

### Video Settings
```python
# High FPS video configuration
DEFAULT_FPS = 60              # 60 FPS for ultra-smooth video
COMPRESSION_QUALITY = 70       # High quality compression
MAX_WIDTH = 1280              # High resolution support
MAX_HEIGHT = 720
```

### Screen Sharing Settings
```python
# Optimized screen sharing
DEFAULT_FPS = 30              # 30 FPS for smooth screen sharing
COMPRESSION_QUALITY = 70       # High quality compression
MAX_WIDTH = 1280              # High resolution screen sharing
MAX_HEIGHT = 720
```

## 📊 Performance Features

### Ultra-Low Latency
- **60 FPS Video**: Smooth, high-frame-rate video streaming
- **Optimized Compression**: Efficient video compression algorithms
- **Network Optimization**: TCP/UDP hybrid for optimal performance
- **Frame Sequencing**: Perfect chronological frame ordering

### High Performance
- **Multi-Threading**: Efficient multi-threaded processing
- **Memory Optimization**: Optimized memory usage and garbage collection
- **CPU Optimization**: Efficient CPU usage with adaptive quality
- **Network Optimization**: Optimized packet sizing and transmission

## 🧪 Testing

### Test Suites
- **Screen Sharing Tests**: FPS, quality, and performance testing
- **Video Conferencing Tests**: Multi-client testing
- **Network Tests**: Connection and performance testing
- **Integration Tests**: End-to-end functionality testing

### Running Tests
```bash
# Run all tests
python run_all_tests.py

# Test specific components
python test_screen_sharing_improvements.py
python test_video_conferencing.py
python test_connection.py
```

## 📈 Performance Metrics

### Video Performance
- **FPS**: Up to 60 FPS video streaming
- **Latency**: Ultra-low latency (< 100ms)
- **Quality**: High-quality video with adaptive compression
- **Stability**: Robust error handling and recovery

### Screen Sharing Performance
- **FPS**: Up to 60 FPS screen sharing
- **Quality**: High-resolution screen sharing
- **Compression**: Optimized compression algorithms
- **Cross-Platform**: Windows, Linux, and macOS support

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

### Development Setup
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- OpenCV community for excellent computer vision tools
- Python community for robust libraries
- Contributors and testers who helped improve the platform

## 📞 Support

For support, please:
1. Check the [Issues](https://github.com/Ganapathi-G2005/goom/issues) page
2. Create a new issue with detailed information
3. Contact the maintainers

## 🔗 Links

- **Repository**: [https://github.com/Ganapathi-G2005/goom](https://github.com/Ganapathi-G2005/goom)
- **Issues**: [https://github.com/Ganapathi-G2005/goom/issues](https://github.com/Ganapathi-G2005/goom/issues)
- **Documentation**: [Project Documentation](docs/)

---

**Goom** - Advanced Video Conferencing & Screen Sharing Platform

Built with ❤️ using Python, OpenCV, and modern networking technologies.