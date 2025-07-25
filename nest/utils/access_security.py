#!/usr/bin/env python
"""
Access Security Module for Nest

This module provides fail2ban-like functionality and rate limiting
for PIN-based authentication attempts. It keeps track of failed access
attempts and temporarily locks accounts when threshold is exceeded.
"""

import os
import time
import json
import logging
import threading
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta

# Configure logging
logger = logging.getLogger(__name__)

# Default security settings
DEFAULT_MAX_ATTEMPTS = 5  # Maximum failed attempts before lockout
DEFAULT_LOCKOUT_MINUTES = 15  # Lockout duration in minutes
DEFAULT_RATE_LIMIT_ATTEMPTS = 3  # Number of attempts allowed in rate limit period
DEFAULT_RATE_LIMIT_SECONDS = 60  # Rate limit period in seconds
DEFAULT_CLEANUP_INTERVAL = 3600  # Cleanup interval in seconds (1 hour)

class AccessSecurity:
    """
    Implements fail2ban-like functionality and rate limiting.
    
    Tracks PIN authentication attempts, locks accounts after too many failed attempts,
    and implements rate limiting to prevent brute force attacks.
    """
    
    def __init__(self, 
                 security_dir: Optional[str] = None,
                 max_attempts: int = DEFAULT_MAX_ATTEMPTS,
                 lockout_minutes: int = DEFAULT_LOCKOUT_MINUTES,
                 rate_limit_attempts: int = DEFAULT_RATE_LIMIT_ATTEMPTS,
                 rate_limit_seconds: int = DEFAULT_RATE_LIMIT_SECONDS):
        """
        Initialize the access security.
        
        Args:
            security_dir: Directory to store security data
            max_attempts: Maximum failed attempts before lockout
            lockout_minutes: Lockout duration in minutes
            rate_limit_attempts: Number of attempts allowed in rate limit period
            rate_limit_seconds: Rate limit period in seconds
        """
        self.logger = logging.getLogger(__name__)
        
        # Set up security directory
        if security_dir is None:
            # Default to nest/security directory
            self.security_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "security")
        else:
            self.security_dir = security_dir
            
        # Create security directory if it doesn't exist
        os.makedirs(self.security_dir, exist_ok=True)
        
        # Security configuration
        self.max_attempts = max_attempts
        self.lockout_minutes = lockout_minutes
        self.rate_limit_attempts = rate_limit_attempts
        self.rate_limit_seconds = rate_limit_seconds
        
        # Path to security data file
        self.security_file = os.path.join(self.security_dir, "access_security.json")
        
        # In-memory storage for tracking attempts
        self._failed_attempts = {}  # {username: [(timestamp, ip_addr), ...]}
        self._locked_until = {}     # {username: unlock_timestamp}
        self._rate_limit = {}       # {username: [(timestamp, ip_addr), ...]}
        
        # Thread lock for synchronization
        self._lock = threading.RLock()
        
        # Load existing security data
        self._load_security_data()
        
        # Start cleanup thread
        self._start_cleanup_thread()
    
    def _load_security_data(self) -> None:
        """Load security data from file."""
        with self._lock:
            try:
                if os.path.exists(self.security_file):
                    with open(self.security_file, 'r') as f:
                        data = json.load(f)
                        
                    # Convert timestamps back to float
                    self._failed_attempts = {k: [(t, ip) for t, ip in v] 
                                            for k, v in data.get('failed_attempts', {}).items()}
                    self._locked_until = {k: float(v) for k, v in data.get('locked_until', {}).items()}
                    self._rate_limit = {k: [(float(t), ip) for t, ip in v] 
                                       for k, v in data.get('rate_limit', {}).items()}
                    
                    self.logger.debug("Loaded security data from file")
            except Exception as e:
                self.logger.error(f"Failed to load security data: {e}")
                # Initialize as empty if loading fails
                self._failed_attempts = {}
                self._locked_until = {}
                self._rate_limit = {}
    
    def _save_security_data(self) -> None:
        """Save security data to file with enhanced security and proper permissions."""
        with self._lock:
            try:
                # Ensure the directory exists with secure permissions
                security_dir = os.path.dirname(self.security_file)
                os.makedirs(security_dir, exist_ok=True)
                
                if hasattr(os, 'chmod'):
                    os.chmod(security_dir, 0o700)
                
                temp_file = self.security_file + '.tmp'
                
                data = {
                    'failed_attempts': self._failed_attempts,
                    'locked_until': self._locked_until,
                    'rate_limit': self._rate_limit
                }
                
                with open(temp_file, 'w') as f:
                    json.dump(data, f)
                
                if hasattr(os, 'chmod'):
                    os.chmod(temp_file, 0o600)
                
                if hasattr(os, 'replace'):
                    os.replace(temp_file, self.security_file)
                else:
                    if os.path.exists(self.security_file):
                        os.remove(self.security_file)
                    os.rename(temp_file, self.security_file)
                
                # Verify final file permissions
                if hasattr(os, 'chmod'):
                    os.chmod(self.security_file, 0o600)
                    
                self.logger.debug("Security data saved securely to file")
            except Exception as e:
                self.logger.error(f"Failed to save security data: {e}")
                temp_file = self.security_file + '.tmp'
                if os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                    except:
                        pass
    
    def _cleanup_expired_entries(self) -> None:
        """Remove expired entries from tracking dictionaries."""
        with self._lock:
            current_time = time.time()
            
            # Clear expired lockouts
            expired_locks = [username for username, unlock_time in self._locked_until.items() 
                           if unlock_time <= current_time]
            for username in expired_locks:
                del self._locked_until[username]
                self.logger.info(f"Lockout expired for '{username}'")
            
            # Cleanup failed attempts older than lockout period
            cutoff = current_time - (self.lockout_minutes * 60)
            for username in list(self._failed_attempts.keys()):
                self._failed_attempts[username] = [
                    (t, ip) for t, ip in self._failed_attempts[username] 
                    if t >= cutoff
                ]
                if not self._failed_attempts[username]:
                    del self._failed_attempts[username]
            
            # Cleanup rate limit attempts older than rate limit period
            cutoff = current_time - self.rate_limit_seconds
            for username in list(self._rate_limit.keys()):
                self._rate_limit[username] = [
                    (t, ip) for t, ip in self._rate_limit[username] 
                    if t >= cutoff
                ]
                if not self._rate_limit[username]:
                    del self._rate_limit[username]
            
            # Save cleaned-up data
            self._save_security_data()
    
    def _cleanup_thread_func(self) -> None:
        """Background thread function to periodically clean up expired entries."""
        while True:
            time.sleep(DEFAULT_CLEANUP_INTERVAL)
            try:
                self._cleanup_expired_entries()
            except Exception as e:
                self.logger.error(f"Error in cleanup thread: {e}")
    
    def _start_cleanup_thread(self) -> None:
        """Start a background thread to clean up expired entries."""
        cleanup_thread = threading.Thread(
            target=self._cleanup_thread_func, 
            daemon=True,
            name="AccessSecurityCleanup"
        )
        cleanup_thread.start()
    
    def is_locked(self, username: str) -> Tuple[bool, float]:
        """
        Check if a user account is currently locked.
        
        Args:
            username: Username to check
            
        Returns:
            Tuple of (is_locked, seconds_remaining)
        """
        with self._lock:
            self._cleanup_expired_entries()
            
            if username in self._locked_until:
                unlock_time = self._locked_until[username]
                current_time = time.time()
                
                if current_time < unlock_time:
                    return True, unlock_time - current_time
            
            return False, 0
    
    def is_rate_limited(self, username: str, ip_addr: Optional[str] = None) -> Tuple[bool, int]:
        """
        Check if a user is currently rate limited.
        
        Args:
            username: Username to check
            ip_addr: IP address (optional)
            
        Returns:
            Tuple of (is_limited, attempts_remaining)
        """
        with self._lock:
            current_time = time.time()
            cutoff = current_time - self.rate_limit_seconds
            
            # Get recent attempts within rate limit window
            recent_attempts = 0
            if username in self._rate_limit:
                recent_attempts = sum(1 for t, _ in self._rate_limit[username] if t >= cutoff)
            
            # Check if rate limited
            if recent_attempts >= self.rate_limit_attempts:
                return True, 0
            else:
                return False, self.rate_limit_attempts - recent_attempts
    
    def record_success(self, username: str, ip_addr: Optional[str] = None) -> None:
        """
        Record a successful authentication.
        
        Args:
            username: Username that succeeded authentication
            ip_addr: IP address (optional)
        """
        with self._lock:
            # Clear failed attempts on success
            if username in self._failed_attempts:
                del self._failed_attempts[username]
                self._save_security_data()
    
    def record_attempt(self, username: str, success: bool, ip_addr: Optional[str] = None) -> Tuple[bool, Optional[float]]:
        """
        Record an authentication attempt and check if account should be locked.
        
        Args:
            username: Username that attempted authentication
            success: Whether the attempt was successful
            ip_addr: IP address (optional)
            
        Returns:
            Tuple of (is_locked, seconds_remaining)
        """
        with self._lock:
            current_time = time.time()
            
            # Add to rate limit tracking regardless of success/failure
            if username not in self._rate_limit:
                self._rate_limit[username] = []
            self._rate_limit[username].append((current_time, ip_addr))
            
            # If success, clear failed attempts
            if success:
                if username in self._failed_attempts:
                    del self._failed_attempts[username]
                if username in self._locked_until:
                    del self._locked_until[username]
                self._save_security_data()
                return False, None
            
            # Handle failed attempt
            if username not in self._failed_attempts:
                self._failed_attempts[username] = []
            self._failed_attempts[username].append((current_time, ip_addr))
            
            # Check if we should lock the account
            recent_failures = len(self._failed_attempts[username])
            if recent_failures >= self.max_attempts:
                # Lock the account
                unlock_time = current_time + (self.lockout_minutes * 60)
                self._locked_until[username] = unlock_time
                self.logger.warning(f"Locked account '{username}' for {self.lockout_minutes} minutes due to {recent_failures} failed attempts")
                
                # Save security data
                self._save_security_data()
                return True, unlock_time - current_time
            
            # Save security data
            self._save_security_data()
            return False, None
    
    def unlock(self, username: str) -> bool:
        """
        Manually unlock a user account.
        
        Args:
            username: Username to unlock
            
        Returns:
            True if account was unlocked, False if it wasn't locked
        """
        with self._lock:
            if username in self._locked_until:
                del self._locked_until[username]
                if username in self._failed_attempts:
                    del self._failed_attempts[username]
                self._save_security_data()
                self.logger.info(f"Manually unlocked account '{username}'")
                return True
            return False
