#!/usr/bin/env python
"""
PIN-based Secure Cache Utility for Nest

Provides PIN-protected encrypted data caching for sensitive customer information.
This module ensures that cached data can only be accessed with a valid employee PIN,
adding an additional layer of security beyond filesystem permissions.
"""

import os
import json
import time
import logging
from typing import Dict, List, Any, Tuple, Optional
from .pin_encryption import PinEncryption
from .access_security import AccessSecurity

# Configure logging
logger = logging.getLogger(__name__)


class PinSecureCache:
    """Provides PIN-protected encrypted cache functionality.
    
    Uses employee PINs for encryption key derivation, ensuring that 
    cached data can only be accessed with a valid PIN. This prevents
    unauthorized access even if cache files are directly accessed.
    """
    
    def __init__(self, cache_dir: Optional[str] = None, ttl_hours: int = 24, 
                 max_attempts: int = 5, lockout_minutes: int = 15):
        """Initialize the PIN-secure cache.
        
        Args:
            cache_dir: Directory to store cache files
            ttl_hours: Time-to-live for cache entries in hours
            max_attempts: Maximum failed PIN attempts before lockout
            lockout_minutes: Lockout duration in minutes after failed attempts
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
        
        # Create security directory for salt storage
        security_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "security")
        os.makedirs(security_dir, exist_ok=True)
        
        # Cache TTL in seconds
        self.ttl = ttl_hours * 3600
        
        # Initialize PIN-based encryption
        self.pin_encryption = PinEncryption(security_dir)
        
        # Initialize access security (fail2ban-like functionality)
        self.access_security = AccessSecurity(
            security_dir=security_dir,
            max_attempts=max_attempts,
            lockout_minutes=lockout_minutes
        )
    
    def save(self, pin: str, filename: str, data: Any, username: str = "default", ip_addr: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """Save data to PIN-protected encrypted cache file.
        
        Args:
            pin: Employee PIN for encryption
            filename: Cache filename (without path)
            data: Data to cache (must be JSON serializable)
            username: Username associated with the PIN (for tracking attempts)
            ip_addr: IP address of the client (optional)
            
        Returns:
            Tuple of (success, error_message)
            If save is successful, error_message will be None
        """
        if not pin:
            error_msg = "Cannot save to cache: No PIN provided"
            self.logger.error(error_msg)
            return False, error_msg
        
        # Verify PIN with fail2ban/rate limiting before allowing save
        is_valid, error_msg = self.verify_pin(pin, username, ip_addr)
        if not is_valid:
            return False, error_msg
            
        try:
            # Prepare cache data with timestamp
            cache_data = {
                "timestamp": time.time(),
                "data": data
            }
            
            # Convert to JSON string
            json_data = json.dumps(cache_data)
            
            # Encrypt the data using PIN
            encrypted_data = self.pin_encryption.encrypt(pin, json_data)
            if encrypted_data is None:
                error_msg = "Failed to encrypt cache data"
                self.logger.error(error_msg)
                return False, error_msg
                
            # Save to file
            cache_path = os.path.join(self.cache_dir, filename)
            with open(cache_path, "w") as f:
                f.write(encrypted_data)
                
            self.logger.info(f"Saved PIN-encrypted cache to {filename}")
            return True, None
            
        except Exception as e:
            error_msg = f"Failed to save PIN-encrypted cache: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg
    
    def load(self, pin: str, filename: str, username: str = "default", ip_addr: Optional[str] = None) -> Tuple[bool, Any, Optional[str]]:
        """Load data from PIN-protected encrypted cache file if not expired.
        
        Args:
            pin: Employee PIN for decryption
            filename: Cache filename (without path)
            username: Username associated with the PIN (for tracking attempts)
            ip_addr: IP address of the client (optional)
            
        Returns:
            Tuple of (success, data, error_message)
            If cache is missing, expired, or PIN is incorrect, success will be False
            and error_message will contain the reason
        """
        if not pin:
            error_msg = "Cannot load cache: No PIN provided"
            self.logger.error(error_msg)
            return False, None, error_msg
        
        # Check if the user is locked out or rate limited
        is_valid, error_msg = self.verify_pin(pin, username, ip_addr)
        if not is_valid:
            return False, None, error_msg
            
        cache_path = os.path.join(self.cache_dir, filename)
        
        if not os.path.exists(cache_path):
            error_msg = f"Cache file {filename} does not exist"
            self.logger.debug(error_msg)
            return False, None, error_msg
            
        try:
            # Read encrypted data
            with open(cache_path, "r") as f:
                encrypted_data = f.read()
                
            # Decrypt the data using PIN
            json_data = self.pin_encryption.decrypt(pin, encrypted_data)
            if json_data is None:
                # Record failed PIN attempt
                self.access_security.record_attempt(username, False, ip_addr)
                error_msg = "Failed to decrypt cache with provided PIN"
                self.logger.warning(error_msg)
                return False, None, error_msg
                
            # Parse JSON
            cache_data = json.loads(json_data)
            
            # Check if cache is expired
            timestamp = cache_data["timestamp"]
            if time.time() - timestamp > self.ttl:
                error_msg = f"Cache file {filename} is expired"
                self.logger.debug(error_msg)
                return False, None, error_msg
            
            # Record successful PIN attempt
            self.access_security.record_success(username, ip_addr)
                
            # Return the data
            self.logger.debug(f"Loaded data from PIN-encrypted cache {filename}")
            return True, cache_data["data"], None
            
        except Exception as e:
            error_msg = f"Failed to load PIN-encrypted cache: {str(e)}"
            self.logger.error(error_msg)
            return False, None, error_msg
    
    def clear(self, filename: Optional[str] = None) -> bool:
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
                    self.logger.debug(f"Cleared PIN-encrypted cache file: {filename}")
            else:
                # Delete all cache files except security-related ones
                for file in os.listdir(self.cache_dir):
                    if not file.startswith("."):  # Don't delete hidden files like .cache_key
                        os.remove(os.path.join(self.cache_dir, file))
                self.logger.debug("Cleared all PIN-encrypted cache files")
                
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to clear PIN-encrypted cache: {e}")
            return False
            
    def verify_pin(self, pin: str, username: str = "default", ip_addr: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """Verify if a PIN is valid for encryption/decryption.
        
        Args:
            pin: Employee PIN to verify
            username: Username associated with the PIN (for tracking attempts)
            ip_addr: IP address of the client (optional)
            
        Returns:
            Tuple of (is_valid, error_message)
            If PIN is valid, error_message will be None
        """
        # First check if the user is locked out
        is_locked, seconds_remaining = self.access_security.is_locked(username)
        if is_locked:
            minutes = int(seconds_remaining / 60)
            seconds = int(seconds_remaining % 60)
            error_msg = f"Account is locked due to too many failed attempts. Try again in {minutes}m {seconds}s."
            return False, error_msg
            
        # Check if rate limited
        is_limited, attempts_remaining = self.access_security.is_rate_limited(username, ip_addr)
        if is_limited:
            error_msg = f"Too many PIN attempts too quickly. Try again soon."
            return False, error_msg
        
        # Verify the PIN
        is_valid = self.pin_encryption.verify_pin(pin)
        
        # Record the attempt
        self.access_security.record_attempt(username, is_valid, ip_addr)
        
        if is_valid:
            return True, None
        else:
            error_msg = "Invalid PIN"
            return False, error_msg
    
    def validate_pin_fields(self, data):
        """Validate that PIN-related fields are present and properly formatted with enhanced security."""
        if not isinstance(data, dict):
            logging.warning("PIN validation failed: data is not a dictionary")
            return False
        
        pin_fields = ['pin', 'PIN', 'access_pin', 'security_pin', 'user_pin']
        valid_pin_found = False
        
        for field in pin_fields:
            if field in data:
                pin_value = data[field]
                if isinstance(pin_value, (str, int)):
                    pin_str = str(pin_value).strip()
                    if pin_str.isdigit() and 4 <= len(pin_str) <= 8:
                        if not self._is_weak_pin(pin_str):
                            valid_pin_found = True
                            break
                        else:
                            logging.warning(f"Weak PIN detected in field '{field}'")
                    else:
                        logging.warning(f"Invalid PIN format in field '{field}': length or format invalid")
                else:
                    logging.warning(f"Invalid PIN type in field '{field}': {type(pin_value)}")
        
        if not valid_pin_found:
            logging.warning("No valid PIN fields found in secure data")
            return False
        
        return True
    
    def _is_weak_pin(self, pin_str: str) -> bool:
        """Check if PIN is weak (sequential numbers, repeated digits, common patterns)."""
        if len(set(pin_str)) == 1:
            return True
        
        if len(pin_str) >= 4:
            ascending = all(int(pin_str[i]) == int(pin_str[i-1]) + 1 for i in range(1, len(pin_str)))
            descending = all(int(pin_str[i]) == int(pin_str[i-1]) - 1 for i in range(1, len(pin_str)))
            if ascending or descending:
                return True
        
        weak_pins = {'0000', '1111', '2222', '3333', '4444', '5555', '6666', '7777', '8888', '9999',
                     '1234', '4321', '0123', '3210', '1122', '2211'}
        if pin_str in weak_pins:
            return True
        
        return False
            
    def secure_test_data(self, test_data: str = "test-data") -> Tuple[bool, Optional[str]]:
        """Test if the PIN-based encryption system is working properly.
        
        Args:
            test_data: Test data to encrypt and decrypt
            
        Returns:
            Tuple of (success, error_message)
            If test succeeds, error_message will be None
        """
        try:
            # Use a test PIN with a special test username that bypasses rate limiting
            test_pin = "1234"
            test_username = "_system_test_"
            
            # Temporarily unlock the test account if it's locked
            self.access_security.unlock(test_username)
            
            # Test encryption and decryption
            encrypted = self.pin_encryption.encrypt(test_pin, test_data)
            if not encrypted:
                return False, "Encryption failed"
                
            decrypted = self.pin_encryption.decrypt(test_pin, encrypted)
            
            # Check if decryption succeeded
            if decrypted == test_data:
                return True, None
            else:
                return False, "Decryption result doesn't match original data"
            
        except Exception as e:
            return False, f"Test failed with error: {str(e)}"
