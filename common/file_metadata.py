"""
File metadata management for the collaboration suite.
Handles file information tracking, validation, and serialization.
"""

import time
import uuid
import os
import hashlib
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from pathlib import Path
from common.platform_utils import PathUtils, ErrorHandler


@dataclass
class FileMetadata:
    """
    Represents metadata for a shared file in the collaboration system.
    
    Tracks file information for upload, download, and sharing operations.
    """
    filename: str
    filesize: int
    uploader_id: str
    file_id: str = None
    upload_time: float = None
    file_hash: Optional[str] = None
    mime_type: Optional[str] = None
    description: Optional[str] = None
    
    def __post_init__(self):
        if self.file_id is None:
            self.file_id = str(uuid.uuid4())
        if self.upload_time is None:
            self.upload_time = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert FileMetadata to dictionary for serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FileMetadata':
        """Create FileMetadata from dictionary."""
        return cls(**data)
    
    def is_valid(self) -> bool:
        """
        Validate file metadata structure and content.
        
        Returns:
            bool: True if metadata is valid
        """
        # Check required fields
        if not self.filename or not isinstance(self.filename, str):
            return False
        
        if not isinstance(self.filesize, int) or self.filesize < 0:
            return False
        
        if not self.uploader_id or not isinstance(self.uploader_id, str):
            return False
        
        if not self.file_id or not isinstance(self.file_id, str):
            return False
        
        # Check filename validity
        if len(self.filename.strip()) == 0:
            return False
        
        # Check for dangerous file paths
        if '..' in self.filename or '/' in self.filename or '\\' in self.filename:
            return False
        
        # Check file size limits (100MB max)
        max_file_size = 100 * 1024 * 1024  # 100MB
        if self.filesize > max_file_size:
            return False
        
        return True
    
    def get_safe_filename(self) -> str:
        """
        Get a safe filename for storage, removing dangerous characters.
        
        Returns:
            str: Safe filename for file system storage
        """
        # Use platform utils to ensure path safety
        if not PathUtils.is_path_safe(self.filename):
            # Remove dangerous characters and path separators
            safe_name = self.filename.replace('/', '_').replace('\\', '_')
            safe_name = safe_name.replace('..', '_')
        else:
            safe_name = self.filename
        
        # Remove other dangerous characters
        dangerous_chars = ['<', '>', ':', '"', '|', '?', '*']
        for char in dangerous_chars:
            safe_name = safe_name.replace(char, '_')
        
        # Limit filename length (platform-specific limits)
        max_length = 255  # Most filesystems support 255 characters
        if len(safe_name) > max_length:
            name_part, ext_part = os.path.splitext(safe_name)
            max_name_len = max_length - len(ext_part)
            safe_name = name_part[:max_name_len] + ext_part
        
        return safe_name
    
    def calculate_hash(self, file_path: str) -> str:
        """
        Calculate SHA-256 hash of the file for integrity verification.
        
        Args:
            file_path: Path to the file to hash
            
        Returns:
            str: SHA-256 hash of the file
        """
        try:
            # Use pathlib for cross-platform path handling
            safe_path = PathUtils.get_safe_path(file_path)
            
            hash_sha256 = hashlib.sha256()
            with safe_path.open('rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            
            self.file_hash = hash_sha256.hexdigest()
            return self.file_hash
        
        except Exception as e:
            error_msg = ErrorHandler.get_platform_specific_error_message(e)
            raise ValueError(f"Failed to calculate file hash: {error_msg}")
    
    def verify_hash(self, file_path: str) -> bool:
        """
        Verify file integrity using stored hash.
        
        Args:
            file_path: Path to the file to verify
            
        Returns:
            bool: True if file hash matches stored hash
        """
        if not self.file_hash:
            return False
        
        try:
            # Use pathlib for cross-platform path handling
            safe_path = PathUtils.get_safe_path(file_path)
            
            calculated_hash = hashlib.sha256()
            with safe_path.open('rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    calculated_hash.update(chunk)
            
            return calculated_hash.hexdigest() == self.file_hash
        
        except Exception:
            return False
    
    def get_display_info(self) -> Dict[str, Any]:
        """
        Get file information for display in UI.
        
        Returns:
            dict: Display-friendly file information
        """
        return {
            'filename': self.filename,
            'filesize': self.filesize,
            'filesize_mb': round(self.filesize / (1024 * 1024), 2),
            'uploader_id': self.uploader_id,
            'upload_time': self.upload_time,
            'file_id': self.file_id,
            'description': self.description or ''
        }


class FileValidator:
    """Utility class for validating files before upload."""
    
    # Allowed file extensions (can be configured)
    ALLOWED_EXTENSIONS = {
        '.txt', '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg',
        '.mp3', '.wav', '.mp4', '.avi', '.mov',
        '.zip', '.rar', '.7z', '.tar', '.gz',
        '.py', '.js', '.html', '.css', '.json', '.xml',
        '.md', '.csv', '.log'
    }
    
    # Maximum file size (100MB)
    MAX_FILE_SIZE = 100 * 1024 * 1024
    
    @classmethod
    def validate_file(cls, file_path: str) -> tuple[bool, str]:
        """
        Validate a file for upload.
        
        Args:
            file_path: Path to the file to validate
            
        Returns:
            tuple: (is_valid, error_message)
        """
        try:
            # Use pathlib for cross-platform path handling
            safe_path = PathUtils.get_safe_path(file_path)
            
            # Check if file exists
            if not safe_path.exists():
                return False, "File does not exist"
            
            # Check if it's a file (not directory)
            if not safe_path.is_file():
                return False, "Path is not a file"
            
            # Check path safety
            if not PathUtils.is_path_safe(str(safe_path)):
                return False, "Unsafe file path detected"
            
            # Check file size
            file_size = safe_path.stat().st_size
            if file_size > cls.MAX_FILE_SIZE:
                return False, f"File too large (max {cls.MAX_FILE_SIZE // (1024*1024)}MB)"
            
            if file_size == 0:
                return False, "File is empty"
            
            # Check file extension
            filename = safe_path.name
            ext = safe_path.suffix.lower()
            
            if ext not in cls.ALLOWED_EXTENSIONS:
                return False, f"File type '{ext}' not allowed"
            
            # Check filename validity
            if len(filename.strip()) == 0:
                return False, "Invalid filename"
            
            # Check for dangerous characters
            dangerous_chars = ['<', '>', ':', '"', '|', '?', '*']
            if any(char in filename for char in dangerous_chars):
                return False, "Filename contains invalid characters"
            
            return True, ""
        
        except Exception as e:
            error_msg = ErrorHandler.get_platform_specific_error_message(e)
            return False, f"Error validating file: {error_msg}"
    
    @classmethod
    def get_mime_type(cls, filename: str) -> str:
        """
        Get MIME type based on file extension.
        
        Args:
            filename: Name of the file
            
        Returns:
            str: MIME type string
        """
        _, ext = os.path.splitext(filename.lower())
        
        mime_types = {
            '.txt': 'text/plain',
            '.pdf': 'application/pdf',
            '.doc': 'application/msword',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.xls': 'application/vnd.ms-excel',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            '.ppt': 'application/vnd.ms-powerpoint',
            '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.bmp': 'image/bmp',
            '.svg': 'image/svg+xml',
            '.mp3': 'audio/mpeg',
            '.wav': 'audio/wav',
            '.mp4': 'video/mp4',
            '.avi': 'video/x-msvideo',
            '.mov': 'video/quicktime',
            '.zip': 'application/zip',
            '.rar': 'application/x-rar-compressed',
            '.7z': 'application/x-7z-compressed',
            '.tar': 'application/x-tar',
            '.gz': 'application/gzip',
            '.py': 'text/x-python',
            '.js': 'application/javascript',
            '.html': 'text/html',
            '.css': 'text/css',
            '.json': 'application/json',
            '.xml': 'application/xml',
            '.md': 'text/markdown',
            '.csv': 'text/csv',
            '.log': 'text/plain'
        }
        
        return mime_types.get(ext, 'application/octet-stream')