"""
File transfer validation tests for the collaboration suite.
Tests upload and download functionality and progress tracking accuracy.
Requirements: 6.1, 6.3, 6.4
"""

import unittest
import threading
import time
import os
import tempfile
import shutil
import hashlib
from unittest.mock import Mock, patch, MagicMock
from server.session_manager import SessionManager
from common.file_metadata import FileMetadata, FileValidator
from common.messages import MessageFactory, MessageType, TCPMessage


class TestFileTransferValidation(unittest.TestCase):
    """Test cases for file transfer upload and download functionality."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        # Create temporary directories for testing
        self.test_dir = tempfile.mkdtemp(prefix="file_transfer_test_")
        self.server_files_dir = os.path.join(self.test_dir, "server_files")
        self.client_downloads_dir = os.path.join(self.test_dir, "client_downloads")
        
        os.makedirs(self.server_files_dir, exist_ok=True)
        os.makedirs(self.client_downloads_dir, exist_ok=True)
        
        # Initialize session manager for file transfer testing
        self.session_manager = SessionManager(file_storage_dir=self.server_files_dir)
        
        # Track test results
        self.test_results = {
            'uploads_completed': 0,
            'downloads_completed': 0,
            'upload_errors': [],
            'download_errors': [],
            'progress_updates': []
        }
    
    def tearDown(self):
        """Clean up after each test method."""
        # Clean up temporary directories
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def _create_test_file(self, filename: str, content: bytes = None, size_kb: int = None) -> str:
        """
        Create a test file for upload testing.
        
        Args:
            filename: Name of the file to create
            content: Specific content for the file (optional)
            size_kb: Size in KB for generated content (optional)
            
        Returns:
            str: Path to the created test file
        """
        file_path = os.path.join(self.test_dir, filename)
        
        if content is not None:
            with open(file_path, 'wb') as f:
                f.write(content)
        elif size_kb is not None:
            # Generate content of specified size
            content = b'A' * (size_kb * 1024)
            with open(file_path, 'wb') as f:
                f.write(content)
        else:
            # Default small test file
            content = b"Test file content for file transfer validation"
            with open(file_path, 'wb') as f:
                f.write(content)
        
        return file_path
    
    def _simulate_progress_callback(self, filename: str, progress: float):
        """Simulate progress callback for testing."""
        self.test_results['progress_updates'].append({
            'filename': filename,
            'progress': progress,
            'timestamp': time.time()
        })
    
    def test_file_upload_functionality(self):
        """Test file upload functionality through session manager."""
        # Create test file
        test_content = b"This is test content for upload validation"
        test_file = self._create_test_file("test_upload.txt", content=test_content)
        
        # Create file metadata
        file_metadata = FileMetadata(
            filename="test_upload.txt",
            filesize=len(test_content),
            uploader_id="test_user_123"
        )
        
        # Calculate file hash
        file_metadata.calculate_hash(test_file)
        
        # Test file upload process (start_file_upload should be used instead of add_file_metadata)
        success, error_msg = self.session_manager.start_file_upload(file_metadata)
        self.assertTrue(success, f"File upload start failed: {error_msg}")
        
        # Simulate file upload in chunks
        chunk_size = 8192
        total_chunks = (len(test_content) + chunk_size - 1) // chunk_size
        
        with open(test_file, 'rb') as f:
            for chunk_num in range(total_chunks):
                chunk_data = f.read(chunk_size)
                if not chunk_data:
                    break
                
                success, error_msg, is_complete = self.session_manager.process_file_chunk(
                    file_metadata.file_id, chunk_num, total_chunks, chunk_data
                )
                
                self.assertTrue(success, f"Chunk {chunk_num} processing failed: {error_msg}")
                
                if chunk_num == total_chunks - 1:
                    self.assertTrue(is_complete, "Upload should be complete on last chunk")
        
        # After upload completion, verify file exists on server
        shared_files = self.session_manager.get_all_shared_files()
        self.assertEqual(len(shared_files), 1, "Expected 1 shared file")
        
        uploaded_file = shared_files[0]
        self.assertEqual(uploaded_file.filename, "test_upload.txt")
        self.assertEqual(uploaded_file.filesize, len(test_content))
        self.assertEqual(uploaded_file.uploader_id, "test_user_123")
        
        # Verify file content integrity
        server_file_path = self.session_manager.get_file_path(uploaded_file.file_id)
        self.assertIsNotNone(server_file_path, "Server file path should exist")
        self.assertTrue(os.path.exists(server_file_path), "Server file should exist")
        
        with open(server_file_path, 'rb') as f:
            server_content = f.read()
        
        self.assertEqual(server_content, test_content, "File content should match")
        
        # Verify file hash integrity
        self.assertTrue(uploaded_file.verify_hash(server_file_path), "File hash should be valid")
    
    def test_file_download_simulation(self):
        """Test file download simulation with progress tracking."""
        # Create and upload a test file first
        test_content = b"Content for download test " * 100  # Make it larger for progress tracking
        test_file = self._create_test_file("download_test.txt", content=test_content)
        
        # Create file metadata and upload
        file_metadata = FileMetadata(
            filename="download_test.txt",
            filesize=len(test_content),
            uploader_id="test_uploader"
        )
        
        # Upload the file
        success, _ = self.session_manager.start_file_upload(file_metadata)
        self.assertTrue(success)
        
        # Upload in chunks
        chunk_size = 8192
        total_chunks = (len(test_content) + chunk_size - 1) // chunk_size
        
        with open(test_file, 'rb') as f:
            for chunk_num in range(total_chunks):
                chunk_data = f.read(chunk_size)
                if not chunk_data:
                    break
                
                success, _, is_complete = self.session_manager.process_file_chunk(
                    file_metadata.file_id, chunk_num, total_chunks, chunk_data
                )
                self.assertTrue(success)
        
        # Simulate download process with progress tracking
        server_file_path = self.session_manager.get_file_path(file_metadata.file_id)
        self.assertIsNotNone(server_file_path, "Server file should exist")
        
        # Simulate chunked download with progress callbacks
        download_path = os.path.join(self.client_downloads_dir, "downloaded_file.txt")
        
        with open(server_file_path, 'rb') as source_file:
            with open(download_path, 'wb') as dest_file:
                bytes_downloaded = 0
                total_size = len(test_content)
                
                while True:
                    chunk = source_file.read(chunk_size)
                    if not chunk:
                        break
                    
                    dest_file.write(chunk)
                    bytes_downloaded += len(chunk)
                    
                    # Simulate progress callback
                    progress = bytes_downloaded / total_size
                    self._simulate_progress_callback("download_test.txt", progress)
        
        # Verify download completion
        self.assertTrue(os.path.exists(download_path), "Downloaded file should exist")
        
        with open(download_path, 'rb') as f:
            downloaded_content = f.read()
        
        self.assertEqual(downloaded_content, test_content, "Downloaded content should match original")
        
        # Verify progress tracking
        progress_updates = self.test_results['progress_updates']
        self.assertGreater(len(progress_updates), 0, "Progress updates should be recorded")
        
        # Check progress values are valid (between 0 and 1)
        for update in progress_updates:
            self.assertGreaterEqual(update['progress'], 0.0, "Progress should be >= 0")
            self.assertLessEqual(update['progress'], 1.0, "Progress should be <= 1")
        
        # Verify final progress is 1.0 (100%)
        final_progress = max(update['progress'] for update in progress_updates)
        self.assertEqual(final_progress, 1.0, "Final progress should be 100%")
    
    def test_progress_tracking_accuracy(self):
        """Test accuracy of progress tracking for file transfers."""
        # Create larger file to ensure multiple chunks and measurable progress
        large_content = b"X" * (50 * 1024)  # 50KB file
        test_file = self._create_test_file("large_test.txt", content=large_content)
        
        # Clear progress tracking
        self.test_results['progress_updates'].clear()
        
        # Simulate chunked upload with progress tracking
        chunk_size = 4096  # Smaller chunks for more progress updates
        total_size = len(large_content)
        bytes_processed = 0
        
        with open(test_file, 'rb') as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                
                bytes_processed += len(chunk)
                progress = bytes_processed / total_size
                
                # Simulate progress callback
                self._simulate_progress_callback("large_test.txt", progress)
        
        # Analyze progress tracking accuracy
        progress_updates = self.test_results['progress_updates']
        self.assertGreater(len(progress_updates), 1, "Should have multiple progress updates")
        
        # Verify progress is monotonically increasing
        previous_progress = 0.0
        for update in progress_updates:
            current_progress = update['progress']
            self.assertGreaterEqual(current_progress, previous_progress, 
                                  "Progress should be monotonically increasing")
            previous_progress = current_progress
        
        # Verify progress starts at or near 0 and ends at 1.0
        first_progress = progress_updates[0]['progress']
        last_progress = progress_updates[-1]['progress']
        
        self.assertLessEqual(first_progress, 0.2, "First progress should be low")
        self.assertEqual(last_progress, 1.0, "Last progress should be 100%")
        
        # Verify reasonable progress intervals (no huge jumps)
        for i in range(1, len(progress_updates)):
            progress_jump = progress_updates[i]['progress'] - progress_updates[i-1]['progress']
            self.assertLessEqual(progress_jump, 0.5, "Progress jumps should be reasonable")
        
        # Verify all progress values are valid
        for update in progress_updates:
            self.assertGreaterEqual(update['progress'], 0.0, "Progress should be >= 0")
            self.assertLessEqual(update['progress'], 1.0, "Progress should be <= 1")
            self.assertIsInstance(update['timestamp'], float, "Timestamp should be float")
            self.assertEqual(update['filename'], "large_test.txt", "Filename should match")
    
    def test_multiple_file_transfers(self):
        """Test handling of multiple concurrent file transfers."""
        # Create multiple test files
        file1_content = b"Content for file 1 " * 50
        file2_content = b"Different content for file 2 " * 40
        
        test_file1 = self._create_test_file("multi_test1.txt", content=file1_content)
        test_file2 = self._create_test_file("multi_test2.txt", content=file2_content)
        
        # Create metadata for both files
        file1_metadata = FileMetadata(
            filename="multi_test1.txt",
            filesize=len(file1_content),
            uploader_id="uploader1"
        )
        
        file2_metadata = FileMetadata(
            filename="multi_test2.txt",
            filesize=len(file2_content),
            uploader_id="uploader2"
        )
        
        # Upload both files
        for file_metadata, test_file in [(file1_metadata, test_file1), (file2_metadata, test_file2)]:
            # Start upload
            success, _ = self.session_manager.start_file_upload(file_metadata)
            self.assertTrue(success, f"Failed to start upload for {file_metadata.filename}")
            
            # Upload in chunks
            chunk_size = 8192
            total_chunks = (file_metadata.filesize + chunk_size - 1) // chunk_size
            
            with open(test_file, 'rb') as f:
                for chunk_num in range(total_chunks):
                    chunk_data = f.read(chunk_size)
                    if not chunk_data:
                        break
                    
                    success, _, _ = self.session_manager.process_file_chunk(
                        file_metadata.file_id, chunk_num, total_chunks, chunk_data
                    )
                    self.assertTrue(success, f"Chunk processing failed for {file_metadata.filename}")
        
        # Verify both files are available
        shared_files = self.session_manager.get_all_shared_files()
        self.assertEqual(len(shared_files), 2, "Expected 2 shared files")
        
        # Verify file content integrity for both files
        for shared_file in shared_files:
            server_file_path = self.session_manager.get_file_path(shared_file.file_id)
            self.assertIsNotNone(server_file_path, f"Server file path should exist for {shared_file.filename}")
            
            with open(server_file_path, 'rb') as f:
                server_content = f.read()
            
            # Match content to original files
            if shared_file.filename == "multi_test1.txt":
                self.assertEqual(server_content, file1_content, "File 1 content should match")
                self.assertEqual(shared_file.uploader_id, "uploader1", "File 1 uploader should match")
            elif shared_file.filename == "multi_test2.txt":
                self.assertEqual(server_content, file2_content, "File 2 content should match")
                self.assertEqual(shared_file.uploader_id, "uploader2", "File 2 uploader should match")
    
    def test_file_validation_and_error_handling(self):
        """Test file validation and error handling during transfers."""
        # Test 1: Validate non-existent file
        is_valid, error = FileValidator.validate_file("/nonexistent/file.txt")
        self.assertFalse(is_valid, "Non-existent file should fail validation")
        self.assertIn("does not exist", error.lower())
        
        # Test 2: Validate empty file
        empty_file = self._create_test_file("empty.txt", content=b"")
        is_valid, error = FileValidator.validate_file(empty_file)
        self.assertFalse(is_valid, "Empty file should fail validation")
        self.assertIn("empty", error.lower())
        
        # Test 3: Validate file with invalid extension
        invalid_file = self._create_test_file("test.invalid_ext", content=b"test content")
        is_valid, error = FileValidator.validate_file(invalid_file)
        self.assertFalse(is_valid, "Invalid file type should fail validation")
        self.assertIn("not allowed", error.lower())
        
        # Test 4: Validate oversized file (simulate)
        with patch('os.path.getsize', return_value=200 * 1024 * 1024):  # 200MB
            large_file = self._create_test_file("large.txt", content=b"content")
            is_valid, error = FileValidator.validate_file(large_file)
            self.assertFalse(is_valid, "Oversized file should fail validation")
            self.assertIn("too large", error.lower())
        
        # Test 5: Test invalid file metadata
        invalid_metadata = FileMetadata(
            filename="",  # Empty filename
            filesize=1024,
            uploader_id="test_user"
        )
        
        success = self.session_manager.add_file_metadata(invalid_metadata)
        self.assertFalse(success, "Invalid metadata should be rejected")
        
        # Test 6: Test file upload with invalid file ID
        success, error_msg, _ = self.session_manager.process_file_chunk(
            "nonexistent_file_id", 0, 1, b"test data"
        )
        self.assertFalse(success, "Processing chunk for non-existent file should fail")
        self.assertIn("no upload in progress", error_msg.lower())
        
        # Test 7: Test file path retrieval for non-existent file
        file_path = self.session_manager.get_file_path("nonexistent_file_id")
        self.assertIsNone(file_path, "Non-existent file should return None path")
    
    def test_file_integrity_verification(self):
        """Test file integrity verification using checksums."""
        # Create test file with known content
        test_content = b"File integrity test content with special chars: !@#$%^&*()"
        test_file = self._create_test_file("integrity_test.txt", content=test_content)
        
        # Calculate original hash
        original_hash = hashlib.sha256(test_content).hexdigest()
        
        # Create file metadata
        file_metadata = FileMetadata(
            filename="integrity_test.txt",
            filesize=len(test_content),
            uploader_id="integrity_tester"
        )
        
        # Calculate file hash
        file_metadata.calculate_hash(test_file)
        
        # Verify hash was calculated correctly
        self.assertIsNotNone(file_metadata.file_hash, "File should have hash")
        self.assertEqual(file_metadata.file_hash, original_hash, "Hash should match original")
        
        # Upload file through session manager
        success, _ = self.session_manager.start_file_upload(file_metadata)
        self.assertTrue(success)
        
        # Upload in chunks
        chunk_size = 8192
        total_chunks = (len(test_content) + chunk_size - 1) // chunk_size
        
        with open(test_file, 'rb') as f:
            for chunk_num in range(total_chunks):
                chunk_data = f.read(chunk_size)
                if not chunk_data:
                    break
                
                success, _, _ = self.session_manager.process_file_chunk(
                    file_metadata.file_id, chunk_num, total_chunks, chunk_data
                )
                self.assertTrue(success)
        
        # Verify file exists and has correct hash
        shared_files = self.session_manager.get_all_shared_files()
        uploaded_file = shared_files[0]
        
        self.assertEqual(uploaded_file.file_hash, original_hash, "Uploaded file hash should match")
        
        # Verify file integrity on server
        server_file_path = self.session_manager.get_file_path(uploaded_file.file_id)
        self.assertTrue(uploaded_file.verify_hash(server_file_path), "Server file should pass hash verification")
        
        # Simulate download and verify integrity
        download_path = os.path.join(self.client_downloads_dir, "downloaded_integrity_test.txt")
        
        # Copy file to simulate download
        with open(server_file_path, 'rb') as src:
            with open(download_path, 'wb') as dst:
                dst.write(src.read())
        
        # Verify downloaded file integrity
        with open(download_path, 'rb') as f:
            downloaded_content = f.read()
        
        downloaded_hash = hashlib.sha256(downloaded_content).hexdigest()
        
        self.assertEqual(downloaded_hash, original_hash, "Downloaded file hash should match original")
        self.assertEqual(downloaded_content, test_content, "Downloaded content should match original")
        self.assertTrue(uploaded_file.verify_hash(download_path), "Downloaded file should pass hash verification")
    
    def test_file_transfer_error_recovery(self):
        """Test file transfer error recovery and cleanup."""
        # Create test file
        test_content = b"Content for error recovery test " * 100
        test_file = self._create_test_file("error_test.txt", content=test_content)
        
        # Create file metadata
        file_metadata = FileMetadata(
            filename="error_test.txt",
            filesize=len(test_content),
            uploader_id="error_tester"
        )
        
        # Start upload
        success, _ = self.session_manager.start_file_upload(file_metadata)
        self.assertTrue(success)
        
        # Simulate upload failure by sending invalid chunk data
        success, error_msg, _ = self.session_manager.process_file_chunk(
            file_metadata.file_id, 0, 2, b"chunk1"
        )
        self.assertTrue(success, "First chunk should succeed")
        
        # Simulate error by sending chunk with wrong total_chunks
        success, error_msg, _ = self.session_manager.process_file_chunk(
            file_metadata.file_id, 1, 3, b"chunk2"  # Wrong total_chunks (3 instead of 2)
        )
        self.assertFalse(success, "Chunk with wrong total should fail")
        self.assertIn("mismatch", error_msg.lower())
        
        # The mismatch error doesn't trigger cleanup, so upload is still in progress
        # This is actually correct behavior - the upload can continue with correct chunks
        upload_in_progress = file_metadata.file_id in self.session_manager.file_uploads_in_progress
        self.assertTrue(upload_in_progress, "Upload should still be in progress after mismatch error")
        
        # Test actual cleanup by simulating a file write error
        # Close the file handle to simulate an error
        upload_state = self.session_manager.file_uploads_in_progress[file_metadata.file_id]
        upload_state['file_handle'].close()
        
        # Now try to write another chunk - this should trigger cleanup
        success, error_msg, _ = self.session_manager.process_file_chunk(
            file_metadata.file_id, 1, 2, b"chunk2"
        )
        self.assertFalse(success, "Chunk processing should fail with closed file")
        
        # Verify upload was cleaned up after the file error
        upload_in_progress = file_metadata.file_id in self.session_manager.file_uploads_in_progress
        self.assertFalse(upload_in_progress, "Failed upload should be cleaned up after file error")
        
        # Test file removal functionality
        # First, complete a successful upload
        file_metadata2 = FileMetadata(
            filename="remove_test.txt",
            filesize=len(test_content),
            uploader_id="remove_tester"
        )
        
        success, _ = self.session_manager.start_file_upload(file_metadata2)
        self.assertTrue(success)
        
        # Complete upload
        chunk_size = 8192
        total_chunks = (len(test_content) + chunk_size - 1) // chunk_size
        
        with open(test_file, 'rb') as f:
            for chunk_num in range(total_chunks):
                chunk_data = f.read(chunk_size)
                if not chunk_data:
                    break
                
                success, _, _ = self.session_manager.process_file_chunk(
                    file_metadata2.file_id, chunk_num, total_chunks, chunk_data
                )
                self.assertTrue(success)
        
        # Verify file exists
        shared_files = self.session_manager.get_all_shared_files()
        self.assertEqual(len(shared_files), 1)
        
        # Test file removal by uploader
        success = self.session_manager.remove_shared_file(file_metadata2.file_id, "remove_tester")
        self.assertTrue(success, "File removal by uploader should succeed")
        
        # Test file removal by non-uploader (should fail)
        file_metadata3 = FileMetadata(
            filename="protected_test.txt",
            filesize=len(test_content),
            uploader_id="original_uploader"
        )
        
        # For this test, we need to add the file to shared_files directly since we're not uploading
        self.session_manager.shared_files[file_metadata3.file_id] = file_metadata3
        success = self.session_manager.remove_shared_file(file_metadata3.file_id, "different_user")
        self.assertFalse(success, "File removal by non-uploader should fail")


class TestFileMetadataValidation(unittest.TestCase):
    """Test cases for file metadata validation and handling."""
    
    def test_file_metadata_creation_and_validation(self):
        """Test FileMetadata creation and validation."""
        # Valid metadata
        valid_metadata = FileMetadata(
            filename="test.txt",
            filesize=1024,
            uploader_id="user123"
        )
        
        self.assertTrue(valid_metadata.is_valid(), "Valid metadata should pass validation")
        self.assertIsNotNone(valid_metadata.file_id, "File ID should be generated")
        self.assertIsNotNone(valid_metadata.upload_time, "Upload time should be set")
        
        # Invalid metadata - empty filename
        invalid_metadata = FileMetadata(
            filename="",
            filesize=1024,
            uploader_id="user123"
        )
        
        self.assertFalse(invalid_metadata.is_valid(), "Empty filename should be invalid")
        
        # Invalid metadata - negative file size
        invalid_metadata = FileMetadata(
            filename="test.txt",
            filesize=-1,
            uploader_id="user123"
        )
        
        self.assertFalse(invalid_metadata.is_valid(), "Negative file size should be invalid")
        
        # Invalid metadata - dangerous filename
        invalid_metadata = FileMetadata(
            filename="../../../etc/passwd",
            filesize=1024,
            uploader_id="user123"
        )
        
        self.assertFalse(invalid_metadata.is_valid(), "Path traversal filename should be invalid")
    
    def test_file_validator_functionality(self):
        """Test FileValidator class functionality."""
        # Create temporary test files
        test_dir = tempfile.mkdtemp()
        
        try:
            # Valid file
            valid_file = os.path.join(test_dir, "valid.txt")
            with open(valid_file, 'w') as f:
                f.write("Valid content")
            
            is_valid, error = FileValidator.validate_file(valid_file)
            self.assertTrue(is_valid, f"Valid file should pass: {error}")
            
            # Non-existent file
            is_valid, error = FileValidator.validate_file("/nonexistent/file.txt")
            self.assertFalse(is_valid, "Non-existent file should fail")
            self.assertIn("does not exist", error)
            
            # Empty file
            empty_file = os.path.join(test_dir, "empty.txt")
            with open(empty_file, 'w') as f:
                pass  # Create empty file
            
            is_valid, error = FileValidator.validate_file(empty_file)
            self.assertFalse(is_valid, "Empty file should fail")
            self.assertIn("empty", error)
            
            # Invalid extension
            invalid_file = os.path.join(test_dir, "test.exe")
            with open(invalid_file, 'w') as f:
                f.write("content")
            
            is_valid, error = FileValidator.validate_file(invalid_file)
            self.assertFalse(is_valid, "Invalid extension should fail")
            self.assertIn("not allowed", error)
        
        finally:
            shutil.rmtree(test_dir, ignore_errors=True)
    
    def test_safe_filename_generation(self):
        """Test safe filename generation for file storage."""
        # Test dangerous filename
        metadata = FileMetadata(
            filename="../../../dangerous.txt",
            filesize=100,
            uploader_id="user123"
        )
        
        safe_name = metadata.get_safe_filename()
        self.assertNotIn("..", safe_name, "Safe filename should not contain '..'")
        self.assertNotIn("/", safe_name, "Safe filename should not contain '/'")
        self.assertNotIn("\\", safe_name, "Safe filename should not contain '\\'")
        
        # Test long filename
        long_name = "a" * 300 + ".txt"
        metadata = FileMetadata(
            filename=long_name,
            filesize=100,
            uploader_id="user123"
        )
        
        safe_name = metadata.get_safe_filename()
        self.assertLessEqual(len(safe_name), 255, "Safe filename should be <= 255 characters")
        self.assertTrue(safe_name.endswith(".txt"), "Extension should be preserved")


if __name__ == '__main__':
    # Run tests with detailed output
    unittest.main(verbosity=2, buffer=True)