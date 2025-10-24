#!/usr/bin/env python3
"""
Verify that all video conferencing fixes are properly applied.
"""

import logging
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def verify_syntax():
    """Verify all Python files compile without syntax errors."""
    logger.info("Verifying syntax...")
    
    files_to_check = [
        'client/gui_manager.py',
        'client/video_capture.py', 
        'client/video_playback.py',
        'client/main_client.py'
    ]
    
    for file_path in files_to_check:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                compile(f.read(), file_path, 'exec')
            logger.info(f"✅ {file_path}: Syntax OK")
        except SyntaxError as e:
            logger.error(f"❌ {file_path}: Syntax Error - {e}")
            return False
        except Exception as e:
            logger.error(f"❌ {file_path}: Error - {e}")
            return False
    
    return True

def verify_video_settings():
    """Verify video capture settings."""
    logger.info("Verifying video settings...")
    
    try:
        from client.video_capture import VideoCapture
        
        # Create test instance
        test_capture = VideoCapture("test_client")
        
        # Check settings
        checks = [
            ("FPS", test_capture.fps, 30),
            ("Width", test_capture.width, 240),
            ("Height", test_capture.height, 180),
            ("Quality", test_capture.compression_quality, 40)
        ]
        
        all_ok = True
        for name, actual, expected in checks:
            if actual == expected:
                logger.info(f"✅ {name}: {actual} (correct)")
            else:
                logger.error(f"❌ {name}: {actual} (expected {expected})")
                all_ok = False
        
        return all_ok
        
    except Exception as e:
        logger.error(f"Error verifying video settings: {e}")
        return False

def verify_gui_fixes():
    """Verify GUI fixes are in place."""
    logger.info("Verifying GUI fixes...")
    
    try:
        with open('client/gui_manager.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        checks = [
            ("Label widget usage", "tk.Label("),
            ("Pending updates tracking", "self.pending_updates"),
            ("Frame rate limiting", "self.frame_rate_limit"),
            ("Widget destruction", "video_widget').destroy()"),
            ("Thread-safe updates", "after_idle")
        ]
        
        all_ok = True
        for name, pattern in checks:
            if pattern in content:
                logger.info(f"✅ {name}: Found")
            else:
                logger.error(f"❌ {name}: Not found")
                all_ok = False
        
        return all_ok
        
    except Exception as e:
        logger.error(f"Error verifying GUI fixes: {e}")
        return False

def verify_imports():
    """Verify all modules can be imported."""
    logger.info("Verifying imports...")
    
    modules_to_test = [
        'client.gui_manager',
        'client.video_capture',
        'client.video_playback',
        'client.main_client'
    ]
    
    for module_name in modules_to_test:
        try:
            __import__(module_name)
            logger.info(f"✅ {module_name}: Import OK")
        except Exception as e:
            logger.error(f"❌ {module_name}: Import Error - {e}")
            return False
    
    return True

def run_verification():
    """Run all verification checks."""
    logger.info("Running video conferencing fixes verification...")
    
    checks = [
        ("Syntax Check", verify_syntax),
        ("Import Check", verify_imports),
        ("Video Settings", verify_video_settings),
        ("GUI Fixes", verify_gui_fixes)
    ]
    
    passed = 0
    failed = 0
    
    for check_name, check_func in checks:
        logger.info(f"\n--- {check_name} ---")
        try:
            if check_func():
                logger.info(f"✅ {check_name} PASSED")
                passed += 1
            else:
                logger.error(f"❌ {check_name} FAILED")
                failed += 1
        except Exception as e:
            logger.error(f"❌ {check_name} FAILED with exception: {e}")
            failed += 1
    
    logger.info(f"\n--- Verification Results ---")
    logger.info(f"Passed: {passed}")
    logger.info(f"Failed: {failed}")
    logger.info(f"Total: {passed + failed}")
    
    return failed == 0

if __name__ == "__main__":
    success = run_verification()
    
    if success:
        print("\n✅ All video conferencing fixes verified successfully!")
        print("\n🎯 Ready to test:")
        print("  • Start the client application")
        print("  • Enable video conferencing")
        print("  • Verify frames replace each other (no stacking)")
        print("  • Check 30 FPS smooth operation")
        print("  • Confirm each client appears in only one slot")
    else:
        print("\n❌ Some verification checks failed!")
        print("Please review the errors above before testing.")
        sys.exit(1)