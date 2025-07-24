import os
import sys
import platform
from pathlib import Path
from typing import Optional
from .feature_detection import FeatureDetection

class PlatformPaths:
    """Cross-platform directory management for Nest application"""
    
    def __init__(self):
        self.feature_detection = FeatureDetection()
        self._app_name = "Nest"
        
    def get_user_data_dir(self) -> Path:
        """Get platform-appropriate user data directory"""
        if self.feature_detection.has_feature("is_windows"):
            if self.feature_detection.has_feature("has_winpe"):
                return self._get_portable_dir()
            else:
                appdata = os.environ.get('LOCALAPPDATA', os.path.expanduser('~/AppData/Local'))
                return Path(appdata) / self._app_name
        elif self.feature_detection.has_feature("is_macos"):
            return Path.home() / "Library" / "Application Support" / self._app_name
        else:
            return Path.home() / ".local" / "share" / self._app_name
            
    def get_config_dir(self) -> Path:
        """Get platform-appropriate config directory"""
        if self.feature_detection.has_feature("is_windows"):
            if self.feature_detection.has_feature("has_winpe"):
                return self._get_portable_dir() / "config"
            else:
                appdata = os.environ.get('APPDATA', os.path.expanduser('~/AppData/Roaming'))
                return Path(appdata) / self._app_name
        elif self.feature_detection.has_feature("is_macos"):
            return Path.home() / "Library" / "Preferences" / self._app_name
        else:
            return Path.home() / ".config" / self._app_name
            
    def get_cache_dir(self) -> Path:
        """Get platform-appropriate cache directory"""
        if self.feature_detection.has_feature("is_windows"):
            if self.feature_detection.has_feature("has_winpe"):
                return self._get_portable_dir() / "cache"
            else:
                appdata = os.environ.get('LOCALAPPDATA', os.path.expanduser('~/AppData/Local'))
                return Path(appdata) / self._app_name / "cache"
        elif self.feature_detection.has_feature("is_macos"):
            return Path.home() / "Library" / "Caches" / self._app_name
        else:
            return Path.home() / ".cache" / self._app_name
            
    def get_logs_dir(self) -> Path:
        """Get platform-appropriate logs directory"""
        if self.feature_detection.has_feature("is_windows"):
            if self.feature_detection.has_feature("has_winpe"):
                return self._get_portable_dir() / "logs"
            else:
                appdata = os.environ.get('LOCALAPPDATA', os.path.expanduser('~/AppData/Local'))
                return Path(appdata) / self._app_name / "logs"
        elif self.feature_detection.has_feature("is_macos"):
            return Path.home() / "Library" / "Logs" / self._app_name
        else:
            return self.get_user_data_dir() / "logs"
            
    def _get_portable_dir(self) -> Path:
        """Get portable directory for WinPE or development"""
        if getattr(sys, 'frozen', False):
            return Path(sys.executable).parent
        else:
            return Path(__file__).parent.parent.parent
            
    def ensure_dir_exists(self, path: Path) -> Path:
        """Ensure directory exists and return the path"""
        path.mkdir(parents=True, exist_ok=True)
        return path
