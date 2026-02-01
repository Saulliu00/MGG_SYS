"""Log manager for CSV-based system logging with rotation and cleanup"""
import os
import csv
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import threading
from app.config.logging_config import (
    LOG_DIR,
    CSV_HEADERS,
    LOG_ROTATION,
    LOG_RETENTION,
    get_current_log_filepath,
    get_current_log_filename
)


class LogManager:
    """Manages CSV-based system logging with rotation and automatic cleanup"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        """Singleton pattern to ensure only one log manager instance"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(LogManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the log manager"""
        if not hasattr(self, 'initialized'):
            self.initialized = True
            self.log_dir = Path(LOG_DIR)
            self.log_dir.mkdir(parents=True, exist_ok=True)
            self.current_log_file = None
            self._ensure_log_file_exists()

    def _ensure_log_file_exists(self):
        """Ensure current log file exists with headers"""
        log_filepath = get_current_log_filepath()

        if not os.path.exists(log_filepath):
            # Create new log file with headers
            with open(log_filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
                writer.writeheader()

        self.current_log_file = log_filepath

    def _get_log_entry_dict(
        self,
        level: str,
        message: str,
        username: Optional[str] = None,
        user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        method: Optional[str] = None,
        endpoint: Optional[str] = None,
        path: Optional[str] = None,
        status_code: Optional[int] = None,
        duration_ms: Optional[float] = None,
        action: Optional[str] = None,
        error: Optional[str] = None,
        traceback: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> Dict:
        """
        Create a log entry dictionary.

        Args:
            level: Log level (INFO, WARNING, ERROR, CRITICAL)
            message: Log message
            username: Username (if authenticated)
            user_id: User ID (if authenticated)
            ip_address: Client IP address
            method: HTTP method
            endpoint: Flask endpoint
            path: Request path
            status_code: HTTP response status code
            duration_ms: Request duration in milliseconds
            action: Action description
            error: Error message
            traceback: Error traceback
            user_agent: User agent string
            request_id: Unique request ID

        Returns:
            Dict: Log entry dictionary
        """
        now = datetime.now()

        return {
            'timestamp': now.isoformat(),
            'date': now.strftime('%Y-%m-%d'),
            'time': now.strftime('%H:%M:%S'),
            'level': level,
            'username': username or '',
            'user_id': str(user_id) if user_id else '',
            'ip_address': ip_address or '',
            'method': method or '',
            'endpoint': endpoint or '',
            'path': path or '',
            'status_code': str(status_code) if status_code else '',
            'duration_ms': f'{duration_ms:.2f}' if duration_ms is not None else '',
            'action': action or '',
            'message': message or '',
            'error': error or '',
            'traceback': traceback or '',
            'user_agent': user_agent or '',
            'request_id': request_id or '',
        }

    def write_log(self, **kwargs):
        """
        Write a log entry to the current log file.

        Args:
            **kwargs: Log entry parameters (see _get_log_entry_dict)
        """
        try:
            # Ensure we're using the current log file (handles daily rotation)
            self._ensure_log_file_exists()

            # Create log entry
            log_entry = self._get_log_entry_dict(**kwargs)

            # Write to CSV file
            with open(self.current_log_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
                writer.writerow(log_entry)

            # Check if cleanup is needed
            self._check_and_cleanup()

        except Exception as e:
            # If logging fails, print to stderr but don't crash the application
            import sys
            print(f'[LOG_MANAGER ERROR] Failed to write log: {str(e)}', file=sys.stderr)

    def log_info(self, message: str, **kwargs):
        """Log an INFO level message"""
        self.write_log(level='INFO', message=message, **kwargs)

    def log_warning(self, message: str, **kwargs):
        """Log a WARNING level message"""
        self.write_log(level='WARNING', message=message, **kwargs)

    def log_error(self, message: str, error: Optional[str] = None, traceback: Optional[str] = None, **kwargs):
        """Log an ERROR level message"""
        self.write_log(level='ERROR', message=message, error=error, traceback=traceback, **kwargs)

    def log_critical(self, message: str, error: Optional[str] = None, traceback: Optional[str] = None, **kwargs):
        """Log a CRITICAL level message"""
        self.write_log(level='CRITICAL', message=message, error=error, traceback=traceback, **kwargs)

    def log_request(
        self,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
        username: Optional[str] = None,
        user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        endpoint: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None,
    ):
        """
        Log an HTTP request.

        Args:
            method: HTTP method
            path: Request path
            status_code: Response status code
            duration_ms: Request duration in milliseconds
            username: Username (if authenticated)
            user_id: User ID
            ip_address: Client IP
            endpoint: Flask endpoint
            user_agent: User agent
            request_id: Request ID
        """
        # Determine log level based on status code
        if status_code >= 500:
            level = 'ERROR'
            message = f'Server error: {method} {path}'
        elif status_code >= 400:
            level = 'WARNING'
            message = f'Client error: {method} {path}'
        else:
            level = 'INFO'
            message = f'Request: {method} {path}'

        self.write_log(
            level=level,
            message=message,
            username=username,
            user_id=user_id,
            ip_address=ip_address,
            method=method,
            endpoint=endpoint,
            path=path,
            status_code=status_code,
            duration_ms=duration_ms,
            user_agent=user_agent,
            request_id=request_id,
        )

    def _check_and_cleanup(self):
        """Check log folder size and cleanup old files if needed"""
        try:
            total_size = self._get_total_log_size()

            # If total size exceeds limit, remove oldest files
            if total_size > LOG_ROTATION['max_folder_size_bytes']:
                self._cleanup_old_logs(total_size)

        except Exception as e:
            import sys
            print(f'[LOG_MANAGER ERROR] Cleanup failed: {str(e)}', file=sys.stderr)

    def _get_total_log_size(self) -> int:
        """
        Get total size of all log files in bytes.

        Returns:
            int: Total size in bytes
        """
        total_size = 0
        for log_file in self.log_dir.glob('*.csv'):
            total_size += log_file.stat().st_size
        return total_size

    def _cleanup_old_logs(self, current_size: int):
        """
        Remove oldest log files until size is under limit.

        Args:
            current_size: Current total size in bytes
        """
        # Get all log files sorted by modification time (oldest first)
        log_files = sorted(
            self.log_dir.glob('*.csv'),
            key=lambda f: f.stat().st_mtime
        )

        # Calculate target size (90% of max to avoid frequent cleanups)
        target_size = int(LOG_ROTATION['max_folder_size_bytes'] * 0.9)

        # Remove oldest files until we're under target size
        for log_file in log_files:
            # Don't delete the current log file
            if str(log_file) == self.current_log_file:
                continue

            # Check if file is old enough to delete based on retention policy
            file_age_days = (datetime.now() - datetime.fromtimestamp(log_file.stat().st_mtime)).days

            if file_age_days < LOG_RETENTION.get('keep_days', 90):
                # Don't delete files newer than retention period
                continue

            # Delete the file
            file_size = log_file.stat().st_size
            log_file.unlink()
            current_size -= file_size

            # Log the deletion
            self.log_info(
                f'Deleted old log file: {log_file.name}',
                action='log_cleanup'
            )

            # Stop if we're under target size
            if current_size <= target_size:
                break

    def get_log_files(self) -> List[Dict]:
        """
        Get list of all log files with metadata.

        Returns:
            List[Dict]: List of log file information
        """
        log_files = []

        for log_file in sorted(self.log_dir.glob('*.csv'), key=lambda f: f.stat().st_mtime, reverse=True):
            stat = log_file.stat()
            log_files.append({
                'filename': log_file.name,
                'filepath': str(log_file),
                'size_bytes': stat.st_size,
                'size_mb': round(stat.st_size / (1024 * 1024), 2),
                'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                'is_current': str(log_file) == self.current_log_file,
            })

        return log_files

    def read_log_file(self, filename: Optional[str] = None, max_rows: int = 1000) -> List[Dict]:
        """
        Read a log file and return entries.

        Args:
            filename: Log filename (defaults to current log file)
            max_rows: Maximum number of rows to return

        Returns:
            List[Dict]: List of log entries
        """
        if filename:
            filepath = self.log_dir / filename
        else:
            filepath = Path(self.current_log_file)

        if not filepath.exists():
            return []

        entries = []

        with open(filepath, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                entries.append(row)
                if len(entries) >= max_rows:
                    break

        # Return in reverse order (newest first)
        return list(reversed(entries))

    def get_log_statistics(self) -> Dict:
        """
        Get statistics about the log system.

        Returns:
            Dict: Log statistics
        """
        total_size = self._get_total_log_size()
        log_files = self.get_log_files()

        return {
            'total_files': len(log_files),
            'total_size_bytes': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'total_size_gb': round(total_size / (1024 * 1024 * 1024), 2),
            'max_size_gb': LOG_ROTATION['max_folder_size_gb'],
            'usage_percent': round((total_size / LOG_ROTATION['max_folder_size_bytes']) * 100, 2),
            'current_log_file': get_current_log_filename(),
            'oldest_log': log_files[-1]['filename'] if log_files else None,
            'newest_log': log_files[0]['filename'] if log_files else None,
        }


# Global singleton instance
log_manager = LogManager()
