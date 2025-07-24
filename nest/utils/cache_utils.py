import os
import logging
from .platform_paths import PlatformPaths

# Set up logger
logger = logging.getLogger(__name__)

_platform_paths = PlatformPaths()

# Cache directory path definition
CACHE_DIR = str(_platform_paths.ensure_dir_exists(_platform_paths.get_cache_dir()))

# Cache file paths
INVENTORY_CACHE_PATH = os.path.join(CACHE_DIR, 'inventory_cache.json')
TICKET_CACHE_PATH = os.path.join(CACHE_DIR, 'ticket_cache.json')
CUSTOMER_CACHE_PATH = os.path.join(CACHE_DIR, 'customer_cache.json')

def get_cache_directory():
    """Get or create the cache directory if it doesn't exist."""
    return str(_platform_paths.ensure_dir_exists(_platform_paths.get_cache_dir()))

# Alias for backward compatibility
ensure_cache_dir_exists = get_cache_directory

def get_inventory_cache_path():
    """Get the path to the inventory cache file."""
    get_cache_directory()
    return INVENTORY_CACHE_PATH

def get_ticket_cache_path():
    """Get the path to the ticket cache file."""
    get_cache_directory()
    return TICKET_CACHE_PATH

def get_customer_cache_path():
    """Get the path to the customer cache file."""
    get_cache_directory()
    return CUSTOMER_CACHE_PATH
