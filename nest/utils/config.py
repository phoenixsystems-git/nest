import os
import json
import logging
from typing import Dict, Any, Optional
from .platform_paths import PlatformPaths


def get_script_dir() -> str:
    """Get the directory containing the main script."""
    platform_paths = PlatformPaths()
    return str(platform_paths._get_portable_dir())


def load_config() -> Dict[str, Any]:
    """Load configuration from config files with fallback support."""
    platform_paths = PlatformPaths()
    config_dir = platform_paths.ensure_dir_exists(platform_paths.get_config_dir())
    config_paths = [
        config_dir / "config.json",
        os.path.join(get_script_dir(), "config.json"),  # fallback for development
    ]

    config = {}
    for config_path in config_paths:
        if os.path.exists(str(config_path)):
            try:
                with open(str(config_path), "r") as f:
                    config = json.load(f)
                logging.info(f"Loaded config from {config_path}")
                break
            except Exception as e:
                logging.error(f"Failed to load config from {config_path}: {e}")

    return config


def get_repairdesk_api_key() -> Optional[str]:
    """Get the RepairDesk API key from configuration."""
    config = load_config()
    # Try both possible API key locations
    api_key = config.get("repairdesk", {}).get("api_key") or config.get("repairdesk_api_key")
    if api_key:
        logging.info("RepairDesk API key loaded successfully")
    else:
        logging.warning("No RepairDesk API key found in configuration")
    return api_key


# Create a singleton config instance
_config = load_config()
_repairdesk_api_key = get_repairdesk_api_key()


def get_config() -> Dict[str, Any]:
    """Get the current configuration."""
    return _config


def get_repairdesk_key() -> Optional[str]:
    """Get the current RepairDesk API key."""
    return _repairdesk_api_key
