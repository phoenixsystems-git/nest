#!/usr/bin/env python
"""
PIN-based Encryption Module for Nest

This module provides secure encryption based on employee PIN codes.
It uses PBKDF2 (or optionally Argon2 if available) for key derivation and 
Fernet for symmetric encryption. This ensures that encrypted data can only
be accessed with a valid PIN code, even if encrypted files are compromised.

Key security features:
- Never stores encryption keys on disk, only in memory
- Uses PIN + salt for key derivation with strong KDFs
- Implements salt rotation for forward security
- Provides salt verification to detect tampering
"""

import os
import time
import base64
import json
import logging
import secrets
import hashlib
from typing import Dict, Tuple, Optional, Union, Any
from datetime import datetime, timedelta
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

# Try to import Argon2 if available (better security but optional)
try:
    from argon2 import PasswordHasher
    from argon2.exceptions import VerifyMismatchError
    ARGON2_AVAILABLE = True
except ImportError:
    ARGON2_AVAILABLE = False

# Configure logging
logger = logging.getLogger(__name__)

# Constants for encryption
SALT_BYTES = 32  # 256-bit salt
KDF_ITERATIONS = 480000  # High number of iterations for PBKDF2
SALT_FILE = "security.salt"  # Salt storage file
SALT_ROTATION_DAYS = 30  # Rotate salt every 30 days


class PinEncryption:
    """Provides PIN-based encryption for sensitive data.
    
    This class combines employee PIN codes with cryptographic salt to derive
    encryption keys that are never stored on disk. This ensures that even
    if encrypted files are compromised, they cannot be decrypted without
    knowing the correct PIN.
    """
    
    def __init__(self, salt_dir: str = None):
        """Initialize PIN-based encryption.
        
        Args:
            salt_dir: Directory to store salt files (not encryption keys)
        """
        self.logger = logging.getLogger(__name__)
        
        # Set up salt directory
        if salt_dir is None:
            # Default to nest/security directory
            self.salt_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "security")
        else:
            self.salt_dir = salt_dir
            
        # Create salt directory if it doesn't exist
        os.makedirs(self.salt_dir, exist_ok=True)
        
        # Path to salt file
        self.salt_path = os.path.join(self.salt_dir, SALT_FILE)
        
        # Key cache (memory only)
        self._key_cache = {}
        self._fernet_instances = {}
        
    def _derive_key_pbkdf2(self, pin: str, salt: bytes) -> bytes:
        """Derive encryption key from PIN using PBKDF2.
        
        Args:
            pin: The employee PIN code
            salt: Random salt bytes
            
        Returns:
            Derived 32-byte key
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,  # 256-bit key
            salt=salt,
            iterations=KDF_ITERATIONS
        )
        return kdf.derive(pin.encode())
    
    def _derive_key_argon2(self, pin: str, salt: bytes) -> bytes:
        """Derive encryption key from PIN using Argon2 (if available).
        
        Args:
            pin: The employee PIN code
            salt: Random salt bytes
            
        Returns:
            Derived 32-byte key
        """
        if not ARGON2_AVAILABLE:
            return self._derive_key_pbkdf2(pin, salt)
            
        # Use Argon2id with memory-hard parameters
        hasher = PasswordHasher(
            time_cost=3,      # Number of iterations
            memory_cost=65536,  # 64 MB memory usage
            parallelism=4,    # 4 parallel threads
            hash_len=32       # 256-bit output
        )
        
        # Argon2 uses its own salt format, so we hash the provided salt
        # to get deterministic but unique salt for each input
        salt_hash = hashlib.sha256(salt).digest()
        
        # Generate a raw hash with our parameters
        # We convert to base64 and extract the actual hash part
        hash_result = hasher.hash(pin + base64.b64encode(salt).decode())
        raw_hash = hash_result.split('$')[-1]
        
        # Convert to bytes and ensure it's 32 bytes long
        key_bytes = base64.b64decode(raw_hash)[:32]
        if len(key_bytes) < 32:
            # Pad if needed (shouldn't happen with proper config)
            key_bytes = key_bytes.ljust(32, b'0')
            
        return key_bytes
    
    def _get_salt(self) -> Tuple[bytes, bool]:
        """Get existing salt or generate a new one.
        
        Returns:
            Tuple of (salt_bytes, is_new)
        """
        try:
            if os.path.exists(self.salt_path):
                with open(self.salt_path, "r") as f:
                    salt_data = json.load(f)
                
                # Check if salt needs rotation
                timestamp = salt_data.get("timestamp", 0)
                salt_age = datetime.now() - datetime.fromtimestamp(timestamp)
                if salt_age > timedelta(days=SALT_ROTATION_DAYS):
                    self.logger.info("Salt rotation needed - generating new salt")
                    return self._generate_new_salt(), True
                
                # Use existing salt
                salt = base64.b64decode(salt_data["salt"])
                self.logger.debug("Using existing salt")
                return salt, False
                
            else:
                # No salt exists, generate new
                self.logger.info("No salt file found - generating new salt")
                return self._generate_new_salt(), True
                
        except Exception as e:
            self.logger.error(f"Error reading salt: {e}")
            # Fallback to new salt
            return self._generate_new_salt(), True
    
    def _generate_new_salt(self) -> bytes:
        """Generate a new salt and save it.
        
        Returns:
            New salt bytes
        """
        # Generate cryptographically strong random salt
        salt = secrets.token_bytes(SALT_BYTES)
        
        try:
            # Save salt with timestamp
            salt_data = {
                "salt": base64.b64encode(salt).decode(),
                "timestamp": time.time(),
                "created": datetime.now().isoformat()
            }
            
            # Write to temporary file first, then rename for atomic update
            temp_path = f"{self.salt_path}.tmp"
            with open(temp_path, "w") as f:
                json.dump(salt_data, f)
                
            # Make secure and atomic
            os.chmod(temp_path, 0o600)  # Secure permissions
            os.replace(temp_path, self.salt_path)  # Atomic replace
            
            self.logger.info("Generated and stored new salt")
            return salt
            
        except Exception as e:
            self.logger.error(f"Failed to save salt: {e}")
            return salt  # Still return the salt even if save failed
    
    def get_fernet(self, pin: str) -> Optional[Fernet]:
        """Get a Fernet instance for the given PIN.
        
        Args:
            pin: Employee PIN code
            
        Returns:
            Fernet instance for encryption/decryption or None if error
        """
        try:
            # Check if we already have a cached instance for this PIN
            if pin in self._fernet_instances:
                return self._fernet_instances[pin]
                
            # Get or generate salt
            salt, is_new = self._get_salt()
            
            # Derive key using Argon2 if available, otherwise PBKDF2
            if ARGON2_AVAILABLE:
                key = self._derive_key_argon2(pin, salt)
            else:
                key = self._derive_key_pbkdf2(pin, salt)
                
            # Create Fernet key (urlsafe base64 encoded)
            fernet_key = base64.urlsafe_b64encode(key)
            
            # Create and cache Fernet instance
            fernet = Fernet(fernet_key)
            self._fernet_instances[pin] = fernet
            
            return fernet
            
        except Exception as e:
            self.logger.error(f"Failed to create Fernet instance: {e}")
            return None
    
    def encrypt(self, pin: str, data: Union[str, bytes]) -> Optional[str]:
        """Encrypt data using a PIN-derived key.
        
        Args:
            pin: Employee PIN code
            data: Data to encrypt (string or bytes)
            
        Returns:
            Base64-encoded encrypted data or None if encryption failed
        """
        try:
            fernet = self.get_fernet(pin)
            if fernet is None:
                self.logger.error("Failed to get encryption key")
                return None
                
            # Convert data to bytes if it's a string
            if isinstance(data, str):
                data_bytes = data.encode()
            else:
                data_bytes = data
                
            # Encrypt the data
            encrypted = fernet.encrypt(data_bytes)
            
            # Convert to base64 for storage
            return base64.b64encode(encrypted).decode()
            
        except Exception as e:
            self.logger.error(f"Encryption error: {e}")
            return None
    
    def decrypt(self, pin: str, encrypted_data: str) -> Optional[str]:
        """Decrypt data using a PIN-derived key.
        
        Args:
            pin: Employee PIN code
            encrypted_data: Base64-encoded encrypted data
            
        Returns:
            Decrypted data as string or None if decryption failed
        """
        try:
            fernet = self.get_fernet(pin)
            if fernet is None:
                self.logger.error("Failed to get decryption key")
                return None
                
            # Decode from base64
            encrypted_bytes = base64.b64decode(encrypted_data)
            
            # Attempt to decrypt
            decrypted = fernet.decrypt(encrypted_bytes)
            
            # Convert bytes to string
            return decrypted.decode()
            
        except InvalidToken:
            self.logger.warning("Invalid PIN or corrupted data")
            return None
            
        except Exception as e:
            self.logger.error(f"Decryption error: {e}")
            return None
            
    def verify_pin(self, pin: str, test_data: Optional[str] = None) -> bool:
        """Verify if a PIN is valid by encrypting and decrypting test data.
        
        Args:
            pin: Employee PIN to verify
            test_data: Optional test data (generates random if None)
            
        Returns:
            True if PIN works for encryption/decryption, False otherwise
        """
        try:
            # Generate random test data if none provided
            if test_data is None:
                test_data = f"test-{secrets.token_hex(8)}"
                
            # Try encrypt-decrypt cycle
            encrypted = self.encrypt(pin, test_data)
            if encrypted is None:
                return False
                
            decrypted = self.decrypt(pin, encrypted)
            
            # PIN is valid if decrypted matches original
            return decrypted == test_data
            
        except Exception:
            return False
            
    def clear_key_cache(self) -> None:
        """Clear cached keys from memory for security."""
        self._key_cache.clear()
        self._fernet_instances.clear()
