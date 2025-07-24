#!/usr/bin/env python
"""
Secure Cache Utility for Nest

Provides encrypted data caching using Fernet symmetric encryption.
This module is used to securely store sensitive data like customer
information in local cache files with proper encryption.
"""

import os
import json
import time
import base64
import logging
from typing import Dict, List, Any, Tuple, Optional
from cryptography.fernet import Fernet

# Configure logging
logger = logging.getLogger(__name__)

class SecureCache:
    """Provides encrypted cache functionality for sensitive data.
    
    Uses Fernet symmetric encryption to store data securely on disk.
    Cache entries include timestamps for automatic expiration.
    """
    
    def __init__(self, cache_dir: str = None, ttl_hours: int = 24):
        """Initialize the secure cache.
        
        Args:
            cache_dir: Directory to store cache files (defaults to app's cache directory)
            ttl_hours: Time-to-live for cache entries in hours
        """
        self.logger = logging.getLogger(__name__)
        
        # Set up cache directory
        if cache_dir is None:
            # Default to nest/cache directory
            self.cache_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cache")
        else:
            self.cache_dir = cache_dir
            
        # Create cache directory if it doesn't exist
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Cache TTL in seconds
        self.ttl = ttl_hours * 3600
        
        # Initialize encryption
        self._init_encryption()
    
    def _init_encryption(self):
        """Initialize Fernet encryption for secure storage."""
        key_file = os.path.join(self.cache_dir, ".cache_key")
        
        try:
            # Get or create encryption key
            if os.path.exists(key_file):
                with open(key_file, "rb") as f:
                    key = f.read()
            else:
                # Generate a new key if none exists
                key = Fernet.generate_key()
                with open(key_file, "wb") as f:
                    f.write(key)
                # Secure the key file (0600 permissions)
                try:
                    os.chmod(key_file, 0o600)
                except Exception as e:
                    self.logger.warning(f"Could not set secure permissions on key file: {e}")
            
            # Initialize Fernet with the key
            self._fernet = Fernet(key)
            self.logger.debug("Encryption initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize encryption: {e}")
            self._fernet = None
    
    def _encrypt(self, data_str: str) -> str:
        """Encrypt data string using Fernet.
        
        Args:
            data_str: JSON string to encrypt
            
        Returns:
            Base64-encoded encrypted data
        """
        if not self._fernet:
            raise ValueError("Encryption not initialized")
            
        encrypted = self._fernet.encrypt(data_str.encode())
        return base64.b64encode(encrypted).decode()
    
    def _decrypt(self, encrypted_str: str) -> str:
        """Decrypt encrypted data string.
        
        Args:
            encrypted_str: Base64-encoded encrypted data
            
        Returns:
            Decrypted JSON string
        """
        if not self._fernet:
            raise ValueError("Encryption not initialized")
            
        encrypted = base64.b64decode(encrypted_str)
        return self._fernet.decrypt(encrypted).decode()
    
    def save(self, filename: str, data: Any) -> bool:
        """Save data to encrypted cache file.
        
        Args:
            filename: Cache filename (without path)
            data: Data to cache (must be JSON serializable)
            
        Returns:
            True if saved successfully, False otherwise
        """
        if not self._fernet:
            self.logger.error("Cannot save to cache: encryption not initialized")
            return False
            
        try:
            # Prepare cache data with timestamp
            cache_data = {
                "timestamp": time.time(),
                "data": data
            }
            
            # Convert to JSON string
            json_data = json.dumps(cache_data)
            
            # Encrypt the data
            encrypted_data = self._encrypt(json_data)
            
            # Save to file
            cache_path = os.path.join(self.cache_dir, filename)
            with open(cache_path, "w") as f:
                f.write(encrypted_data)
                
            self.logger.info(f"Saved encrypted cache to {filename}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save cache: {e}")
            return False
    
    def load(self, filename: str) -> Tuple[bool, Any]:
        """Load data from encrypted cache file if not expired.
        
        Args:
            filename: Cache filename (without path)
            
        Returns:
            Tuple of (success, data)
            If cache is missing or expired, success will be False
        """
        cache_path = os.path.join(self.cache_dir, filename)
        
        if not os.path.exists(cache_path):
            self.logger.debug(f"Cache file {filename} does not exist")
            return False, None
            
        try:
            # Read encrypted data
            with open(cache_path, "r") as f:
                encrypted_data = f.read()
                
            # Decrypt the data
            json_data = self._decrypt(encrypted_data)
            
            # Parse JSON
            cache_data = json.loads(json_data)
            
            # Check if cache is expired
            timestamp = cache_data["timestamp"]
            if time.time() - timestamp > self.ttl:
                self.logger.debug(f"Cache file {filename} is expired")
                return False, None
                
            # Return the data
            self.logger.debug(f"Loaded data from encrypted cache {filename}")
            return True, cache_data["data"]
            
        except Exception as e:
            self.logger.error(f"Failed to load cache: {e}")
            return False, None
    
    def clear(self, filename: str = None) -> bool:
        """Clear specific cache file or all cache files.
        
        Args:
            filename: Specific cache file to clear (or None for all)
            
        Returns:
            True if cleared successfully, False otherwise
        """
        try:
            if filename:
                # Delete specific cache file
                cache_path = os.path.join(self.cache_dir, filename)
                if os.path.exists(cache_path):
                    os.remove(cache_path)
                    self.logger.debug(f"Cleared cache file: {filename}")
            else:
                # Delete all cache files except the key file
                for file in os.listdir(self.cache_dir):
                    if file != ".cache_key":
                        os.remove(os.path.join(self.cache_dir, file))
                self.logger.debug("Cleared all cache files")
                
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to clear cache: {e}")
            return False
