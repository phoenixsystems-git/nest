import os
import json
import logging
from typing import Dict, Any


class ConfigManager:
    _instance = None
    _config = None
    _config_path = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if self._config is None:
            self._config_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), "config", "config.json"
            )
            self._load_config()

    def _load_config(self) -> None:
        """Load configuration from file.
        
        If configuration file doesn't exist or is empty, load default AI API configurations
        and models to ensure essential functionality works.
        """
        try:
            if os.path.exists(self._config_path):
                with open(self._config_path, "r") as f:
                    self._config = json.load(f)
                logging.info("Configuration loaded successfully")
            else:
                self._config = self._get_default_config()
                logging.warning(f"Config file not found at {self._config_path}, using default configuration")
                
                # Save the default config
                self._save_config()
        except Exception as e:
            self._config = self._get_default_config()
            logging.error(f"Error loading config: {e}, using default configuration")
            
            # Save the default config
            try:
                self._save_config()
            except Exception as save_error:
                logging.error(f"Failed to save default config: {save_error}")
    
    def _save_config(self) -> None:
        """Save configuration to file."""
        try:
            os.makedirs(os.path.dirname(self._config_path), exist_ok=True)
            with open(self._config_path, "w") as f:
                json.dump(self._config, f, indent=2)
            logging.info("Configuration saved successfully")
        except Exception as e:
            logging.error(f"Error saving config: {e}")
            
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration with essential AI API settings.
        
        Returns:
            Default configuration dictionary with AI API settings
        """
        return {
            "store_name": "Nest",  # Default store display name
            "store_slug": "default",  # Default store identifier
            "repairdesk": {
                "api_key": "",  # Store-specific, must be provided by user
                "base_url": "https://api.repairdesk.co/api/web/v1"
            },
            "gpt": {
                "api_key": "",  # Set via environment variable OPENAI_API_KEY
                "base_url": "https://api.openai.com/v1",
                "model": "gpt-4",
                "temperature": 0.7
            },
            "claude": {
                "api_key": "",  # Set via environment variable CLAUDE_API_KEY
                "base_url": "https://api.anthropic.com",
                "model": "claude-3-opus-20240229",
                "temperature": 0.7
            },
            "gemini": {
                "api_key": "",  # Set via environment variable GEMINI_API_KEY
                "base_url": "https://generativelanguage.googleapis.com",
                "model": "gemini-2.5-pro-preview-05-06",
                "temperature": 0.7
            },
            "ai_models": [
                {
                    "name": "Gemini 2.5 Pro",
                    "api": "gemini",
                    "model": "gemini-2.5-pro-preview-05-06"
                },
                {
                    "name": "Gemini 2.0 Flash",
                    "api": "gemini",
                    "model": "gemini-2.0-flash"
                },
                {
                    "name": "GPT-4.1",
                    "api": "gpt",
                    "model": "gpt-4.1-2025-04-14"
                },
                {
                    "name": "GPT-4o",
                    "api": "gpt",
                    "model": "gpt-4o"
                },
                {
                    "name": "GPT-4 Turbo",
                    "api": "gpt",
                    "model": "gpt-4-turbo"
                },
                {
                    "name": "GPT-4",
                    "api": "gpt",
                    "model": "gpt-4"
                },
                {
                    "name": "GPT-3.5 Turbo",
                    "api": "gpt",
                    "model": "gpt-3.5-turbo-16k"
                },
                {
                    "name": "Claude 3.7 Sonnet",
                    "api": "claude",
                    "model": "claude-3-7-sonnet-20250219"
                },
                {
                    "name": "Claude 3.5 Sonnet (Oct 2024)",
                    "api": "claude",
                    "model": "claude-3-5-sonnet-20241022"
                },
                {
                    "name": "Claude 3.5 Sonnet (Jun 2024)",
                    "api": "claude",
                    "model": "claude-3-5-sonnet-20240620"
                },
                {
                    "name": "Claude 3 Haiku",
                    "api": "claude",
                    "model": "claude-3-haiku-20240307"
                },
                {
                    "name": "Claude 3 Opus",
                    "api": "claude",
                    "model": "claude-3-opus-20240229"
                }
            ],
            "folder": {
                "base_path": "",
                "naming_convention": "CustomerName_TicketNumber"
            },
            "logging": {
                "log_file": "repair_tool.log",
                "log_level": "INFO"
            },
            "calendar": {
                "google_api_key": "",
                "calendar_id": ""
            },
            "notifications": {
                "popup_threshold": "critical",
                "default_style": {
                    "success_color": "green",
                    "warning_color": "yellow",
                    "error_color": "red"
                }
            }
        }

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value.
        
        Special handling for repairdesk_api_key and api_key to ensure consistency.
        """
        if key == 'repairdesk_api_key' and key not in self._config:
            # Try to get from api_key or repairdesk.api_key
            return self._config.get('api_key', self._config.get('repairdesk', {}).get('api_key', default))
        
        return self._config.get(key, default)

    def get_repairdesk_api_key(self) -> str:
        """Get the RepairDesk API key.
        
        Checks multiple locations where the API key might be stored to ensure consistency.
        """
        # Check all possible locations for the API key and use the first non-empty one
        api_key = self._config.get("repairdesk_api_key", "")
        
        if not api_key:
            # Try the root level api_key
            api_key = self._config.get("api_key", "")
            
        if not api_key:
            # Try the repairdesk object
            api_key = self._config.get("repairdesk", {}).get("api_key", "")
            
        return api_key

    def get_repairdesk_base_url(self) -> str:
        """Get the RepairDesk base URL from configuration."""
        return self._config.get("repairdesk", {}).get("base_url", "").rstrip("/")
    
    def get_all(self) -> Dict[str, Any]:
        """Get the entire configuration dictionary."""
        return self._config
        
    def get_store_name(self) -> str:
        """Get the proper store name from configuration.
        
        Returns:
            The store's display name or the store slug if no name is set
        """
        store_name = self._config.get("store_name", "")
        # Fall back to store_slug if store_name is not set
        if not store_name:
            store_name = self._config.get("store_slug", "")
        return store_name




# Convenience functions
def load_config() -> Dict[str, Any]:
    """Load configuration from file."""
    config_manager = ConfigManager()
    return config_manager.get_all()

# Backward compatibility helpers
def get_repairdesk_api_key():
    """Get the RepairDesk API key."""
    config_manager = ConfigManager()
    return config_manager.get_repairdesk_api_key()
    
def get_repairdesk_base_url():
    """Get the RepairDesk base URL."""
    config_manager = ConfigManager()
    return config_manager.get_repairdesk_base_url()
    
def get_config_value(key, default=None):
    """Get a configuration value."""
    config_manager = ConfigManager()
    return config_manager.get(key, default)
    
def set_config_value(key, value, encrypt=False):
    """Set a configuration value."""
    config_manager = ConfigManager()
    return config_manager.set(key, value, encrypt)
