#!/usr/bin/env python3
"""
Check and install dependencies for the LAN Collaboration Suite client.
"""

import sys
import subprocess
import importlib

def check_module(module_name, package_name=None):
    """Check if a module is available and try to import it."""
    if package_name is None:
        package_name = module_name
    
    try:
        importlib.import_module(module_name)
        print(f"✅ {module_name} - Available")
        return True
    except ImportError:
        print(f"❌ {module_name} - Missing (install with: pip install {package_name})")
        return False

def install_package(package_name):
    """Install a package using pip."""
    try:
        print(f"Installing {package_name}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])
        print(f"✅ {package_name} installed successfully")
        return True
    except subprocess.CalledProcessError:
        print(f"❌ Failed to install {package_name}")
        return False

def main():
    """Check and install dependencies."""
    print("🔍 Checking LAN Collaboration Suite Dependencies")
    print("=" * 50)
    
    # Core Python modules (should be built-in)
    core_modules = [
        ("tkinter", None),  # Built-in, no pip install needed
        ("socket", None),   # Built-in
        ("threading", None), # Built-in
        ("json", None),     # Built-in
        ("time", None),     # Built-in
        ("os", None),       # Built-in
        ("sys", None),      # Built-in
    ]
    
    # External packages that need pip install
    external_packages = [
        ("pyaudio", "pyaudio"),
        ("cv2", "opencv-python"),
        ("pyautogui", "pyautogui"),
    ]
    
    # Windows-specific packages
    windows_packages = [
        ("pygetwindow", "pygetwindow"),
    ]
    
    print("\n📋 Core Python Modules:")
    all_core_available = True
    for module, _ in core_modules:
        if not check_module(module):
            all_core_available = False
    
    print("\n📦 External Packages:")
    missing_packages = []
    for module, package in external_packages:
        if not check_module(module, package):
            missing_packages.append(package)
    
    if sys.platform == "win32":
        print("\n🪟 Windows-Specific Packages:")
        for module, package in windows_packages:
            if not check_module(module, package):
                missing_packages.append(package)
    
    # Install missing packages
    if missing_packages:
        print(f"\n🔧 Installing {len(missing_packages)} missing packages...")
        
        for package in missing_packages:
            install_package(package)
    
    else:
        print("\n✅ All dependencies are already installed!")
    
    # Final check
    print("\n🎯 Final Dependency Check:")
    all_good = True
    
    # Check core functionality
    try:
        import tkinter
        print("✅ GUI framework (tkinter) - Ready")
    except ImportError:
        print("❌ GUI framework (tkinter) - Missing")
        all_good = False
    
    try:
        import pyaudio
        print("✅ Audio capture (pyaudio) - Ready")
    except ImportError:
        print("⚠️ Audio capture (pyaudio) - Missing (audio features will be disabled)")
    
    try:
        import cv2
        print("✅ Video capture (opencv-python) - Ready")
    except ImportError:
        print("⚠️ Video capture (opencv-python) - Missing (video features will be disabled)")
    
    try:
        import pyautogui
        print("✅ Screen capture (pyautogui) - Ready")
    except ImportError:
        print("⚠️ Screen capture (pyautogui) - Missing (screen sharing will be disabled)")
    
    if all_good:
        print("\n🎉 All dependencies ready! You can now run the client.")
    else:
        print("\n⚠️ Some dependencies are missing, but basic functionality should still work.")
    
    print("\n📝 To connect to the server, run:")
    print("   python test_lan_connection.py")
    print("   or")
    print("   python start_client.py")

if __name__ == "__main__":
    main()
    input("\nPress Enter to exit...")