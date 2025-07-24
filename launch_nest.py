#!/usr/bin/env python3
"""
Launcher script for Nest application.
This ensures the Python path is set up correctly before launching the app.
"""
import os
import sys
import subprocess

def main():
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Add the project root to Python path
    sys.path.insert(0, script_dir)
    
    # Set PYTHONPATH environment variable
    os.environ['PYTHONPATH'] = script_dir
    
    # Run the application
    from nest.main import main as run_app
    run_app()

if __name__ == "__main__":
    main()
