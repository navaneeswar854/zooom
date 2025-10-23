#!/usr/bin/env python3
"""
Comprehensive test runner for the LAN Collaboration Suite.
Runs all tests including cross-platform compatibility, end-to-end workflows, and system validation.
"""

import sys
import os
import unittest
import time
import logging
from pathlib import Path
from io import StringIO

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TestResult:
    """Container for test results."""
    
    def __init__(self, name: str):
        self.name = name
        self.tests_run = 0
        self.failures = 0
        self.errors = 0
        self.skipped = 0
        self.success_rate = 0.0
        self.duration = 0.0
        self.details = []


class ComprehensiveTestRunner:
    """Comprehensive test runner with detailed reporting."""
    
    def __init__(self):
        self.results = []
        self.total_start_time = None
        self.platform_info = None
        
        # Initialize platform info
        try:
            from common.platform_utils import PLATFORM_INFO, log_platform_info
            self.platform_info = PLATFORM_INFO
            log_platform_info()
        except Exception as e:
            logger.warning(f"Could not load platform info: {e}")
    
    def run_test_suite(self, test_module_name: str, test_suite_name: str) -> TestResult:
        """Run a specific test suite and return results."""
        logger.info(f"Running {test_suite_name}...")
        
        result = TestResult(test_suite_name)
        start_time = time.time()
        
        try:
            # Import test module
            test_module = __import__(test_module_name, fromlist=[''])
            
            # Create test suite
            loader = unittest.TestLoader()
            suite = loader.loadTestsFromModule(test_module)
            
            # Run tests with custom result collector
            stream = StringIO()
            runner = unittest.TextTestRunner(
                stream=stream,
                verbosity=2,
                buffer=True
            )
            
            test_result = runner.run(suite)
            
            # Collect results
            result.tests_run = test_result.testsRun
            result.failures = len(test_result.failures)
            result.errors = len(test_result.errors)
            result.skipped = len(test_result.skipped)
            result.duration = time.time() - start_time
            
            # Calculate success rate
            if result.tests_run > 0:
                successful_tests = result.tests_run - result.failures - result.errors
                result.success_rate = (successful_tests / result.tests_run) * 100
            
            # Collect failure/error details
            for failure in test_result.failures:
                result.details.append(f"FAILURE: {failure[0]} - {failure[1]}")
            
            for error in test_result.errors:
                result.details.append(f"ERROR: {error[0]} - {error[1]}")
            
            # Log summary
            logger.info(f"{test_suite_name} completed: {result.tests_run} tests, "
                       f"{result.failures} failures, {result.errors} errors, "
                       f"{result.skipped} skipped in {result.duration:.2f}s")
            
        except Exception as e:
            logger.error(f"Failed to run {test_suite_name}: {e}")
            result.details.append(f"SUITE ERROR: {e}")
        
        return result
    
    def run_all_tests(self):
        """Run all test suites."""
        logger.info("Starting comprehensive test run...")
        self.total_start_time = time.time()
        
        # Define test suites
        test_suites = [
            ("tests.test_cross_platform_compatibility", "Cross-Platform Compatibility Tests"),
            ("tests.test_end_to_end_workflow", "End-to-End Workflow Tests"),
            ("tests.test_system_validation", "System Validation Tests"),
            ("tests.test_session_manager", "Session Manager Tests"),
            ("tests.test_client_server_integration", "Client-Server Integration Tests"),
            ("tests.test_chat_reliability", "Chat Reliability Tests"),
            ("tests.test_file_transfer_validation", "File Transfer Validation Tests"),
            ("tests.test_audio_quality_latency", "Audio Quality & Latency Tests"),
            ("tests.test_video_performance", "Video Performance Tests"),
            ("tests.test_screen_sharing_integration", "Screen Sharing Integration Tests"),
            ("tests.test_advanced_session_management", "Advanced Session Management Tests")
        ]
        
        # Run each test suite
        for module_name, suite_name in test_suites:
            try:
                result = self.run_test_suite(module_name, suite_name)
                self.results.append(result)
            except Exception as e:
                logger.error(f"Failed to run test suite {suite_name}: {e}")
                # Create error result
                error_result = TestResult(suite_name)
                error_result.details.append(f"SUITE LOAD ERROR: {e}")
                self.results.append(error_result)
    
    def generate_report(self):
        """Generate comprehensive test report."""
        total_duration = time.time() - self.total_start_time if self.total_start_time else 0
        
        # Calculate totals
        total_tests = sum(r.tests_run for r in self.results)
        total_failures = sum(r.failures for r in self.results)
        total_errors = sum(r.errors for r in self.results)
        total_skipped = sum(r.skipped for r in self.results)
        
        overall_success_rate = 0
        if total_tests > 0:
            successful_tests = total_tests - total_failures - total_errors
            overall_success_rate = (successful_tests / total_tests) * 100
        
        # Generate report
        report = []
        report.append("=" * 80)
        report.append("LAN COLLABORATION SUITE - COMPREHENSIVE TEST REPORT")
        report.append("=" * 80)
        report.append("")
        
        # Platform information
        if self.platform_info:
            platform_summary = self.platform_info.get_platform_summary()
            report.append("PLATFORM INFORMATION:")
            report.append(f"  System: {platform_summary['system']} {platform_summary['version']}")
            report.append(f"  Architecture: {platform_summary['architecture']}")
            report.append(f"  Python Version: {platform_summary['python_version']}")
            report.append("")
            
            report.append("PLATFORM CAPABILITIES:")
            for capability, available in platform_summary['capabilities'].items():
                status = "✓" if available else "✗"
                report.append(f"  {status} {capability}: {available}")
            report.append("")
        
        # Overall summary
        report.append("OVERALL SUMMARY:")
        report.append(f"  Total Test Suites: {len(self.results)}")
        report.append(f"  Total Tests Run: {total_tests}")
        report.append(f"  Successful: {total_tests - total_failures - total_errors}")
        report.append(f"  Failures: {total_failures}")
        report.append(f"  Errors: {total_errors}")
        report.append(f"  Skipped: {total_skipped}")
        report.append(f"  Success Rate: {overall_success_rate:.1f}%")
        report.append(f"  Total Duration: {total_duration:.2f} seconds")
        report.append("")
        
        # Individual suite results
        report.append("DETAILED RESULTS BY TEST SUITE:")
        report.append("-" * 80)
        
        for result in self.results:
            status = "PASS" if result.failures == 0 and result.errors == 0 else "FAIL"
            report.append(f"{result.name}: {status}")
            report.append(f"  Tests: {result.tests_run}, Failures: {result.failures}, "
                         f"Errors: {result.errors}, Skipped: {result.skipped}")
            report.append(f"  Success Rate: {result.success_rate:.1f}%, Duration: {result.duration:.2f}s")
            
            if result.details:
                report.append("  Issues:")
                for detail in result.details[:5]:  # Limit to first 5 issues
                    report.append(f"    - {detail}")
                if len(result.details) > 5:
                    report.append(f"    ... and {len(result.details) - 5} more issues")
            
            report.append("")
        
        # Recommendations
        report.append("RECOMMENDATIONS:")
        report.append("-" * 80)
        
        if overall_success_rate >= 95:
            report.append("✓ Excellent! System is ready for production use.")
        elif overall_success_rate >= 85:
            report.append("⚠ Good overall performance. Address remaining issues before production.")
        elif overall_success_rate >= 70:
            report.append("⚠ Moderate performance. Significant issues need attention.")
        else:
            report.append("✗ Poor performance. Major issues must be resolved.")
        
        # Platform-specific recommendations
        if self.platform_info:
            capabilities = self.platform_info.capabilities
            
            if not capabilities.get('audio_capture', True):
                report.append("• Install audio dependencies (pyaudio) for full audio functionality")
            
            if not capabilities.get('video_capture', True):
                report.append("• Install video dependencies (opencv-python) for video features")
            
            if not capabilities.get('screen_capture', True):
                report.append("• Install screen capture dependencies (pyautogui) for screen sharing")
        
        report.append("")
        report.append("=" * 80)
        
        return "\n".join(report)
    
    def save_report(self, filename: str = None):
        """Save test report to file."""
        if filename is None:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"test_report_{timestamp}.txt"
        
        report = self.generate_report()
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(report)
            logger.info(f"Test report saved to: {filename}")
        except Exception as e:
            logger.error(f"Failed to save report: {e}")
        
        return filename


def main():
    """Main test runner function."""
    print("LAN Collaboration Suite - Comprehensive Test Runner")
    print("=" * 60)
    
    # Check Python version
    if sys.version_info < (3, 7):
        print("ERROR: Python 3.7 or higher is required")
        sys.exit(1)
    
    # Check if we're in the right directory
    if not Path("common").exists() or not Path("server").exists() or not Path("client").exists():
        print("ERROR: Please run this script from the project root directory")
        sys.exit(1)
    
    # Create test runner
    runner = ComprehensiveTestRunner()
    
    try:
        # Run all tests
        runner.run_all_tests()
        
        # Generate and display report
        report = runner.generate_report()
        print(report)
        
        # Save report to file
        report_file = runner.save_report()
        
        # Determine exit code based on results
        total_failures = sum(r.failures for r in runner.results)
        total_errors = sum(r.errors for r in runner.results)
        
        if total_failures > 0 or total_errors > 0:
            print(f"\nTests completed with {total_failures} failures and {total_errors} errors.")
            print(f"Report saved to: {report_file}")
            sys.exit(1)
        else:
            print(f"\nAll tests passed successfully!")
            print(f"Report saved to: {report_file}")
            sys.exit(0)
    
    except KeyboardInterrupt:
        print("\nTest run interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nTest run failed with error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()