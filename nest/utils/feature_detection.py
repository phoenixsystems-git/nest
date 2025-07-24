#!/usr/bin/env python3
"""
Feature Detection

Provides cross-platform feature detection for PC Tools to determine
available capabilities and adapt functionality accordingly.
"""

import os
import sys
import platform
import logging
import importlib.util
import subprocess
import shutil
from typing import Dict, List, Any, Set, Optional, Tuple


class FeatureDetection:
    """Cross-platform detection of system capabilities and features
    
    This class detects available system capabilities and tools, allowing 
    the application to adapt its functionality based on the current platform 
    and available features.
    """
    
    def __init__(self):
        """Initialize feature detection"""
        self.system = platform.system().lower()
        self.features: Dict[str, bool] = {}
        self.tools: Dict[str, bool] = {}
        self.capabilities: Dict[str, Dict[str, Any]] = {}
        
        # Initialize feature detection
        self._detect_platform_features()
        self._detect_available_tools()
        self._detect_system_capabilities()
    
    def _detect_platform_features(self) -> None:
        """Detect platform-specific features"""
        # Basic platform features
        self.features["is_windows"] = self.system == "windows"
        self.features["is_linux"] = self.system == "linux"
        self.features["is_macos"] = self.system == "darwin"
        
        # Windows-specific feature detection
        if self.features["is_windows"]:
            self.features["is_admin"] = self._is_windows_admin()
            self.features["has_wmi"] = self._check_module_available("wmi")
            self.features["has_winreg"] = self._check_module_available("winreg")
            self.features["has_pywin32"] = self._check_module_available("win32api")
            self.features["has_winpe"] = self._is_winpe_environment()
            
        # Linux-specific feature detection
        elif self.features["is_linux"]:
            self.features["is_root"] = os.geteuid() == 0 if hasattr(os, 'geteuid') else False
            self.features["has_systemd"] = self._check_tool_available("systemctl")
            self.features["has_x11"] = 'DISPLAY' in os.environ
            self.features["has_wayland"] = 'WAYLAND_DISPLAY' in os.environ
    
    def _detect_available_tools(self) -> None:
        """Detect available command-line tools"""
        # Common tools detection (platform-agnostic)
        common_tools = [
            "python", "pip", "git", "curl", "ssh"
        ]
        
        # Windows-specific tools
        windows_tools = [
            "powershell", "diskpart", "chkdsk", "sfc", "dism",
            "netsh", "tasklist", "wmic", "reg"
        ]
        
        # Linux-specific tools
        linux_tools = [
            "lspci", "lsusb", "lsblk", "smartctl", "dmidecode",
            "lshw", "hdparm", "fdisk", "df", "free", "systemctl",
            "apt", "dnf", "pacman", "zypper"
        ]
        
        # Check all common tools
        for tool in common_tools:
            self.tools[tool] = self._check_tool_available(tool)
        
        # Check platform-specific tools
        if self.features["is_windows"]:
            for tool in windows_tools:
                self.tools[tool] = self._check_tool_available(tool)
        elif self.features["is_linux"]:
            for tool in linux_tools:
                self.tools[tool] = self._check_tool_available(tool)
    
    def _detect_system_capabilities(self) -> None:
        """Detect system capabilities based on hardware and software"""
        # Initialize capability categories
        self.capabilities = {
            "diagnostics": {},
            "repair": {},
            "performance": {},
            "security": {},
            "hardware": {}
        }
        
        # Check diagnostic capabilities
        self._detect_diagnostic_capabilities()
        
        # Check repair capabilities
        self._detect_repair_capabilities()
        
        # Check hardware capabilities
        self._detect_hardware_capabilities()
    
    def _detect_diagnostic_capabilities(self) -> None:
        """Detect available diagnostic capabilities"""
        diag = self.capabilities["diagnostics"]
        
        # SMART diagnostics
        if self.features["is_windows"]:
            diag["smart"] = self.features["has_wmi"]
        else:  # Linux
            diag["smart"] = self.tools["smartctl"]
        
        # Memory diagnostics
        diag["memory_test"] = True  # Basic memory info always available via psutil
        
        # Disk diagnostics
        if self.features["is_windows"]:
            diag["disk_health"] = self.tools["chkdsk"]
            diag["file_system_check"] = self.tools["chkdsk"]
        else:  # Linux
            diag["disk_health"] = self.tools["smartctl"] or self.tools["hdparm"]
            diag["file_system_check"] = True  # Various tools like fsck available
        
        # Advanced hardware diagnostics
        if self.features["is_windows"]:
            diag["hardware_info"] = self.features["has_wmi"]
        else:  # Linux
            diag["hardware_info"] = self.tools["lshw"] or self.tools["dmidecode"]
    
    def _detect_repair_capabilities(self) -> None:
        """Detect available repair capabilities"""
        repair = self.capabilities["repair"]
        
        # System file repair
        if self.features["is_windows"]:
            repair["system_file_repair"] = self.tools["sfc"]
            repair["component_store_repair"] = self.tools["dism"]
        else:  # Linux
            repair["system_file_repair"] = self.features["is_root"]  # Need root access
            repair["package_repair"] = self._detect_package_manager()
        
        # Disk repair
        if self.features["is_windows"]:
            repair["disk_repair"] = self.tools["chkdsk"]
        else:  # Linux
            repair["disk_repair"] = self.features["is_root"]  # Various tools available
    
    def _detect_hardware_capabilities(self) -> None:
        """Detect hardware capabilities"""
        hardware = self.capabilities["hardware"]
        
        # Check if battery is present
        try:
            import psutil
            if hasattr(psutil, "sensors_battery"):
                battery = psutil.sensors_battery()
                hardware["has_battery"] = battery is not None
            else:
                hardware["has_battery"] = False
        except (ImportError, AttributeError):
            hardware["has_battery"] = False
        
        # Check if temperature sensors are available
        try:
            import psutil
            if hasattr(psutil, "sensors_temperatures"):
                temps = psutil.sensors_temperatures()
                hardware["has_temperature_sensors"] = bool(temps)
            else:
                hardware["has_temperature_sensors"] = False
        except (ImportError, AttributeError):
            hardware["has_temperature_sensors"] = False
    
    def _check_tool_available(self, tool_name: str) -> bool:
        """Check if a command-line tool is available in the system path
        
        Args:
            tool_name: Name of the tool to check
            
        Returns:
            True if the tool is available, False otherwise
        """
        return shutil.which(tool_name) is not None
    
    def _check_module_available(self, module_name: str) -> bool:
        """Check if a Python module is available
        
        Args:
            module_name: Name of the module to check
            
        Returns:
            True if the module is available, False otherwise
        """
        try:
            importlib.util.find_spec(module_name)
            return True
        except ImportError:
            return False
    
    def _is_windows_admin(self) -> bool:
        """Check if the current Windows process has admin privileges
        
        Returns:
            True if running with admin rights, False otherwise
        """
        if not self.system == "windows":
            return False
            
        try:
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False
    
    def _is_winpe_environment(self) -> bool:
        """Detect if the current environment is WinPE
        
        Returns:
            True if running in WinPE, False otherwise
        """
        if not self.system == "windows":
            return False
            
        try:
            # Check for typical WinPE characteristics
            if os.path.exists('X:\\Windows\\System32') and not os.path.exists('C:\\Windows\\System32'):
                return True
            elif 'winpe' in platform.version().lower() or 'winpe' in platform.release().lower():
                return True
                
            # RAM disk check
            import psutil
            for part in psutil.disk_partitions(all=True):
                if part.device == 'X:' and 'ramdisk' in part.opts.lower():
                    return True
                    
            return False
        except Exception as e:
            logging.error(f"Error detecting WinPE environment: {e}")
            return False
    
    def _detect_package_manager(self) -> bool:
        """Detect available Linux package managers
        
        Returns:
            True if a supported package manager is available, False otherwise
        """
        if not self.features["is_linux"]:
            return False
            
        package_managers = ["apt", "dnf", "yum", "pacman", "zypper"]
        return any(self.tools.get(pm, False) for pm in package_managers)
    
    def has_feature(self, feature_name: str) -> bool:
        """Check if a specific feature is available
        
        Args:
            feature_name: Name of the feature to check
            
        Returns:
            True if the feature is available, False otherwise
        """
        return self.features.get(feature_name, False)
    
    def has_tool(self, tool_name: str) -> bool:
        """Check if a specific command-line tool is available
        
        Args:
            tool_name: Name of the tool to check
            
        Returns:
            True if the tool is available, False otherwise
        """
        return self.tools.get(tool_name, False)
    
    def has_capability(self, category: str, capability_name: str) -> bool:
        """Check if a specific capability is available
        
        Args:
            category: Category of the capability (diagnostics, repair, etc.)
            capability_name: Name of the capability to check
            
        Returns:
            True if the capability is available, False otherwise
        """
        if category not in self.capabilities:
            return False
            
        return self.capabilities[category].get(capability_name, False)
    
    def get_all_capabilities(self) -> Dict[str, Dict[str, Any]]:
        """Get all detected capabilities
        
        Returns:
            Dictionary of all capability categories and their detected values
        """
        return self.capabilities
    
    def get_all_features(self) -> Dict[str, bool]:
        """Get all detected features
        
        Returns:
            Dictionary of all features and their detected values
        """
        return self.features
    
    def get_all_tools(self) -> Dict[str, bool]:
        """Get all detected command-line tools
        
        Returns:
            Dictionary of all tools and their availability
        """
        return self.tools


# Test the class when run directly
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Create feature detection instance
    detector = FeatureDetection()
    
    print(f"Running on: {platform.system()} {platform.release()}")
    
    # Show platform features
    print("\nPlatform Features:")
    for feature, available in detector.get_all_features().items():
        print(f"  {feature}: {'Available' if available else 'Not available'}")
    
    # Show diagnostic capabilities
    print("\nDiagnostic Capabilities:")
    for capability, available in detector.get_all_capabilities()["diagnostics"].items():
        print(f"  {capability}: {'Available' if available else 'Not available'}")
    
    # Show repair capabilities
    print("\nRepair Capabilities:")
    for capability, available in detector.get_all_capabilities()["repair"].items():
        print(f"  {capability}: {'Available' if available else 'Not available'}")
    
    # Check for specific tools based on platform
    print("\nPlatform-specific Tools:")
    if detector.has_feature("is_windows"):
        windows_tools = ["powershell", "diskpart", "sfc", "dism", "chkdsk"]
        for tool in windows_tools:
            print(f"  {tool}: {'Available' if detector.has_tool(tool) else 'Not available'}")
    else:  # Linux
        linux_tools = ["smartctl", "dmidecode", "lshw", "lsblk"]
        for tool in linux_tools:
            print(f"  {tool}: {'Available' if detector.has_tool(tool) else 'Not available'}")
