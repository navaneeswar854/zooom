# Project Structure

## Directory Organization

```
goom/
├── client/                     # Client-side components
│   ├── main_client.py         # Main client application entry point
│   ├── connection_manager.py  # Network connectivity management
│   ├── gui_manager.py         # Main GUI coordination and display
│   ├── audio_*.py            # Audio capture/playback/management
│   ├── video_*.py            # Video capture/playback/optimization
│   ├── screen_*.py           # Screen sharing capture/playback/management
│   └── __init__.py
├── server/                     # Server-side components
│   ├── network_handler.py     # Network communication handling
│   ├── session_manager.py     # Client session and participant management
│   ├── media_relay.py         # Audio/video streaming relay
│   ├── performance_monitor.py # System monitoring and statistics
│   └── __init__.py
├── common/                     # Shared utilities and protocols
│   ├── messages.py            # Message types and serialization
│   ├── platform_utils.py      # Cross-platform compatibility utilities
│   ├── networking.py          # Network utility functions
│   ├── file_metadata.py       # File handling metadata
│   └── __init__.py
├── tests/                      # Comprehensive test suite
│   ├── test_*_integration.py  # Integration tests
│   ├── test_*_unit.py         # Unit tests
│   └── __init__.py
├── downloaded_files/           # Default file download directory
├── start_client.py            # Client application launcher
├── start_server.py            # Server application launcher
├── requirements.txt           # Python dependencies
└── README.md                  # Project documentation
```

## Module Responsibilities

### Client Modules

- **main_client.py**: Application coordinator, integrates all client components
- **connection_manager.py**: TCP/UDP connection handling, message routing
- **gui_manager.py**: Tkinter GUI management, user interface coordination
- **audio_manager.py**: Audio capture, playback, and processing
- **video_capture.py**: Camera video capture with optimization
- **video_playback.py**: Video rendering and display management
- **screen_manager.py**: Screen sharing coordination and control
- **screen_capture.py**: Screen capture functionality
- **screen_playback.py**: Screen sharing display and rendering

### Server Modules

- **network_handler.py**: TCP/UDP server management, client connections
- **session_manager.py**: Client session tracking, participant management
- **media_relay.py**: Audio/video packet relay between clients
- **performance_monitor.py**: System performance tracking and optimization

### Common Modules

- **messages.py**: `TCPMessage`, `UDPPacket` classes, `MessageFactory`, validation
- **platform_utils.py**: Cross-platform compatibility, device detection
- **networking.py**: Network utility functions and helpers
- **file_metadata.py**: File transfer metadata and validation

## Naming Conventions

### Files and Modules

- **Snake case**: `module_name.py`, `function_name()`, `variable_name`
- **Descriptive names**: `connection_manager.py` not `conn_mgr.py`
- **Component grouping**: `audio_*`, `video_*`, `screen_*` for related functionality

### Classes

- **PascalCase**: `ConnectionManager`, `SessionManager`, `TCPMessage`
- **Descriptive suffixes**: `*Manager` for coordinators, `*Handler` for processors

### Constants and Enums

- **UPPER_CASE**: `DEFAULT_FPS`, `MAX_WIDTH`, `MESSAGE_TYPE`
- **Enum classes**: `MessageType`, `ConnectionStatus`

## Import Patterns

### Standard Structure

```python
# Standard library imports
import os
import sys
import threading
import logging

# Third-party imports
import cv2
import numpy as np
from PIL import Image

# Local imports
from client.connection_manager import ConnectionManager
from common.messages import TCPMessage, MessageFactory
from common.platform_utils import PLATFORM_INFO
```

### Relative Imports

- Use absolute imports from project root
- Avoid relative imports except within same package
- Import specific classes/functions, not entire modules when possible

## Configuration Management

### Default Settings

- **Video**: 60 FPS, 1280x720 resolution, 70% compression quality
- **Audio**: Standard sample rates, server-side mixing
- **Network**: TCP port 8080, UDP port 8081
- **Files**: `downloaded_files/` directory for downloads

### Platform-Specific Handling

- Use `common.platform_utils.PLATFORM_INFO` for capability detection
- Implement graceful degradation when features unavailable
- Platform-specific optimizations in respective utility functions

## Error Handling Patterns

### Logging

```python
import logging
logger = logging.getLogger(__name__)

# Use appropriate log levels
logger.info("Connection established")
logger.warning("Feature disabled due to missing dependency")
logger.error("Connection failed", exc_info=True)
```

### Exception Handling

- Catch specific exceptions where possible
- Use `try/except/finally` for resource cleanup
- Provide user-friendly error messages through GUI
- Log detailed errors for debugging

### Thread Safety

- Use `threading.RLock()` for reentrant locks
- Protect shared resources with proper locking
- Use thread-safe data structures where applicable
