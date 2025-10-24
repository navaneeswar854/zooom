#!/usr/bin/env python3
"""
Fix Connection Import Issues
Ensures all necessary imports are present to fix the "deque is not defined" error.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def check_and_fix_imports():
    """Check and fix import issues in key files."""
    
    print("🔧 Checking and fixing import issues...")
    
    files_to_check = [
        'client/video_capture.py',
        'client/video_playback.py', 
        'client/video_optimization.py',
        'client/extreme_video_optimizer.py',
        'client/ultra_stable_gui.py',
        'client/stable_video_system.py',
        'client/frame_sequencer.py',
        'client/audio_playback.py'
    ]
    
    for file_path in files_to_check:
        try:
            print(f"   📄 Checking {file_path}...")
            
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Check if file uses deque but doesn't import it
            uses_deque = 'deque(' in content or 'deque[' in content or ': deque' in content
            has_deque_import = 'from collections import deque' in content
            
            if uses_deque and not has_deque_import:
                print(f"   ⚠️  {file_path} uses deque but missing import - fixing...")
                
                # Find the imports section and add deque import
                lines = content.split('\n')
                import_added = False
                
                for i, line in enumerate(lines):
                    if line.startswith('from typing import') and not import_added:
                        lines.insert(i + 1, 'from collections import deque')
                        import_added = True
                        break
                    elif line.startswith('import ') and 'from collections' not in lines[max(0, i-3):i+3] and not import_added:
                        lines.insert(i, 'from collections import deque')
                        import_added = True
                        break
                
                if import_added:
                    # Write back the fixed content
                    with open(file_path, 'w') as f:
                        f.write('\n'.join(lines))
                    print(f"   ✅ Fixed deque import in {file_path}")
                else:
                    print(f"   ❌ Could not fix deque import in {file_path}")
            else:
                print(f"   ✅ {file_path} imports are correct")
                
        except Exception as e:
            print(f"   ❌ Error checking {file_path}: {e}")
    
    return True


def test_imports():
    """Test that all imports work correctly."""
    
    print("\n🧪 Testing imports...")
    
    try:
        # Test core imports
        print("   📦 Testing core imports...")
        from collections import deque
        import time
        import threading
        import logging
        print("   ✅ Core imports working")
        
        # Test video system imports
        print("   📦 Testing video system imports...")
        from client.video_capture import VideoCapture
        from client.video_playback import VideoRenderer
        print("   ✅ Video system imports working")
        
        # Test optimization imports
        print("   📦 Testing optimization imports...")
        from client.video_optimization import video_optimizer
        from client.extreme_video_optimizer import extreme_video_optimizer
        from client.stable_video_system import stability_manager
        from client.ultra_stable_gui import ultra_stable_manager
        from client.frame_sequencer import frame_sequencing_manager
        print("   ✅ Optimization imports working")
        
        # Test message imports
        print("   📦 Testing message imports...")
        from common.messages import MessageFactory, MessageType
        print("   ✅ Message imports working")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Import test failed: {e}")
        return False


def test_basic_functionality():
    """Test basic functionality to ensure everything works."""
    
    print("\n⚡ Testing basic functionality...")
    
    try:
        # Test deque creation
        from collections import deque
        test_deque = deque(maxlen=10)
        test_deque.append("test")
        print("   ✅ deque functionality working")
        
        # Test video capture creation
        from client.video_capture import VideoCapture
        video_capture = VideoCapture("test_client")
        print("   ✅ VideoCapture creation working")
        
        # Test video renderer creation
        from client.video_playback import VideoRenderer
        video_renderer = VideoRenderer()
        print("   ✅ VideoRenderer creation working")
        
        # Test message factory
        from common.messages import MessageFactory
        test_message = MessageFactory.create_chat_message("test", "hello")
        print("   ✅ MessageFactory working")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Functionality test failed: {e}")
        return False


def main():
    """Main function to fix connection issues."""
    
    print("🔧 FIXING CONNECTION IMPORT ISSUES")
    print("Resolving 'deque is not defined' error")
    print("=" * 50)
    
    # Fix imports
    success1 = check_and_fix_imports()
    
    # Test imports
    success2 = test_imports()
    
    # Test functionality
    success3 = test_basic_functionality()
    
    print(f"\n📊 RESULTS")
    print("=" * 50)
    
    if success1 and success2 and success3:
        print("✅ ALL IMPORT ISSUES FIXED!")
        print("The 'deque is not defined' error should be resolved.")
        print("\n🚀 Ready to connect:")
        print("1. Start the server: python start_server.py")
        print("2. Start the client: python start_client.py")
        print("3. Connect to the server")
        
        return 0
    else:
        print("❌ SOME ISSUES REMAIN")
        print("Please check the error messages above.")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)