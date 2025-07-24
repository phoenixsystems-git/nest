#!/usr/bin/env python3
"""Test script to verify platform paths are working correctly."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

def test_platform_paths():
    """Test that platform paths are configured correctly."""
    print("Testing platform paths...")
    
    try:
        from nest.utils.platform_paths import PlatformPaths
        platform_paths = PlatformPaths()
        
        print(f"Config dir: {platform_paths.get_config_dir()}")
        print(f"Cache dir: {platform_paths.get_cache_dir()}")
        print(f"User data dir: {platform_paths.get_user_data_dir()}")
        
        return True
    except Exception as e:
        print(f"Error testing platform paths: {e}")
        return False

def test_config_manager():
    """Test that config manager uses platform paths."""
    print("\nTesting config manager...")
    
    try:
        from nest.utils.config_util import ConfigManager
        config_manager = ConfigManager()
        
        print(f"Config path: {config_manager._config_path}")
        
        if "AppData" in str(config_manager._config_path) or ".config" in str(config_manager._config_path):
            print("✓ Config manager using platform-appropriate path")
            return True
        else:
            print("✗ Config manager still using development path")
            return False
            
    except Exception as e:
        print(f"Error testing config manager: {e}")
        return False

def test_config_manager_new():
    """Test that new config manager uses platform paths."""
    print("\nTesting new config manager...")
    
    try:
        from nest.utils.config_manager import ConfigManager
        config_manager = ConfigManager()
        
        print(f"Config file path: {config_manager.config_file}")
        
        if "AppData" in str(config_manager.config_file) or ".config" in str(config_manager.config_file):
            print("✓ New config manager using platform-appropriate path")
            return True
        else:
            print("✗ New config manager still using development path")
            return False
            
    except Exception as e:
        print(f"Error testing new config manager: {e}")
        return False

def test_repairdesk_api():
    """Test that RepairDesk API uses platform paths."""
    print("\nTesting RepairDesk API...")
    
    try:
        from nest.utils.repairdesk_api import RepairDeskAPI
        api = RepairDeskAPI()
        config_path = api._find_config_file()
        
        print(f"RepairDesk API config path: {config_path}")
        
        if config_path and ("AppData" in config_path or ".config" in config_path):
            print("✓ RepairDesk API using platform-appropriate path")
            return True
        else:
            print("✗ RepairDesk API still using development path")
            return False
            
    except Exception as e:
        print(f"Error testing RepairDesk API: {e}")
        return False

def test_cache_utils():
    """Test that cache utilities use platform paths."""
    print("\nTesting cache utilities...")
    
    try:
        from nest.utils.cache_utils import get_cache_directory, get_ticket_cache_path
        
        cache_dir = get_cache_directory()
        ticket_cache = get_ticket_cache_path()
        
        print(f"Cache directory: {cache_dir}")
        print(f"Ticket cache path: {ticket_cache}")
        
        if "AppData" in cache_dir or ".cache" in cache_dir:
            print("✓ Cache utilities using platform-appropriate path")
            return True
        else:
            print("✗ Cache utilities still using development path")
            return False
            
    except Exception as e:
        print(f"Error testing cache utilities: {e}")
        return False

if __name__ == "__main__":
    print("=== Testing Directory Path Consolidation ===\n")
    
    results = []
    results.append(test_platform_paths())
    results.append(test_config_manager())
    results.append(test_config_manager_new())
    results.append(test_repairdesk_api())
    results.append(test_cache_utils())
    
    print(f"\n=== Results ===")
    print(f"Tests passed: {sum(results)}/{len(results)}")
    
    if all(results):
        print("✓ All directory path tests passed!")
        sys.exit(0)
    else:
        print("✗ Some directory path tests failed!")
        sys.exit(1)
