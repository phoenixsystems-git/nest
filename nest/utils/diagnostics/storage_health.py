# nest/utils/diagnostics/storage_health.py
import platform
import asyncio
import logging
import os
from typing import Dict, Any, Optional, List

from nest.utils.system.process_manager import ProcessManager
from nest.utils.feature_detection import FeatureDetection

class StorageHealthAnalyzer:
    """Cross-platform storage health analysis with consistent API
    
    This class performs storage health checks using platform-specific methods
    while providing a unified interface for diagnostics results.
    """
    
    def __init__(self):
        """Initialize the storage health analyzer"""
        self.system = platform.system().lower()
        self.process_manager = ProcessManager()
        self.feature_detection = FeatureDetection()
    
    async def analyze_all_drives(self) -> Dict[str, Any]:
        """Analyze all storage devices and return health metrics
        
        Returns:
            Dictionary containing analysis results for all drives
        """
        # Get list of drives
        drives = await self._get_drives()
        
        # Run health checks concurrently
        tasks = [self.analyze_drive(drive) for drive in drives]
        results = await asyncio.gather(*tasks)
        
        # Combine results
        return {
            "timestamp": self._get_timestamp(),
            "system": self.system,
            "drives": {r["device"]: r for r in results if r}
        }
    
    async def analyze_drive(self, drive_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Analyze a specific drive using platform-appropriate methods
        
        Args:
            drive_info: Dictionary containing drive information
                Required keys: "device" with device path/identifier
        
        Returns:
            Dictionary containing health analysis results with unified structure:
            {
                "device": Device identifier (consistent with input),
                "model": Device model name,
                "health_status": One of "healthy", "failing", "unknown",
                ... (platform-specific details in nested dictionaries)
            }
            
        Platform-specific notes:
            Windows:
                - Requires admin access for some storage operations
                - May report "unknown" for USB flash drives without SMART
                - Returns WMI predictive failure status on supported devices
            
            Linux:
                - Full SMART data requires smartctl with sudo access
                - Falls back to lsblk basic info when smartctl unavailable
                - SSDs may report different attributes than HDDs
        """
        device = drive_info.get("device")
        if not device:
            return None
            
        try:
            if self.system == "windows":
                return await self._analyze_windows_drive(drive_info)
            elif self.system == "linux":
                return await self._analyze_linux_drive(drive_info)
            else:
                logging.warning(f"Storage health analysis not supported on {self.system}")
                return {
                    "device": device,
                    "model": drive_info.get("model", "Unknown"),
                    "health_status": "unknown",
                    "message": f"Storage health analysis not supported on {self.system}"
                }
        except Exception as e:
            logging.error(f"Error analyzing drive {device}: {e}")
            return {
                "device": device,
                "model": drive_info.get("model", "Unknown"),
                "health_status": "unknown",
                "error": str(e)
            }
    
    async def _get_drives(self) -> List[Dict[str, Any]]:
        """Get list of storage devices with platform-specific detection
        
        Returns:
            List of drive info dictionaries, each containing at least a "device" key
        """
        if self.system == "windows":
            return await self._get_windows_drives()
        elif self.system == "linux":
            return await self._get_linux_drives()
        else:
            return []
    
    async def _get_windows_drives(self) -> List[Dict[str, Any]]:
        """Get list of Windows storage devices
        
        Returns:
            List of drive info dictionaries
        """
        drives = []
        
        try:
            # Get physical drives using WMI
            result = await self.process_manager.start_process(
                ["powershell", "-Command", 
                 "Get-WmiObject -Class Win32_DiskDrive | " +
                 "Select-Object DeviceID, Model, Size, MediaType | " +
                 "ConvertTo-Json"],
                wait=True
            )
            
            if result.get("success"):
                import json
                try:
                    # Parse the JSON output
                    data = json.loads(result.get("stdout", "[]"))
                    
                    # Handle single drive case (not in array)
                    if not isinstance(data, list):
                        data = [data]
                    
                    for drive in data:
                        device_id = drive.get("DeviceID")
                        if device_id:
                            # Calculate size in GB
                            size_bytes = drive.get("Size")
                            size_gb = round(int(size_bytes) / (1024**3), 2) if size_bytes else None
                            
                            drives.append({
                                "device": device_id,
                                "model": drive.get("Model", "Unknown"),
                                "size_gb": size_gb,
                                "media_type": drive.get("MediaType", "Unknown")
                            })
                except json.JSONDecodeError:
                    logging.error("Error parsing WMI output")
            
            # If no drives found or WMI failed, fall back to drive letters
            if not drives:
                result = await self.process_manager.start_process(
                    ["powershell", "-Command", 
                     "Get-PSDrive -PSProvider FileSystem | " +
                     "Select-Object Name, Used, Free | " +
                     "ConvertTo-Json"],
                    wait=True
                )
                
                if result.get("success"):
                    try:
                        data = json.loads(result.get("stdout", "[]"))
                        
                        # Handle single drive case
                        if not isinstance(data, list):
                            data = [data]
                        
                        for drive in data:
                            name = drive.get("Name")
                            if name:
                                # Calculate total size in GB
                                used = drive.get("Used", 0)
                                free = drive.get("Free", 0)
                                total = (used + free) / (1024**3)
                                
                                drives.append({
                                    "device": f"{name}:",
                                    "model": f"Drive {name}",
                                    "size_gb": round(total, 2),
                                    "media_type": "Unknown"
                                })
                    except json.JSONDecodeError:
                        logging.error("Error parsing drive letters output")
        except Exception as e:
            logging.error(f"Error getting Windows drives: {e}")
        
        return drives
    
    async def _get_linux_drives(self) -> List[Dict[str, Any]]:
        """Get list of Linux storage devices
        
        Returns:
            List of drive info dictionaries
        """
        drives = []
        
        try:
            # Use lsblk to get block devices
            result = await self.process_manager.start_process(
                ["lsblk", "-d", "-o", "NAME,MODEL,SIZE,TYPE", "--json"],
                wait=True
            )
            
            if result.get("success"):
                import json
                try:
                    # Parse the JSON output
                    data = json.loads(result.get("stdout", "{}"))
                    block_devices = data.get("blockdevices", [])
                    
                    for device in block_devices:
                        name = device.get("name")
                        if name and device.get("type") in ["disk", "part"]:
                            # Add /dev/ prefix if not already present
                            if not name.startswith("/dev/"):
                                name = f"/dev/{name}"
                                
                            drives.append({
                                "device": name,
                                "model": device.get("model", "").strip() or "Unknown",
                                "size": device.get("size", "Unknown"),
                                "type": device.get("type", "Unknown")
                            })
                except json.JSONDecodeError:
                    logging.error("Error parsing lsblk output")
            
            # If no drives found or lsblk failed, fall back to mount points
            if not drives:
                result = await self.process_manager.start_process(
                    ["mount"],
                    wait=True
                )
                
                if result.get("success"):
                    lines = result.get("stdout", "").splitlines()
                    
                    for line in lines:
                        parts = line.split()
                        if len(parts) >= 3 and parts[1] == "on":
                            device = parts[0]
                            mountpoint = parts[2]
                            
                            # Skip virtual filesystems
                            if any(fs in line for fs in ["tmpfs", "sysfs", "proc", "devpts"]):
                                continue
                                
                            drives.append({
                                "device": device,
                                "model": "Unknown",
                                "mountpoint": mountpoint
                            })
        except Exception as e:
            logging.error(f"Error getting Linux drives: {e}")
        
        return drives
    
    async def _analyze_windows_drive(self, drive_info: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze drive health on Windows
        
        Args:
            drive_info: Drive information dictionary
            
        Returns:
            Health analysis results
        """
        device = drive_info.get("device", "")
        model = drive_info.get("model", "Unknown")
        
        # Initialize result with basic info
        health_info = {
            "device": device,
            "model": model,
            "health_status": "unknown",
            "smart_attributes": {},
            "predicted_failure": False
        }
        
        try:
            # Get SMART status using PowerShell and WMI
            ps_command = (
                "Get-WmiObject -Namespace root\\wmi -Class MSStorageDriver_FailurePredictStatus | " +
                "Select-Object InstanceName, PredictFailure, Reason | " +
                "ConvertTo-Json"
            )
            
            result = await self.process_manager.start_process(
                ["powershell", "-Command", ps_command],
                wait=True
            )
            
            if result.get("success"):
                import json
                try:
                    data = json.loads(result.get("stdout", "[]"))
                    
                    # Handle single result
                    if not isinstance(data, list):
                        data = [data]
                        
                    # Find matching drive
                    for item in data:
                        instance = item.get("InstanceName", "")
                        
                        # Extract physical drive number or drive letter
                        if "physicaldrive" in device.lower() and "physicaldrive" in instance.lower():
                            # Match by physical drive number
                            if device.lower() in instance.lower():
                                health_info["predicted_failure"] = item.get("PredictFailure", False)
                                health_info["health_status"] = "failing" if item.get("PredictFailure") else "healthy"
                                health_info["reason"] = item.get("Reason", "")
                                break
                        elif ":" in device:
                            # Match by drive letter (less reliable)
                            drive_letter = device[0].lower()
                            if f"disk{drive_letter}:" in instance.lower():
                                health_info["predicted_failure"] = item.get("PredictFailure", False)
                                health_info["health_status"] = "failing" if item.get("PredictFailure") else "healthy"
                                health_info["reason"] = item.get("Reason", "")
                                break
                except json.JSONDecodeError:
                    logging.error("Error parsing SMART data")
                
            # If health status is still unknown, try an alternative method
            if health_info["health_status"] == "unknown":
                # Get disk volume information
                disk_command = f'Get-Volume -DriveLetter {device[0]} | Select-Object HealthStatus | ConvertTo-Json'
                
                vol_result = await self.process_manager.start_process(
                    ["powershell", "-Command", disk_command],
                    wait=True
                )
                
                if vol_result.get("success"):
                    try:
                        vol_data = json.loads(vol_result.get("stdout", "{}"))
                        health_status = vol_data.get("HealthStatus", "Unknown")
                        
                        # Map health status
                        if health_status == "Healthy":
                            health_info["health_status"] = "healthy"
                        elif health_status in ["AtRisk", "Unhealthy"]:
                            health_info["health_status"] = "failing"
                            health_info["predicted_failure"] = True
                    except json.JSONDecodeError:
                        logging.error("Error parsing volume health data")
        except Exception as e:
            logging.error(f"Error analyzing Windows drive: {e}")
        
        return health_info
    
    async def _analyze_linux_drive(self, drive_info: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze drive health on Linux
        
        Args:
            drive_info: Drive information dictionary
            
        Returns:
            Health analysis results
        """
        device = drive_info.get("device", "")
        model = drive_info.get("model", "Unknown")
        
        # Initialize result with basic info
        health_info = {
            "device": device,
            "model": model,
            "health_status": "unknown",
            "smart_attributes": {},
            "temperature": None
        }
        
        # Check if smartctl is available
        smartctl_available = self.feature_detection.is_command_available("smartctl")
        
        if smartctl_available:
            try:
                # Run SMART test
                result = await self.process_manager.start_process(
                    ["smartctl", "-a", device],
                    admin=True,  # May need sudo
                    wait=True
                )
                
                if result.get("success"):
                    output = result.get("stdout", "")
                    
                    # Extract overall health
                    for line in output.splitlines():
                        if "SMART overall-health" in line or "SMART Health Status" in line:
                            if "PASSED" in line or "OK" in line:
                                health_info["health_status"] = "healthy"
                            else:
                                health_info["health_status"] = "failing"
                        
                        # Extract temperature
                        if "Temperature" in line and "Celsius" in line:
                            try:
                                temp = int(line.split("Celsius")[0].strip().split()[-1])
                                health_info["temperature"] = temp
                            except (ValueError, IndexError):
                                pass
                                
                        # Extract SMART attributes
                        if "SMART Attributes Data Structure" in line:
                            # Parse attribute table
                            attr_section = False
                            for section_line in output.splitlines():
                                if "SMART Attributes Data Structure" in section_line:
                                    attr_section = True
                                    continue
                                
                                if attr_section and "ID#" in section_line:
                                    continue
                                
                                if attr_section and len(section_line.strip()) > 0:
                                    parts = section_line.split()
                                    if len(parts) >= 10:
                                        try:
                                            attr_id = parts[0]
                                            attr_name = parts[1]
                                            attr_value = parts[3]
                                            attr_thresh = parts[5]
                                            attr_raw = parts[9]
                                            
                                            health_info["smart_attributes"][attr_name] = {
                                                "id": attr_id,
                                                "value": attr_value,
                                                "threshold": attr_thresh,
                                                "raw": attr_raw
                                            }
                                        except (ValueError, IndexError):
                                            pass
                                    else:
                                        attr_section = False
            except Exception as e:
                logging.error(f"Error running SMART test: {e}")
        
        # If health status is still unknown, try to get basic information
        if health_info["health_status"] == "unknown":
            try:
                # Use lsblk to get basic info
                result = await self.process_manager.start_process(
                    ["lsblk", "-o", "NAME,SIZE,MODEL,TRAN,ROTA", "--json", device],
                    wait=True
                )
                
                if result.get("success"):
                    import json
                    try:
                        data = json.loads(result.get("stdout", "{}"))
                        block_devices = data.get("blockdevices", [])
                        
                        if block_devices:
                            block = block_devices[0]
                            health_info["model"] = block.get("model", model).strip() or model
                            health_info["size"] = block.get("size", "Unknown")
                            health_info["is_ssd"] = not block.get("rota", True)
                            
                            # If it's a device that was successfully queried, assume it's at least functional
                            health_info["health_status"] = "unknown_functional"
                    except json.JSONDecodeError:
                        logging.error("Error parsing lsblk output")
                
                # Try to get filesystem usage
                if "mountpoint" in drive_info:
                    mountpoint = drive_info["mountpoint"]
                    
                    df_result = await self.process_manager.start_process(
                        ["df", "-h", mountpoint],
                        wait=True
                    )
                    
                    if df_result.get("success"):
                        # Parse df output to get usage
                        lines = df_result.get("stdout", "").splitlines()
                        if len(lines) >= 2:
                            parts = lines[1].split()
                            if len(parts) >= 5:
                                health_info["usage_percent"] = parts[4].rstrip("%")
            except Exception as e:
                logging.error(f"Error getting basic disk info: {e}")
        
        return health_info
    
    def _get_timestamp(self) -> str:
        """Get current timestamp string
        
        Returns:
            Formatted timestamp string
        """
        from datetime import datetime
        return datetime.now().isoformat()