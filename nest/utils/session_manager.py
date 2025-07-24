import json
import os
import logging
from datetime import datetime
from typing import Optional, Dict, Any

class SessionManager:
    """Manages user sessions for the Nest application.
    
    Handles creating, loading, and managing user sessions including
    authentication state and user preferences.
    """
    
    def __init__(self):
        """Initialize the session manager."""
        self.session_data = {}
        self.session_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "session.json")
        self.logger = logging.getLogger(__name__)
        self.load_session()
    
    def load_session(self) -> bool:
        """Load session data from disk.
        
        Returns:
            True if session was loaded successfully, False otherwise
        """
        try:
            if os.path.exists(self.session_file):
                with open(self.session_file, "r") as f:
                    self.session_data = json.load(f)
                self.logger.info("Session loaded successfully")
                return True
            else:
                self.logger.info("No session file found")
                return False
        except Exception as e:
            self.logger.error(f"Failed to load session: {str(e)}")
            return False
    
    def save_session(self) -> bool:
        """Save session data to disk.
        
        Returns:
            True if session was saved successfully, False otherwise
        """
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.session_file), exist_ok=True)
            
            with open(self.session_file, "w") as f:
                json.dump(self.session_data, f, indent=2)
            self.logger.info("Session saved successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to save session: {str(e)}")
            return False
    
    def create_session(self, store_slug: str, employee_id: str, employee_name: str, 
                      employee_data: Dict[str, Any]) -> bool:
        """Create a new user session.
        
        Args:
            store_slug: The RepairDesk store slug
            employee_id: Employee ID of the logged-in user
            employee_name: Employee name of the logged-in user
            employee_data: Additional employee data
            
        Returns:
            True if session was created successfully, False otherwise
        """
        self.session_data = {
            "store_slug": store_slug,
            "employee": {
                "id": employee_id,
                "name": employee_name,
                "role": employee_data.get("type", "Staff"),
                "data": employee_data
            },
            "created_at": datetime.now().isoformat(),
            "last_active": datetime.now().isoformat()
        }
        
        self.logger.info(f"Session created for {employee_name} at store {store_slug}")
        return self.save_session()
    
    def end_session(self) -> bool:
        """End the current session by clearing session data.
        
        Returns:
            True if session was ended successfully, False otherwise
        """
        self.session_data = {}
        self.logger.info("Session ended")
        return self.save_session()
    
    def is_logged_in(self) -> bool:
        """Check if user is currently logged in.
        
        Returns:
            True if session exists and is valid, False otherwise
        """
        return bool(self.session_data and self.session_data.get("employee"))
    
    def get_current_user(self) -> Optional[Dict[str, Any]]:
        """Get the current logged-in user data.
        
        Returns:
            User data dictionary or None if not logged in
        """
        if not self.is_logged_in():
            return None
            
        return {
            "id": self.session_data.get("employee", {}).get("id"),
            "name": self.session_data.get("employee", {}).get("name"),
            "role": self.session_data.get("employee", {}).get("role"),
            "store_slug": self.session_data.get("store_slug")
        }
    
    def get_store_slug(self) -> Optional[str]:
        """Get the store slug from the current session.
        
        Returns:
            Store slug or None if not available
        """
        return self.session_data.get("store_slug")
        
    def get_store_name(self) -> Optional[str]:
        """Get the proper store name from the current session.
        
        Returns:
            Store name or store slug if name not available, or None if neither is available
        """
        store_name = self.session_data.get("store_name")
        if not store_name:
            store_name = self.session_data.get("store_slug")
        return store_name
    
    def set_store_info(self, store_slug: str, store_name: Optional[str] = None) -> None:
        """Set store information in the session.
        
        Args:
            store_slug: The store slug (required)
            store_name: The proper store name (optional)
        """
        self.session_data["store_slug"] = store_slug
        if store_name:
            self.session_data["store_name"] = store_name
        self.save_session()
    
    def update_last_active(self) -> None:
        """Update the last active timestamp."""
        if self.is_logged_in():
            self.session_data["last_active"] = datetime.now().isoformat()
            self.save_session()
