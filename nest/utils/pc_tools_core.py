#!/usr/bin/env python3
"""
PC Tools Core Functionality

Provides the core functionality for PC Tools, including system scanning,
diagnostic reports, and data export capabilities. Designed to work in both
WinPE standalone environment and within the Nest application.
"""

import os
import sys
import time
import json
import shutil
import logging
import platform
import subprocess
from datetime import datetime
from pathlib import Path

# Import utilities conditionally to support both standalone and integrated modes
try:
    from nest.utils.snapshot_logger import SnapshotLogger
    from nest.utils.ticket_context import TicketContext
    from nest.utils.config_util import ConfigManager
    INTEGRATED_MODE = True
except ImportError:
    try:
        from utils.snapshot_logger import SnapshotLogger
        from utils.ticket_context import TicketContext
        
        # Define minimal ConfigManager for standalone mode if needed
        class ConfigManager:
            def __init__(self):
                try:
                    from .platform_paths import PlatformPaths
                    platform_paths = PlatformPaths()
                    config_dir = platform_paths.get_config_dir()
                    self.config_path = str(config_dir / "config.json")
                except ImportError:
                    self.config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "config.json")
                self.config = self._load_config()
                
            def _load_config(self):
                if os.path.exists(self.config_path):
                    try:
                        with open(self.config_path, 'r') as f:
                            return json.load(f)
                    except:
                        return {}
                return {}
                
            def get(self, key, default=None):
                return self.config.get(key, default)
                
            def get_repairdesk_api_key(self):
                return self.config.get("api_key", "")
        
        INTEGRATED_MODE = False
    except ImportError:
        logging.error("Failed to import required modules")
        INTEGRATED_MODE = False


class PCToolsCore:
    """Core functionality for PC Tools diagnostic and repair operations."""
    
    def __init__(self):
        self.config = ConfigManager()
        self.api_key = self.config.get_repairdesk_api_key()
        self.store_slug = self.config.get("store_slug", "eliterepairs")
        self.store_name = self.config.get("store_name", self.store_slug)  # Use proper store name or fall back to slug
        self.server_path = self.config.get("server_path", "\\\\fileserver\\Jobs")
        self.technician = self.config.get("default_technician", "Technician")
        
        # Initialize ticket context manager
        self.ticket_context = TicketContext(self.api_key, self.store_slug)
        
        # Keep track of the last snapshot
        self.last_snapshot = None
        self.last_snapshot_path = None
        self.last_json_path = None
        
        # Base path for logs using platform-appropriate directory handling
        try:
            from .platform_paths import PlatformPaths
            platform_paths = PlatformPaths()
            self.logs_dir = str(platform_paths.ensure_dir_exists(platform_paths.get_logs_dir()))
            self.base_dir = str(platform_paths.get_user_data_dir())
        except ImportError:
            if getattr(sys, 'frozen', False):
                # We're running in a bundle (PyInstaller)
                self.base_dir = os.path.dirname(sys.executable)
            else:
                # We're running in a normal Python environment
                self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                
            self.logs_dir = os.path.join(self.base_dir, "logs")
            os.makedirs(self.logs_dir, exist_ok=True)
        
        logging.info("PCToolsCore initialized")
    
    def get_system_info(self):
        """Get complete system information."""
        snapshot = SnapshotLogger()
        snapshot.capture_snapshot()
        self.last_snapshot = snapshot
        return snapshot.snapshot_data
    
    def load_ticket(self, ticket_id):
        """Load ticket information and associate with the current session."""
        if not ticket_id:
            return None
            
        ticket_info = self.ticket_context.lookup_ticket(ticket_id)
        return ticket_info
    
    def load_last_ticket(self):
        """Load the last ticket that was accessed."""
        return self.ticket_context.load_last_ticket()
    
    def get_customer_name(self):
        """Get the name of the customer associated with the current ticket."""
        return self.ticket_context.get_customer_name()
    
    def get_formatted_ticket_id(self):
        """Get the formatted ticket ID (e.g., T-12345)."""
        return self.ticket_context.get_formatted_ticket_id()
    
    def get_customer_reported_issues(self):
        """Get the customer-reported issues from the ticket."""
        return self.ticket_context.get_customer_reported_issues()
    
    def create_snapshot(self, ticket_id=None, customer_name=None):
        """Create a complete system snapshot."""
        # Get ticket ID and customer name if not provided
        ticket_id = ticket_id or self.ticket_context.get_formatted_ticket_id()
        customer_name = customer_name or self.ticket_context.get_customer_name()
        
        # Create the snapshot
        snapshot = SnapshotLogger(ticket_id, customer_name)
        snapshot.capture_snapshot()
        self.last_snapshot = snapshot
        
        # Save snapshot files
        self.last_snapshot_path = snapshot.save_snapshot(self.logs_dir)
        self.last_json_path = snapshot.save_snapshot_json(self.logs_dir)
        
        return snapshot.snapshot_data
    
    def generate_report(self):
        """Generate a technician-friendly report from the snapshot."""
        if not self.last_snapshot:
            self.create_snapshot()
            
        return self.last_snapshot.get_technician_summary()
    
    def export_to_usb(self):
        """Export the snapshot to a USB drive."""
        if not self.last_snapshot_path:
            return None
            
        # Look for USB drives
        usb_drives = self._find_usb_drives()
        if not usb_drives:
            logging.error("No USB drives found")
            return None
            
        # Use the first USB drive found
        target_drive = usb_drives[0]
        target_dir = os.path.join(target_drive, "PC_Tools_Logs")
        
        try:
            os.makedirs(target_dir, exist_ok=True)
            
            # Copy log files
            target_file = os.path.join(target_dir, os.path.basename(self.last_snapshot_path))
            shutil.copy2(self.last_snapshot_path, target_file)
            
            # Copy JSON file if available
            if self.last_json_path and os.path.exists(self.last_json_path):
                json_target = os.path.join(target_dir, os.path.basename(self.last_json_path))
                shutil.copy2(self.last_json_path, json_target)
                
            logging.info(f"Exported snapshot to USB drive: {target_file}")
            return target_file
        except Exception as e:
            logging.error(f"Error exporting to USB drive: {e}")
            return None
    
    def export_to_server(self):
        """Export the snapshot to the configured server path."""
        if not self.last_snapshot_path or not self.server_path:
            return None
            
        return self.ticket_context.save_to_network_folder(self.last_snapshot_path, self.server_path)
    
    def upload_to_repairdesk(self):
        """Upload the snapshot as a note to the associated RepairDesk ticket."""
        if not self.last_snapshot:
            return False
            
        report = self.last_snapshot.get_technician_summary()
        if not report:
            return False
            
        # Add technician signature
        report += f"\n\nDiagnostic performed by: {self.technician}\n"
        report += f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        return self.ticket_context.upload_diagnostic_note(report)
    
    def _find_usb_drives(self):
        """Find USB drives connected to the system."""
        usb_drives = []
        
        if platform.system() == "Windows":
            # On Windows, find removable drives
            import win32file
            drives = [f"{chr(d)}:" for d in range(ord('A'), ord('Z')+1) if os.path.exists(f"{chr(d)}:\\")]
            
            for drive in drives:
                try:
                    drive_type = win32file.GetDriveType(drive)
                    # DRIVE_REMOVABLE = 2
                    if drive_type == 2:
                        usb_drives.append(drive)
                except:
                    pass
        else:
            # On Linux/macOS, check /media or /mnt directories
            media_dirs = ["/media", "/mnt"]
            for media_dir in media_dirs:
                if os.path.exists(media_dir):
                    for user_dir in os.listdir(media_dir):
                        user_path = os.path.join(media_dir, user_dir)
                        if os.path.isdir(user_path):
                            for mount in os.listdir(user_path):
                                mount_path = os.path.join(user_path, mount)
                                if os.path.isdir(mount_path) and os.access(mount_path, os.W_OK):
                                    usb_drives.append(mount_path)
        
        return usb_drives
    
    def create_server_folder(self):
        """Create a folder on the server for the current ticket."""
        if not self.server_path:
            return None
            
        # Get customer and ticket info for folder naming
        customer_name = self.ticket_context.get_customer_name() or "Unknown_Customer"
        ticket_id = self.ticket_context.get_formatted_ticket_id() or "No_Ticket"
        
        # Clean up customer name for folder naming
        safe_customer_name = ''.join(c if c.isalnum() or c in '- ' else '_' for c in customer_name)
        folder_name = f"{safe_customer_name}_{ticket_id}"
        
        # Create the target path
        target_dir = os.path.join(self.server_path, folder_name)
        
        try:
            # Create the target directory if it doesn't exist
            os.makedirs(target_dir, exist_ok=True)
            
            # Create a README file in the folder
            readme_path = os.path.join(target_dir, "README.txt")
            with open(readme_path, "w") as f:
                f.write(f"Folder created by PC Tools for ticket {ticket_id}\n")
                f.write(f"Customer: {customer_name}\n")
                f.write(f"Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Technician: {self.technician}\n")
            
            logging.info(f"Created server folder: {target_dir}")
            return target_dir
        except Exception as e:
            logging.error(f"Error creating server folder: {e}")
            return None


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    pc_tools = PCToolsCore()
    
    # Example workflow
    print("Initializing PC Tools...")
    print("Creating system snapshot...")
    pc_tools.create_snapshot()
    
    print("\nSystem Report:")
    print(pc_tools.generate_report())
