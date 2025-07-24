import os
import json
import logging
from typing import Any, Dict, Optional
from cryptography.fernet import Fernet
import base64
import hashlib

class ConfigManager:
    """Manages application configuration including encrypted API keys.
    
    Provides methods to load, save, and access configuration values with
    support for encrypting sensitive values like API keys.
    """
    
    def __init__(self):
        """Initialize the configuration manager."""
        self.config = {}
        self.config_file = self.find_config_path()
        self.logger = logging.getLogger(__name__)
        self.load_config()
        
        # Initialize encryption
        self._fernet = None
        try:
            self._init_encryption()
        except Exception as e:
            self.logger.warning(f"Could not initialize encryption: {str(e)}")
    
    def find_config_path(self) -> str:
        """Find the configuration file path using platform-appropriate location.
        
        Returns:
            Path to the configuration file
        """
        try:
            from .platform_paths import PlatformPaths
            platform_paths = PlatformPaths()
            config_dir = platform_paths.get_config_dir()
            config_path = config_dir / 'config.json'
            if config_path.exists():
                return str(config_path)
            platform_paths.ensure_dir_exists(config_dir)
            return str(config_path)
        except ImportError:
            app_dir = os.path.dirname(os.path.dirname(__file__))
            config_dir = os.path.join(app_dir, "config")
            os.makedirs(config_dir, exist_ok=True)
            return os.path.join(config_dir, "config.json")
    
    def _init_encryption(self) -> None:
        """Initialize Fernet encryption for secure storage."""
        # Get or create encryption key
        key_path = os.path.join(os.path.dirname(self.config_file), ".key")
        
        if os.path.exists(key_path):
            with open(key_path, "rb") as f:
                key = f.read()
        else:
            # Generate a new key
            key = Fernet.generate_key()
            with open(key_path, "wb") as f:
                f.write(key)
            os.chmod(key_path, 0o600)  # Restrict permissions
            
        self._fernet = Fernet(key)
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from the config file.
        
        Returns:
            Configuration dictionary
        """
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, "r") as f:
                    self.config = json.load(f)
                self.logger.info("Configuration loaded successfully")
            else:
                self.config = {}
                with open(self.config_file, "w") as f:
                    json.dump(self.config, f, indent=2)
                self.logger.info("Created new configuration file")
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {str(e)}")
            self.config = {}
            
        return self.config
    
    def save_config(self) -> bool:
        """Save configuration to the config file.
        
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            with open(self.config_file, "w") as f:
                json.dump(self.config, f, indent=2)
            self.logger.info("Configuration saved successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to save configuration: {str(e)}")
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value.
        
        Args:
            key: Configuration key
            default: Default value if key not found
            
        Returns:
            Configuration value or default if not found
        """
        value = self.config.get(key, default)
        
        # Check if value is encrypted
        if isinstance(value, str) and value.startswith("encrypted:"):
            try:
                return self._decrypt(value[10:])  # Remove 'encrypted:' prefix
            except Exception as e:
                self.logger.error(f"Failed to decrypt value for key '{key}': {str(e)}")
                return default
                
        return value
    
    def set(self, key: str, value: Any, encrypt: bool = False) -> bool:
        """Set a configuration value.
        
        Args:
            key: Configuration key
            value: Configuration value
            encrypt: Whether to encrypt the value
            
        Returns:
            True if set successfully, False otherwise
        """
        try:
            if encrypt and self._fernet and isinstance(value, str):
                encrypted_value = self._encrypt(value)
                self.config[key] = f"encrypted:{encrypted_value}"
            else:
                self.config[key] = value
                
            return self.save_config()
        except Exception as e:
            self.logger.error(f"Failed to set configuration value for key '{key}': {str(e)}")
            return False
    
    def remove(self, key: str) -> bool:
        """Remove a configuration value.
        
        Args:
            key: Configuration key to remove
            
        Returns:
            True if removed successfully, False otherwise
        """
        if key in self.config:
            del self.config[key]
            return self.save_config()
        return True
    
    def _encrypt(self, text: str) -> str:
        """Encrypt a string.
        
        Args:
            text: Text to encrypt
            
        Returns:
            Base64-encoded encrypted string
        """
        if not self._fernet:
            raise ValueError("Encryption not initialized")
            
        encrypted = self._fernet.encrypt(text.encode())
        return base64.b64encode(encrypted).decode()
    
    def _decrypt(self, encrypted_text: str) -> str:
        """Decrypt an encrypted string.
        
        Args:
            encrypted_text: Base64-encoded encrypted string
            
        Returns:
            Decrypted string
        """
        if not self._fernet:
            raise ValueError("Encryption not initialized")
            
        encrypted = base64.b64decode(encrypted_text)
        return self._fernet.decrypt(encrypted).decode()
