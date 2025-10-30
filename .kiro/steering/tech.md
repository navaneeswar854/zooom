# Technology Stack

## Core Technologies

- **Python 3.7+**: Main programming language
- **Tkinter**: GUI framework (built-in with Python)
- **OpenCV**: Video processing and computer vision
- **PyAudio**: Audio capture and playback
- **PyAutoGUI**: Screen capture functionality
- **Socket**: Network communication (TCP/UDP)

## Key Dependencies

```
opencv-python>=4.5.0    # Video processing
numpy>=1.21.0          # Numerical computing
Pillow>=8.3.0          # Image processing
pyautogui>=0.9.53      # Screen capture
pygetwindow>=0.0.9     # Windows window management
```

## Platform-Specific Dependencies

- **Windows**: `pygetwindow` for enhanced window management
- **Linux**: System packages `scrot`, `xvfb`, `python3-tk`
- **macOS**: Screen recording permissions required

## Architecture Patterns

- **Dataclasses**: Used for message structures (`@dataclass`)
- **Factory Pattern**: `MessageFactory` for creating standardized messages
- **Observer Pattern**: Callback-based event handling
- **Threading**: Separate threads for GUI, network, and media processing
- **Enum Classes**: `MessageType` for type-safe message handling

## Common Commands

### Setup & Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Platform setup (Windows)
setup_firewall.bat
```

### Running the Application

```bash
# Start server
python start_server.py

# Start client
python start_client.py
```

### Testing

```bash
# Run all tests
python -m pytest tests/

# Run specific test categories
python -m pytest tests/test_client_server_integration.py
python -m pytest tests/test_screen_sharing_*.py
python -m pytest tests/test_video_performance.py

# Test connection
python test_connection.py
python minimal_lan_test.py
```

### Development Tools

```bash
# Check dependencies
python check_dependencies.py

# Network diagnostics
python network_diagnostics.py
```

## Code Quality Standards

- **Type Hints**: Use typing annotations where applicable
- **Docstrings**: Document all classes and public methods
- **Error Handling**: Comprehensive try/catch with logging
- **Thread Safety**: Use locks for shared resources (`threading.RLock()`)
- **Cross-Platform**: Use `common.platform_utils` for platform-specific code
