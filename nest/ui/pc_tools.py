#!/usr/bin/env python3
"""
PC Tools Module - Compatibility Bridge

This module serves as a bridge to the refactored PC Tools module in nest.ui.modules.pc_tools
It allows the main Nest application to continue to import from nest.ui.pc_tools while
we transition to the new modular architecture.
"""

import os
import sys
import logging
import importlib.util

# Set up basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

# Get the absolute path to this file
THIS_FILE = os.path.abspath(__file__)

# Get the ui directory (parent of this file)
UI_DIR = os.path.dirname(THIS_FILE)

# Get the nest directory (parent of ui)
NEST_DIR = os.path.dirname(UI_DIR)

# Get the project root directory (parent of nest)
ROOT_DIR = os.path.dirname(NEST_DIR)

# Ensure log directory exists
os.makedirs(os.path.join(ROOT_DIR, 'logs'), exist_ok=True)

# Dynamically import the refactored PCToolsModule
try:
    # First try direct import
    logging.info("Attempting to import PCToolsModule from refactored module location")
    from nest.ui.modules.pc_tools.pc_tools import PCToolsModule
    logging.info("Successfully imported PCToolsModule from nest.ui.modules.pc_tools.pc_tools")
except ImportError as e:
    logging.warning(f"Direct import failed: {e}")
    
    # If direct import fails, try using importlib
    try:
        logging.info("Attempting to import PCToolsModule using importlib")
        # Construct the exact absolute path to the pc_tools.py file
        module_path = os.path.join(UI_DIR, 'modules', 'pc_tools', 'pc_tools.py')
        
        # Log the exact path we're trying to use
        logging.info(f"Looking for module at: {module_path}")
        
        if not os.path.exists(module_path):
            logging.warning(f"Module file not found at {module_path}")
            raise ImportError(f"Could not find module file at {module_path}")
        
        # Dynamically load the module
        module_name = "nest.ui.modules.pc_tools.pc_tools"
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        pc_tools_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(pc_tools_module)
        
        # Get the PCToolsModule class from the loaded module
        if hasattr(pc_tools_module, 'PCToolsModule'):
            PCToolsModule = pc_tools_module.PCToolsModule
            logging.info("Successfully imported PCToolsModule using importlib")
        else:
            raise ImportError("PCToolsModule class not found in the module")
    except Exception as e2:
        logging.error(f"Failed to import PCToolsModule: {e2}")
        # Re-raise with more context
        raise ImportError(f"Could not import PCToolsModule: {e2}") from e

# Log successful bridge setup
logging.info("PC Tools bridge module loaded - redirecting to refactored implementation")

# Export the PCToolsModule for the main Nest application
__all__ = ['PCToolsModule']
