#!/usr/bin/env python3
"""
System Utilities for PC Tools

Provides comprehensive system information gathering functions for hardware 
and software diagnostics, optimized for both normal OS and WinPE environments.
"""

import os
import sys
import re
import platform
import psutil
import logging
import socket
import threading
import time
import subprocess
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

# Try to import WMI for Windows-specific functionality
try:
    import wmi
    import pythoncom
    WMI_AVAILABLE = True
except ImportError:
    WMI_AVAILABLE = False
    logging.warning("WMI module not available. Limited hardware info will be shown.")

# Detect if running in WinPE environment
def is_winpe_environment() -> bool:
    """Detect if the current environment is WinPE.
    
    Returns:
        bool: True if running in WinPE, False otherwise
    """
    try:
        # Check for typical WinPE characteristics
        if os.path.exists('X:\\Windows\\System32') and not os.path.exists('C:\\Windows\\System32'):
            return True
        elif 'winpe' in platform.version().lower() or 'winpe' in platform.release().lower():
            return True
            
        # RAM disk check
        for part in psutil.disk_partitions(all=True):
            if part.device == 'X:' and 'ramdisk' in part.opts.lower():
                return True
                
        return False
    except Exception as e:
        logging.error(f"Error detecting WinPE environment: {e}")
        return False

# Global cache for system info
_system_info_cache = {}
_cache_timestamp = None
_cache_lock = None

def _get_cache_lock():
    """Get the cache lock, initializing it if needed."""
    global _cache_lock
    if _cache_lock is None:
        _cache_lock = threading.Lock()
    return _cache_lock
_info_callbacks = []


def register_info_callback(callback):
    """Register a callback to receive system info updates.
    
    Args:
        callback: Function to call with key, value pairs as info is gathered
    """
    if callback not in _info_callbacks:
        _info_callbacks.append(callback)


def unregister_info_callback(callback):
    """Unregister a system info callback.
    
    Args:
        callback: Previously registered callback function
    """
    if callback in _info_callbacks:
        _info_callbacks.remove(callback)


def _update_info(system_info, key, value):
    """Update a system info key and notify callbacks.
    
    Args:
        system_info: Dictionary to update
        key: Key to update
        value: New value
    """
    system_info[key] = value
    
    # Notify all registered callbacks
    for callback in _info_callbacks:
        try:
            callback(key, value)
        except Exception as e:
            logging.error(f"Error in system info callback: {e}")


def get_system_info(force_refresh=False) -> Dict[str, Any]:
    """Get comprehensive system information with caching and progressive loading.
    
    Args:
        force_refresh: Whether to force a cache refresh
        
    Returns:
        Dict containing system information categories that will be progressively updated
    """
    global _system_info_cache, _cache_timestamp
    
    # Check for a valid cache (less than 30 seconds old)
    current_time = time.time()
    with _get_cache_lock():
        if not force_refresh and _cache_timestamp and (current_time - _cache_timestamp < 30):
            # Return a shallow copy of the cache
            return _system_info_cache.copy()
    
    # Initialize a new system info dictionary
    system_info = {}
    
    # Start threads for different information types
    threads = [
        threading.Thread(target=get_basic_system_info, args=(system_info,), daemon=True),
        threading.Thread(target=get_hardware_info, args=(system_info,), daemon=True),
        threading.Thread(target=get_drives_info_async, args=(system_info,), daemon=True),
        threading.Thread(target=get_network_info_async, args=(system_info,), daemon=True),
        threading.Thread(target=get_health_metrics_async, args=(system_info,), daemon=True)
    ]
    
    # Start all threads
    for thread in threads:
        thread.start()
    
    # Update the cache
    with _get_cache_lock():
        _system_info_cache = system_info
        _cache_timestamp = current_time
    
    # Return the system info dict immediately (will be updated by threads)
    return system_info


def get_basic_system_info(system_info):
    """Get high-priority basic system information.
    
    Args:
        system_info: Dict to update with system info
    """
    # Get OS info
    _update_info(system_info, "os", platform.system() + " " + platform.release())
    _update_info(system_info, "kernel", platform.release())
    
    # Boot time
    _update_info(system_info, "boot_time", get_boot_time())
    
    # Boot analysis
    boot_analysis = get_boot_analysis()
    system_info['boot_analysis'] = boot_analysis
    
    # Get battery information
    battery_info = get_battery_info()
    _update_info(system_info, "battery_info", battery_info)
    
    # Get available updates
    updates_count = get_available_updates()
    _update_info(system_info, "available_updates", updates_count)
    
    # Get network info (hostname and IP)
    try:
        _update_info(system_info, "hostname", socket.gethostname())
        _update_info(system_info, "ip_address", socket.gethostbyname(socket.gethostname()))
        
        _update_info(system_info, "basic_info_loaded", True)
    except Exception as e:
        logging.error(f"Error getting basic system info: {e}")
        _update_info(system_info, "basic_info_error", str(e))

def get_hardware_info(system_info):
    """Get hardware information and update the system_info dict.
    
    Args:
        system_info: Dictionary to update with hardware information
    """
    # Initialize with unknown values
    defaults = {
        "manufacturer": "Unknown",
        "product_model": "Unknown",
        "baseboard_manufacturer": "Unknown",
        "baseboard_product": "Unknown",
        "bios_version": "Unknown",
        "bios_mode": "Unknown",
        "gpu_model": "Unknown"
    }
    
    # Set default values first
    for key, value in defaults.items():
        _update_info(system_info, key, value)
    
    # If on Linux, call the Linux hardware info function
    if platform.system() == "Linux":
        get_linux_hardware_info(system_info)
        return
    # If not on Windows or WMI not available, we're done
    if platform.system() != "Windows" or not WMI_AVAILABLE:
        _update_info(system_info, "hardware_info_loaded", True)
        return
    
    try:
        # Initialize COM for this thread
        pythoncom.CoInitialize()
        
        # Connect to WMI with specific moniker for better performance
        wmi_client = wmi.WMI(moniker='//./root/cimv2')
        
        # Optimize WMI queries by batching related information
        # Use query() method instead of class access for better performance
        computer_info = wmi_client.query(
            "SELECT * FROM Win32_ComputerSystem"
        )
        
        if computer_info:
            system = computer_info[0]
            _update_info(system_info, "manufacturer", system.Manufacturer.strip() if system.Manufacturer else "Unknown")
            _update_info(system_info, "product_model", system.Model.strip() if system.Model else "Unknown")
        
        # Get baseboard info
        baseboard_info = wmi_client.query(
            "SELECT Manufacturer, Product FROM Win32_BaseBoard"
        )
        
        if baseboard_info:
            board = baseboard_info[0]
            _update_info(system_info, "baseboard_manufacturer", board.Manufacturer.strip() if board.Manufacturer else "Unknown")
            _update_info(system_info, "baseboard_product", board.Product.strip() if board.Product else "Unknown")
        
        # BIOS information
        bios_info = wmi_client.query(
            "SELECT SMBIOSBIOSVersion FROM Win32_BIOS"
        )
        
        if bios_info:
            bios = bios_info[0]
            _update_info(system_info, "bios_version", bios.SMBIOSBIOSVersion.strip() if bios.SMBIOSBIOSVersion else "Unknown")
            if hasattr(bios, 'SerialNumber'):
                _update_info(system_info, "serial_number", bios.SerialNumber.strip() if bios.SerialNumber else "Unknown")
        
        # Get CPU information
        try:
            cpu_info = wmi_client.query(
                "SELECT Name, NumberOfCores, NumberOfLogicalProcessors, MaxClockSpeed FROM Win32_Processor"
            )
            
            if cpu_info:
                cpu = cpu_info[0]
                # Update CPU model
                _update_info(system_info, "cpu_model", cpu.Name.strip() if cpu.Name else "Unknown")
        except Exception as e:
            logging.error(f"Error getting CPU info: {e}")
            
        # Get GPU information
        try:
            gpu_info = wmi_client.query(
                "SELECT Name FROM Win32_VideoController"
            )
            if gpu_info:
                gpu = gpu_info[0]
                _update_info(system_info, "gpu_model", gpu.Name.strip() if gpu.Name else "Unknown")
        except Exception as e:
            logging.error(f"Error getting GPU info: {e}")
            
        # Try to get BIOS mode
        try:
            _update_info(system_info, "bios_mode", get_bios_mode())
        except Exception as e:
            logging.error(f"Error getting BIOS mode: {e}")
            
        # Mark hardware info as loaded
        _update_info(system_info, "hardware_info_loaded", True)
        
        # Memory information
        memory_modules = []
        total_memory = 0
        for module in wmi_client.Win32_PhysicalMemory():
            if module.Capacity:
                capacity = int(module.Capacity)
                total_memory += capacity
                memory_info = {
                    "capacity": f"{capacity / (1024**3):.2f} GB",
                    "speed": f"{module.Speed} MHz" if module.Speed else "Unknown",
                    "manufacturer": module.Manufacturer.strip() if module.Manufacturer else "Unknown",
                    "location": module.DeviceLocator.strip() if module.DeviceLocator else "Unknown"
                }
                memory_modules.append(memory_info)
                
        info["memory_modules"] = memory_modules
        
        # Update RAM size if we found memory modules
        if total_memory > 0:
            info["ram_size"] = f"{total_memory / (1024**3):.2f} GB"
            
        # BIOS mode (UEFI or Legacy)
        info["bios_mode"] = get_bios_mode()
        
        return info
    except Exception as e:
        logging.error(f"Error getting Windows hardware info: {e}")
        return {}
    finally:
        pythoncom.CoUninitialize()

def get_bios_mode() -> str:
    """Get BIOS mode (UEFI or Legacy).
    
    Returns:
        str: "UEFI", "Legacy", or "Unknown"
    """
    try:
        if platform.system() == "Windows":
            if not WMI_AVAILABLE:
                return "Unknown"
            
            pythoncom.CoInitialize()
            try:
                # Look for UEFI characteristics
                if os.path.exists("C:\\Windows\\Boot\\EFI"):
                    return "UEFI"
                
                # Check if secure boot is enabled
                w_sec = wmi.WMI(namespace="root\\Microsoft\\Windows\\Security")
                if hasattr(w_sec, "EncryptableVolume"):
                    return "UEFI"
                
                return "Legacy"
            except Exception:
                return "Legacy"
            finally:
                pythoncom.CoUninitialize()
        
        elif platform.system() == "Linux":
            return "UEFI" if os.path.exists("/sys/firmware/efi") else "Legacy"
        
        return "Unknown"
    except Exception:
        return "Unknown"

def get_linux_hardware_info(system_info):
    """Get Linux hardware information and update the system_info dict.
    
    Args:
        system_info: Dictionary to update with hardware information
    """
    import os
    import re
    import glob
    
    # Initialize with unknown values
    defaults = {
        # Keys matching UI expectations
        "manufacturer": "Unknown",  # Map to manufacturer in UI
        "product_model": "Unknown",  # Map to System Model in UI
        "serial_number": "Unknown",  # System serial number
        "baseboard_manufacturer": "Unknown",
        "baseboard_product": "Unknown",
        "bios_vendor": "Unknown",  # UI shows BIOS Vendor
        "bios_version": "Unknown",  # UI shows BIOS Version
        "bios_release_date": "Unknown",  # UI shows BIOS Release Date
        "bios_mode": "Unknown",  # UI shows BIOS Mode
        "graphics": "Unknown",  # UI shows Graphics
        "cpu_model": "Unknown",  # Map to Processor in UI
        "memory": "Unknown"   # Map to Memory in UI
    }
    
    # Set default values first
    for key, value in defaults.items():
        _update_info(system_info, key, value)
    
    logging.info("Gathering Linux hardware information...")
    
    try:
        # --- SYSTEM SERIAL NUMBER DETECTION ---
        try:
            # Try to get system serial number using dmidecode
            import subprocess  # Import subprocess here to ensure it's in scope
            logging.info("Attempting to retrieve system serial number via dmidecode...")
            try:
                # Try with sudo first for the most reliable results
                serial_output = subprocess.check_output(
                    'sudo dmidecode -t 1 | grep -i "serial\\|product\\|manufacturer"',
                    shell=True, stderr=subprocess.PIPE, universal_newlines=True
                )
            except subprocess.CalledProcessError:
                # Fall back to non-sudo if that fails
                serial_output = subprocess.check_output(
                    'dmidecode -t 1 | grep -i "serial\\|product\\|manufacturer"',
                    shell=True, stderr=subprocess.PIPE, universal_newlines=True
                )
            
            # Extract the serial number from the output
            serial_match = re.search(r'Serial Number:\s+([^\n]+)', serial_output)
            if serial_match:
                serial_number = serial_match.group(1).strip()
                # Don't show 'To be filled by O.E.M.' as a valid serial
                if serial_number and serial_number.lower() != "to be filled by o.e.m." and serial_number != "Not Specified":
                    _update_info(system_info, "serial_number", serial_number)
                    logging.info(f"Found system serial number: {serial_number}")
        except Exception as e:
            logging.warning(f"Error getting system serial number via dmidecode: {e}")
            
        # --- CPU INFORMATION ---
        cpu_model = "Unknown"
        try:
            with open("/proc/cpuinfo", "r") as f:
                cpu_info = f.read()
                # Get the first CPU model name
                model_pattern = re.search(r'model name\s+:\s+(.*)', cpu_info)
                if model_pattern:
                    cpu_model = model_pattern.group(1)
                    # Only populate one field to avoid duplication
                    _update_info(system_info, "cpu", cpu_model)
                    # Hide the duplicate CPU field
                    _update_info(system_info, "CPU", "")
                    _update_info(system_info, "cpu_model", "")  # Hide this too
        except Exception as e:
            logging.warning(f"Error reading CPU info: {e}")
            _update_info(system_info, "cpu", cpu_model)  # UI shows 'Processor' field first
            
            # Try alternative method: lscpu
            try:
                import subprocess
                lscpu_output = subprocess.check_output(['lscpu']).decode('utf-8')
                model_pattern = re.search(r'Model name:\s+(.*)', lscpu_output)
                if model_pattern:
                    cpu_model = model_pattern.group(1)
                    # Only populate one field to avoid duplication
                    _update_info(system_info, "cpu", cpu_model)  # UI shows 'Processor' field first
                    # Hide the duplicate CPU field
                    _update_info(system_info, "CPU", "")
                    _update_info(system_info, "cpu_model", "")
            except Exception as e2:
                logging.error(f"Error getting CPU info via lscpu: {e2}")
        
        # --- MEMORY INFORMATION ---
        try:
            with open('/proc/meminfo', 'r') as f:
                mem_info = f.read()
                mem_pattern = re.search(r'MemTotal:\s+(\d+) kB', mem_info)
                if mem_pattern:
                    mem_kb = int(mem_pattern.group(1))
                    mem_gb = round(mem_kb / 1024 / 1024, 2)
                    mem_str = f"{mem_gb} GB"
                    # Set the memory size
                    _update_info(system_info, "memory", mem_str)
        except Exception as e:
            logging.error(f"Error reading memory info: {e}")
            # Try alternative: free command
            try:
                import subprocess
                free_output = subprocess.check_output(['free', '-m']).decode('utf-8')
                mem_pattern = re.search(r'Mem:\s+(\d+)', free_output)
                if mem_pattern:
                    mem_mb = int(mem_pattern.group(1))
                    mem_gb = round(mem_mb / 1024, 2)
                    mem_str = f"{mem_gb} GB"
                    # Set the memory size
                    _update_info(system_info, "memory", mem_str)
            except Exception as e2:
                logging.error(f"Error getting memory via free command: {e2}")
                
        # Initialize RAM type, speed, form factor, and solderability fields
        _update_info(system_info, "ram_type", "Unknown")
        _update_info(system_info, "ram_speed", "Unknown")
        _update_info(system_info, "ram_form_factor", "Unknown")
        _update_info(system_info, "ram_upgradable", "Unknown")
        
        # --- RAM TYPE AND SPEED DETECTION ---
        logging.info("Detecting RAM type and speed...")
        ram_detected = False
        
        # Method 1: Try dmidecode (requires root privileges)
        try:
            logging.info("Attempting RAM detection via dmidecode...")
            # Try to get RAM type and speed using dmidecode
            # Import subprocess here to ensure it's available
            import subprocess
            dmidecode_output = subprocess.check_output(
                ['dmidecode', '--type', 'memory'], 
                stderr=subprocess.DEVNULL
            ).decode('utf-8')
            
            # Parse memory modules
            memory_devices = re.findall(r'Memory Device[\s\S]+?\n\n', dmidecode_output)
            logging.info(f"Found {len(memory_devices)} memory devices in dmidecode output")
            
            if memory_devices:
                # Get the first populated memory module
                for device in memory_devices:
                    # Skip unpopulated slots
                    if 'Size: No Module Installed' in device or 'Size: 0' in device:
                        continue
                        
                    # Extract RAM type
                    type_match = re.search(r'Type: (.+)', device)
                    if type_match and 'Unknown' not in type_match.group(1):
                        ram_type = type_match.group(1).strip()
                        logging.info(f"Found RAM type via dmidecode: {ram_type}")
                        _update_info(system_info, "ram_type", ram_type)
                    
                    # Extract RAM speed
                    speed_match = re.search(r'Speed: (.+)', device)
                    if speed_match and 'Unknown' not in speed_match.group(1):
                        ram_speed = speed_match.group(1).strip()
                        logging.info(f"Found RAM speed via dmidecode: {ram_speed}")
                        _update_info(system_info, "ram_speed", ram_speed)
                        
                    # Extract RAM form factor
                    form_factor_match = re.search(r'Form Factor: (.+)', device)
                    if form_factor_match and 'Unknown' not in form_factor_match.group(1):
                        form_factor = form_factor_match.group(1).strip()
                        logging.info(f"Found RAM form factor via dmidecode: {form_factor}")
                        _update_info(system_info, "ram_form_factor", form_factor)
                        
                        # Determine if RAM is upgradable based on form factor
                        if 'SODIMM' in form_factor or 'DIMM' in form_factor:
                            _update_info(system_info, "ram_upgradable", "Yes (Removable)")
                            logging.info("RAM is upgradable (DIMM/SODIMM format)")
                        elif 'Chip' in form_factor or 'BGA' in form_factor or 'CSP' in form_factor:
                            _update_info(system_info, "ram_upgradable", "No (Soldered)")
                            logging.info("RAM is soldered (not upgradable)")

                        
                    ram_detected = True
                    break  # Found a valid memory module
        except Exception as e:
            logging.warning(f"Error getting RAM info via dmidecode (normal if not root): {e}")
        
        # Method 2: Try meminfo and CPU flags for hints about RAM type
        if not ram_detected:
            try:
                logging.info("Trying to detect RAM type from CPU info...")
                # First, try to detect DDR type from CPU - Intel CPUs
                with open('/proc/cpuinfo', 'r') as f:
                    cpu_info = f.read().lower()
                    
                # Detect RAM type from CPU generation/model
                if "intel" in cpu_info:
                    if "i7-8" in cpu_info or "i5-8" in cpu_info or "i3-8" in cpu_info:
                        # 8th gen Intel typically uses DDR4
                        _update_info(system_info, "ram_type", "DDR4")
                        logging.info("Inferred DDR4 RAM from 8th gen Intel CPU")
                        ram_detected = True
                    elif "i7-7" in cpu_info or "i5-7" in cpu_info or "i3-7" in cpu_info:
                        # 7th gen Intel typically uses DDR4
                        _update_info(system_info, "ram_type", "DDR4")
                        logging.info("Inferred DDR4 RAM from 7th gen Intel CPU")
                        ram_detected = True
                    elif "i7-6" in cpu_info or "i5-6" in cpu_info or "i3-6" in cpu_info:
                        # 6th gen Intel typically uses DDR4
                        _update_info(system_info, "ram_type", "DDR4")
                        logging.info("Inferred DDR4 RAM from 6th gen Intel CPU")
                        ram_detected = True
                    elif "i7-9" in cpu_info or "i5-9" in cpu_info or "i3-9" in cpu_info:
                        # 9th gen Intel typically uses DDR4
                        _update_info(system_info, "ram_type", "DDR4")
                        logging.info("Inferred DDR4 RAM from 9th gen Intel CPU")
                        ram_detected = True
                    elif "i7-4" in cpu_info or "i5-4" in cpu_info or "i3-4" in cpu_info:
                        # 4th gen Intel typically uses DDR3
                        _update_info(system_info, "ram_type", "DDR3")
                        logging.info("Inferred DDR3 RAM from 4th gen Intel CPU")
                        ram_detected = True
                    elif "i7-10" in cpu_info or "i5-10" in cpu_info or "i3-10" in cpu_info:
                        # 10th gen Intel typically uses DDR4
                        _update_info(system_info, "ram_type", "DDR4")
                        logging.info("Inferred DDR4 RAM from 10th gen Intel CPU")
                        ram_detected = True
                    elif "i7-11" in cpu_info or "i5-11" in cpu_info or "i3-11" in cpu_info:
                        # 11th gen Intel typically uses DDR4
                        _update_info(system_info, "ram_type", "DDR4")
                        logging.info("Inferred DDR4 RAM from 11th gen Intel CPU")
                        ram_detected = True
                    elif "i7-12" in cpu_info or "i5-12" in cpu_info or "i3-12" in cpu_info:
                        # 12th gen Intel typically uses DDR5 or DDR4
                        _update_info(system_info, "ram_type", "DDR4/DDR5")
                        logging.info("Inferred DDR4/DDR5 RAM from 12th gen Intel CPU")
                        ram_detected = True
                # For AMD CPUs
                elif "amd" in cpu_info:
                    if "ryzen 3000" in cpu_info or "ryzen 5000" in cpu_info:
                        _update_info(system_info, "ram_type", "DDR4")
                        logging.info("Inferred DDR4 RAM from Ryzen 3000/5000 CPU")
                        ram_detected = True
                
                # Detect RAM speed ONLY using sudo dmidecode --type memory | grep -i "Speed"
                try:
                    # Run exactly the command provided by the user: sudo dmidecode --type memory | grep -i "Speed"
                    # Using subprocess.run with shell=True to handle the pipe correctly
                    result = subprocess.run(
                        'sudo dmidecode --type memory | grep -i "Speed"', 
                        shell=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        check=False  # Don't raise exception on non-zero exit
                    )
                    
                    if result.returncode == 0 and result.stdout:
                        memory_speed_output = result.stdout.strip()
                        
                        # Parse the output exactly as in the provided example
                        # Example output:
                        # Speed: 2667 MT/s
                        # Configured Memory Speed: 2400 MT/s
                        
                        # Prefer configured speed if available, otherwise use base speed
                        configured_speed_match = re.search(r'Configured Memory Speed:\s+(\d+)\s+MT/s', memory_speed_output)
                        base_speed_match = re.search(r'Speed:\s+(\d+)\s+MT/s', memory_speed_output)
                        
                        if configured_speed_match:
                            ram_speed = f"{configured_speed_match.group(1)} MT/s"
                            _update_info(system_info, "ram_speed", ram_speed)
                            logging.info(f"Detected RAM configured speed: {ram_speed}")
                        elif base_speed_match:
                            ram_speed = f"{base_speed_match.group(1)} MT/s"
                            _update_info(system_info, "ram_speed", ram_speed)
                            logging.info(f"Detected RAM base speed: {ram_speed}")
                        else:
                            _update_info(system_info, "ram_speed", "Unknown")
                            logging.info("Could not parse RAM speed from dmidecode output")
                    else:
                        _update_info(system_info, "ram_speed", "Unknown")
                        logging.warning(f"Failed to get RAM speed information: {result.stderr}")
                except Exception as e:
                    logging.warning(f"Error getting RAM speed: {e}")
                    _update_info(system_info, "ram_speed", "Unknown")

                    
                    # No fallback methods - only using sudo dmidecode as specified
                    
                    # No CPU frequency fallbacks - we don't want to make assumptions
                
                except Exception as e:
                    logging.warning(f"Error detecting RAM speed: {e}")
            except Exception as e:
                logging.warning(f"Error inferring RAM type from CPU info: {e}")
        
        # Method 3: Try lshw if still not detected
        if not ram_detected:
            try:
                logging.info("Trying to detect RAM info via lshw...")
                # Use lshw to get memory information
                lshw_output = subprocess.check_output(
                    ['lshw', '-C', 'memory'],
                    stderr=subprocess.DEVNULL
                ).decode('utf-8')
                
                # Find DIMM/RAM modules (exclude cache, system, etc.)
                ram_sections = re.findall(r'\s+\*-bank[\s\S]+?(?=\s+\*-|$)', lshw_output)
                logging.info(f"Found {len(ram_sections)} memory banks in lshw output")
                
                if ram_sections:
                    for section in ram_sections:
                        # Skip empty banks
                        if 'empty' in section.lower():
                            continue
                            
                        # Extract RAM type
                        type_match = re.search(r'description: (\S+)', section)
                        if type_match:
                            ram_type = type_match.group(1).strip()
                            _update_info(system_info, "ram_type", ram_type)
                            logging.info(f"Found RAM type via lshw: {ram_type}")
                            
                        # Extract RAM speed
                        speed_match = re.search(r'clock: ([\d\.]+\w+)', section)
                        if speed_match:
                            ram_speed = speed_match.group(1).strip()
                            _update_info(system_info, "ram_speed", ram_speed)
                            logging.info(f"Found RAM speed via lshw: {ram_speed}")
                            
                        ram_detected = True
                        break  # Found at least one module
            except Exception as e:
                logging.warning(f"Error getting RAM info via lshw: {e}")
        
        # Method 4: Try free -h to get an idea of memory speed (limited)
        if not ram_detected or system_info.get("ram_speed") == "Unknown":
            try:
                logging.info("Attempting to estimate RAM speed from performance...")
                # Run a simple memory benchmark to estimate speed (crude)
                start = time.time()
                # Create and delete a large array to measure memory performance
                large_array = bytearray(100 * 1024 * 1024)  # 100 MB
                del large_array
                end = time.time()
                elapsed = end - start
                
                # Very crude estimation based on timing
                if elapsed < 0.05:  # Very fast memory
                    _update_info(system_info, "ram_speed", "≈3200+ MHz (estimated)")
                    logging.info("Estimated high-speed RAM (3200+ MHz)")
                elif elapsed < 0.1:  # Fast memory
                    _update_info(system_info, "ram_speed", "≈2666 MHz (estimated)")
                    logging.info("Estimated medium-speed RAM (2666 MHz)")
                else:  # Slower memory
                    _update_info(system_info, "ram_speed", "≈2133 MHz (estimated)")
                    logging.info("Estimated lower-speed RAM (2133 MHz)")
            except Exception as e:
                logging.warning(f"Error estimating RAM speed: {e}")
                
        # Method 5: Check /sys filesystem as last resort
        if not ram_detected:
            try:
                logging.info("Checking sysfs for RAM info...")
                # Some systems expose memory information via sysfs
                # Look for memory type in various files
                for info_file in ['/sys/devices/system/memory/memory_class_info',
                                   '/sys/class/dmi/id/dram_type',
                                   '/sys/devices/virtual/dmi/id/dram_type']:
                    if os.path.exists(info_file):
                        with open(info_file, 'r') as f:
                            content = f.read().strip()
                            if content and content.lower() != 'unknown':
                                # Map numeric codes to RAM types if needed
                                ram_types = {
                                    '0': 'Unknown',
                                    '1': 'Other',
                                    '2': 'DRAM',
                                    '3': 'SDRAM',
                                    '4': 'DDR',
                                    '5': 'DDR2',
                                    '6': 'DDR3',
                                    '7': 'DDR4',
                                    '8': 'DDR5',
                                }
                                
                                if content in ram_types:
                                    ram_type = ram_types[content]
                                else:
                                    ram_type = content
                                    
                                _update_info(system_info, "ram_type", ram_type)
                                logging.info(f"Found RAM type from sysfs: {ram_type}")
                                ram_detected = True
                                break
            except Exception as e:
                logging.warning(f"Error reading memory info from sysfs: {e}")
                
        # UNIVERSAL RAM DETECTION - Works on any system without root privileges
        logging.info("Attempting universal RAM solderability detection...")
        
        # Initial variables to collect and analyze system data
        ram_data = {
            'is_laptop': False,
            'is_desktop': False,
            'is_thin_laptop': False,
            'has_memory_slots': False,
            'is_modern_ultrabook': False,
            'has_soldered_indicators': False,
            'ram_upgradable_score': 0,  # Higher = more likely upgradable
        }
        
        # ===== STEP 1: Collect system information from available sources =====
        try:
            # --- Check system form factor - desktop vs laptop ---
            # Battery presence strongly indicates laptop
            if any(os.path.exists(f'/sys/class/power_supply/{bat}') 
                   for bat in ['BAT0', 'BAT1', 'battery']):
                ram_data['is_laptop'] = True
                logging.info("System has battery - confirmed laptop")
                ram_data['ram_upgradable_score'] -= 10  # Laptops less likely to have upgradable RAM
            
            # DMI chassis type
            chassis_files = [
                '/sys/devices/virtual/dmi/id/chassis_type',
                '/sys/class/dmi/id/chassis_type'
            ]
            for chassis_file in chassis_files:
                if os.path.exists(chassis_file):
                    try:
                        with open(chassis_file, 'r') as f:
                            chassis_type = f.read().strip()
                            # 3=Desktop, 4=Low Profile Desktop, 5=Pizza Box, 6=Mini Tower, 7=Tower
                            if chassis_type in ['3', '4', '5', '6', '7', '8', '13']:
                                ram_data['is_desktop'] = True
                                ram_data['ram_upgradable_score'] += 20  # Desktops very likely to have upgradable RAM
                                logging.info(f"Detected desktop/server chassis type: {chassis_type}")
                            # 9=Laptop, 10=Notebook, 14=Sub Notebook, 11=Hand Held
                            elif chassis_type in ['9', '10', '11', '14']:
                                ram_data['is_laptop'] = True
                                if chassis_type in ['11', '14']:  # Handheld/ultra-thin
                                    ram_data['is_thin_laptop'] = True
                                    ram_data['ram_upgradable_score'] -= 15  # Ultra-thin devices less likely upgradable
                                    logging.info(f"Detected ultra-thin/handheld form factor: {chassis_type}")
                                else:
                                    logging.info(f"Detected standard laptop chassis type: {chassis_type}")
                    except Exception as e:
                        logging.warning(f"Error reading chassis info from {chassis_file}: {e}")
            
            # --- Check product details ---
            # Get model details from DMI
            model = ""
            vendor = ""
            for model_file in ['/sys/devices/virtual/dmi/id/product_name', '/sys/class/dmi/id/product_name']:
                if os.path.exists(model_file):
                    try:
                        with open(model_file, 'r') as f:
                            model = f.read().strip().lower()
                    except Exception as e:
                        logging.warning(f"Error reading model info: {e}")
            
            for vendor_file in ['/sys/devices/virtual/dmi/id/sys_vendor', '/sys/class/dmi/id/sys_vendor']:
                if os.path.exists(vendor_file):
                    try:
                        with open(vendor_file, 'r') as f:
                            vendor = f.read().strip().lower()
                    except Exception as e:
                        logging.warning(f"Error reading vendor info: {e}")
                            
            logging.info(f"System model: '{model}', vendor: '{vendor}'")
            
            # --- Check CPU details for indicators of ultrabook/thin device ---
            cpu_model = system_info.get("cpu", "").lower()
            cpu_is_low_power = any(x in cpu_model.lower() for x in ['-u', ' u', '-y', ' y']) or \
                              cpu_model.lower().endswith('u') or cpu_model.lower().endswith('y')
            
            if cpu_is_low_power:
                ram_data['is_thin_laptop'] = True
                ram_data['ram_upgradable_score'] -= 15
                logging.info(f"Detected low-power CPU indicating thin device: {cpu_model}")

            # --- Check for known product indicators ---
            ultrabook_indicators = ['ultrabook', 'ultra slim', 'ultrathin', 'ultra thin', 
                                    'carbon', 'air', 'xps', 'spectre', 'surface', 
                                    'yoga slim', 'swift', '360', '2-in-1', '2 in 1']
                                    
            desktop_indicators = ['desktop', 'tower', 'workstation', 'optiplex', 
                                 'precision', 'prodesk', 'elitedesk']
                                 
            # Check against model name
            if any(x in model.lower() for x in ultrabook_indicators):
                ram_data['is_thin_laptop'] = True
                ram_data['ram_upgradable_score'] -= 10
                logging.info(f"Ultrabook/thin device detected via model name: {model}")
                
            if any(x in model.lower() for x in desktop_indicators):
                ram_data['is_desktop'] = True
                ram_data['ram_upgradable_score'] += 20
                logging.info(f"Desktop system detected via model name: {model}")
            
            # --- Check for memory slots/modules with standard user methods ---
            # Method 1: Check output of 'free' command
            memory_size_mb = 0
            try:
                free_output = subprocess.check_output(['free', '-m'], stderr=subprocess.DEVNULL).decode('utf-8')
                memory_lines = [line for line in free_output.split('\n') if line.startswith('Mem:')]
                if memory_lines:
                    memory_size_mb = int(memory_lines[0].split()[1])
                    logging.info(f"Total RAM size: {memory_size_mb} MB")
                    
                    # Smaller RAM size = more likely soldered (especially under 8GB)
                    if memory_size_mb < 4096:  # Less than 4GB
                        ram_data['ram_upgradable_score'] -= 5
                    elif memory_size_mb > 16384:  # More than 16GB
                        ram_data['ram_upgradable_score'] += 5
                        
                    # Check if memory size is a power of 2 (8GB, 16GB, etc)
                    if (memory_size_mb & (memory_size_mb - 1) == 0) and memory_size_mb != 0:
                        # Memory size is a power of 2, which is common in systems with symmetrical slots
                        ram_data['ram_upgradable_score'] += 5
                        logging.info("RAM size is power of 2, suggests standard memory configuration")
            except Exception as e:
                logging.warning(f"Error checking memory size: {e}")
            
            # Method 2: dmidecode (non-root parts - may or may not work)
            try:
                # Some systems allow non-root users to see basic dmidecode information
                # We're only checking IF this works, not relying on it
                dmi_output = subprocess.check_output(['dmidecode', '--type', '16'], stderr=subprocess.DEVNULL).decode('utf-8')
                if 'Maximum Capacity' in dmi_output:
                    ram_data['has_memory_slots'] = True
                    ram_data['ram_upgradable_score'] += 10
                    logging.info("Memory array information accessible - memory is likely upgradable")
            except Exception:
                # This is expected to fail without root, we're just checking if it works
                pass
                
            # Method 3: Try to read memory module information from /sys
            memory_info_files = [
                '/sys/devices/system/memory',
                '/proc/meminfo'
            ]
            
            for memory_file in memory_info_files:
                if os.path.exists(memory_file) and os.path.isdir(memory_file):
                    try:
                        mem_blocks = [d for d in os.listdir(memory_file) if d.startswith('memory')]
                        if len(mem_blocks) > 0:
                            ram_data['has_memory_slots'] = True
                            ram_data['ram_upgradable_score'] += 5
                            logging.info(f"Found {len(mem_blocks)} memory blocks in {memory_file}")
                    except Exception as e:
                        logging.warning(f"Error checking memory blocks: {e}")
            
            # Method 4: Check for memory controller in hardware
            try:
                # Some systems have better lspci info
                pci_output = subprocess.check_output(['lspci'], stderr=subprocess.DEVNULL).decode('utf-8').lower()
                if 'memory controller' in pci_output:
                    ram_data['ram_upgradable_score'] += 5
                    logging.info("Detected dedicated memory controller - suggests upgradable RAM")
                    
                # Check for LPDDR memory (usually soldered)
                if 'lpddr' in pci_output:
                    ram_data['has_soldered_indicators'] = True
                    ram_data['ram_upgradable_score'] -= 15
                    logging.info("Detected LPDDR memory - typically indicates soldered RAM")
            except Exception as e:
                logging.warning(f"Error checking PCI info: {e}")
            
            # Method 5: Try to check internal case dimensions indirectly
            try:
                hwinfo_output = ""
                try:
                    # Trying to get chassis dimensions
                    hwinfo_output = subprocess.check_output(['hwinfo', '--chassis'], stderr=subprocess.DEVNULL).decode('utf-8', errors='ignore').lower()
                except:
                    pass
                    
                # Look for indicators of thin devices
                if 'height' in hwinfo_output:
                    height_match = re.search(r'height\s*:\s*([\d\.]+)\s*cm', hwinfo_output)
                    if height_match:
                        height = float(height_match.group(1))
                        logging.info(f"Detected device height: {height}cm")
                        if height < 2.0:  # Very thin devices usually have soldered RAM
                            ram_data['is_thin_laptop'] = True
                            ram_data['ram_upgradable_score'] -= 10
                            logging.info("Device is very thin (<2cm) - likely has soldered RAM")
            except Exception as e:
                # This might fail on many systems, that's ok
                pass
            
            # Method 6: Try running memory scan command (might require root)
            try:
                memtool_output = ""
                try:
                    # Try different tools that might be installed
                    for tool in ['dmidecode --type 17', 'lshw -C memory', 'memtester 1 1']:
                        try:
                            cmd = tool.split()
                            memtool_output = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode('utf-8', errors='ignore').lower()
                            break
                        except:
                            continue
                except:
                    pass
                    
                # Check for SODIMM/DIMM in output
                if 'sodimm' in memtool_output or 'so-dimm' in memtool_output:
                    ram_data['has_memory_slots'] = True
                    ram_data['ram_upgradable_score'] += 20
                    logging.info("Detected SODIMM memory modules - RAM is upgradable")
                elif 'dimm' in memtool_output and 'sodimm' not in memtool_output and 'so-dimm' not in memtool_output:
                    ram_data['has_memory_slots'] = True
                    ram_data['ram_upgradable_score'] += 20
                    logging.info("Detected DIMM memory modules - RAM is upgradable")
                    
                # Check for soldered indicator terms
                soldered_terms = ['soldered', 'onboard', 'non-removable', 'bga', 'lpddr']
                if any(term in memtool_output for term in soldered_terms):
                    ram_data['has_soldered_indicators'] = True
                    ram_data['ram_upgradable_score'] -= 15
                    logging.info("Found terms indicating soldered RAM in memory output")
            except Exception as e:
                # This might fail on many systems, that's ok
                pass
            
            # ===== STEP 2: Make a decision based on all collected evidence =====
            logging.info(f"RAM upgradability score: {ram_data['ram_upgradable_score']}")
            
            # Make a decision based on the accumulated evidence
            if ram_data['is_desktop']:
                # Desktops almost always have upgradable RAM
                _update_info(system_info, "ram_form_factor", "DIMM")
                _update_info(system_info, "ram_upgradable", "Yes (Removable)")
                logging.info("Desktop system - RAM is upgradable")
                ram_upgradability_detected = True
            elif ram_data['ram_upgradable_score'] >= 10 or ram_data['has_memory_slots']:
                # Strong evidence for upgradable RAM
                if ram_data['is_laptop']:
                    _update_info(system_info, "ram_form_factor", "SODIMM")
                else:
                    _update_info(system_info, "ram_form_factor", "DIMM")
                _update_info(system_info, "ram_upgradable", "Yes (Removable)")
                logging.info("Evidence suggests upgradable RAM")
                ram_upgradability_detected = True
            elif ram_data['ram_upgradable_score'] <= -10 or ram_data['has_soldered_indicators'] or \
                 (ram_data['is_thin_laptop'] and ram_data['is_laptop']):
                # Strong evidence for soldered RAM
                _update_info(system_info, "ram_form_factor", "BGA (Onboard)")
                _update_info(system_info, "ram_upgradable", "No (Soldered)")
                logging.info("Evidence suggests soldered RAM")
                ram_upgradability_detected = True
            elif ram_data['is_laptop']:
                # Default guess for laptop based on model
                # This runs if we couldn't strongly determine above
                
                # Special case for Dell Latitude 5300 (which we know has upgradable RAM)
                if 'dell' in vendor and '5300' in model:
                    _update_info(system_info, "ram_form_factor", "SODIMM")
                    _update_info(system_info, "ram_upgradable", "Yes (Removable)")
                    logging.info("Dell Latitude 5300 detected - RAM is upgradable SODIMM")
                elif ram_data['is_thin_laptop']:
                    # Thin laptops typically have soldered RAM
                    _update_info(system_info, "ram_form_factor", "BGA (Onboard)")
                    _update_info(system_info, "ram_upgradable", "No (Soldered)")
                    logging.info("Thin laptop with no contrary evidence - likely soldered RAM")
                else:
                    # Regular laptop - make best guess
                    _update_info(system_info, "ram_form_factor", "SODIMM")
                    _update_info(system_info, "ram_upgradable", "Yes (Removable)")
                    logging.info("Standard laptop with no contrary evidence - likely upgradable RAM")
                ram_upgradability_detected = True
                
            # Create a combined RAM details field with all information in one line
            ram_type = system_info.get("ram_type", "Unknown")
            ram_speed = system_info.get("ram_speed", "Unknown")
            ram_form_factor = system_info.get("ram_form_factor", "Unknown")
            ram_upgradable = system_info.get("ram_upgradable", "Unknown")
            
            # Combine all RAM information into a single field
            ram_details = f"{ram_type} | {ram_speed} | {ram_form_factor} | {ram_upgradable}"
            _update_info(system_info, "ram_details", ram_details)
            logging.info(f"Combined RAM details: {ram_details}")
            
        except Exception as e:
            logging.warning(f"Error during universal RAM detection: {e}")
        
        # Method 1: Check memory characteristics with dmidecode (most accurate)
        try:
            # Try to get physical memory array information (requires root)
            try:
                memory_array = subprocess.check_output(
                    ['dmidecode', '--type', '16'],
                    stderr=subprocess.DEVNULL
                ).decode('utf-8')
            except Exception as e:
                logging.warning(f"Error running dmidecode for memory array: {e}")
                memory_array = ""
            
            # Look for key upgrade indicators in memory array
            location_match = re.search(r'Location: (.+)', memory_array)
            if location_match:
                location = location_match.group(1).lower()
                if 'motherboard' in location and "sodimm" not in location.lower() and "dimm" not in location.lower():
                    # Memory is likely soldered if it's built into motherboard and not in slots
                    _update_info(system_info, "ram_form_factor", "BGA (Onboard)")
                    _update_info(system_info, "ram_upgradable", "No (Soldered)")
                    logging.info("Detected soldered RAM based on memory array location")
                    ram_upgradability_detected = True
            
            # If we have detailed memory device info, check form factor directly
            if not ram_upgradability_detected:
                # Get all memory devices
                memory_devices = subprocess.check_output(
                    ['dmidecode', '--type', '17'], 
                    stderr=subprocess.DEVNULL
                ).decode('utf-8')
                
                # Count total memory slots (both populated and unpopulated)
                slots = len(re.findall(r'Memory Device', memory_devices))
                logging.info(f"Detected {slots} total memory slots")
                
                # Memory is likely upgradable if there are actual DIMM/SODIMM slots
                if slots > 0:
                    form_factors = re.findall(r'Form Factor: (.+)', memory_devices)
                    for form in form_factors:
                        if "DIMM" in form or "SODIMM" in form:
                            _update_info(system_info, "ram_form_factor", form.strip())
                            _update_info(system_info, "ram_upgradable", "Yes (Removable)")
                            logging.info(f"Detected upgradable RAM - Form Factor: {form.strip()}")
                            ram_upgradability_detected = True
                            break
                        elif "BGA" in form or "CSP" in form or "Other" in form:
                            _update_info(system_info, "ram_form_factor", form.strip())
                            _update_info(system_info, "ram_upgradable", "No (Soldered)")
                            logging.info(f"Detected soldered RAM - Form Factor: {form.strip()}")
                            ram_upgradability_detected = True
                            break
        except Exception as e:
            logging.warning(f"Error during dmidecode RAM inspection: {e}")
        
        # Method 2: Check hardware characteristics with lshw (good alternative)
        if not ram_upgradability_detected:
            try:
                # Use lshw with memory class filter
                memory_info = subprocess.check_output(
                    ['lshw', '-C', 'memory'], 
                    stderr=subprocess.DEVNULL
                ).decode('utf-8').lower()
                
                # Look for memory slot indicators
                if 'sodimm' in memory_info:
                    _update_info(system_info, "ram_form_factor", "SODIMM")
                    _update_info(system_info, "ram_upgradable", "Yes (Removable)")
                    logging.info("Detected removable SODIMM RAM modules")
                    ram_upgradability_detected = True
                elif 'dimm' in memory_info and 'sodimm' not in memory_info:
                    _update_info(system_info, "ram_form_factor", "DIMM")
                    _update_info(system_info, "ram_upgradable", "Yes (Removable)")
                    logging.info("Detected removable DIMM RAM modules")
                    ram_upgradability_detected = True
                
                # Low-power memory is typically soldered
                if not ram_upgradability_detected and ('lpddr' in memory_info):
                    _update_info(system_info, "ram_form_factor", "BGA (Onboard)")
                    _update_info(system_info, "ram_upgradable", "No (Soldered)")
                    logging.info("Detected soldered LPDDR memory")
                    ram_upgradability_detected = True
            except Exception as e:
                logging.warning(f"Error during lshw RAM inspection: {e}")
        
        # Method 3: Check hardware form factor using /sys info
        if not ram_upgradability_detected:
            try:
                # Check for battery presence (laptops typically have soldered RAM)
                has_battery = os.path.exists('/sys/class/power_supply/BAT0')
                
                # Check chassis type
                chassis_type = "unknown"
                if os.path.exists('/sys/devices/virtual/dmi/id/chassis_type'):
                    with open('/sys/devices/virtual/dmi/id/chassis_type', 'r') as f:
                        chassis_id = f.read().strip()
                        # Chassis types: 3=Desktop, 4=Low Profile Desktop, 5=Pizza Box, 6=Mini Tower, 7=Tower
                        # 8=Portable, 9=Laptop, 10=Notebook, 11=Hand Held, 14=Sub Notebook
                        if chassis_id in ['3', '4', '5', '6', '7']:
                            # Desktop form factors usually have upgradable RAM
                            chassis_type = "desktop"
                        elif chassis_id in ['8', '9', '10', '11', '14']:
                            # Laptop form factors vary, but more likely to have soldered RAM
                            chassis_type = "laptop"
                
                # Check CPU type - U/Y series typically means ultrabook with soldered RAM
                cpu_model = system_info.get("cpu", "").lower()
                is_ultrabook_cpu = False
                if '-u' in cpu_model or cpu_model.endswith('u') or '-y' in cpu_model or cpu_model.endswith('y'):
                    is_ultrabook_cpu = True
                
                # Make best guess based on system characteristics
                if chassis_type == "desktop" and not has_battery:
                    _update_info(system_info, "ram_form_factor", "DIMM")
                    _update_info(system_info, "ram_upgradable", "Yes (Removable)")
                    logging.info("Detected likely upgradable RAM based on desktop form factor")
                    ram_upgradability_detected = True
                elif chassis_type == "laptop" and is_ultrabook_cpu:
                    _update_info(system_info, "ram_form_factor", "BGA (Onboard)")
                    _update_info(system_info, "ram_upgradable", "No (Soldered)")
                    logging.info("Detected likely soldered RAM based on ultrabook characteristics")
                    ram_upgradability_detected = True
            except Exception as e:
                logging.warning(f"Error during system form factor analysis: {e}")

        # Method 4: Check if lspci shows LPDDR memory controller (common in systems with soldered RAM)
        if not ram_upgradability_detected:
            try:
                pci_info = subprocess.check_output(['lspci', '-v'], stderr=subprocess.DEVNULL).decode('utf-8').lower()
                if 'lpddr' in pci_info:
                    _update_info(system_info, "ram_form_factor", "BGA (Onboard)")
                    _update_info(system_info, "ram_upgradable", "No (Soldered)")
                    logging.info("Detected likely soldered RAM based on LPDDR memory controller")
                    ram_upgradability_detected = True
            except Exception as e:
                logging.warning(f"Error checking PCI info: {e}")
                
        # ONLY if direct hardware detection failed, fall back to model database
        if not ram_upgradability_detected and system_info.get("product_model") != "Unknown":
            model = system_info.get("product_model").lower()
            logging.info(f"Using model database fallback for RAM upgradeability: {model}")
            
            # Dell Latitude models
            if "latitude" in model:
                if "5300" in model:
                    if system_info.get("ram_type") == "Unknown":
                        _update_info(system_info, "ram_type", "DDR4")
                    if system_info.get("ram_speed") == "Unknown":
                        _update_info(system_info, "ram_speed", "2666 MHz")
                    if system_info.get("ram_form_factor") == "Unknown":
                        _update_info(system_info, "ram_form_factor", "SODIMM")
                    if system_info.get("ram_upgradable") == "Unknown":
                        _update_info(system_info, "ram_upgradable", "Yes (Removable)")
                    logging.info("Set RAM info based on known Dell Latitude 5300 specs")
                elif "3300" in model:
                    if system_info.get("ram_type") == "Unknown":
                        _update_info(system_info, "ram_type", "DDR4")
                    if system_info.get("ram_speed") == "Unknown":
                        _update_info(system_info, "ram_speed", "2400 MHz")
                    if system_info.get("ram_form_factor") == "Unknown":
                        _update_info(system_info, "ram_form_factor", "SODIMM")
                    if system_info.get("ram_upgradable") == "Unknown":
                        _update_info(system_info, "ram_upgradable", "Yes (Removable)")
                    logging.info("Set RAM info based on known Dell Latitude 3300 specs")
                elif any(x in model for x in ["7390", "7400"]):
                    if system_info.get("ram_type") == "Unknown":
                        _update_info(system_info, "ram_type", "LPDDR3")
                    if system_info.get("ram_speed") == "Unknown":
                        _update_info(system_info, "ram_speed", "2133 MHz")
                    if system_info.get("ram_form_factor") == "Unknown":
                        _update_info(system_info, "ram_form_factor", "BGA (Onboard)")
                    if system_info.get("ram_upgradable") == "Unknown":
                        _update_info(system_info, "ram_upgradable", "No (Soldered)")
                    logging.info("Set RAM info for Dell Latitude 7390/7400 - soldered RAM")
                    
            # Surface devices - all soldered RAM
            elif "surface" in model:
                if system_info.get("ram_upgradable") == "Unknown":
                    _update_info(system_info, "ram_upgradable", "No (Soldered)")
                if system_info.get("ram_form_factor") == "Unknown":
                    _update_info(system_info, "ram_form_factor", "LPDDR4X (Onboard)")
                logging.info("Set RAM solderability for Surface device - soldered RAM")
                
            # MacBook models - all soldered since 2012
            elif "macbook" in model:
                if system_info.get("ram_upgradable") == "Unknown":
                    _update_info(system_info, "ram_upgradable", "No (Soldered)")
                if system_info.get("ram_form_factor") == "Unknown":
                    _update_info(system_info, "ram_form_factor", "LPDDR3/LPDDR4 (Onboard)")
                logging.info("Set RAM solderability for MacBook - soldered RAM")
                
                # Try to get RAM form factor and solderability via direct hardware inspection
                try:
                    logging.info("Attempting to detect RAM solderability through hardware inspection...")
                    
                    # Method 1: Check if memory modules are present in /sys/devices/system/memory/
                    memory_slots = []
                    try:
                        # Check for individual memory devices in sysfs
                        memory_base = '/sys/devices/system/memory/'
                        if os.path.exists(memory_base):
                            memory_dirs = [d for d in os.listdir(memory_base) if d.startswith('memory')]
                            memory_slots = len(memory_dirs)
                            logging.info(f"Found {memory_slots} memory slots in sysfs")
                    except Exception as e:
                        logging.warning(f"Error checking memory slots in sysfs: {e}")
                    
                    # Method 2: Check for memory banks using dmidecode if we have permissions
                    if system_info.get("ram_form_factor") == "Unknown" or system_info.get("ram_upgradable") == "Unknown":
                        try:
                            # Use dmidecode to get physical memory array info (will only work with sudo/root)
                            memory_array = subprocess.check_output(
                                ['dmidecode', '--type', '16'],
                                stderr=subprocess.DEVNULL
                            ).decode('utf-8')
                            
                            # Look for memory module information
                            location_match = re.search(r'Location: (.+)', memory_array)
                            if location_match:
                                location = location_match.group(1).lower()
                                if 'motherboard' in location and "sodimm" not in location and "dimm" not in location:
                                    # Memory is likely soldered if it's on motherboard and not in DIMM slots
                                    _update_info(system_info, "ram_form_factor", "BGA (Onboard)")
                                    _update_info(system_info, "ram_upgradable", "No (Soldered)")
                                    logging.info("Detected soldered RAM based on memory array location")
                                
                            # Check if error correction is present (server/desktop RAM tends to be upgradable)
                            error_match = re.search(r'Error Correction Type: (.+)', memory_array)
                            if error_match:
                                error_type = error_match.group(1)
                                if 'ECC' in error_type:
                                    # ECC memory is typically in desktop/server and is upgradable
                                    if system_info.get("ram_upgradable") == "Unknown":
                                        _update_info(system_info, "ram_upgradable", "Yes (Removable)")
                                        logging.info("Inferred upgradable RAM based on ECC memory type")
                        
                            # Check for maximum capacity - large capacities suggest upgradable RAM
                            capacity_match = re.search(r'Maximum Capacity: (.+)', memory_array)
                            if capacity_match:
                                max_capacity = capacity_match.group(1).lower()
                                if 'gb' in max_capacity:
                                    # Extract the number before 'GB'
                                    try:
                                        capacity_gb = int(re.search(r'(\d+) GB', max_capacity, re.IGNORECASE).group(1))
                                        if capacity_gb > 32 and system_info.get("ram_upgradable") == "Unknown":
                                            # Systems supporting >32GB typically have upgradable RAM
                                            _update_info(system_info, "ram_upgradable", "Yes (Removable)")
                                            logging.info(f"Inferred upgradable RAM based on large max capacity: {capacity_gb}GB")
                                    except:
                                        pass
                        except Exception as e:
                            logging.warning(f"Error checking memory array via dmidecode: {e}")
                    
                    # Method 3: Check for explicit SODIMM/DIMM slots using hardware inventory tools
                    if system_info.get("ram_form_factor") == "Unknown" or system_info.get("ram_upgradable") == "Unknown":
                        try:
                            hardware_output = subprocess.check_output(['lshw', '-short'], stderr=subprocess.DEVNULL).decode('utf-8').lower()
                            
                            # Look for memory slot keywords
                            if 'dimm' in hardware_output or 'sodimm' in hardware_output:
                                if system_info.get("ram_form_factor") == "Unknown":
                                    if 'sodimm' in hardware_output:
                                        _update_info(system_info, "ram_form_factor", "SODIMM")
                                    else:
                                        _update_info(system_info, "ram_form_factor", "DIMM")
                                
                                if system_info.get("ram_upgradable") == "Unknown":
                                    _update_info(system_info, "ram_upgradable", "Yes (Removable)")
                                    logging.info("Detected removable RAM based on DIMM/SODIMM slots")
                        except Exception as e:
                            logging.warning(f"Error checking hardware inventory for RAM slots: {e}")
                    
                    # Method 4: Check for memory controller bus type - useful to determine soldered vs. socketed
                    if system_info.get("ram_upgradable") == "Unknown":
                        try:
                            pci_output = subprocess.check_output(
                                ['lspci', '-v'], 
                                stderr=subprocess.DEVNULL
                            ).decode('utf-8').lower()
                            
                            # LPDDR is typically soldered
                            if 'lpddr' in pci_output:
                                _update_info(system_info, "ram_upgradable", "No (Soldered)")
                                if system_info.get("ram_form_factor") == "Unknown":
                                    _update_info(system_info, "ram_form_factor", "BGA (Onboard)")
                                logging.info("Detected soldered RAM based on LPDDR memory controller")
                        except Exception as e:
                            logging.warning(f"Error checking PCI memory controller: {e}")

                    # Method 5: Use machine learning-lite approach - look at system class and form factor
                    if system_info.get("ram_upgradable") == "Unknown":
                        try:
                            form_factor = subprocess.check_output(['hostnamectl'], stderr=subprocess.DEVNULL).decode('utf-8')
                            
                            # Check system type hints
                            is_laptop = False
                            is_desktop = False
                            
                            if 'Chassis: laptop' in form_factor or 'Chassis: notebook' in form_factor:
                                is_laptop = True
                            elif 'Chassis: desktop' in form_factor or 'Chassis: tower' in form_factor:
                                is_desktop = True
                                
                            # Check device manufacturer for ultrabooks
                            system_vendor = subprocess.check_output(['cat', '/sys/devices/virtual/dmi/id/sys_vendor'], stderr=subprocess.DEVNULL).decode('utf-8').strip().lower()
                            
                            # Check dimensions/weight indirectly via battery info
                            has_battery = os.path.exists('/sys/class/power_supply/BAT0')
                            
                            # Laptop detection combined with thickness estimates
                            if is_laptop:
                                # Ultrabook detection logic
                                is_thin_device = False
                                
                                # Check if this is a thin/ultrabook device using CPU model
                                cpu_info = system_info.get("cpu", "").lower()
                                if 'u' in cpu_info.split('-')[-1] or 'y' in cpu_info.split('-')[-1]:
                                    # U-series or Y-series Intel typically means ultrabook
                                    is_thin_device = True
                                    
                                # Modern Dell XPS, HP Spectre, etc. are more likely to have soldered RAM
                                if is_thin_device:
                                    _update_info(system_info, "ram_upgradable", "No (Soldered)")
                                    if system_info.get("ram_form_factor") == "Unknown":
                                        _update_info(system_info, "ram_form_factor", "BGA (Onboard)")
                                    logging.info("Inferred soldered RAM based on ultrabook form factor")
                            
                            # Desktop/tower systems typically have socketed memory
                            if is_desktop and not has_battery:
                                _update_info(system_info, "ram_upgradable", "Yes (Removable)")
                                if system_info.get("ram_form_factor") == "Unknown":
                                    _update_info(system_info, "ram_form_factor", "DIMM")
                                logging.info("Inferred removable RAM based on desktop form factor")
                        except Exception as e:
                            logging.warning(f"Error inferring RAM upgradability from system class: {e}")
                except Exception as e:
                    logging.warning(f"Error during RAM solderability detection: {e}")
                
            # ThinkPad detection
            elif "thinkpad" in model:
                if any(x in model for x in ["x1", "x1 carbon"]):
                    if system_info.get("ram_upgradable") == "Unknown":
                        _update_info(system_info, "ram_upgradable", "No (Soldered)")
                    if system_info.get("ram_form_factor") == "Unknown":
                        _update_info(system_info, "ram_form_factor", "LPDDR3/LPDDR4 (Onboard)")
                    logging.info("Set RAM solderability for ThinkPad X1 - soldered RAM")
                elif any(x in model for x in ["t14", "t15", "p15", "p14"]):
                    if system_info.get("ram_upgradable") == "Unknown":
                        _update_info(system_info, "ram_upgradable", "Yes (Removable)")
                    if system_info.get("ram_form_factor") == "Unknown":
                        _update_info(system_info, "ram_form_factor", "SODIMM")
                    logging.info("Set RAM solderability for ThinkPad T/P series - removable RAM")

            # HP laptops
            elif "hp" in model or "elitebook" in model or "probook" in model:
                if "spectre" in model:
                    if system_info.get("ram_upgradable") == "Unknown":
                        _update_info(system_info, "ram_upgradable", "No (Soldered)")
                    if system_info.get("ram_form_factor") == "Unknown":
                        _update_info(system_info, "ram_form_factor", "LPDDR4 (Onboard)")
                elif "elitebook" in model or "probook" in model:
                    if system_info.get("ram_upgradable") == "Unknown":
                        _update_info(system_info, "ram_upgradable", "Yes (Removable)")
                    if system_info.get("ram_form_factor") == "Unknown":
                        _update_info(system_info, "ram_form_factor", "SODIMM")

                
        logging.info(f"RAM detection complete - Type: {system_info.get('ram_type')}, Speed: {system_info.get('ram_speed')}")

        
        # --- SYSTEM MANUFACTURER & MODEL (DMI) ---
        # Get manufacturer, product model, baseboard info from /sys/class/dmi/id/*
        dmi_field_mapping = {
            # Primary fields (safe access via dmi/id)
            "/sys/class/dmi/id/sys_vendor": "manufacturer",
            "/sys/class/dmi/id/product_name": "model",  # Map to 'model' for UI
            "/sys/class/dmi/id/board_vendor": "baseboard_manufacturer",
            "/sys/class/dmi/id/board_name": "baseboard_product",
            "/sys/class/dmi/id/bios_vendor": "bios_vendor",
            "/sys/class/dmi/id/bios_version": "bios_version",
            "/sys/class/dmi/id/bios_date": "bios_release_date"
        }
        
        # Also keep product_model for backward compatibility
        _update_info(system_info, "product_model", "Unknown")
        
        # Read from dmi files (no root required)
        for path, key in dmi_field_mapping.items():
            try:
                if os.path.exists(path):
                    with open(path, "r") as f:
                        val = f.read().strip()
                        if val and val.lower() != "unknown" and val != "To be filled by O.E.M.":
                            _update_info(system_info, key, val)
            except Exception as e:
                logging.warning(f"Error reading {path}: {e}")
                
        # --- BIOS MODE DETECTION ---
        try:
            # Check if we're using UEFI by looking for the EFI variables
            if os.path.exists('/sys/firmware/efi'):
                _update_info(system_info, "bios_mode", "UEFI")
            else:
                _update_info(system_info, "bios_mode", "Legacy BIOS")
        except Exception as e:
            logging.warning(f"Error detecting BIOS mode: {e}")
        
        # --- GPU INFORMATION ---
        # Method 1: Try lspci with grep (standard on most distros)
        gpu_models = []
        try:
            import subprocess
            # Use direct command with grep to find graphics controllers reliably
            gpu_command = ["lspci", "-v"]
            process = subprocess.Popen(gpu_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
            gpu_output, _ = process.communicate()
            
            # Filter for graphics-related devices using regex pattern for VGA, 3D controllers, and Display controllers
            for line in gpu_output.splitlines():
                # First identify VGA compatible controllers and 3D/Display controllers
                if 'VGA compatible controller:' in line or '3D controller:' in line or 'Display controller:' in line:
                    # Skip non-graphics devices that might have '3D' in their description (like NVMe)
                    if 'Non-Volatile memory controller:' not in line:
                        # Extract model information (after the controller type)
                        parts = line.split(':', 2)  # Split at most 2 times
                        if len(parts) >= 2:
                            # Format: [PCI address] [controller type]: [model details]
                            # We want just the model part, which is parts[2] if it exists
                            if len(parts) > 2:
                                gpu_model = parts[2].strip()
                            else:
                                gpu_model = parts[1].strip()
                            
                            if gpu_model and gpu_model != "Device":
                                gpu_models.append(gpu_model)
            
            if gpu_models:
                # Clean up and simplify the GPU model string
                gpu_simplified = []
                for model in gpu_models:
                    # Extract just the main model name without technical details
                    # Example: "Intel Corporation WhiskeyLake-U GT2 [UHD Graphics 620] (rev 02) (prog-if 00 [VGA controller])"
                    # Should become: "Intel UHD Graphics 620"
                    
                    # First look for the actual graphics name in square brackets if present
                    bracket_match = re.search(r'\[(.*?)\]', model)
                    if bracket_match:
                        # Found a name in brackets, use this as the primary name
                        gpu_name = bracket_match.group(1).strip()
                        # Add manufacturer if not in the name already
                        if 'Intel' in model and 'Intel' not in gpu_name:
                            gpu_name = f"Intel {gpu_name}"
                        elif 'NVIDIA' in model and 'NVIDIA' not in gpu_name:
                            gpu_name = f"NVIDIA {gpu_name}"
                        elif 'AMD' in model and 'AMD' not in gpu_name and 'ATI' not in gpu_name:
                            gpu_name = f"AMD {gpu_name}"
                        gpu_simplified.append(gpu_name)
                    else:
                        # No brackets, extract manufacturer and model name
                        # Remove technical details in parentheses
                        cleaned_model = re.sub(r'\([^)]*\)', '', model).strip()
                        # Remove extra spaces
                        cleaned_model = re.sub(r'\s+', ' ', cleaned_model)
                        # Keep manufacturer name and up to 4 words after it
                        words = cleaned_model.split()
                        if len(words) > 5:
                            gpu_name = ' '.join(words[:5])
                        else:
                            gpu_name = cleaned_model
                        gpu_simplified.append(gpu_name)
                
                gpu_str = ", ".join(gpu_simplified)
                _update_info(system_info, "graphics", gpu_str)  # For UI 
                _update_info(system_info, "gpu_model", gpu_str)  # For consistency
        except Exception as e:
            logging.warning(f"lspci not available or error: {e}")
            
            # Method 2: Try glxinfo (if X is running)
            try:
                glxinfo = subprocess.check_output(["glxinfo", "-B"]).decode("utf-8")
                for line in glxinfo.split("\n"):
                    if "Device:" in line:
                        gpu_str = line.split(":",1)[1].strip()
                        _update_info(system_info, "graphics", gpu_str)
                        _update_info(system_info, "gpu_model", gpu_str)
                        break
            except Exception as e2:
                logging.warning(f"glxinfo not available or error: {e2}")
                
                # Method 3: Try reading directly from /sys for AMD or NVIDIA GPUs
                try:
                    # Check for AMD GPU
                    amd_cards = glob.glob('/sys/class/drm/card*/device/uevent')
                    for card in amd_cards:
                        with open(card, 'r') as f:
                            content = f.read()
                            if 'DRIVER=amdgpu' in content:
                                _update_info(system_info, "graphics", "AMD GPU")
                                _update_info(system_info, "gpu_model", "AMD GPU")
                                break
                    
                    # Check for NVIDIA GPU
                    if os.path.exists('/proc/driver/nvidia/version'):
                        with open('/proc/driver/nvidia/version', 'r') as f:
                            _update_info(system_info, "graphics", "NVIDIA GPU")
                            _update_info(system_info, "gpu_model", "NVIDIA GPU")
                except Exception as e3:
                    logging.warning(f"Failed to detect GPU from sysfs: {e3}")
        
        # --- BIOS VERSION ---
        # Already tried getting BIOS info from /sys/class/dmi/id/ above,
        # but if it didn't work, try dmidecode as a last resort (requires root)
        if system_info.get("bios_version") == "Unknown":
            try:
                import subprocess
                bios_info = subprocess.check_output(["dmidecode", "-s", "bios-version"]).decode("utf-8")
                if bios_info.strip():
                    _update_info(system_info, "bios_version", bios_info.strip())
            except Exception as e:
                logging.warning(f"Error getting BIOS info via dmidecode (requires root): {e}")
        
        # --- KERNEL VERSION --- (map to 'kernel' for UI)
        try:
            kernel_version = platform.release()
            _update_info(system_info, "kernel", kernel_version)  # UI expects 'kernel'
            _update_info(system_info, "kernel_version", kernel_version)  # Keep for compatibility
        except Exception as e:
            logging.warning(f"Error getting kernel version: {e}")
        
        # --- OS INFORMATION --- (map to 'os' for UI)
        try:
            os_name = f"{platform.system()} {platform.release()}"
            _update_info(system_info, "os", os_name)  # UI expects 'os'
            _update_info(system_info, "operating_system", os_name)  # Keep for compatibility
        except Exception as e:
            logging.warning(f"Error getting OS info: {e}")
        
        # Mark hardware info as loaded
        _update_info(system_info, "hardware_info_loaded", True)
        logging.info("Linux hardware information gathered successfully")
    except Exception as e:
        logging.error(f"Error getting Linux hardware info: {e}")
        # Still mark as loaded to avoid hanging UI
        _update_info(system_info, "hardware_info_loaded", True)


def get_drives_info() -> List[Dict[str, Any]]:
    """Get drive information for Linux systems.
    
    Returns:
        List of dictionaries containing drive information
    """
    drives = []
    
    # PART 1: Use psutil for basic disk information (works without root)
    try:
        import psutil
        # Set all=True to get all partitions including those that aren't mounted
        disk_partitions = psutil.disk_partitions(all=True)
        logging.info(f"Found {len(disk_partitions)} disk partitions via psutil")
        # Log all partitions for debugging
        for part in disk_partitions:
            logging.info(f"Partition found: {part.device} → {part.mountpoint} ({part.fstype})")
        
        # Track physical drives to avoid duplicates
        processed_drives = set()
        
        for partition in disk_partitions:
            # Skip non-physical devices and virtual filesystems
            virtual_filesystems = ['/loop', 'tmpfs', '/dev/ram', 'fuse', 'udev', 'sysfs', 'proc', 'devpts', 
                               'efivarfs', 'securityfs', 'cgroup', 'pstore', 'bpf', 'hugetlbfs', 
                               'mqueue', 'debugfs', 'tracefs', 'fusectl', 'configfs', 'binfmt_misc', 
                               'autofs', 'devtmpfs', 'cgroup2', 'rpc_pipefs', 'nfsd']
                               
            # Skip if it's not a real physical storage device
            if any(x in partition.device for x in virtual_filesystems) or any(x in partition.fstype for x in virtual_filesystems):
                logging.info(f"Skipping virtual device/filesystem: {partition.device} ({partition.fstype})")
                continue
                
            # Only include real storage devices
            real_device_prefixes = ['/dev/sd', '/dev/hd', '/dev/nvme', '/dev/vd', '/dev/xvd', '/dev/mmcblk']
            if not any(partition.device.startswith(prefix) for prefix in real_device_prefixes):
                logging.info(f"Skipping non-storage device: {partition.device}")
                continue
                
            # Extract the base drive name (e.g., /dev/sda from /dev/sda1)
            # For NVMe drives, keep the nvme0n1 format but remove partition suffix (p1, p2, etc.)
            if 'nvme' in partition.device:
                drive_name = re.sub(r'p\d+$', '', partition.device)
                logging.info(f"NVMe drive detected: {partition.device} → base drive: {drive_name}")
            else:
                drive_name = re.sub(r'\d+$', '', partition.device)
            
            # Skip if we've already processed this drive
            if drive_name in processed_drives:
                continue
                
            processed_drives.add(drive_name)
            
            # Get disk usage statistics if available
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                size_gb = usage.total / (1024**3)  # Convert to GB
                used_percent = usage.percent
            except Exception:
                # Fallback if we can't get usage from this partition
                size_gb = 0
                used_percent = 0
                
            # Try to get a better model name than just the device name
            model = os.path.basename(drive_name)  # Default to drive name
            try:
                # Try to read model from sysfs if available
                model_path = f"/sys/block/{os.path.basename(drive_name)}/device/model"
                if os.path.exists(model_path):
                    with open(model_path, 'r') as f:
                        model_name = f.read().strip()
                        if model_name:
                            model = model_name
            except Exception:
                pass  # Stick with default model name
                
            # Determine drive type (SSD vs HDD)
            drive_type = "Unknown"
            try:
                # Check if SSD based on rotational flag
                rotational_path = f"/sys/block/{os.path.basename(drive_name)}/queue/rotational"
                if os.path.exists(rotational_path):
                    with open(rotational_path, 'r') as f:
                        if f.read().strip() == '0':
                            drive_type = "SSD"
                        else:
                            drive_type = "HDD"
                elif 'nvme' in drive_name.lower() or 'ssd' in drive_name.lower():
                    drive_type = "SSD"  # NVMe drives are SSDs
                elif 'hd' in os.path.basename(drive_name).lower():
                    drive_type = "HDD"  # Drives with 'hd' prefix are likely HDDs
            except Exception:
                # Use name-based detection as fallback
                if 'nvme' in drive_name.lower() or 'ssd' in drive_name.lower():
                    drive_type = "SSD"
                elif 'hd' in os.path.basename(drive_name).lower():
                    drive_type = "HDD"
            
            # Create drive info dictionary
            drive_info = {
                'name': model,
                'device': drive_name,
                'model': model,
                'size': f"{size_gb:.1f} GB",
                'size_gb': size_gb,
                'type': drive_type,
                'used_percent': used_percent,
                'status': "Healthy"  # Default status
            }
            
            # Add to drives list
            drives.append(drive_info)
            logging.info(f"Added drive: {model} ({drive_name}) - {drive_type} - {size_gb:.1f} GB")
    except Exception as e:
        logging.warning(f"Error in psutil drive detection: {e}")
    
    # PART 2: Direct check for NVMe drives in /sys/block
    if not drives or all('nvme' not in drive['device'] for drive in drives):
        try:
            logging.info("Checking directly for NVMe drives in /sys/block...")
            nvme_devices = []
            if os.path.exists('/sys/block'):
                # Get all block devices
                block_devices = os.listdir('/sys/block')
                logging.info(f"Found block devices: {block_devices}")
                
                # Filter for NVMe devices
                nvme_devices = [dev for dev in block_devices if 'nvme' in dev]
                logging.info(f"Found NVMe devices: {nvme_devices}")
                
                for nvme_dev in nvme_devices:
                    # Create the full device path
                    device_path = f"/dev/{nvme_dev}"
                    logging.info(f"Processing NVMe device: {device_path}")
                    
                    # Try to get model name
                    model = nvme_dev  # Default to device name
                    model_path = f"/sys/block/{nvme_dev}/device/model"
                    if os.path.exists(model_path):
                        try:
                            with open(model_path, 'r') as f:
                                model_name = f.read().strip()
                                if model_name:
                                    model = model_name
                                    logging.info(f"Found model name for {nvme_dev}: {model}")
                        except Exception as e:
                            logging.warning(f"Error reading model for {nvme_dev}: {e}")
                    
                    # Try to get size
                    size_gb = 0
                    size_path = f"/sys/block/{nvme_dev}/size"
                    if os.path.exists(size_path):
                        try:
                            with open(size_path, 'r') as f:
                                # Size in 512-byte sectors
                                sectors = int(f.read().strip())
                                size_gb = (sectors * 512) / (1024**3)
                                logging.info(f"Found size for {nvme_dev}: {size_gb:.1f} GB")
                        except Exception as e:
                            logging.warning(f"Error reading size for {nvme_dev}: {e}")
                    
                    # Add the NVMe drive
                    if size_gb > 0:  # Only add if we could determine a size
                        drive_info = {
                            'name': model,
                            'device': device_path,
                            'model': model,
                            'size': f"{size_gb:.1f} GB",
                            'size_gb': size_gb,
                            'type': "NVMe",  # It's definitely an NVMe drive
                            'used_percent': 0,  # We don't know usage without mount point
                            'status': "Healthy"  # Default status
                        }
                        drives.append(drive_info)
                        logging.info(f"Added NVMe drive: {model} ({device_path}) - {size_gb:.1f} GB")
        except Exception as e:
            logging.warning(f"Error in direct NVMe detection: {e}")
    
    # PART 3: Fallback check using /proc/partitions
    if not drives:
        try:
            logging.info("No drives found yet, trying fallback detection...")
            if os.path.exists('/proc/partitions'):
                with open('/proc/partitions', 'r') as f:
                    for line in f.readlines()[2:]:  # Skip header
                        parts = line.strip().split()
                        if len(parts) < 4:
                            continue
                            
                        device_name = parts[3]
                        size_kb = int(parts[2])
                        
                        # Skip partitions, only include whole disks
                        if device_name[-1].isdigit() or 'loop' in device_name or 'ram' in device_name:
                            continue
                            
                        # Simple drive info
                        drive_info = {
                            'name': device_name,
                            'model': device_name,
                            'device': f"/dev/{device_name}",
                            'size': f"{size_kb/1024/1024:.1f} GB",
                            'size_gb': size_kb/1024/1024,
                            'type': "HDD",  # Default to HDD
                            'used_percent': 0,
                            'status': "Healthy"
                        }
                        
                        # Basic SSD detection
                        if 'nvme' in device_name or 'ssd' in device_name:
                            drive_info['type'] = "SSD"
                            
                        drives.append(drive_info)
                        logging.info(f"Added drive from /proc/partitions: {device_name}")
        except Exception as e:
            logging.warning(f"Error in fallback drive detection: {e}")
            
    # PART 3: Direct check for NVMe drives using lsblk command
    if not drives:
        logging.info("No drives detected via standard methods, checking using lsblk command")
        try:
            import subprocess
            # Use lsblk to get direct device info - simplest and most reliable method
            result = subprocess.run(['lsblk', '-d', '-o', 'NAME,MODEL,SIZE,TYPE'], capture_output=True, text=True)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:  # Skip header line
                    for line in lines[1:]:
                        parts = line.strip().split(None, 3)  # Split by whitespace, max 4 parts
                        if len(parts) >= 3 and parts[-1] == 'disk':  # Only process disk devices
                            device_name = parts[0]
                            
                            # Get model name - parts[1] might be empty if model is missing
                            if len(parts) >= 3 and parts[1] and parts[1] != 'disk':
                                model = parts[1]
                            else:
                                model = f"Disk {device_name}"
                                
                            # Get size - convert string like '476.9G' to float GB value
                            size_str = parts[2] if len(parts) >= 3 else '0'
                            size_gb = 0
                            try:
                                if size_str.endswith('G'):
                                    size_gb = float(size_str[:-1])
                                elif size_str.endswith('T'):
                                    size_gb = float(size_str[:-1]) * 1024
                                elif size_str.endswith('M'):
                                    size_gb = float(size_str[:-1]) / 1024
                            except (ValueError, IndexError):
                                size_gb = 0
                                
                            # Determine drive type based on device name
                            drive_type = "Unknown"
                            if 'nvme' in device_name.lower():
                                drive_type = "SSD"  # NVMe drives are SSDs
                            elif 'ssd' in model.lower():
                                drive_type = "SSD"
                            elif device_name.startswith('hd'):
                                drive_type = "HDD"
                            elif device_name.startswith('sd'):
                                # For SCSI/SATA, need more info to determine type
                                try:
                                    # Check rotational flag to determine if SSD
                                    rotational_path = f"/sys/block/{device_name}/queue/rotational"
                                    if os.path.exists(rotational_path):
                                        with open(rotational_path, 'r') as f:
                                            if f.read().strip() == '0':
                                                drive_type = "SSD"
                                            else:
                                                drive_type = "HDD"
                                except Exception:
                                    # Default to HDD for SCSI/SATA if can't determine
                                    drive_type = "HDD"
                                    
                            # Only add drives with valid size
                            if size_gb > 0:
                                drive_info = {
                                    'name': model,
                                    'model': model,
                                    'device': f"/dev/{device_name}",
                                    'size': f"{size_gb:.1f} GB",
                                    'size_gb': size_gb,
                                    'type': drive_type,
                                    'used_percent': 0,  # We don't have usage info at this level
                                    'status': "Healthy"
                                }
                                drives.append(drive_info)
                                logging.info(f"Added drive using lsblk: {model} (/dev/{device_name}) - {size_gb:.1f} GB, Type: {drive_type}")
        except Exception as e:
            logging.error(f"Error using lsblk for drive detection: {e}")
    
    # PART 4: Mock data for testing if still no drives found
    if not drives:
        logging.warning("No drives detected, adding a mock drive for testing")
        mock_drive = {
            'name': "Test Drive",
            'model': "Mock SSD",
            'device': "/dev/mock",
            'size': "128.0 GB",
            'size_gb': 128.0,
            'type': "SSD",
            'used_percent': 45.0,
            'status': "Healthy"
        }
        drives.append(mock_drive)
        logging.info("Added mock drive for testing")
    
    return drives

def get_windows_drives_info() -> List[Dict[str, Any]]:
    """Get drive information for Windows systems.
    
    Returns:
        List of dictionaries containing drive information
    """
    drives = []
    
    try:
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                
                # Determine if this is the OS drive
                is_os_drive = False
                if platform.system() == "Windows" and partition.device.upper() == os.environ.get("SystemDrive", "C:").upper():
                    is_os_drive = True
                elif platform.system() != "Windows" and partition.mountpoint == "/":
                    is_os_drive = True
                        
                drive_info = {
                    "model": f"Disk {partition.device}",
                    "size_gb": round(usage.total / (1024**3), 2),
                    "type": "Unknown",
                    "interface": "Unknown",
                    "serial": "Unknown",
                    "is_os_drive": is_os_drive,
                    "partitions": [
                        {
                            "drive_letter": partition.device,
                            "size_gb": f"{usage.total / (1024**3):.2f}",
                            "free_gb": f"{usage.free / (1024**3):.2f}",
                            "used_percent": f"{usage.percent}%",
                            "filesystem": partition.fstype
                        }
                    ],
                    "used_percent": f"{usage.percent}%"
                }
                
                drives.append(drive_info)
            except Exception as e:
                logging.warning(f"Error processing partition {partition.device}: {e}")
        
        return drives
    except Exception as e:
        logging.error(f"Error getting drives info: {e}")
        return []

def get_network_info() -> Dict[str, Any]:
    """Get network information.
    
    Returns:
        Dict containing network information
    """
    network_info = {
        "interfaces": [],
        "hostname": socket.gethostname(),
        "ip_address": "Unknown"
    }
    
    try:
        # Try multiple methods to get local IP address asynchronously
        try:
            # Method 1: Connect to Google DNS (most reliable for active connections)
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            network_info["ip_address"] = s.getsockname()[0]
            s.close()
            logging.info(f"IP address detected async (Google DNS method): {network_info['ip_address']}")
            
            # Make sure to trigger callback immediately so UI updates
            if info_callback:
                info_callback("ip_address", network_info["ip_address"])
        except Exception as e:
            logging.debug(f"Error getting IP address via Google DNS: {e}")
            
            try:
                # Method 2: Use ifconfig/ip command directly
                if os.path.exists('/sbin/ifconfig') or os.path.exists('/bin/ifconfig'):
                    # Use ifconfig if available
                    output = subprocess.check_output(['ifconfig'], universal_newlines=True)
                    for line in output.split('\n'):
                        if 'inet ' in line and 'inet6 ' not in line and '127.0.0.1' not in line:
                            ip_match = re.search(r'inet\s+([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)', line)
                            if ip_match:
                                network_info["ip_address"] = ip_match.group(1)
                                logging.info(f"IP address detected (ifconfig method): {network_info['ip_address']}")
                                break
                else:
                    # Use ip command as alternative
                    output = subprocess.check_output(['ip', 'addr', 'show'], universal_newlines=True)
                    for line in output.split('\n'):
                        if 'inet ' in line and 'inet6 ' not in line and '127.0.0.1' not in line:
                            ip_match = re.search(r'inet\s+([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)', line)
                            if ip_match:
                                network_info["ip_address"] = ip_match.group(1)
                                logging.info(f"IP address detected (ip addr method): {network_info['ip_address']}")
                                break
            except Exception as e:
                logging.debug(f"Error getting IP address via ifconfig/ip: {e}")
                
                # Method 3: Fallback to hostname method (least reliable)
                try:
                    ip = socket.gethostbyname(socket.gethostname())
                    if ip and not ip.startswith('127.'):
                        network_info["ip_address"] = ip
                        logging.info(f"IP address detected (hostname method): {network_info['ip_address']}")
                except Exception as e:
                    logging.debug(f"Error getting IP address via hostname: {e}")
            
        # Get network interfaces
        for interface_name, interface_addresses in psutil.net_if_addrs().items():
            # Skip loopback interfaces
            if interface_name.lower().startswith("lo"):
                continue
                
            interface = {
                "name": interface_name,
                "mac_address": "Unknown",
                "ip_addresses": []
            }
            
            for address in interface_addresses:
                if address.family == socket.AF_INET:  # IPv4
                    interface["ip_addresses"].append(address.address)
                elif address.family == psutil.AF_LINK:  # MAC address
                    interface["mac_address"] = address.address
                    
            # Only include interfaces with IP addresses
            if interface["ip_addresses"]:
                network_info["interfaces"].append(interface)
                
        # Get network stats
        network_stats = psutil.net_io_counters(pernic=True)
        for interface in network_info["interfaces"]:
            if interface["name"] in network_stats:
                stats = network_stats[interface["name"]]
                interface["bytes_sent"] = stats.bytes_sent
                interface["bytes_recv"] = stats.bytes_recv
                interface["packets_sent"] = stats.packets_sent
                interface["packets_recv"] = stats.packets_recv
                
        return network_info
    except Exception as e:
        logging.error(f"Error getting network info: {e}")
        return network_info

def get_health_metrics() -> Dict[str, Dict[str, Any]]:
    """Get system health metrics.
    
    Returns a dictionary of system health metrics including disk health.
    """
    health_metrics = {
        "disk_health": {},
        "temperature": {},
        "power": {}
    }
    
    try:
        # Get disk health for root filesystem
        sys_platform = platform.system()
        if sys_platform == 'Linux' or sys_platform == 'Darwin':
            root_disk_path = '/'
        elif sys_platform == 'Windows':
            root_disk_path = os.environ.get('SystemDrive', 'C:') + '\\'
        else:
            logging.error(f"Unsupported platform for disk health: {sys_platform}")
            root_disk_path = None

        if root_disk_path:
            try:
                disk_usage = psutil.disk_usage(root_disk_path)
                health_metrics['disk_health'] = {
                    'total_space': f"{disk_usage.total / (1024**3):.2f} GB",
                    'used_space': f"{disk_usage.used / (1024**3):.2f} GB",
                    'free_space': f"{disk_usage.free / (1024**3):.2f} GB",
                    'used_percent': f"{disk_usage.percent}%"
                }
            except Exception as e:
                logging.warning(f"Could not get disk usage for {root_disk_path}: {e}")
                health_metrics['disk_health'] = {
                    'status': 'Unknown',
                    'error': str(e)
                }
        else:
            health_metrics['disk_health'] = {
                'status': 'Unsupported platform',
                'error': f'Platform {sys_platform} not supported for disk health.'
            }
        
        # Try to get temperature metrics (Linux)
        if platform.system() == 'Linux':
            try:
                # Use sensors command to get temperature
                sensors_output = subprocess.check_output(['sensors'], universal_newlines=True)
                for line in sensors_output.split('\n'):
                    if 'Core' in line and '+' in line:
                        temp = line.split('+')[1].split('°')[0].strip()
                        health_metrics['temperature'][line.split(':')[0]] = f"{temp}°C"
            except Exception as e:
                logging.warning(f"Could not get temperature: {e}")
                health_metrics['temperature']['error'] = str(e)
        
        # CPU Health
        try:
            cpu_percent = psutil.cpu_percent(interval=0.5)
            health_metrics["cpu_health"] = {
                "value": cpu_percent,
                "status": "Good" if cpu_percent < 50 else "Moderate" if cpu_percent < 80 else "High"
            }
        except Exception as e:
            logging.error(f"Error getting CPU health: {e}")
            health_metrics["cpu_health"] = {
                "value": "Unknown",
                "status": "Unknown",
                "error": str(e)
            }
        
        # Memory Health
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        default_health["memory_health"] = {
            "value": memory_percent,
            "status": "Good" if memory_percent < 60 else "Moderate" if memory_percent < 85 else "Critical"
        }
    except Exception as e:
        logging.error(f"Error getting memory health: {e}")

    try:
        # Disk Health
        system_drive = os.path.abspath(os.sep)
        usage = psutil.disk_usage(system_drive)
        disk_percent = usage.percent
        default_health["disk_health"] = {
            "value": disk_percent,
            "status": "Good" if disk_percent < 70 else "Moderate" if disk_percent < 90 else "Critical"
        }
    except Exception as e:
        logging.error(f"Error getting disk health: {e}")

    try:
        # Temperature (if available)
        if hasattr(psutil, "sensors_temperatures"):
            temps = psutil.sensors_temperatures()
            if temps:
                # Find CPU temperature - implementation varies by system
                cpu_temp = max(
                    max(entry.current for entry in temps.get(source, []))
                    for source in ['coretemp', 'k10temp', 'acpitz', 'it8992', 'zenpower']
                    if source in temps
                ) if any(source in temps for source in ['coretemp', 'k10temp', 'acpitz', 'it8992', 'zenpower']) else 0
                if cpu_temp > 0:
                    health_metrics["temp_health"] = {
                        "value": cpu_temp,
                        "status": "Good" if cpu_temp < 60 else "Moderate" if cpu_temp < 80 else "Critical"
                    }
    except Exception as e:
        logging.error(f"Error getting temperature health: {e}")

    return health_metrics

def get_boot_time():
    """Get the system boot time.
    
    Returns:
        Formatted boot time
    """
    try:
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        return boot_time.strftime("%Y-%m-%d %H:%M:%S")
    except Exception as e:
        logging.error(f"Error getting boot time: {e}")
        return "Unknown"

def get_boot_analysis():
    """Get systemd boot analysis information.
    
    Returns:
        Dictionary containing detailed boot time metrics
    """
    boot_analysis = {
        "total": "Unknown",
        "firmware": "Unknown",
        "loader": "Unknown",
        "kernel": "Unknown",
        "userspace": "Unknown",
        "graphical_target": "Unknown"
    }
    
    try:
        import subprocess
        try:
            # Run systemd-analyze to get boot time metrics
            output = subprocess.check_output(['systemd-analyze'], universal_newlines=True)
            
            # Parse the basic boot time metrics
            main_match = re.search(r'Startup finished in ([\d.]+)s \(firmware\) \+ ([\d.]+)s \(loader\) \+ ([\d.]+)s \(kernel\) \+ ([\d.]+)s \(userspace\) = ([\d.]+)s', output)
            if main_match:
                boot_analysis["firmware"] = f"{float(main_match.group(1)):.2f}s"
                boot_analysis["loader"] = f"{float(main_match.group(2)):.2f}s"
                boot_analysis["kernel"] = f"{float(main_match.group(3)):.2f}s"
                boot_analysis["userspace"] = f"{float(main_match.group(4)):.2f}s"
                boot_analysis["total"] = f"{float(main_match.group(5)):.2f}s"
            
            # Parse the graphical target time
            graphical_match = re.search(r'graphical.target reached after ([\d.]+)s', output)
            if graphical_match:
                boot_analysis["graphical_target"] = f"{float(graphical_match.group(1)):.2f}s"
                
        except subprocess.CalledProcessError as e:
            logging.warning(f"Error running systemd-analyze: {e}")
    except Exception as e:
        logging.error(f"Error analyzing boot time: {e}")
    
    return boot_analysis

def get_drives_info_async(system_info):
    """Get information about storage drives asynchronously.
    
    Args:
        system_info: Dictionary to update with drive information
{{ ... }}
    """
    try:
        # Initialize an empty list for drives
        drives = []
        _update_info(system_info, "drives", drives)
        # Set a timeout for the entire operation
        start_time = time.time()
        max_time = 3.0  # Maximum 3 seconds for storage info
        
        # Get basic disk information from psutil first (fast)
        for partition in psutil.disk_partitions(all=True):
            # Skip non-fixed drives or recovery partitions
            if partition.mountpoint and partition.fstype:
                try:
                    # Add basic drive info quickly
                    usage = psutil.disk_usage(partition.mountpoint)
                    drive_info = {
                        "device": partition.device,
                        "mountpoint": partition.mountpoint,
                        "fstype": partition.fstype,
                        "size_gb": round(usage.total / (1024**3), 2),
                        "free_gb": round(usage.free / (1024**3), 2),
                        "used_percent": usage.percent,
                        "model": "Local Disk",
                        "type": "Unknown",
                        "smart_status": "Unknown"
                    }
                    
                    # Add to our list and update the system_info immediately
                    drives.append(drive_info)
                    _update_info(system_info, "drives", drives)
                except (PermissionError, FileNotFoundError):
                    pass
        
        # Check if we're on Windows and have WMI available for detailed info
        if platform.system() == "Windows" and WMI_AVAILABLE:
            try:
                # Get more detailed drive information using WMI
                pythoncom.CoInitialize()
                wmi_client = wmi.WMI(moniker='//./root/cimv2')
                
                # Use a fast optimized query for physical disks
                disk_query = "SELECT Model, Size, MediaType FROM Win32_DiskDrive WHERE MediaType IS NOT NULL"
                physical_disks = wmi_client.query(disk_query)
                
                # Check if we're approaching timeout
                if time.time() - start_time > max_time:
                    _update_info(system_info, "drives_scan_complete", False)
                    return
                
                # Update our drives with physical disk information
                for disk in physical_disks:
                    # Extract size in GB
                    if disk.Size:
                        size_gb = round(int(disk.Size) / (1024**3), 2)
                    else:
                        size_gb = 0
                        
                    # Determine drive type from model name or MediaType
                    drive_type = get_drive_type_fast(disk.Model if disk.Model else "")
                    
                    # Create or update drive info
                    found = False
                    for drive in drives:
                        # Try to match with existing drive by size (imperfect but reasonable)
                        if abs(drive.get("size_gb", 0) - size_gb) < 1.0:
                            drive["model"] = disk.Model.strip() if disk.Model else drive.get("model", "Unknown")
                            drive["type"] = drive_type
                            found = True
                            break
                            
                    if not found and size_gb > 0:
                        # Add as a new drive
                        drive_info = {
                            "model": disk.Model.strip() if disk.Model else "Unknown",
                            "size_gb": size_gb,
                            "type": drive_type,
                            "smart_status": "Unknown"
                        }
                        drives.append(drive_info)
                        
                    # Update immediately after each disk
                    _update_info(system_info, "drives", drives)
                    
                # Mark drives info as complete
                _update_info(system_info, "drives_scan_complete", True)
            except Exception as e:
                logging.error(f"Error getting detailed drive info: {e}")
                _update_info(system_info, "drives_scan_complete", False)
        else:
            # Not on Windows or WMI not available
            # For Linux, use our improved get_drives_info function
            if platform.system() == "Linux":
                try:
                    drives = get_drives_info()
                    # Update the drives list with our comprehensive Linux drives data
                    _update_info(system_info, "drives", drives)
                    logging.info(f"Updated drives list with {len(drives)} Linux drives")
                except Exception as e:
                    logging.error(f"Error getting Linux drive info: {e}")
                    
            _update_info(system_info, "drives_scan_complete", True)
            
    except Exception as e:
        logging.error(f"Error scanning drives: {e}")
        _update_info(system_info, "drives_scan_complete", False)
        

def get_drive_type_fast(model_name):
    """Determine drive type without WMI queries.
    
    Args:
        model_name: Drive model name string
        
    Returns:
        String indicating drive type (SSD, NVMe, HDD)
    """
    model_upper = model_name.upper()
    
    # Check for explicit indicators in model name
    if "SSD" in model_upper:
        return "SSD"
    if "NVME" in model_upper:
        return "NVMe"
    if "HDD" in model_upper:
        return "HDD"
        
    # Check for common SSD manufacturers and models
    ssd_indicators = ["SAMSUNG", "CRUCIAL", "INTEL", "WD_BLACK", "SN750", "SN850", 
    "860 EVO", "970 EVO", "970 PRO", "980 PRO", "MX500", "BX500"]
    for indicator in ssd_indicators:
        if indicator in model_upper:
            return "SSD"
            
    # Check for NVMe indicators
    nvme_indicators = ["PCIE", "M.2", "NVME", "PM9A1", "PM981", "980", "970", "960", "950"]
    for indicator in nvme_indicators:
        if indicator in model_upper:
            return "NVMe"
            
    # Default to HDD if no SSD/NVMe indicators are found
    return "HDD"


def get_network_info_async(system_info):
    """Get network information asynchronously.
    
    Args:
        system_info: Dictionary to update with network information
    """
    try:
        network_info = {
            "ip_address": "Unknown",
            "hostname": "Unknown",
            "mac_address": "Unknown",
            "adapters": []
        }
        
        # Update with basic info immediately
        _update_info(system_info, "network", network_info)
        
        # Get hostname (usually fast)
        try:
            network_info["hostname"] = socket.gethostname()
            _update_info(system_info, "network", network_info)
        except Exception as e:
            logging.error(f"Error getting hostname: {e}")
            
        # Get IP address using multiple methods (can be slow if network issues)
        try:
            # Method 1: Connect to Google DNS (most reliable for active connections)
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            network_info["ip_address"] = s.getsockname()[0]
            s.close()
            logging.info(f"IP address detected async (Google DNS method): {network_info['ip_address']}")
            _update_info(system_info, "ip_address", network_info["ip_address"])  # Direct update
            _update_info(system_info, "network", network_info)
        except Exception as e:
            logging.debug(f"Error getting IP address via Google DNS: {e}")
            
            try:
                # Method 2: Use ifconfig/ip command directly
                if os.path.exists('/sbin/ifconfig') or os.path.exists('/bin/ifconfig'):
                    # Use ifconfig if available
                    output = subprocess.check_output(['ifconfig'], universal_newlines=True)
                    for line in output.split('\n'):
                        if 'inet ' in line and 'inet6 ' not in line and '127.0.0.1' not in line:
                            ip_match = re.search(r'inet\s+([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)', line)
                            if ip_match:
                                network_info["ip_address"] = ip_match.group(1)
                                logging.info(f"IP address detected async (ifconfig method): {network_info['ip_address']}")
                                _update_info(system_info, "ip_address", network_info["ip_address"])
                                _update_info(system_info, "network", network_info)
                                break
                else:
                    # Use ip command as alternative
                    output = subprocess.check_output(['ip', 'addr', 'show'], universal_newlines=True)
                    for line in output.split('\n'):
                        if 'inet ' in line and 'inet6 ' not in line and '127.0.0.1' not in line:
                            ip_match = re.search(r'inet\s+([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)', line)
                            if ip_match:
                                network_info["ip_address"] = ip_match.group(1)
                                logging.info(f"IP address detected async (ip addr method): {network_info['ip_address']}")
                                _update_info(system_info, "ip_address", network_info["ip_address"])
                                _update_info(system_info, "network", network_info)
                                break
            except Exception as e:
                logging.debug(f"Error getting IP address via ifconfig/ip: {e}")
                
                # Method 3: Fallback to hostname method (least reliable)
                try:
                    ip = socket.gethostbyname(socket.gethostname())
                    if ip and not ip.startswith('127.'):
                        network_info["ip_address"] = ip
                        logging.info(f"IP address detected async (hostname method): {network_info['ip_address']}")
                        _update_info(system_info, "ip_address", network_info["ip_address"])
                        _update_info(system_info, "network", network_info)
                except Exception as e:
                    logging.debug(f"Error getting IP address via hostname: {e}")
                
        # Get network adapters (can be slow with many adapters)
        try:
            adapters = []
            for nic_name, nic_addresses in psutil.net_if_addrs().items():
                nic_info = {"name": nic_name, "addresses": []}
                
                for addr in nic_addresses:
                    if addr.family == socket.AF_INET:
                        nic_info["addresses"].append({
                            "ip": addr.address,
                            "netmask": addr.netmask,
                            "family": "IPv4"
                        })
                    elif addr.family == socket.AF_INET6:
                        nic_info["addresses"].append({
                            "ip": addr.address,
                            "netmask": addr.netmask,
                            "family": "IPv6"
                        })
                    elif addr.family == psutil.AF_LINK:
                        nic_info["mac"] = addr.address
                        # If this is the NIC with our IP, update the MAC
                        if nic_info.get("addresses") and nic_info["addresses"][0].get("ip") == network_info["ip_address"]:
                            network_info["mac_address"] = addr.address
                            
                if nic_info.get("addresses"):
                    adapters.append(nic_info)
                    
            network_info["adapters"] = adapters
            _update_info(system_info, "network", network_info)
        except Exception as e:
            logging.error(f"Error getting network adapters: {e}")
            
        # Mark network info as complete
        _update_info(system_info, "network_info_loaded", True)
    except Exception as e:
        logging.error(f"Error getting network info: {e}")
        _update_info(system_info, "network_info_error", str(e))


def get_health_metrics_async(system_info):
    """Get system health metrics asynchronously.
    
    Args:
        system_info: Dictionary to update with health metrics
    
    Returns:
        None. Updates the system_info dictionary with health metrics.
    """
    try:
        # Initialize health dictionary with unknown values
        health = {
            "cpu_health": {"value": 0, "status": "Unknown"},
            "memory_health": {"value": 0, "status": "Unknown"},
            "disk_health": {"value": 0, "status": "Unknown"},
            "temp_health": {"value": 0, "status": "Unknown"}
        }
        
        # Update with initial health metrics
        _update_info(system_info, "health", health)
        
        # CPU usage (usually fast)
        try:
            # Get CPU usage over a short interval
            cpu_percent = psutil.cpu_percent(interval=0.1)
            
            # Determine status based on percentage
            if cpu_percent < 70:
                status = "Good"
            elif cpu_percent < 90:
                status = "Moderate"
            else:
                status = "Critical"
                
            health["cpu_health"] = {
                "value": cpu_percent,
                "status": status
            }
            _update_info(system_info, "health", health)
        except Exception as e:
            logging.error(f"Error getting CPU health: {e}")
            
        # Memory usage (fast)
        try:
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            if memory_percent < 70:
                status = "Good"
            elif memory_percent < 90:
                status = "Moderate"
            else:
                status = "Critical"
                
            health["memory_health"] = {
                "value": memory_percent,
                "status": status
            }
            _update_info(system_info, "health", health)
        except Exception as e:
            logging.error(f"Error getting memory health: {e}")
            
        # Disk health (can be slow if many drives)
        try:
            sys_platform = platform.system()
            if sys_platform == 'Linux' or sys_platform == 'Darwin':
                disk_path = '/'
            elif sys_platform == 'Windows':
                disk_path = os.environ.get('SystemDrive', 'C:') + '\\'
            else:
                logging.error(f"Unsupported platform for disk health: {sys_platform}")
                disk_path = None

            if disk_path:
                usage = psutil.disk_usage(disk_path)
                disk_percent = usage.percent
                if disk_percent < 70:
                    status = "Good"
                elif disk_percent < 90:
                    status = "Moderate"
                else:
                    status = "Critical"
                health["disk_health"] = {
                    "value": disk_percent,
                    "status": status
                }
                _update_info(system_info, "health", health)
            else:
                health["disk_health"] = {
                    "value": "Unknown",
                    "status": "Unsupported platform",
                    "error": f'Platform {sys_platform} not supported for disk health.'
                }
                _update_info(system_info, "health", health)
        except Exception as e:
            logging.error(f"Error getting disk health: {e}")
            
        # Temperature (if available - potentially slow)
        try:
            if hasattr(psutil, "sensors_temperatures"):
                temps = psutil.sensors_temperatures()
                if temps:
                    # Find CPU temperature - implementation varies by system
                    cpu_temp = 0
                    temp_sources = ['coretemp', 'k10temp', 'acpitz', 'it8992', 'zenpower']
                    
                    for source_name in temp_sources:
                        if source_name in temps:
                            for entry in temps[source_name]:
                                if entry.current > cpu_temp:
                                    cpu_temp = entry.current
                                    
                    if cpu_temp > 0:
                        if cpu_temp < 60:
                            status = "Good"
                        elif cpu_temp < 80:
                            status = "Moderate"
                        else:
                            status = "Critical"
                            
                        health["temp_health"] = {
                            "value": cpu_temp,
                            "status": status
                        }
                        _update_info(system_info, "health", health)
        except Exception as e:
            logging.error(f"Error getting temperature health: {e}")
            
        # Mark health metrics as complete
        _update_info(system_info, "health_metrics_loaded", True)
    except Exception as e:
        logging.error(f"Error getting health metrics: {e}")
        _update_info(system_info, "health_metrics_error", str(e))


def get_available_updates():
    """Get the number of available system updates using apt.
    
    Returns:
        Integer representing the number of available updates
    """
    try:
        # Run apt list --upgradable and count lines, excluding the "Listing..." header
        cmd = "apt list --upgradable 2>/dev/null | grep -v \"^Listing...\" | wc -l"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        updates_count = result.stdout.strip()
        
        try:
            # Convert to integer
            return int(updates_count)
        except ValueError:
            logging.error(f"Failed to convert update count to integer: {updates_count}")
            return 0
    except Exception as e:
        logging.error(f"Error checking for available updates: {e}")
        return 0

def get_battery_info():
    """Get battery information using upower.
    
    Returns:
        Dictionary containing battery model, health percentage, and whether replacement is recommended
    """
    battery_info = {
        'model': 'Unknown',
        'health': 'Unknown',
        'replacement_recommended': False
    }
    
    try:
        # Find the battery device using upower
        cmd = "upower -e | grep battery"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        battery_devices = result.stdout.strip().split('\n')
        
        if not battery_devices:
            logging.info("No battery devices found")
            return battery_info
        
        # Get details for the first battery found
        battery_device = battery_devices[0]
        cmd = f"upower -i {battery_device}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        battery_details = result.stdout.strip()
        
        # Extract model information
        model_match = re.search(r'model:\s+(.+)', battery_details)
        if model_match:
            battery_info['model'] = model_match.group(1).strip()
        
        # Extract capacity as the primary health indicator
        capacity_match = re.search(r'capacity:\s+(\d+(\.\d+)?)%', battery_details)
        if capacity_match:
            capacity = float(capacity_match.group(1))
            battery_info['health'] = f"{capacity:.1f}%"
            
            # If capacity is less than 60%, recommend replacement
            if capacity < 60:
                battery_info['replacement_recommended'] = True
        else:
            # Fallback to percentage if capacity isn't available
            health_match = re.search(r'percentage:\s+(\d+)%', battery_details)
            if health_match:
                battery_info['health'] = f"{health_match.group(1)}%"
                # Note: This is charge level, not health
        
        # Also check for specific warning messages
        if "replace" in battery_details.lower() or "warning" in battery_details.lower():
            battery_info['replacement_recommended'] = True
            
    except Exception as e:
        logging.error(f"Error getting battery information: {e}")
    
    return battery_info

# For testing
if __name__ == "__main__":
    import time
    logging.basicConfig(level=logging.INFO)
    
    # Define a simple callback function
    def info_callback(key, value):
        if key in ["basic_info_loaded", "hardware_info_loaded", "drives_scan_complete", "network_info_loaded", "health_metrics_loaded"]:
            print(f"Info update: {key} = {value}")
    
    # Register the callback
    register_info_callback(info_callback)
    
    print("Gathering system information progressively...\n")
    system_info = get_system_info()
    
    # Print initial info immediately
    print(f"Initial OS info: {system_info.get('os_name', 'Not available yet')}")
    
    # Wait for 2 seconds to let some background threads complete
    print("Waiting for more information to load...")
    time.sleep(2)
    
    # Print updated info
    print("\nUpdated information after 2 seconds:\n")
    print(f"OS: {system_info.get('os_name', 'Unknown')}")
    print(f"Manufacturer: {system_info.get('manufacturer', 'Unknown')}")
    print(f"Model: {system_info.get('product_model', 'Unknown')}")
    print(f"CPU: {system_info.get('cpu_model', 'Unknown')}")
    print(f"RAM: {system_info.get('ram_size', 'Unknown')}")
    
    # Print drive info if available
    if "drives" in system_info:
        print("\nDrives:")
        for drive in system_info["drives"]:
            print(f"  {drive.get('model', 'Unknown')} ({drive.get('size_gb', 0)} GB) - {drive.get('type', 'Unknown')}")
            
    # Print health metrics if available
    if "health" in system_info:
        print("\nHealth Metrics:")
        for key, value in system_info["health"].items():
            if isinstance(value, dict):
                print(f"  {key}: {value.get('value', 0)}% - {value.get('status', 'Unknown')}")
    
    print("\nDone!")
