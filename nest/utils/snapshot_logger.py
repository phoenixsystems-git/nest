#!/usr/bin/env python3
"""
Snapshot Logger for PC Tools

Generates dot-point system summaries with technician-style recommendations
and flags important issues. Optimized for WinPE environment diagnostic tasks.
"""

import os
import json
import time
import psutil
import logging
import platform
from datetime import datetime
from pathlib import Path

try:
    import wmi
    import pythoncom
    WMI_AVAILABLE = True
except ImportError:
    WMI_AVAILABLE = False

class SnapshotLogger:
    """Generates structured, technician-friendly system snapshots."""
    
    def __init__(self, ticket_id=None, customer_name=None):
        self.ticket_id = ticket_id
        self.customer_name = customer_name
        self.snapshot_time = datetime.now()
        self.snapshot_data = {}
        self.flags = []
        self.recommendations = []
        self.technician_notes = []
        
    def capture_snapshot(self):
        """Capture full system snapshot with important diagnostic information."""
        self._capture_system_info()
        self._capture_hardware_info()
        self._capture_disk_info()
        self._capture_memory_info()
        self._analyze_issues()
        return self.snapshot_data
    
    def _capture_system_info(self):
        """Capture basic system information."""
        system_info = {
            "hostname": platform.node(),
            "os": platform.system(),
            "os_version": platform.version(),
            "os_release": platform.release(),
            "architecture": platform.machine(),
            "capture_time": self.snapshot_time.strftime("%Y-%m-%d %H:%M:%S"),
            "is_winpe": self._detect_winpe_environment()
        }
        
        self.snapshot_data["system"] = system_info
        
    def _detect_winpe_environment(self):
        """Detect if running in WinPE environment."""
        # WinPE typically has X:\ as system drive and runs from RAM
        is_winpe = False
        try:
            # Check for typical WinPE characteristics
            if os.path.exists('X:\\Windows\\System32') and not os.path.exists('C:\\Windows\\System32'):
                is_winpe = True
            elif 'winpe' in platform.version().lower() or 'winpe' in platform.release().lower():
                is_winpe = True
            # RAM disk check
            for part in psutil.disk_partitions(all=True):
                if part.device == 'X:' and part.fstype == 'NTFS' and 'ramdisk' in part.opts.lower():
                    is_winpe = True
        except Exception as e:
            logging.error(f"Error detecting WinPE environment: {e}")
        
        return is_winpe
    
    def _capture_hardware_info(self):
        """Capture hardware information using WMI if available."""
        hardware_info = {
            "cpu": "Unknown",
            "motherboard": "Unknown",
            "manufacturer": "Unknown",
            "model": "Unknown",
            "bios": "Unknown",
            "serial": "Unknown",
            "gpus": []
        }
        
        # Try to get CPU info from platform module
        try:
            hardware_info["cpu"] = platform.processor()
        except:
            pass
            
        # Use WMI for detailed hardware info if available
        if WMI_AVAILABLE:
            try:
                pythoncom.CoInitialize()
                c = wmi.WMI()
                
                # Get CPU info
                for cpu in c.Win32_Processor():
                    hardware_info["cpu"] = cpu.Name.strip()
                    break
                    
                # Get system info
                for system in c.Win32_ComputerSystem():
                    hardware_info["manufacturer"] = system.Manufacturer.strip() if system.Manufacturer else "Unknown"
                    hardware_info["model"] = system.Model.strip() if system.Model else "Unknown"
                    
                # Get motherboard info
                for board in c.Win32_BaseBoard():
                    hardware_info["motherboard"] = f"{board.Manufacturer} {board.Product}".strip()
                    break
                    
                # Get BIOS info
                for bios in c.Win32_BIOS():
                    hardware_info["bios"] = bios.SMBIOSBIOSVersion.strip() if bios.SMBIOSBIOSVersion else "Unknown"
                    hardware_info["serial"] = bios.SerialNumber.strip() if bios.SerialNumber else "Unknown"
                    break
                    
                # Get GPU info
                for gpu in c.Win32_VideoController():
                    gpu_info = {
                        "name": gpu.Name.strip() if gpu.Name else "Unknown GPU",
                        "driver_version": gpu.DriverVersion.strip() if gpu.DriverVersion else "Unknown",
                        "memory": f"{gpu.AdapterRAM / (1024**2):.0f} MB" if gpu.AdapterRAM else "Unknown"
                    }
                    hardware_info["gpus"].append(gpu_info)
                    
                pythoncom.CoUninitialize()
            except Exception as e:
                logging.error(f"Error getting hardware info via WMI: {e}")
        
        self.snapshot_data["hardware"] = hardware_info
        
    def _capture_disk_info(self):
        """Capture disk information and health status."""
        disks = []
        disk_problems = False
        
        # Get basic disk info via psutil
        try:
            partitions = psutil.disk_partitions(all=True)
            for partition in partitions:
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    disk = {
                        "device": partition.device,
                        "mountpoint": partition.mountpoint,
                        "fstype": partition.fstype,
                        "opts": partition.opts,
                        "total": usage.total,
                        "used": usage.used,
                        "free": usage.free,
                        "percent": usage.percent,
                        "total_gb": f"{usage.total / (1024**3):.2f} GB",
                        "used_gb": f"{usage.used / (1024**3):.2f} GB",
                        "free_gb": f"{usage.free / (1024**3):.2f} GB"
                    }
                    
                    # Check if disk is critically full
                    if usage.percent > 90:
                        disk["status"] = "CRITICAL"
                        disk_problems = True
                        self.flags.append(f"Low disk space on {partition.device} ({usage.percent}% full)")
                    elif usage.percent > 75:
                        disk["status"] = "WARNING"
                        self.flags.append(f"Disk space getting low on {partition.device} ({usage.percent}% full)")
                    else:
                        disk["status"] = "OK"
                        
                    disks.append(disk)
                except Exception as e:
                    # Skip inaccessible drives
                    logging.debug(f"Cannot access drive {partition.mountpoint}: {e}")
        except Exception as e:
            logging.error(f"Error getting disk information: {e}")
            
        # Use WMI to get physical disk health if available
        if WMI_AVAILABLE:
            try:
                pythoncom.CoInitialize()
                c = wmi.WMI()
                physical_disks = []
                
                for drive in c.Win32_DiskDrive():
                    physical_disk = {
                        "model": drive.Model.strip() if drive.Model else "Unknown",
                        "serial": drive.SerialNumber.strip() if drive.SerialNumber else "Unknown",
                        "size": int(drive.Size) if drive.Size else 0,
                        "size_gb": f"{int(drive.Size) / (1024**3):.2f} GB" if drive.Size else "Unknown",
                        "interface": drive.InterfaceType if drive.InterfaceType else "Unknown"
                    }
                    
                    # Get SMART data if possible (requires admin privileges)
                    try:
                        smart_data = c.MSStorageDriver_FailurePredictStatus(InstanceName=drive.PNPDeviceID)
                        if smart_data:
                            for item in smart_data:
                                if hasattr(item, 'PredictFailure') and item.PredictFailure:
                                    physical_disk["smart_status"] = "FAILING"
                                    disk_problems = True
                                    self.flags.append(f"CRITICAL: Drive {drive.Model} is reporting SMART failures. DATA LOSS POSSIBLE!")
                                    break
                                else:
                                    physical_disk["smart_status"] = "OK"
                    except:
                        physical_disk["smart_status"] = "Unknown"
                        
                    physical_disks.append(physical_disk)
                    
                self.snapshot_data["physical_disks"] = physical_disks
                pythoncom.CoUninitialize()
            except Exception as e:
                logging.error(f"Error getting physical disk info via WMI: {e}")
        
        self.snapshot_data["disks"] = disks
        
        # Add recommendations for disk issues
        if disk_problems:
            self.recommendations.append("Perform data backup before proceeding with any repairs")
            self.recommendations.append("Check disk health with full SMART diagnostics")
    
    def _capture_memory_info(self):
        """Capture memory information."""
        memory_info = {}
        
        # Get memory info via psutil
        try:
            vm = psutil.virtual_memory()
            memory_info["total"] = vm.total
            memory_info["available"] = vm.available
            memory_info["used"] = vm.used
            memory_info["percent"] = vm.percent
            memory_info["total_gb"] = f"{vm.total / (1024**3):.2f} GB"
            memory_info["available_gb"] = f"{vm.available / (1024**3):.2f} GB"
            memory_info["used_gb"] = f"{vm.used / (1024**3):.2f} GB"
            
            # Check if memory is critically low
            if vm.percent > 90:
                memory_info["status"] = "CRITICAL"
                self.flags.append(f"Memory usage critically high ({vm.percent}%)")
                self.recommendations.append("Check for memory leaks or excessive background processes")
            elif vm.percent > 75:
                memory_info["status"] = "WARNING"
                self.flags.append(f"Memory usage high ({vm.percent}%)")
            else:
                memory_info["status"] = "OK"
                
        except Exception as e:
            logging.error(f"Error getting memory information: {e}")
            memory_info["status"] = "ERROR"
            
        # Use WMI to get physical memory info if available
        if WMI_AVAILABLE:
            try:
                pythoncom.CoInitialize()
                c = wmi.WMI()
                physical_memory = []
                
                for mem in c.Win32_PhysicalMemory():
                    memory_module = {
                        "manufacturer": mem.Manufacturer.strip() if mem.Manufacturer else "Unknown",
                        "capacity": int(mem.Capacity) if mem.Capacity else 0,
                        "capacity_gb": f"{int(mem.Capacity) / (1024**3):.2f} GB" if mem.Capacity else "Unknown",
                        "speed": f"{mem.Speed} MHz" if mem.Speed else "Unknown",
                        "location": mem.DeviceLocator.strip() if mem.DeviceLocator else "Unknown"
                    }
                    physical_memory.append(memory_module)
                    
                memory_info["modules"] = physical_memory
                pythoncom.CoUninitialize()
            except Exception as e:
                logging.error(f"Error getting physical memory info via WMI: {e}")
                
        self.snapshot_data["memory"] = memory_info
    
    def _analyze_issues(self):
        """Analyze captured data for common issues and add recommendations."""
        # Store flags and recommendations in snapshot
        self.snapshot_data["flags"] = self.flags
        self.snapshot_data["recommendations"] = self.recommendations
        
    def format_system_info(self, system_info, technician_name="Unknown"):
        """Format system information for RepairDesk ticket.
        
        Args:
            system_info: Dictionary containing system information
            technician_name: Name of the technician
            
        Returns:
            Formatted string for RepairDesk ticket
        """
        # Check if we're formatting our own snapshot or an external one
        if not self.snapshot_data and system_info:
            # Store the externally provided system info in our snapshot_data
            self.snapshot_data = system_info
        elif not system_info:
            # Use our own snapshot data
            system_info = self.snapshot_data
        
        # Generate header with RepairDesk branding
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted = []
        formatted.append("===== RepairDesk System Diagnostic Report =====")
        formatted.append(f"Technician: {technician_name}")
        formatted.append(f"Date: {timestamp}")
        if self.ticket_id:
            formatted.append(f"Ticket: {self.ticket_id}")
        formatted.append("")
        
        # Format system info section
        formatted.append("--- SYSTEM INFORMATION ---")
        if "system" in system_info:
            sys_info = system_info["system"]
            formatted.append(f"Hostname: {sys_info.get('hostname', 'Unknown')}")
            formatted.append(f"OS: {sys_info.get('os', 'Unknown')} {sys_info.get('os_version', '')}")
            formatted.append(f"Architecture: {sys_info.get('architecture', 'Unknown')}")
            formatted.append(f"Boot Mode: {'WinPE' if sys_info.get('is_winpe', False) else 'Normal OS'}")
        else:
            # Alternative format for system_info from system_utils - Include ALL system details
            formatted.append(f"Operating System: {system_info.get('os_name', 'Unknown')}")
            formatted.append(f"Kernel Version: {system_info.get('kernel_version', 'Unknown')}")
            formatted.append(f"System Model: {system_info.get('product_model', 'Unknown')}")
            formatted.append(f"Manufacturer: {system_info.get('manufacturer', 'Unknown')}")
            formatted.append(f"Serial Number: {system_info.get('serial_number', 'Unknown')}")
            formatted.append(f"Baseboard: {system_info.get('baseboard_manufacturer', 'Unknown')} {system_info.get('baseboard_product', 'Unknown')}")
            formatted.append(f"BIOS Vendor: {system_info.get('bios_vendor', 'Unknown')}")
            formatted.append(f"BIOS Version: {system_info.get('bios_version', 'Unknown')}")
            formatted.append(f"BIOS Release Date: {system_info.get('bios_release_date', 'Unknown')}")
            formatted.append(f"BIOS Mode: {system_info.get('bios_mode', 'Unknown')}")
            formatted.append(f"IP Address: {system_info.get('ip_address', 'Unknown')}")
            formatted.append(f"Hostname: {system_info.get('hostname', 'Unknown')}")
            
            # Add boot time with boot analysis data
            boot_time = system_info.get('boot_time', 'Unknown')
            boot_total = system_info.get('boot_analysis', {}).get('total', 'Unknown')
            formatted.append(f"Boot Time: {boot_time} | Total: {boot_total}")
            
            # Add available updates information
            updates_count = system_info.get('available_updates', 0)
            if updates_count > 0:
                formatted.append(f"⚠️ Available Updates: {updates_count} updates pending")
            else:
                formatted.append(f"🟢 Available Updates: System up to date")
        formatted.append("")
        
        # Format hardware section
        formatted.append("--- HARDWARE INFORMATION ---")
        if "hardware" in system_info:
            hw = system_info["hardware"]
            formatted.append(f"CPU: {hw.get('cpu', 'Unknown')}")
            formatted.append(f"Motherboard: {hw.get('motherboard', 'Unknown')}")
            formatted.append(f"Manufacturer: {hw.get('manufacturer', 'Unknown')}")
            formatted.append(f"Model: {hw.get('model', 'Unknown')}")
        else:
            # Alternative format for system_info from system_utils - Include ALL hardware details
            formatted.append(f"Processor: {system_info.get('cpu', 'Unknown')}")
            formatted.append(f"Memory: {system_info.get('memory', 'Unknown')} | {system_info.get('ram_details', 'Unknown')}")
            formatted.append(f"Graphics: {system_info.get('graphics', 'Unknown')}")
            
            # Add battery information if available
            if 'battery_info' in system_info:
                battery = system_info['battery_info']
                model = battery.get('model', 'Unknown')
                health = battery.get('health', 'Unknown')
                replacement = battery.get('replacement_recommended', False)
                
                status_symbol = "⚠️" if replacement else "🟢"
                formatted.append(f"{status_symbol} Battery: {model} - Health: {health}" + 
                                (" (Replacement Recommended)" if replacement else ""))
        formatted.append("")
        
        # Format storage section
        formatted.append("--- STORAGE INFORMATION ---")
        if "storage" in system_info and system_info["storage"].get("disks"):
            disks = system_info["storage"]["disks"]
            for disk in disks:
                status = disk.get("status", "Unknown")
                status_symbol = "🔴" if status == "CRITICAL" else "⚠️" if status == "WARNING" else "🟢"
                formatted.append(
                    f"{status_symbol} {disk.get('device', '')} - {disk.get('model', 'Unknown')} "
                    f"{disk.get('total_gb', 'Unknown')}GB ({disk.get('free_gb', 'Unknown')}GB free, {disk.get('percent', 0)}% used)"
                )
        elif "drives" in system_info:
            # Alternative format for system_info from system_utils
            for drive in system_info["drives"]:
                status_symbol = "🔴" if drive.get("smart_status", "") == "Failed" else "⚠️" if drive.get("smart_status", "") == "Warning" else "🟢"
                formatted.append(
                    f"{status_symbol} {drive.get('model', 'Unknown')} - {drive.get('size_gb', 0)}GB "
                    f"({drive.get('type', 'Unknown')}, {drive.get('used_percent', 0)}% used)"
                )
        formatted.append("")
        
        # Format health section if available
        if "health" in system_info:
            formatted.append("--- SYSTEM HEALTH ---")
            health = system_info["health"]
            for key, val in health.items():
                if isinstance(val, dict):
                    status = val.get("status", "Unknown")
                    value = val.get("value", 0)
                    health_symbol = "🔴" if status == "Critical" else "⚠️" if status == "Moderate" else "🟢"
                    formatted.append(f"{health_symbol} {key.replace('_', ' ').title()}: {value}% ({status})")
            formatted.append("")
        
        # Add issues and recommendations
        if self.flags:
            formatted.append("--- ⚠️ ISSUES DETECTED ---")
            for flag in self.flags:
                formatted.append(f"! {flag}")
            formatted.append("")
            
        if self.recommendations:
            formatted.append("--- 📋 RECOMMENDATIONS ---")
            for rec in self.recommendations:
                formatted.append(f"* {rec}")
            formatted.append("")
        
        # RepairDesk footer
        formatted.append("--------------------------------------------")
        formatted.append("Generated by Nest PC Tools - RepairDesk Integration")
        
        return "\n".join(formatted)
        
    def get_technician_summary(self):
        """Generate a dot-point technician summary suitable for RepairDesk tickets."""
        summary = []
        
        # Generate header
        customer_info = self.customer_name or "Customer"
        ticket_info = f"Ticket: {self.ticket_id}" if self.ticket_id else ""
        timestamp = self.snapshot_time.strftime("%Y-%m-%d %H:%M:%S")
        
        summary.append(f"## System Snapshot for {customer_info} {ticket_info}")
        summary.append(f"Generated: {timestamp}")
        summary.append("")
        
        # System info
        summary.append("### SYSTEM INFORMATION")
        sys_info = self.snapshot_data.get("system", {})
        hw_info = self.snapshot_data.get("hardware", {})
        summary.append(f"* Manufacturer: {hw_info.get('manufacturer', 'Unknown')}")
        summary.append(f"* Model: {hw_info.get('model', 'Unknown')}")
        summary.append(f"* Operating System: {sys_info.get('os', 'Unknown')} {sys_info.get('os_version', '')}")
        summary.append(f"* CPU: {hw_info.get('cpu', 'Unknown')}")
        summary.append(f"* BIOS Version: {hw_info.get('bios', 'Unknown')}")
        summary.append(f"* Serial Number: {hw_info.get('serial', 'Unknown')}")
        
        # GPU info
        gpus = hw_info.get("gpus", [])
        if gpus:
            summary.append("")
            summary.append("### GRAPHICS")
            for gpu in gpus:
                summary.append(f"* {gpu.get('name', 'Unknown GPU')} ({gpu.get('memory', 'Unknown RAM')})")
        
        # Memory info
        mem_info = self.snapshot_data.get("memory", {})
        summary.append("")
        summary.append("### MEMORY")
        summary.append(f"* Total RAM: {mem_info.get('total_gb', 'Unknown')}")
        summary.append(f"* Memory Usage: {mem_info.get('percent', 'Unknown')}%")
        
        # Disk info
        summary.append("")
        summary.append("### STORAGE")
        disks = self.snapshot_data.get("disks", [])
        physical_disks = self.snapshot_data.get("physical_disks", [])
        
        # Physical disks first
        if physical_disks:
            for disk in physical_disks:
                status = disk.get("smart_status", "Unknown")
                status_indicator = "🔴" if status == "FAILING" else "🟢" if status == "OK" else "⚠️"
                summary.append(f"* {status_indicator} {disk.get('model', 'Unknown')} - {disk.get('size_gb', 'Unknown')} ({disk.get('interface', 'Unknown')})")
                
        # Logical disks/partitions
        if disks:
            summary.append("")
            summary.append("### PARTITIONS")
            for disk in disks:
                status_indicator = "🔴" if disk.get("status") == "CRITICAL" else "⚠️" if disk.get("status") == "WARNING" else "🟢"
                summary.append(f"* {status_indicator} {disk.get('device', '')} - {disk.get('total_gb', 'Unknown')} ({disk.get('free_gb', 'Unknown')} free, {disk.get('percent', 0)}% used)")
        
        # Issues and recommendations
        if self.flags:
            summary.append("")
            summary.append("### ⚠️ ISSUES DETECTED")
            for flag in self.flags:
                summary.append(f"* {flag}")
                
        if self.recommendations:
            summary.append("")
            summary.append("### 📋 RECOMMENDATIONS")
            for rec in self.recommendations:
                summary.append(f"* {rec}")
        
        return "\n".join(summary)
    
    def save_snapshot(self, output_dir=None, prefix=None):
        """Save the snapshot to a file."""
        if not self.snapshot_data:
            logging.error("No snapshot data to save")
            return None
            
        # Generate filename
        timestamp = self.snapshot_time.strftime("%Y%m%d_%H%M%S")
        ticket_str = f"_{self.ticket_id}" if self.ticket_id else ""
        customer_str = f"_{self.customer_name.replace(' ', '_')}" if self.customer_name else ""
        prefix_str = f"{prefix}_" if prefix else ""
        
        filename = f"{prefix_str}snapshot{customer_str}{ticket_str}_{timestamp}.txt"
        
        # Determine output directory
        if not output_dir:
            # Default to a logs directory in the current working directory
            output_dir = os.path.join(os.getcwd(), "logs")
            
        # Ensure directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Save summary to file
        filepath = os.path.join(output_dir, filename)
        try:
            with open(filepath, "w") as f:
                f.write(self.get_technician_summary())
            logging.info(f"Saved snapshot to {filepath}")
            return filepath
        except Exception as e:
            logging.error(f"Error saving snapshot: {e}")
            return None
    
    def save_snapshot_json(self, output_dir=None, prefix=None):
        """Save the raw snapshot data as JSON."""
        if not self.snapshot_data:
            logging.error("No snapshot data to save")
            return None
            
        # Generate filename
        timestamp = self.snapshot_time.strftime("%Y%m%d_%H%M%S")
        ticket_str = f"_{self.ticket_id}" if self.ticket_id else ""
        customer_str = f"_{self.customer_name.replace(' ', '_')}" if self.customer_name else ""
        prefix_str = f"{prefix}_" if prefix else ""
        
        filename = f"{prefix_str}snapshot{customer_str}{ticket_str}_{timestamp}.json"
        
        # Determine output directory
        if not output_dir:
            # Default to a logs directory in the current working directory
            output_dir = os.path.join(os.getcwd(), "logs")
            
        # Ensure directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Save JSON to file
        filepath = os.path.join(output_dir, filename)
        try:
            with open(filepath, "w") as f:
                json.dump(self.snapshot_data, f, indent=2)
            logging.info(f"Saved snapshot JSON to {filepath}")
            return filepath
        except Exception as e:
            logging.error(f"Error saving snapshot JSON: {e}")
            return None


# If run directly, generate a snapshot
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("Generating system snapshot...")
    snapshot = SnapshotLogger()
    snapshot.capture_snapshot()
    
    # Save the snapshot files
    output_dir = os.path.join(os.getcwd(), "logs")
    snapshot.save_snapshot(output_dir)
    snapshot.save_snapshot_json(output_dir)
    
    # Print the summary
    print("\nSystem Snapshot Complete!\n")
    print(snapshot.get_technician_summary())
