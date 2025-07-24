"""Authentication and user management for Nest application."""

import os
import json
import hashlib
import secrets
import logging
import time
from typing import Dict, Optional, List, Any


class UserManager:
    """Manages user authentication and sessions."""

    def __init__(self, app_dir: str):
        """Initialize the user manager.

        Args:
            app_dir: Application directory path
        """
        self.app_dir = app_dir
        self.users_dir = os.path.join(app_dir, "data", "users")
        self.sessions = {}

        # Create users directory if it doesn't exist
        if not os.path.exists(self.users_dir):
            os.makedirs(self.users_dir)

        # Create default admin user if no users exist
        if not os.listdir(self.users_dir):
            self._create_default_admin()

    def _create_default_admin(self):
        """Create a default admin user."""
        default_admin = {
            "username": "admin",
            "fullname": "Administrator",
            "email": "admin@example.com",
            "role": "Administrator",
            "password_hash": self._hash_password("admin"),
            "created_at": time.time(),
            "last_login": None,
            "active": True,
            "permissions": ["all"],
        }

        try:
            with open(os.path.join(self.users_dir, "admin.json"), "w") as f:
                json.dump(default_admin, f, indent=2)
            logging.info("Created default admin user")
        except Exception as e:
            logging.error(f"Failed to create default admin user: {e}")

    def _hash_password(self, password: str) -> str:
        """Hash a password using SHA-256."""
        return hashlib.sha256(password.encode()).hexdigest()

    def authenticate(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate a user.

        Args:
            username: Username to authenticate
            password: Password to verify

        Returns:
            User data dict if authenticated, None otherwise
        """
        user_path = os.path.join(self.users_dir, f"{username}.json")

        if not os.path.exists(user_path):
            logging.warning(f"Authentication attempt for non-existent user: {username}")
            return None

        try:
            with open(user_path, "r") as f:
                user = json.load(f)

            if user.get("password_hash") == self._hash_password(password):
                if not user.get("active", True):
                    logging.warning(f"Login attempt for inactive user: {username}")
                    return None

                # Create a session
                session_id = secrets.token_hex(16)
                self.sessions[session_id] = {
                    "user": user,
                    "created": time.time(),
                    "last_activity": time.time(),
                }

                # Update last login
                user["last_login"] = time.time()
                with open(user_path, "w") as f:
                    json.dump(user, f, indent=2)

                # Return user data with session ID
                user_data = user.copy()
                user_data["session_id"] = session_id
                if "password_hash" in user_data:
                    del user_data["password_hash"]

                logging.info(f"User '{username}' logged in successfully")
                return user_data
            else:
                logging.warning(f"Failed login attempt for user: {username}")
                return None

        except Exception as e:
            logging.error(f"Error during authentication for {username}: {e}")
            return None

    def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user data by username."""
        user_path = os.path.join(self.users_dir, f"{username}.json")

        if not os.path.exists(user_path):
            return None

        try:
            with open(user_path, "r") as f:
                user = json.load(f)
                if "password_hash" in user:
                    del user["password_hash"]
                return user
        except Exception as e:
            logging.error(f"Error getting user {username}: {e}")
            return None

    def create_user(self, user_data: Dict[str, Any], password: str) -> bool:
        """Create a new user."""
        username = user_data.get("username")
        if not username:
            logging.error("Cannot create user: Missing username")
            return False

        user_path = os.path.join(self.users_dir, f"{username}.json")

        if os.path.exists(user_path):
            logging.warning(f"Cannot create user: User {username} already exists")
            return False

        # Hash the password and add created_at timestamp
        user_data["password_hash"] = self._hash_password(password)
        user_data["created_at"] = time.time()
        user_data["last_login"] = None
        user_data["active"] = True

        try:
            with open(user_path, "w") as f:
                json.dump(user_data, f, indent=2)
            logging.info(f"Created new user: {username}")
            return True
        except Exception as e:
            logging.error(f"Error creating user {username}: {e}")
            return False

    def update_user(self, username: str, user_data: Dict[str, Any]) -> bool:
        """Update an existing user."""
        user_path = os.path.join(self.users_dir, f"{username}.json")

        if not os.path.exists(user_path):
            logging.warning(f"Cannot update user: User {username} does not exist")
            return False

        try:
            # Read existing user data
            with open(user_path, "r") as f:
                existing_user = json.load(f)

            # Update fields while preserving password_hash and timestamps
            for key, value in user_data.items():
                if key not in ["password_hash", "created_at"]:
                    existing_user[key] = value

            # Write updated user data
            with open(user_path, "w") as f:
                json.dump(existing_user, f, indent=2)

            logging.info(f"Updated user: {username}")
            return True
        except Exception as e:
            logging.error(f"Error updating user {username}: {e}")
            return False

    def change_password(self, username: str, new_password: str) -> bool:
        """Change a user's password."""
        user_path = os.path.join(self.users_dir, f"{username}.json")

        if not os.path.exists(user_path):
            logging.warning(f"Cannot change password: User {username} does not exist")
            return False

        try:
            # Read existing user data
            with open(user_path, "r") as f:
                user = json.load(f)

            # Update password hash
            user["password_hash"] = self._hash_password(new_password)

            # Write updated user data
            with open(user_path, "w") as f:
                json.dump(user, f, indent=2)

            logging.info(f"Changed password for user: {username}")
            return True
        except Exception as e:
            logging.error(f"Error changing password for {username}: {e}")
            return False

    def deactivate_user(self, username: str) -> bool:
        """Deactivate a user account."""
        user_path = os.path.join(self.users_dir, f"{username}.json")

        if not os.path.exists(user_path):
            logging.warning(f"Cannot deactivate user: User {username} does not exist")
            return False

        try:
            # Read existing user data
            with open(user_path, "r") as f:
                user = json.load(f)

            # Set active flag to False
            user["active"] = False

            # Write updated user data
            with open(user_path, "w") as f:
                json.dump(user, f, indent=2)

            logging.info(f"Deactivated user: {username}")
            return True
        except Exception as e:
            logging.error(f"Error deactivating user {username}: {e}")
            return False

    def get_all_users(self) -> List[Dict[str, Any]]:
        """Get a list of all users (without password hashes)."""
        users = []
        try:
            for filename in os.listdir(self.users_dir):
                if filename.endswith(".json"):
                    with open(os.path.join(self.users_dir, filename), "r") as f:
                        user = json.load(f)
                        if "password_hash" in user:
                            del user["password_hash"]
                        users.append(user)
            return users
        except Exception as e:
            logging.error(f"Error listing users: {e}")
            return []

    def validate_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Validate a session and return user data."""
        if session_id not in self.sessions:
            return None

        session = self.sessions[session_id]

        # Check if session is expired (e.g., after 12 hours of inactivity)
        if time.time() - session["last_activity"] > 12 * 3600:
            del self.sessions[session_id]
            return None

        # Update last activity time
        session["last_activity"] = time.time()

        # Return user data without password_hash
        user_data = session["user"].copy()
        if "password_hash" in user_data:
            del user_data["password_hash"]

        return user_data

    def logout(self, session_id: str) -> bool:
        """End a user session."""
        if session_id in self.sessions:
            del self.sessions[session_id]
            logging.info(f"User session {session_id[:8]}... logged out")
            return True
        return False
