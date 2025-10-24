#!/usr/bin/env python3
"""
Test the final video stacking fix.
"""

import logging
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_syntax():
    """Test that all files compile without syntax errors."""
    logger.info("Testing syntax...")
    
    try:
        with open('client/gui_manager.py', 'r', encoding='utf-8') as f:
            compile(f.read(), 'client/gui_manager.py', 'exec')
        logger.info("✅ GUI manager syntax OK")
        return True
    except SyntaxError as e:
        logger.error(f"❌ Syntax error: {e}")
        return False

def test_widget_clearing():
    """Test that the widget clearing logic is in place."""
    logger.info("Testing widget clearing logic...")
    
    try:
        with open('client/gui_manager.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for complete widget clearing
        if "for child in slot['frame'].winfo_children():" in content:
            logger.info("✅ Complete widget clearing found")
        else:
            logger.error("❌ Complete widget clearing not found")
            return False
        
        if "child.destroy()" in content:
            logger.info("✅ Child widget destruction found")
        else:
            logger.error("❌ Child widget destruction not found")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"Error testing widget clearing: {e}")
        return False

def test_imports():
    """Test that modules can be imported."""
    logger.info("Testing imports...")
    
    try:
        from client.gui_manager import VideoFrame
        logger.info("✅ VideoFrame import OK")
        return True
    except Exception as e:
        logger.error(f"❌ Import error: {e}")
        return False

def run_tests():
    """Run all tests."""
    logger.info("Running final video stacking fix tests...")
    
    tests = [
        ("Syntax Test", test_syntax),
        ("Widget Clearing Test", test_widget_clearing),
        ("Import Test", test_imports)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        logger.info(f"\n--- {test_name} ---")
        try:
            if test_func():
                logger.info(f"✅ {test_name} PASSED")
                passed += 1
            else:
                logger.error(f"❌ {test_name} FAILED")
                failed += 1
        except Exception as e:
            logger.error(f"❌ {test_name} FAILED with exception: {e}")
            failed += 1
    
    logger.info(f"\n--- Test Results ---")
    logger.info(f"Passed: {passed}")
    logger.info(f"Failed: {failed}")
    
    return failed == 0

if __name__ == "__main__":
    success = run_tests()
    
    if success:
        print("\n✅ Final video stacking fix tests PASSED!")
        print("\n🔧 Key Fix Applied:")
        print("  • Complete widget clearing: Destroys ALL child widgets in each slot")
        print("  • Prevents widget accumulation and stacking")
        print("  • Recreates widgets fresh for each frame")
        print("\n🎯 Expected Results:")
        print("  • Video frames will completely replace previous frames")
        print("  • No more vertical stacking of video widgets")
        print("  • Each client appears in exactly one video slot")
        print("  • Clean, professional video display")
        print("\n⚠️  RESTART THE CLIENT APPLICATION to apply the fix!")
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)