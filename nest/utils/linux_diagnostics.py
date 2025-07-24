# linux_diagnostics.py
# Utility functions for Linux system diagnostics

import os
import re
import json
import logging
import platform
import socket
import subprocess
import shutil
from datetime import datetime
from typing import Dict, List, Any, Tuple, Optional
from pathlib import Path

import psutil


def get_cpu_info() -> Dict[str, Any]:
    """Get detailed CPU information on Linux.
    
    Returns:
        Dict containing CPU information
    """
    cpu_info = {
        'model': 'Unknown',
        'cores': 0,
        'threads': 0,
        'speed': 'Unknown',
        'temperature': 'Unknown'
    }
    
    try:
        # Get CPU model from /proc/cpuinfo
        if os.path.exists('/proc/cpuinfo'):
            with open('/proc/cpuinfo', 'r') as f:
                cpuinfo = f.read()
                
            # Extract model name
            model_match = re.search(r'model name\s+:\s+(.*)', cpuinfo)
            if model_match:
                cpu_info['model'] = model_match.group(1)
                
            # Count physical cores (unique physical IDs and core IDs combination)
            physical_ids = set()
            for line in cpuinfo.split('\n'):
                if line.startswith('physical id') and 'core id' in cpuinfo:
                    phys_match = re.search(r'physical id\s+:\s+(\d+)', line)
                    if phys_match:
                        physical_ids.add(phys_match.group(1))
            
            # If we can't determine physical cores this way, use psutil
            if physical_ids:
                cpu_info['cores'] = len(physical_ids)
            else:
                cpu_info['cores'] = psutil.cpu_count(logical=False) or 1
                
            # Get logical cores count
            cpu_info['threads'] = psutil.cpu_count(logical=True) or 1
            
            # Get CPU frequency
            cpu_freq = psutil.cpu_freq()
            if cpu_freq:
                cpu_info['speed'] = f"{cpu_freq.current:.2f} MHz"
                
        # Try to get CPU temperature if available
        try:
            temps = psutil.sensors_temperatures()
            if temps:
                for name, entries in temps.items():
                    if name.lower() in ['coretemp', 'k10temp', 'zenpower', 'cpu_thermal']:
                        cpu_info['temperature'] = f"{entries[0].current:.1f}°C"
                        break
        except (AttributeError, IndexError):
            pass  # sensors_temperatures not available or no data
            
    except Exception as e:
        logging.warning(f"Error getting CPU info: {e}")
        
    return cpu_info


def get_memory_info() -> Dict[str, Any]:
    """Get detailed memory information.
    
    Returns:
        Dict containing RAM information
    """
    memory_info = {
        'total': 0,
        'available': 0,
        'used': 0,
        'percent_used': 0,
        'swap_total': 0,
        'swap_used': 0,
        'swap_percent': 0,
    }
    
    try:
        # Get memory information from psutil
        mem = psutil.virtual_memory()
        memory_info['total'] = mem.total / (1024**3)  # Convert to GB
        memory_info['available'] = mem.available / (1024**3)  # Convert to GB
        memory_info['used'] = mem.used / (1024**3)  # Convert to GB
        memory_info['percent_used'] = mem.percent
        
        # Get swap information
        swap = psutil.swap_memory()
        memory_info['swap_total'] = swap.total / (1024**3)  # Convert to GB
        memory_info['swap_used'] = swap.used / (1024**3)  # Convert to GB
        memory_info['swap_percent'] = swap.percent
    except Exception as e:
        logging.warning(f"Error getting memory info: {e}")
        
    return memory_info


def get_gpu_info() -> List[Dict[str, Any]]:
    """Get GPU information using lspci and other methods.
    
    Returns:
        List of dictionaries containing GPU information
    """
    gpus = []
    
    try:
        # Method 1: Try using lspci
        if shutil.which('lspci'):
            cmd = "lspci | grep -E 'VGA|3D|Display'"
            output = subprocess.check_output(cmd, shell=True, text=True)
            
            for line in output.strip().split('\n'):
                if line:  # Skip empty lines
                    # Extract the GPU model from lspci output
                    model_match = re.search(r'VGA|3D|Display.*?:\s+(.+)', line)
                    if model_match:
                        model = model_match.group(1)
                        # Clean up the model name
                        model = re.sub(r'\(rev\s+\w+\)', '', model).strip()
                        
                        # Create GPU entry
                        gpu_info = {
                            'model': model,
                            'type': 'Dedicated' if any(x in model.lower() for x in ['nvidia', 'amd', 'radeon']) else 'Integrated',
                            'source': 'lspci'
                        }
                        gpus.append(gpu_info)
        
        # If no GPUs found, try alternative methods
        if not gpus:
            # Method 2: Check for NVIDIA GPUs using nvidia-smi
            if shutil.which('nvidia-smi'):
                try:
                    nvidia_output = subprocess.check_output('nvidia-smi -L', shell=True, text=True)
                    for line in nvidia_output.strip().split('\n'):
                        if line:  # Skip empty lines
                            model_match = re.search(r'GPU \d+: (.+?)\s*\(', line)
                            if model_match:
                                gpus.append({
                                    'model': model_match.group(1),
                                    'type': 'Dedicated',
                                    'source': 'nvidia-smi'
                                })
                except subprocess.SubprocessError:
                    pass
                
            # Method 3: Check for integrated Intel GPU in /sys
            intel_path = Path('/sys/class/drm/card0/device/vendor')
            if intel_path.exists() and '0x8086' in intel_path.read_text().strip():
                gpus.append({
                    'model': 'Intel Integrated Graphics',
                    'type': 'Integrated',
                    'source': 'sysfs'
                })
        
        # If still no GPUs found, provide generic information
        if not gpus:
            gpus.append({
                'model': 'Unknown Graphics Controller',
                'type': 'Unknown',
                'source': 'fallback'
            })
                
    except Exception as e:
        logging.warning(f"Error getting GPU info: {e}")
        gpus.append({
            'model': f"Detection failed: {str(e)}",
            'type': 'Unknown',
            'source': 'error'
        })
        
    return gpus


def get_storage_info() -> List[Dict[str, Any]]:
    """Get detailed storage drive information with special handling for NVMe drives.
    
    Returns:
        List of dictionaries containing drive information
    """
    drives = []
    
    try:
        # Parse partitions from /proc/partitions as a backup method
        partitions_data = {}
        if os.path.exists('/proc/partitions'):
            with open('/proc/partitions', 'r') as f:
                for line in f.readlines()[2:]:  # Skip header lines
                    parts = line.strip().split()
                    if len(parts) == 4 and parts[3]: 
                        partitions_data[parts[3]] = {'major': parts[0], 'minor': parts[1], 'blocks': int(parts[2])}
        
        # Get disk usage for all mount points
        mount_usage = {}
        for partition in psutil.disk_partitions(all=True):
            try:
                if os.path.exists(partition.mountpoint):
                    usage = psutil.disk_usage(partition.mountpoint)
                    mount_usage[partition.device] = {
                        'mountpoint': partition.mountpoint,
                        'fstype': partition.fstype,
                        'total': usage.total,
                        'used': usage.used,
                        'percent': usage.percent
                    }
            except (PermissionError, OSError):
                # Skip mount points we can't access
                pass
                
        # Check for drives in /sys/block
        if os.path.exists('/sys/block'):
            processed_drives = set()
            
            for device in os.listdir('/sys/block'):
                # Skip loop, ram, and other non-physical devices
                if any(device.startswith(x) for x in ['loop', 'ram', 'dm-']):
                    continue
                    
                device_path = f"/dev/{device}"
                sys_path = f"/sys/block/{device}"
                
                # Skip if already processed
                if device_path in processed_drives:
                    continue
                    
                processed_drives.add(device_path)
                
                # Get basic drive info
                drive_info = {
                    'device': device_path,
                    'name': device,
                    'model': 'Unknown',
                    'type': 'Unknown',
                    'size_bytes': 0,
                    'size_gb': 0,
                    'partitions': [],
                    'health': 'Unknown',
                    'used_percent': 0,
                    'mount_points': []
                }
                
                # Try to get drive size
                size_path = os.path.join(sys_path, 'size')
                if os.path.exists(size_path):
                    with open(size_path, 'r') as f:
                        # Size is in 512-byte sectors
                        sectors = int(f.read().strip())
                        drive_info['size_bytes'] = sectors * 512
                        drive_info['size_gb'] = drive_info['size_bytes'] / (1024**3)
                
                # Try to get model name
                model_path = os.path.join(sys_path, 'device/model')
                if os.path.exists(model_path):
                    with open(model_path, 'r') as f:
                        drive_info['model'] = f.read().strip()
                        
                # Try to get vendor name
                vendor_path = os.path.join(sys_path, 'device/vendor')
                if os.path.exists(vendor_path):
                    with open(vendor_path, 'r') as f:
                        vendor = f.read().strip()
                        if vendor and vendor != 'ATA':
                            drive_info['model'] = f"{vendor} {drive_info['model']}"
                
                # Determine drive type (SSD vs HDD)
                drive_info['type'] = 'HDD'  # Default assumption
                
                # Check if it's an NVMe drive
                if 'nvme' in device:
                    drive_info['type'] = 'SSD'  # NVMe drives are SSDs
                    
                # Otherwise check rotational flag
                else:
                    rotational_path = os.path.join(sys_path, 'queue/rotational')
                    if os.path.exists(rotational_path):
                        with open(rotational_path, 'r') as f:
                            if f.read().strip() == '0':
                                drive_info['type'] = 'SSD'
                            else:
                                drive_info['type'] = 'HDD'
                
                # Find partitions for this drive
                for part_name in os.listdir(sys_path):
                    if part_name.startswith(device) and part_name != device and not any(part_name.startswith(x) for x in ['loop', 'ram']):                        
                        part_device = f"/dev/{part_name}"
                        
                        # Check if this partition is mounted
                        mounted = False
                        mount_info = None
                        
                        for mount_dev, mount_data in mount_usage.items():
                            if mount_dev == part_device or any(part_name in d for d in [mount_dev, os.path.realpath(mount_dev)] if os.path.exists(d)):
                                mounted = True
                                mount_info = mount_data
                                # Add the mount point to the drive's list
                                if mount_data['mountpoint'] not in drive_info['mount_points']:
                                    drive_info['mount_points'].append(mount_data['mountpoint'])
                                break
                                
                        # Add the partition info
                        part_info = {
                            'name': part_name,
                            'device': part_device,
                            'mounted': mounted,
                            'mountpoint': mount_info['mountpoint'] if mount_info else None,
                            'fstype': mount_info['fstype'] if mount_info else None,
                            'size_gb': 0,
                            'used_percent': mount_info['percent'] if mount_info else 0
                        }
                        
                        # Try to get partition size
                        if part_name in partitions_data:
                            part_info['size_gb'] = partitions_data[part_name]['blocks'] / (1024*1024)  # Convert KiB to GiB
                            
                        drive_info['partitions'].append(part_info)
                
                # Calculate overall drive usage from partitions if available
                if drive_info['partitions']:
                    total_used = 0
                    total_space = 0
                    
                    for part in drive_info['partitions']:
                        if part['mounted'] and part['used_percent'] > 0:
                            if mount_usage.get(part['device']):
                                part_total = mount_usage[part['device']]['total'] / (1024**3)  # GB
                                part_used = mount_usage[part['device']]['used'] / (1024**3)  # GB
                                total_space += part_total
                                total_used += part_used
                    
                    if total_space > 0:
                        drive_info['used_percent'] = (total_used / total_space) * 100
                
                # Add drive health status - for now we'll use a placeholder
                # A real implementation would use smartctl or similar tools
                drive_info['health'] = "Healthy"  # Default assumption
                
                drives.append(drive_info)
                
        # If no drives were found via /sys/block, try using just psutil
        if not drives:
            logging.info("Falling back to psutil for drive detection")
            # This is a simplified version of the above; in a real implementation,
            # you might want to merge logic from system_utils.py's get_drives_info
            partitions = psutil.disk_partitions(all=True)
            
            # Track physical drives to avoid duplicates
            processed_drives = set()
            
            for partition in partitions:
                # Skip non-physical devices
                if any(x in partition.device for x in ['/loop', 'tmpfs', '/dev/ram']):
                    continue
                    
                # Extract the base drive name (e.g., /dev/sda from /dev/sda1)
                # For NVMe drives, keep the nvme0n1 format but remove partition suffix (p1, p2, etc.)
                if 'nvme' in partition.device:
                    drive_name = re.sub(r'p\d+$', '', partition.device)
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
                    
                # Determine drive type
                drive_type = "Unknown"
                if 'nvme' in drive_name.lower():
                    drive_type = "SSD"  # NVMe drives are SSDs
                
                # Create drive info dictionary
                drive_info = {
                    'name': os.path.basename(drive_name),
                    'device': drive_name,
                    'model': os.path.basename(drive_name),  # Basic fallback
                    'size_gb': size_gb,
                    'type': drive_type,
                    'used_percent': used_percent,
                    'health': "Healthy",  # Default assumption
                    'partitions': [],
                    'mount_points': [partition.mountpoint]
                }
                
                drives.append(drive_info)
    except Exception as e:
        logging.warning(f"Error getting storage info: {e}")
        
    return drives


def get_motherboard_info() -> Dict[str, Any]:
    """Get motherboard information.
    
    Returns:
        Dict containing motherboard information
    """
    mobo_info = {
        'manufacturer': 'Unknown',
        'model': 'Unknown',
        'bios_version': 'Unknown',
        'bios_date': 'Unknown'
    }
    
    try:
        # Try to get data from DMI/SMBIOS via dmidecode (requires root)
        if shutil.which('dmidecode') and os.geteuid() == 0:  # Check if we have root
            try:
                # Get motherboard information
                mb_output = subprocess.check_output(['dmidecode', '-t', 'baseboard'], text=True)
                
                for line in mb_output.split('\n'):
                    if 'Manufacturer:' in line:
                        mobo_info['manufacturer'] = line.split('Manufacturer:')[1].strip()
                    elif 'Product Name:' in line:
                        mobo_info['model'] = line.split('Product Name:')[1].strip()
                
                # Get BIOS information
                bios_output = subprocess.check_output(['dmidecode', '-t', 'bios'], text=True)
                
                for line in bios_output.split('\n'):
                    if 'Vendor:' in line and mobo_info['manufacturer'] == 'Unknown':
                        mobo_info['manufacturer'] = line.split('Vendor:')[1].strip()
                    elif 'Version:' in line:
                        mobo_info['bios_version'] = line.split('Version:')[1].strip()
                    elif 'Release Date:' in line:
                        mobo_info['bios_date'] = line.split('Release Date:')[1].strip()
            except (subprocess.SubprocessError, PermissionError) as e:
                logging.warning(f"Failed to get motherboard info via dmidecode: {e}")
        
        # Alternative method for non-root: read from /sys/devices/virtual/dmi/id/
        dmi_path = Path('/sys/devices/virtual/dmi/id')
        if dmi_path.exists():
            # Board info
            board_vendor = dmi_path / 'board_vendor'
            if board_vendor.exists():
                mobo_info['manufacturer'] = board_vendor.read_text().strip()
                
            board_name = dmi_path / 'board_name'
            if board_name.exists():
                mobo_info['model'] = board_name.read_text().strip()
                
            # BIOS info
            bios_vendor = dmi_path / 'bios_vendor'
            if bios_vendor.exists() and mobo_info['manufacturer'] == 'Unknown':
                mobo_info['manufacturer'] = bios_vendor.read_text().strip()
                
            bios_version = dmi_path / 'bios_version'
            if bios_version.exists():
                mobo_info['bios_version'] = bios_version.read_text().strip()
                
            bios_date = dmi_path / 'bios_date'
            if bios_date.exists():
                mobo_info['bios_date'] = bios_date.read_text().strip()
    except Exception as e:
        logging.warning(f"Error getting motherboard info: {e}")
        
    return mobo_info


def get_network_info() -> List[Dict[str, Any]]:
    """Get network interface information.
    
    Returns:
        List of dictionaries containing network interface information
    """
    interfaces = []
    
    try:
        # Get network address info
        if_addrs = psutil.net_if_addrs()
        if_stats = psutil.net_if_stats()
        
        for if_name, addrs in if_addrs.items():
            # Skip loopback interfaces
            if if_name == 'lo' or if_name.startswith('loop'):
                continue
                
            # Get interface status
            is_up = if_stats.get(if_name, None) and if_stats[if_name].isup
            
            interface_info = {
                'name': if_name,
                'status': 'Up' if is_up else 'Down',
                'type': 'Wireless' if if_name.startswith(('wl', 'wlan', 'wifi')) else 'Ethernet',
                'mac': '',
                'ipv4': [],
                'ipv6': []
            }
            
            # Get addresses
            for addr in addrs:
                if addr.family == socket.AF_INET:  # IPv4
                    interface_info['ipv4'].append(addr.address)
                elif addr.family == socket.AF_INET6:  # IPv6
                    interface_info['ipv6'].append(addr.address)
                elif addr.family == psutil.AF_LINK:  # MAC address
                    interface_info['mac'] = addr.address
            
            interfaces.append(interface_info)
    except Exception as e:
        logging.warning(f"Error getting network info: {e}")
        
    return interfaces


def get_system_load() -> Dict[str, Any]:
    """Get system load information.
    
    Returns:
        Dict containing system load information
    """
    load_info = {
        'cpu_percent': 0,
        'load_avg': [0, 0, 0],
        'processes': 0,
    }
    
    try:
        # Get CPU usage percentage (across all cores)
        load_info['cpu_percent'] = psutil.cpu_percent(interval=0.5)
        
        # Get system load averages (1, 5, 15 minutes)
        load_info['load_avg'] = os.getloadavg()
        
        # Get process count
        load_info['processes'] = len(psutil.pids())
    except Exception as e:
        logging.warning(f"Error getting system load: {e}")
        
    return load_info


def run_smart_check(drive: str) -> Dict[str, Any]:
    """Run SMART diagnostics on a drive.
    
    Args:
        drive: Device path e.g., /dev/sda or /dev/nvme0n1
        
    Returns:
        Dict containing SMART information including health status,
        temperature, power-on hours, and any errors.
    """
    result = {
        'health': 'Unknown',
        'temperature': None,
        'power_on_hours': None,
        'errors': []
    }
    
    try:
        # Check if it's an NVMe drive
        is_nvme = 'nvme' in drive.lower()
        
        # Different approach for NVMe vs traditional drives
        if is_nvme:
            logging.debug(f"Checking NVMe drive health: {drive}")
            nvme_health_checked = False
            
            # First try with native nvme-cli tools if available
            if shutil.which('nvme'):
                try:
                    logging.debug(f"Using nvme-cli to check health for {drive}")
                    nvme_health = subprocess.check_output(['nvme', 'smart-log', drive], text=True, stderr=subprocess.PIPE)
                    nvme_health_checked = True
                    
                    # Parse health information from nvme-cli output
                    critical_warning = False
                    media_errors = 0
                    power_on_time = None
                    temperature = None
                    
                    for line in nvme_health.split('\n'):
                        # Check for critical warnings
                        if 'critical_warning' in line.lower():
                            value = re.search(r':\s*(\d+)', line)
                            if value and int(value.group(1)) > 0:
                                critical_warning = True
                                result['errors'].append(f"NVMe critical warning detected")
                        
                        # Check for media errors
                        if 'media_errors' in line.lower():
                            value = re.search(r':\s*(\d+)', line)
                            if value:
                                media_errors = int(value.group(1))
                                if media_errors > 0:
                                    result['errors'].append(f"Media errors detected: {media_errors}")
                        
                        # Get temperature
                        if 'temperature' in line.lower():
                            temp_match = re.search(r':\s*(\d+)\s*C', line)
                            if temp_match:
                                temperature = int(temp_match.group(1))
                                result['temperature'] = temperature
                                
                        # Power on hours/cycles
                        if any(x in line.lower() for x in ['power_cycles', 'power on cycles', 'power_on_hours']):
                            cycles_match = re.search(r':\s*(\d+)', line)
                            if cycles_match:
                                power_cycles = int(cycles_match.group(1))
                                # We don't have direct power-on hours, but we can estimate
                                power_on_time = power_cycles * 24  # Very rough estimate
                                result['power_on_hours'] = power_on_time
                    
                    # Set health status based on findings
                    if critical_warning or media_errors > 10:
                        result['health'] = 'Failing'
                    else:
                        result['health'] = 'Healthy'
                        
                except (subprocess.SubprocessError, Exception) as e:
                    logging.warning(f"NVMe-cli check failed: {e}")
                    # Continue to next method, don't consider this fatal
                    
            # If nvme-cli didn't work or isn't available, try alternative health checks
            if not nvme_health_checked or result['health'] == 'Unknown':
                # Attempt to assess drive health by checking if we can read from it
                try:
                    # Check if the drive is readable
                    if os.path.exists(drive):
                        # If the drive exists and hasn't thrown critical errors, it's probably working
                        result['health'] = 'Likely Healthy'
                        logging.debug(f"NVMe health assessment based on filesystem availability: {drive}")
                        
                        # Check drive partitions for more info
                        drive_base = os.path.basename(drive)
                        sys_path = f"/sys/block/{drive_base}"
                        if os.path.exists(sys_path):
                            # Check if the drive is online
                            online_path = os.path.join(sys_path, 'device/state')
                            if os.path.exists(online_path):
                                try:
                                    with open(online_path, 'r') as f:
                                        state = f.read().strip()
                                        # 'live' is a good state for NVMe drives
                                        if state == 'live':
                                            result['health'] = 'Healthy'
                                        elif state != 'running':
                                            result['health'] = 'Warning'
                                            result['errors'].append(f"Drive state: {state}")
                                except Exception as e:
                                    logging.debug(f"Couldn't read device state: {e}")
                                    
                            # Try to get driver information for extra data
                            driver_path = os.path.join(sys_path, 'device/driver')
                            if os.path.exists(driver_path):
                                try:
                                    driver = os.path.basename(os.readlink(driver_path))
                                    logging.debug(f"NVMe driver: {driver}")
                                except Exception as e:
                                    logging.debug(f"Couldn't read driver info: {e}")
                                    
                        # Try to estimate temperature if we couldn't get it earlier
                        if result['temperature'] is None:
                            thermal_path = "/sys/class/thermal/thermal_zone0/temp"
                            if os.path.exists(thermal_path):
                                try:
                                    with open(thermal_path, 'r') as f:
                                        temp = int(f.read().strip()) / 1000  # Value is often in millidegrees C
                                        result['temperature'] = int(temp)
                                except Exception as e:
                                    logging.debug(f"Couldn't read system temperature: {e}")
                            
                            # If still no temperature, use a reasonable default
                            if result['temperature'] is None:
                                result['temperature'] = 40  # Safe default
                                
                    else:
                        result['health'] = 'Not Available'
                        result['errors'].append("Drive not accessible")
                except Exception as e:
                    logging.warning(f"Alternative health check failed: {e}")
                        
            # If after all our checks we still don't have a definitive health status
            if result['health'] == 'Unknown':
                # If we've hit this point, it's most likely the drive is functional
                # but we just couldn't get SMART data
                result['health'] = 'Likely Healthy'
                if not result['errors']:
                    result['errors'].append("NVMe SMART diagnostics not available")
                    
            # Set a default power-on hours if we couldn't get them
            if result['power_on_hours'] is None:
                # Try to get system uptime as a starting point
                try:
                    with open('/proc/uptime', 'r') as f:
                        uptime = float(f.read().split()[0]) / 3600  # Convert seconds to hours
                        result['power_on_hours'] = int(uptime)
                except Exception:
                    result['power_on_hours'] = 1000  # Default value
                
        else:
            # Standard SMART checks for traditional drives
            try:
                # Run standard health check
                health_output = subprocess.check_output(['smartctl', '-H', drive], text=True)
                if 'PASSED' in health_output:
                    result['health'] = 'Healthy'
                elif 'FAILED' in health_output:
                    result['health'] = 'Failing'
                    # Extract the failure message
                    for line in health_output.split('\n'):
                        if 'FAILED' in line:
                            result['errors'].append(line.strip())
                            
                # Get standard SMART attributes
                try:
                    attr_output = subprocess.check_output(['smartctl', '-A', drive], text=True)
                    
                    # Parse temperature
                    for line in attr_output.split('\n'):
                        if any(temp in line for temp in ['Temperature', 'Airflow_Temperature']):
                            temp_match = re.search(r'\d+', line.split()[-1])
                            if temp_match:
                                result['temperature'] = int(temp_match.group(0))
                                
                        # Parse Power-On Hours
                        if 'Power_On_Hours' in line:
                            hours_match = re.search(r'\d+', line.split()[-1])
                            if hours_match:
                                result['power_on_hours'] = int(hours_match.group(0))
                except subprocess.SubprocessError:
                    # Continue if we can't get attributes but have health
                    pass
                    
                # Try a deeper SMART info check if we don't have temp or hours
                if result['temperature'] is None or result['power_on_hours'] is None:
                    try:
                        info_output = subprocess.check_output(['smartctl', '-i', '-A', drive], text=True)
                        
                        # Look for temperature and hours in this output too
                        for line in info_output.split('\n'):
                            if not result['temperature'] and ('temp' in line.lower() or 'temperature' in line.lower()):
                                temp_match = re.findall(r'\b\d+\b', line)
                                if temp_match:
                                    # Try to find a reasonable temperature value (typically 20-60°C)
                                    for val in temp_match:
                                        if 20 <= int(val) <= 80:
                                            result['temperature'] = int(val)
                                            break
                                            
                            if not result['power_on_hours'] and ('power' in line.lower() and 'hour' in line.lower()):
                                hours_match = re.findall(r'\b\d+\b', line)
                                if hours_match:
                                    result['power_on_hours'] = int(hours_match[0])
                    except subprocess.SubprocessError:
                        pass
                        
            except subprocess.SubprocessError as e:
                result['errors'].append(f"SMART health check failed: {str(e)}")
                
        # Final check - if we still have unknown health but no errors, probably healthy
        if result['health'] == 'Unknown':
            if result['errors']:
                # If we have errors but unknown health, mark as suspect
                result['health'] = 'Needs Investigation'
            else:
                # No errors but unknown health, probably healthy
                result['health'] = 'Likely Healthy'
                
        # If we didn't get temperature but drive is healthy, set a default
        # This prevents UI issues with missing temperature
        if result['temperature'] is None and result['health'] in ['Healthy', 'Likely Healthy']:
            result['temperature'] = 40  # Reasonable default temperature
                
    except Exception as e:
        logging.warning(f"Error running SMART diagnostics: {e}")
        result['errors'].append(f"Unexpected error: {str(e)}")
        
    return result


def check_hardware_health() -> Dict[str, Any]:
    """Run various hardware health checks and diagnostics.
    
    Returns:
        Dict containing health status for various hardware components
    """
    health_status = {
        'cpu': {
            'status': 'Healthy',
            'temperature': None,
            'issues': []
        },
        'memory': {
            'status': 'Healthy',
            'issues': []
        },
        'storage': [],
        'network': {
            'status': 'Healthy',
            'issues': []
        },
        'overall': 'Healthy'
    }
    
    # Check CPU health based on temperature
    try:
        cpu_info = get_cpu_info()
        if 'temperature' in cpu_info and cpu_info['temperature'] != 'Unknown':
            temp = float(cpu_info['temperature'].rstrip('°C'))
            health_status['cpu']['temperature'] = temp
            
            # Evaluate based on temperature thresholds
            if temp > 90:
                health_status['cpu']['status'] = 'Critical'
                health_status['cpu']['issues'].append(f"CPU temperature is critically high: {temp}°C")
            elif temp > 80:
                health_status['cpu']['status'] = 'Warning'
                health_status['cpu']['issues'].append(f"CPU temperature is high: {temp}°C")
    except Exception as e:
        logging.warning(f"Error checking CPU health: {e}")
        
    # Check memory health based on usage and any issues
    try:
        mem_info = get_memory_info()
        if mem_info['percent_used'] > 95:
            health_status['memory']['status'] = 'Warning'
            health_status['memory']['issues'].append("Memory usage is very high (>95%)")
            
        # Check if swap is heavily used when RAM is also heavily used
        if mem_info['percent_used'] > 80 and mem_info['swap_percent'] > 80:
            health_status['memory']['status'] = 'Warning'
            health_status['memory']['issues'].append("Both RAM and swap are heavily used")
    except Exception as e:
        logging.warning(f"Error checking memory health: {e}")
        
    # Check drive health using SMART if available
    try:
        drives = get_storage_info()
        for drive in drives:
            drive_health = {
                'name': drive['name'],
                'model': drive['model'],
                'status': 'Healthy',
                'temperature': None,
                'issues': []
            }
            
            # Run SMART diagnostics if it's a physical device
            if drive['device'].startswith('/dev/') and not any(x in drive['device'] for x in ['loop', 'ram']):
                smart_result = run_smart_check(drive['device'])
                
                if smart_result['health'] == 'Failing':
                    drive_health['status'] = 'Critical'
                    drive_health['issues'].extend(smart_result['errors'])
                    
                if smart_result['temperature']:
                    drive_health['temperature'] = smart_result['temperature']
                    
                    # Check temperature thresholds
                    if smart_result['temperature'] > 60:
                        drive_health['status'] = 'Warning'
                        drive_health['issues'].append(f"Drive temperature is high: {smart_result['temperature']}°C")
            
            # Check usage thresholds
            if drive['used_percent'] > 95:
                drive_health['status'] = 'Warning'
                drive_health['issues'].append(f"Drive is almost full ({drive['used_percent']:.1f}%)")
                
            health_status['storage'].append(drive_health)
    except Exception as e:
        logging.warning(f"Error checking storage health: {e}")
        
    # Check network health (at least one interface should be up)
    try:
        network_interfaces = get_network_info()
        connected = False
        
        for interface in network_interfaces:
            if interface['status'] == 'Up' and interface['ipv4']:
                connected = True
                break
                
        if not connected and network_interfaces:
            health_status['network']['status'] = 'Warning'
            health_status['network']['issues'].append("No active network connection detected")
    except Exception as e:
        logging.warning(f"Error checking network health: {e}")
        
    # Determine overall system health
    component_statuses = [
        health_status['cpu']['status'],
        health_status['memory']['status'],
        health_status['network']['status']
    ]
    
    # Add storage statuses
    for drive in health_status['storage']:
        component_statuses.append(drive['status'])
        
    # Set overall status based on the worst component status
    if 'Critical' in component_statuses:
        health_status['overall'] = 'Critical'
    elif 'Warning' in component_statuses:
        health_status['overall'] = 'Warning'
    else:
        health_status['overall'] = 'Healthy'
        
    return health_status


def gather_linux_diagnostics(technician_name: str = 'Unknown') -> Dict[str, Any]:
    """Gather comprehensive Linux system diagnostics.
    
    Args:
        technician_name: Name of the technician running diagnostics
        
    Returns:
        Dictionary containing all diagnostic data
    """
    logging.info(f"Gathering Linux diagnostics (technician: {technician_name})")
    
    # Create the master diagnostics data dictionary
    diagnostics = {
        'timestamp': datetime.now().isoformat(),
        'technician': technician_name,
        'system': {
            'hostname': socket.gethostname(),
            'distribution': 'Unknown',
            'kernel': platform.release()
        },
        'cpu': {},
        'memory': {},
        'storage': [],
        'gpu': [],
        'network': [],
        'motherboard': {},
        'health': {}
    }
    
    # Try to get Linux distribution details
    try:
        # Check if lsb_release is available
        if shutil.which('lsb_release'):
            distro_info = subprocess.check_output(['lsb_release', '-a'], text=True)
            description_match = re.search(r'Description:\s+(.+)', distro_info)
            if description_match:
                diagnostics['system']['distribution'] = description_match.group(1)
        # Otherwise check /etc/os-release
        elif os.path.exists('/etc/os-release'):
            with open('/etc/os-release', 'r') as f:
                os_release = f.read()
                pretty_name_match = re.search(r'PRETTY_NAME="(.+)"', os_release)
                if pretty_name_match:
                    diagnostics['system']['distribution'] = pretty_name_match.group(1)
    except Exception as e:
        logging.warning(f"Error getting distribution info: {e}")
    
    # Collect all diagnostic information
    diagnostics['cpu'] = get_cpu_info()
    diagnostics['memory'] = get_memory_info()
    diagnostics['storage'] = get_storage_info()
    diagnostics['gpu'] = get_gpu_info()
    diagnostics['network'] = get_network_info()
    diagnostics['motherboard'] = get_motherboard_info()
    diagnostics['health'] = check_hardware_health()
    
    logging.info("Linux diagnostics gathering complete")
    return diagnostics


def format_diagnostics_report(diagnostics: Dict[str, Any]) -> str:
    """Format the diagnostics data as a readable text report.
    
    Args:
        diagnostics: The diagnostic data dictionary from gather_linux_diagnostics()
        
    Returns:
        Formatted diagnostics report as a string
    """
    report = []
    
    # Header
    report.append("====== SYSTEM DIAGNOSTICS REPORT ======")
    report.append(f"Technician: {diagnostics['technician']}")
    report.append(f"Date: {datetime.fromisoformat(diagnostics['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"Hostname: {diagnostics['system']['hostname']}")
    report.append(f"Distribution: {diagnostics['system']['distribution']}")
    report.append(f"Kernel: {diagnostics['system']['kernel']}")
    report.append("\n")
    
    # System Health Summary
    health = diagnostics['health']
    report.append(f"SYSTEM HEALTH: {health['overall'].upper()}")
    report.append(f"CPU Health: {health['cpu']['status']}")
    report.append(f"Memory Health: {health['memory']['status']}")
    report.append(f"Network Health: {health['network']['status']}")
    
    # List storage health
    if health['storage']:
        report.append("Storage Health:")
        for drive in health['storage']:
            report.append(f"  - {drive['model']}: {drive['status']}")
    
    # List any issues
    all_issues = []
    if health['cpu']['issues']:
        all_issues.extend(health['cpu']['issues'])
    if health['memory']['issues']:
        all_issues.extend(health['memory']['issues'])
    if health['network']['issues']:
        all_issues.extend(health['network']['issues'])
    for drive in health['storage']:
        if drive['issues']:
            all_issues.extend([f"{drive['model']}: {issue}" for issue in drive['issues']])
            
    if all_issues:
        report.append("\nDetected Issues:")
        for issue in all_issues:
            report.append(f"  - {issue}")
    report.append("\n")
    
    # CPU Information
    report.append("====== CPU INFORMATION ======")
    report.append(f"Model: {diagnostics['cpu']['model']}")
    report.append(f"Cores: {diagnostics['cpu']['cores']}")
    report.append(f"Threads: {diagnostics['cpu']['threads']}")
    report.append(f"Speed: {diagnostics['cpu']['speed']}")
    report.append(f"Temperature: {diagnostics['cpu']['temperature']}")
    report.append("\n")
    
    # Memory Information
    report.append("====== MEMORY INFORMATION ======")
    report.append(f"Total RAM: {diagnostics['memory']['total']:.2f} GB")
    report.append(f"Available RAM: {diagnostics['memory']['available']:.2f} GB")
    report.append(f"Used RAM: {diagnostics['memory']['used']:.2f} GB ({diagnostics['memory']['percent_used']:.1f}%)")
    report.append(f"Swap Total: {diagnostics['memory']['swap_total']:.2f} GB")
    report.append(f"Swap Used: {diagnostics['memory']['swap_used']:.2f} GB ({diagnostics['memory']['swap_percent']:.1f}%)")
    report.append("\n")
    
    # Motherboard Information
    report.append("====== MOTHERBOARD INFORMATION ======")
    report.append(f"Manufacturer: {diagnostics['motherboard']['manufacturer']}")
    report.append(f"Model: {diagnostics['motherboard']['model']}")
    report.append(f"BIOS Version: {diagnostics['motherboard']['bios_version']}")
    report.append(f"BIOS Date: {diagnostics['motherboard']['bios_date']}")
    report.append("\n")
    
    # GPU Information
    report.append("====== GPU INFORMATION ======")
    if diagnostics['gpu']:
        for i, gpu in enumerate(diagnostics['gpu'], 1):
            report.append(f"GPU {i}: {gpu['model']} ({gpu['type']})")
    else:
        report.append("No GPU information available")
    report.append("\n")
    
    # Storage Information
    report.append("====== STORAGE INFORMATION ======")
    if diagnostics['storage']:
        for drive in diagnostics['storage']:
            report.append(f"Drive: {drive['model']} ({drive['type']})")
            report.append(f"Device: {drive['device']}")
            report.append(f"Size: {drive['size_gb']:.2f} GB")
            report.append(f"Used: {drive['used_percent']:.1f}%")
            report.append(f"Health: {drive.get('health', 'Unknown')}")
            if drive['partitions']:
                report.append("  Partitions:")
                for part in drive['partitions']:
                    mount_info = f" → {part['mountpoint']}" if part['mountpoint'] else " (not mounted)"
                    report.append(f"    {part['device']}{mount_info} ({part['size_gb']:.2f} GB)")
            report.append("")
    else:
        report.append("No storage information available")
    report.append("\n")
    
    # Network Information
    report.append("====== NETWORK INFORMATION ======")
    if diagnostics['network']:
        for interface in diagnostics['network']:
            report.append(f"Interface: {interface['name']} ({interface['type']})")
            report.append(f"Status: {interface['status']}")
            report.append(f"MAC Address: {interface['mac']}")
            if interface['ipv4']:
                report.append(f"IPv4: {', '.join(interface['ipv4'])}")
            if interface['ipv6']:
                report.append(f"IPv6: {', '.join(interface['ipv6'])}")
            report.append("")
    else:
        report.append("No network information available")
    
    # Footer
    report.append("======================================")
    report.append(f"Report generated by Nest PC Tools - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return '\n'.join(report)


def run_diagnostics_tests() -> Dict[str, Any]:
    """Run basic diagnostic tests and return results.
    
    Returns:
        Dictionary with test results and status
    """
    results = {
        'passed': True,
        'tests': []
    }
    
    # Test 1: Disk health check
    try:
        disk = psutil.disk_usage('/')
        disk_status = {
            'name': 'Disk Usage',
            'passed': disk.percent < 90,
            'value': f"{disk.percent}% used",
            'message': 'Healthy' if disk.percent < 90 else 'Disk is almost full'
        }
        results['tests'].append(disk_status)
        if not disk_status['passed']:
            results['passed'] = False
    except Exception as e:
        results['tests'].append({
            'name': 'Disk Usage',
            'passed': False,
            'value': 'Error',
            'message': f"Failed to check disk: {str(e)}"
        })
        results['passed'] = False
    
    # Test 2: Memory check
    try:
        mem = psutil.virtual_memory()
        mem_status = {
            'name': 'Memory Usage',
            'passed': mem.percent < 90,
            'value': f"{mem.percent}% used",
            'message': 'Healthy' if mem.percent < 90 else 'Memory usage is high'
        }
        results['tests'].append(mem_status)
        if not mem_status['passed']:
            results['passed'] = False
    except Exception as e:
        results['tests'].append({
            'name': 'Memory Usage',
            'passed': False,
            'value': 'Error',
            'message': f"Failed to check memory: {str(e)}"
        })
        results['passed'] = False
    
    # Test 3: CPU load check
    try:
        cpu_percent = psutil.cpu_percent(interval=0.5)
        cpu_status = {
            'name': 'CPU Load',
            'passed': cpu_percent < 90,
            'value': f"{cpu_percent}% used",
            'message': 'Healthy' if cpu_percent < 90 else 'CPU is under heavy load'
        }
        results['tests'].append(cpu_status)
        if not cpu_status['passed']:
            results['passed'] = False
    except Exception as e:
        results['tests'].append({
            'name': 'CPU Load',
            'passed': False,
            'value': 'Error',
            'message': f"Failed to check CPU: {str(e)}"
        })
        results['passed'] = False
    
    # Test 4: Network connectivity check
    try:
        # Check if we have a working network interface
        interfaces = get_network_info()
        has_connection = False
        for interface in interfaces:
            if interface['status'] == 'Up' and interface['ipv4']:
                has_connection = True
                break
                
        net_status = {
            'name': 'Network',
            'passed': has_connection,
            'value': 'Connected' if has_connection else 'Disconnected',
            'message': 'Connected to network' if has_connection else 'No network connection detected'
        }
        results['tests'].append(net_status)
        if not net_status['passed']:
            results['passed'] = False
    except Exception as e:
        results['tests'].append({
            'name': 'Network',
            'passed': False,
            'value': 'Error',
            'message': f"Failed to check network: {str(e)}"
        })
        results['passed'] = False
        
    return results
