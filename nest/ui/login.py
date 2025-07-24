import tkinter as tk
from tkinter import ttk, messagebox
import logging
import os
import json
from datetime import datetime
import threading
import requests
import re
import io
from PIL import Image, ImageTk
from nest.utils.normalize import normalize_store_name


class LoginFrame(ttk.Frame):
    """Login frame for Nest - Computer Repair Management with store-first authentication."""
    
    def show_loading(self, msg="Loading..."):
        """Show a loading indicator (only logs to console)."""
        self.loading = True
        logging.info(f"LOADING: {msg}")
        
        # For backward compatibility, keep the status_var
        if not hasattr(self, 'status_var'):
            self.status_var = tk.StringVar()
        self.status_var.set(msg)
    
    def animate_loading(self, count):
        """Animate loading dots (only logs to console)."""
        # No longer needed since we're not showing the loading indicator in the UI
        pass
    
    def hide_loading(self):
        """Hide the loading indicator (only logs to console)."""
        self.loading = False
        logging.info("LOADING: Complete")
        
        # For backward compatibility, keep the status_var
        if hasattr(self, 'status_var'):
            self.status_var.set("")
            
    def show_error(self, msg):
        """Display error message (only logs to console)."""
        logging.error(f"ERROR: {msg}")
        
        # For backward compatibility, keep the status_var
        if not hasattr(self, 'status_var'):
            self.status_var = tk.StringVar()
        self.status_var.set(msg)

    def show_warning(self, msg):
        """Display warning message (only logs to console)."""
        logging.warning(f"WARNING: {msg}")
        
        # For backward compatibility, keep the status_var
        if not hasattr(self, 'status_var'):
            self.status_var = tk.StringVar()
        self.status_var.set(msg)

    def show_success(self, msg):
        """Display success message (only logs to console)."""
        logging.info(f"SUCCESS: {msg}")
        
        # For backward compatibility, keep the status_var
        if not hasattr(self, 'status_var'):
            self.status_var = tk.StringVar()
        self.status_var.set(msg)
    
    def _reset_last_login_file(self, file_path):
        """Reset the last login file with a proper empty structure."""
        try:
            empty_data = {
                "username": "",
                "id": "",
                "role": "",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            with open(file_path, 'w') as f:
                json.dump(empty_data, f, indent=4)
            logging.info("Reset last_login.json file with proper structure")
        except Exception as e:
            logging.warning(f"Failed to reset last_login.json: {e}")    
    
    def animate_loading(self, count):
        """Animate loading dots."""
        if not self.loading:
            return
        dots = "." * (count % 4)
        base = self.status_var.get().rstrip(".") or "Loading"
        self.status_var.set(f"{base}{dots}")
        self.after(500, lambda: self.animate_loading(count + 1))
    
    def restrict_pin_input(self, *args):
        """Allow only digits, max 4."""
        pin = "".join(filter(str.isdigit, self.pin_var.get()))[:4]
        if pin != self.pin_var.get():
            self.pin_var.set(pin)
            
    def check_api_key_validity(self, api_key):
        """Validate the API key format before attempting connection."""
        # Basic validation of API key format (typically hexadecimal string)
        if not api_key or len(api_key) < 20:  # Most API keys are longer than 20 chars
            return False
        
        # Check if API key has valid characters (alphanumeric)
        import re
        if not re.match(r'^[a-zA-Z0-9_\-]+$', api_key):
            return False
            
        return True

    # Note: remember_credentials method removed as we now always save credentials in connect_to_store

    def forget_credentials(self):
        """Remove stored credentials from config."""
        config_updates = {
            "api_key": "",
            "store_slug": "",
            "repairdesk": {
                "api_key": "",
                "store_slug": ""
            }
        }
        
        # Keep store_name for user convenience
        self.save_config(config_updates)
        logging.info("Store credentials removed from config")

    def get_employee_by_id(self, employee_id):
        """Find an employee by their ID in the employees list."""
        if not self.employees:
            return None
            
        return next((emp for emp in self.employees if emp.get("id") == employee_id), None)

    def preselect_last_user(self):
        """Preselect the last logged in user if available."""
        if not hasattr(self, 'last_user') or not self.last_user:
            return
            
        # Find the last user in the employee list
        employee_names = [emp.get('fullname', '') for emp in self.employees]
        if self.last_user in employee_names:
            index = employee_names.index(self.last_user)
            self.employee_combo.current(index)
            self.update_employee_avatar(index)
            
            # Set the selected employee
            self.selected_employee = self.employees[index]
            logging.info(f"Preselected last user: {self.last_user}")

    def show_welcome_message(self):
        """Show a welcome message for returning users."""
        if not hasattr(self, 'last_user') or not self.last_user:
            return
            
        # Create welcome frame if needed
        if not self.welcome_frame:
            self.welcome_frame = ttk.Frame(self.container, style="Login.TFrame")
            self.welcome_frame.pack(fill="x", pady=(0, 20))
            
            # Create avatar and welcome message
            welcome_text = f"Welcome back, {self.last_user}!"
            self.welcome_label = ttk.Label(
                self.welcome_frame,
                text=welcome_text,
                style="Login.TLabel",
                font=("Segoe UI", 14)
            )
            self.welcome_label.pack(pady=10)
            
            # Show last login time if available
            if "last_login" in self.config:
                last_login = self.config.get("last_login")
                last_login_text = f"Last login: {last_login}"
                ttk.Label(
                    self.welcome_frame,
                    text=last_login_text,
                    style="Login.TLabel",
                    font=("Segoe UI", 9)
                ).pack()

    def handle_logout(self):
        """Handle user logout and return to store selection."""
        # Confirm logout
        if messagebox.askyesno("Logout", "Are you sure you want to log out?"):
            self.show_store_view()
            
            # Clear PIN field
            if hasattr(self, 'pin_var'):
                self.pin_var.set("")

    def encrypt_sensitive_data(self, data):
        """Encrypt sensitive data before storing in config.
        
        Uses the Fernet encryption from cryptography package.
        """
        try:
            from cryptography.fernet import Fernet
            import base64
            import os
            
            # Generate or load encryption key
            key_path = os.path.join(self.find_config_dir(), ".encryption_key")
            if os.path.exists(key_path):
                with open(key_path, "rb") as f:
                    key = f.read()
            else:
                key = Fernet.generate_key()
                with open(key_path, "wb") as f:
                    f.write(key)
                    
            # Create Fernet cipher and encrypt
            cipher = Fernet(key)
            encrypted = cipher.encrypt(data.encode())
            
            return base64.b64encode(encrypted).decode()
        except ImportError:
            logging.warning("Cryptography package not available, storing data unencrypted")
            return data
        except Exception as e:
            logging.error(f"Encryption error: {e}")
            return data

    def decrypt_sensitive_data(self, encrypted_data):
        """Decrypt sensitive data from config."""
        try:
            from cryptography.fernet import Fernet
            import base64
            import os
            
            # Load encryption key
            key_path = os.path.join(self.find_config_dir(), ".encryption_key")
            if not os.path.exists(key_path):
                logging.error("Encryption key not found")
                return ""
                
            with open(key_path, "rb") as f:
                key = f.read()
                
            # Create Fernet cipher and decrypt
            cipher = Fernet(key)
            decoded = base64.b64decode(encrypted_data)
            decrypted = cipher.decrypt(decoded)
            
            return decrypted.decode()
        except ImportError:
            logging.warning("Cryptography package not available, returning data as-is")
            return encrypted_data
        except Exception as e:
            logging.error(f"Decryption error: {e}")
            return ""

    def create_draggable_title_bar(self):
        """Create a custom title bar that allows window dragging."""
        # Only applicable if we're in a top-level window
        if not isinstance(self.parent, tk.Tk) and not isinstance(self.parent, tk.Toplevel):
            return
            
        # Create title bar frame
        title_bar = ttk.Frame(self, style="TitleBar.TFrame")
        title_bar.pack(fill="x", side="top")
        
        # App title
        title_label = ttk.Label(
            title_bar, 
            text="RepairDesk Nest - Login",
            style="TitleBar.TLabel"
        )
        title_label.pack(side="left", padx=10)
        
        # Close button
        close_button = ttk.Button(
            title_bar,
            text="×",
            width=3,
            command=self.parent.destroy,
            style="TitleBar.TButton"
        )
        close_button.pack(side="right")
        
        # Configure title bar style
        style = ttk.Style()
        style.configure(
            "TitleBar.TFrame",
            background=self.colors.get("primary_dark", "#0D47A1")
        )
        style.configure(
            "TitleBar.TLabel",
            background=self.colors.get("primary_dark", "#0D47A1"),
            foreground="white",
            font=("Segoe UI", 10, "bold")
        )
        style.configure(
            "TitleBar.TButton",
            background=self.colors.get("primary_dark", "#0D47A1"),
            foreground="white",
            borderwidth=0
        )
        
        # Bind dragging events to title bar
        title_bar.bind("<ButtonPress-1>", self._start_drag)
        title_bar.bind("<ButtonRelease-1>", self._stop_drag)
        title_bar.bind("<B1-Motion>", self._do_drag)
        title_label.bind("<ButtonPress-1>", self._start_drag)
        title_label.bind("<ButtonRelease-1>", self._stop_drag)
        title_label.bind("<B1-Motion>", self._do_drag)
        
    def _start_drag(self, event):
        """Start window dragging."""
        self._drag_data = {"x": event.x, "y": event.y}
        
    def _stop_drag(self, event):
        """Stop window dragging."""
        self._drag_data = None
        
    def _do_drag(self, event):
        """Update window position during drag."""
        if self._drag_data:
            x = self.parent.winfo_x() + (event.x - self._drag_data["x"])
            y = self.parent.winfo_y() + (event.y - self._drag_data["y"])
            self.parent.geometry(f"+{x}+{y}")

    def create_auto_login_option(self):
        """Create option to automatically login next time."""
        # Only show in employee selection view
        if self.current_view != "employee":
            return
            
        # Create a checkbutton for auto-login
        self.auto_login_var = tk.BooleanVar(value=False)
        auto_login_check = ttk.Checkbutton(
            self.content_frame,
            text="Log in automatically next time",
            variable=self.auto_login_var,
            style="Login.TCheckbutton"
        )
        auto_login_check.pack(pady=(5, 0))
        
        # Update config when option changes
        def update_auto_login(*args):
            self.save_config({"auto_login": self.auto_login_var.get()})
            
        self.auto_login_var.trace_add("write", update_auto_login)

    def check_auto_login(self):
        """Check if auto-login is enabled and perform login if possible."""
        auto_login = self.config.get("auto_login", False)
        if not auto_login:
            return False
            
        # Need store, employee ID and PIN
        store_slug = self.config.get("store_slug")
        store_name = self.config.get("store_name")
        api_key = self.config.get("api_key")
        employee_id = self.config.get("last_user_id")
        encrypted_pin = self.config.get("last_pin")
        
        if not all([store_slug, store_name, api_key, employee_id, encrypted_pin]):
            return False
            
        # Decrypt PIN
        pin = self.decrypt_sensitive_data(encrypted_pin)
        if not pin:
            return False
            
        # Connect to store
        self.show_loading("Auto-login in progress...")
        self.connect_to_store(store_name, store_slug, api_key)
        
        # Set employee and PIN after a delay to allow employee list to load
        def complete_auto_login():
            # Find employee by ID
            employee = self.get_employee_by_id(employee_id)
            if not employee:
                self.hide_loading()
                self.show_error("Auto-login failed: Employee not found")
                return
                
            # Set employee in dropdown
            employee_names = [emp.get('fullname', '') for emp in self.employees]
            employee_name = employee.get("fullname", "")
            if employee_name in employee_names:
                index = employee_names.index(employee_name)
                self.employee_combo.current(index)
                self.selected_employee = employee
                
                # Set PIN and trigger login
                self.pin_var.set(pin)
                self.handle_login()
                
        # Wait for employees to load
        self.after(1500, complete_auto_login)
        return True

    def verify_compatibility(self):
        """Verify the system compatibility with Nest application."""
        import platform
        import sys
        
        # Check Python version
        python_version = sys.version_info
        if python_version.major < 3 or (python_version.major == 3 and python_version.minor < 8):
            messagebox.showwarning(
                "Compatibility Warning",
                "Nest requires Python 3.8 or higher. Some features may not work correctly."
            )
        
        # Check operating system
        os_name = platform.system()
        if os_name not in ["Windows", "Darwin", "Linux"]:
            messagebox.showwarning(
                "Compatibility Warning",
                f"Nest is not fully tested on {os_name}. Some features may not work correctly."
            )
        
        # Check required packages
        required_packages = [
            "tkinter", 
            "pillow", 
            "requests", 
            "cryptography"
        ]
        missing_packages = []
        
        for package in required_packages:
            try:
                __import__(package)
            except ImportError:
                missing_packages.append(package)
        
        if missing_packages:
            message = (
                f"The following packages are required but missing:\n" +
                f"{', '.join(missing_packages)}\n\n" +
                f"Some features may not work correctly without these packages."
            )
            messagebox.showwarning("Missing Packages", message)

    def cleanup(self):
        """Clean up resources before closing."""
        # Stop any running threads
        if hasattr(self, "_bg_thread") and self._bg_thread and self._bg_thread.is_alive():
            self._bg_thread_running = False
            self._bg_thread.join(timeout=1.0)
        
        # Remove temporary files
        for attr in dir(self):
            if attr.startswith("_temp_") and hasattr(self, attr):
                temp_file = getattr(self, attr)
                try:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                except:
                    pass

    def show_about_dialog(self):
        """Show information about the application."""
        version = "1.0.0"  # Get from config or hardcode
        
        about_text = (
            f"RepairDesk Nest\n" +
            f"Version: {version}\n\n" +
            f"A desktop companion application for\n" +
            f"RepairDesk repair shop management system.\n\n" +
            f"© 2025 RepairDesk\n" +
            f"All rights reserved."
        )
        
        messagebox.showinfo("About RepairDesk Nest", about_text)

    def show_help(self):
        """Show help information."""
        help_text = (
            "Login Help:\n\n" +
            "1. Enter your RepairDesk store name\n" +
            "2. Enter your API key (available in RepairDesk settings)\n" +
            "3. Click 'Connect to Store'\n" +
            "4. Select your name from the dropdown\n" +
            "5. Enter your PIN\n" +
            "6. Click 'Login'\n\n" +
            "Need more help? Contact support at support@repairdesk.co"
        )
        
        messagebox.showinfo("Login Help", help_text)

    def handle_connectivity_issues(self, error):
        """Handle network connectivity issues during login."""
        import socket
        
        if isinstance(error, requests.exceptions.ConnectionError):
            messagebox.showerror(
                "Connection Error",
                "Could not connect to RepairDesk. Please check your internet connection."
            )
        elif isinstance(error, requests.exceptions.Timeout):
            messagebox.showerror(
                "Connection Timeout",
                "Connection to RepairDesk timed out. Please try again later."
            )
        elif isinstance(error, socket.gaierror):
            messagebox.showerror(
                "DNS Resolution Error",
                "Could not resolve RepairDesk server. Please check your internet connection."
            )
        else:
            messagebox.showerror(
                "Connection Error",
                f"An error occurred while connecting to RepairDesk: {str(error)}"
            )
            
        # Auto-submit if 4 digits entered
        if len(pin) == 4:
            self.after(100, self.handle_login)
            
    def is_login_locked(self):
        """Check if login is currently locked."""
        if self.locked_until is None:
            return False
        
        # Check if lock period has expired
        if datetime.now().timestamp() > self.locked_until:
            self.locked_until = None
            return False
        
        return True
    
    def get_lock_remaining_time(self):
        """Return remaining lockout time in minutes."""
        return round(max(0, self.locked_until - datetime.now().timestamp()) / 60, 1)
    
    def handle_failed_login(self):
        """Handle failed login attempts with lockout."""
        self.login_attempts += 1
        remaining = self.max_attempts - self.login_attempts
        
        if remaining <= 0:
            # Lock login for 5 minutes
            self.locked_until = datetime.now().timestamp() + (5 * 60)
            self.login_attempts = 0
            self.show_error(f"Too many failed attempts. Login locked for 5 minutes.")
        else:
            self.show_error(f"Invalid PIN. {remaining} attempts remaining before lockout.")
    
    def validate_pin(self, pin):
        """Check PIN against selected employee."""
        if not self.selected_employee:
            logging.warning("No employee selected for PIN validation")
            return False
        
        # Try different possible field names for PIN
        possible_pin_fields = ["accesspin", "pin", "password", "passcode", "pass", "code", "access_code", "security_code"]
    
        # Debug log of employee data
        employee_id = self.selected_employee.get("id", "unknown")
        employee_name = self.selected_employee.get("fullname", "unknown")
        logging.info(f"Validating PIN for employee: {employee_name} (ID: {employee_id})")
        logging.debug(f"Employee data keys: {list(self.selected_employee.keys())}")
        
        # Check if the PIN matches any of the possible fields
        for field in possible_pin_fields:
            stored_pin = str(self.selected_employee.get(field, ""))
            if stored_pin and pin == stored_pin:
                logging.info(f"PIN matched using field: {field}")
                return True
        
        # Log failure reason
        logging.warning(f"PIN validation failed for {employee_name}. Entered: {pin}")
        return False
    
    def handle_successful_login(self, employee):
        """Handle actions after a successful login."""
        # Reset login attempts
        self.login_attempts = 0
        self.locked_until = None
        
        # Show success message with role information
        role_display = employee.get("role", "User")
        self.show_success(f"Welcome, {employee['fullname']}! Logged in as {role_display}")
        
        # Prepare comprehensive user data
        user = {
            "id": str(employee.get("id", "")),
            "username": employee.get("fullname", "").lower().replace(" ", ""),
            "fullname": employee.get("fullname", ""),
            "role": employee.get("role", "User"),
            "store_slug": self.store_slug,
            "store_name": self.store_name,
            "api_key": self.api_key,
            "last_login": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "image": employee.get("image", ""),  # Direct URL from API
            "avatar": employee.get("avatar", "")  # Alternative field name
        }
        
        # Get avatar URL from avatar_util if available
        try:
            from nest.utils.avatar_util import get_avatar_for_user
            avatar_url = get_avatar_for_user(
                user_id=user["id"],
                name=user["fullname"],
                direct_url=user.get("image") or user.get("avatar")
            )
            if avatar_url:
                user["avatar_url"] = avatar_url
                logging.info(f"Added avatar URL from avatar_util: {avatar_url}")
        except Exception as avatar_error:
            logging.warning(f"Could not get avatar URL: {avatar_error}")
        
        # Save this user as the last logged in user - without touching store information
        current_config = self.load_config()
        # Only update user-related fields, don't touch store_name or store_slug
        config_data = {
            "last_user": user["fullname"],
            "last_user_id": user["id"],
            "name": user["fullname"],
            "role": user["role"],
            "last_login": user["last_login"]
        }
        
        # Add avatar URL to config if available
        for field in ["avatar_url", "avatar", "image", "photo", "picture", "gravatar"]:
            if field in user and user[field]:
                config_data["avatar"] = user[field]
                # Log the source of the avatar URL
                logging.info(f"Saved avatar URL from {field} field: {user[field]}")
                break
        
        # Save the config
        self.save_config(config_data)
        
        # Also save to the last_login.json file for easier retrieval
        try:
            last_login_data = {
                "username": user["fullname"],
                "id": user["id"],
                "role": user["role"],
                "store": user["store_name"],
                "timestamp": user["last_login"]
            }
            
            # Add avatar URL if available
            if "avatar_url" in user:
                last_login_data["avatar_url"] = user["avatar_url"]
            elif "avatar" in user:
                last_login_data["avatar_url"] = user["avatar"]
            elif "image" in user:
                last_login_data["avatar_url"] = user["image"]
            
            # Get the root directory of the Nest application.
            current_dir = os.path.dirname(os.path.abspath(__file__))
            # Go up one level to the nest directory
            root_dir = os.path.dirname(current_dir)
            
            last_login_path = os.path.join(root_dir, "last_login.json")
            with open(last_login_path, 'w') as f:
                json.dump(last_login_data, f, indent=4)
            logging.info(f"Last login data saved to {last_login_path}")
        except Exception as e:
            logging.warning(f"Failed to save last login data: {e}")
        
        # Log successful login with store information
        logging.info(f"User '{user['fullname']}' logged in to store '{user['store_name']}' as {user['role']}")
        
        # Call the success callback after a short delay
        self.after(500, lambda: self.on_login_success(user) if self.on_login_success else None)
    

    def create_tooltip(self, widget, text):
        """Create a tooltip for a given widget."""
        tooltip_window = None
        
        def enter(event=None):
            nonlocal tooltip_window
            x, y, _, _ = widget.bbox("insert")
            x += widget.winfo_rootx() + 25
            y += widget.winfo_rooty() + 25
            
            # Create a toplevel window
            tooltip_window = tk.Toplevel(widget)
            tooltip_window.wm_overrideredirect(True)  # Remove window decorations
            tooltip_window.wm_geometry(f"+{x}+{y}")
            
            # Create tooltip content
            tooltip_frame = ttk.Frame(tooltip_window, style="Tooltip.TFrame", padding=5)
            tooltip_frame.pack(fill=tk.BOTH, expand=True)
            
            # Add text to tooltip
            tooltip_label = ttk.Label(
                tooltip_frame, 
                text=text, 
                style="Tooltip.TLabel",
                wraplength=250,
                justify=tk.LEFT
            )
            tooltip_label.pack()
            
            # Style the tooltip
            style = ttk.Style()
            style.configure("Tooltip.TFrame", background="#333333")
            style.configure("Tooltip.TLabel", background="#333333", foreground="white", font=("Segoe UI", 9))
        
        def leave(event=None):
            nonlocal tooltip_window
            if tooltip_window:
                tooltip_window.destroy()
                tooltip_window = None
        
        # Bind events to show/hide tooltip
        widget.bind("<Enter>", enter)
        widget.bind("<Leave>", leave)
    
    def set_placeholder(self, entry_widget, string_var, placeholder):
        """Add placeholder text to an entry widget."""
        entry_widget.placeholder = placeholder
        entry_widget.placeholder_color = "#aaaaaa"
        entry_widget.default_fg_color = entry_widget["foreground"]
        
        def on_focus_in(event):
            if string_var.get() == entry_widget.placeholder:
                entry_widget.delete(0, tk.END)
                entry_widget.config(foreground=entry_widget.default_fg_color)
        
        def on_focus_out(event):
            if string_var.get() == "":
                entry_widget.insert(0, entry_widget.placeholder)
                entry_widget.config(foreground=entry_widget.placeholder_color)
        
        # Set initial placeholder if empty
        if string_var.get() == "":
            string_var.set(placeholder)
            entry_widget.config(foreground=entry_widget.placeholder_color)
        
        # Bind events
        entry_widget.bind("<FocusIn>", on_focus_in)
        entry_widget.bind("<FocusOut>", on_focus_out)
    
    def toggle_api_key_visibility(self):
        """Toggle visibility of API key."""
        if self.show_api_key.get():
            self.api_entry.config(show="")
            self.toggle_api_button.config(text="Hide")
            self.show_api_key.set(False)
        else:
            self.api_entry.config(show="•")
            self.toggle_api_button.config(text="Show")
            self.show_api_key.set(True)
    
    def apply_background_svg(self, svg_path):
        """Apply SVG background to the login screen."""
        try:
            # For SVG support, we need to check if cairosvg is available
            try:
                import cairosvg
                from io import BytesIO
                from PIL import Image, ImageTk
                
                # Convert SVG to PNG in memory
                png_data = BytesIO()
                cairosvg.svg2png(url=str(svg_path), write_to=png_data)
                png_data.seek(0)
                
                # Create background image
                bg_img = Image.open(png_data)
                bg_img = bg_img.resize((800, 600), Image.Resampling.LANCZOS)  # Adjust size as needed
                self.bg_image = ImageTk.PhotoImage(bg_img)
                
                # Create background label
                bg_label = tk.Label(self, image=self.bg_image)
                bg_label.place(x=0, y=0, relwidth=1, relheight=1)
                
                # Make sure content stays on top
                self.container.lift()
                
            except ImportError:
                # Fallback to transparent PNG if available
                from pathlib import Path
                png_path = Path(svg_path).parent / "background_image_transparent.png"
                
                if png_path.exists():
                    from PIL import Image, ImageTk
                    bg_img = Image.open(png_path)
                    bg_img = bg_img.resize((800, 600), Image.Resampling.LANCZOS)
                    self.bg_image = ImageTk.PhotoImage(bg_img)
                    
                    # Create background label
                    bg_label = tk.Label(self, image=self.bg_image)
                    bg_label.place(x=0, y=0, relwidth=1, relheight=1)
                    
                    # Make sure content stays on top
                    self.container.lift()
                else:
                    logging.warning(f"CairoSVG not installed and PNG fallback not found at {png_path}")
        except Exception as e:
            logging.warning(f"Failed to apply background: {e}")
    
    def setup_ui(self):
        """Set up the base UI components and styles."""
        # Configure the frame to expand to fill its parent
        self.pack(fill=tk.BOTH, expand=True)
        
        # Status variable for displaying messages (only used for backward compatibility)
        self.status_var = tk.StringVar()
        
        # Main container for the login form
        self.container = ttk.Frame(self, style="Login.TFrame")
        self.container.pack(expand=True, fill=tk.BOTH, padx=20, pady=20)
        
        # Create the main content frame that will hold either store or employee view
        self.content_frame = ttk.Frame(self.container, style="Login.TFrame")
        self.content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Configure grid weights for responsive layout
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        
        # Style configuration
        style = ttk.Style()
        # Login styles
        style.configure(
            "Login.TFrame", 
            background=self.colors.get("content_bg", "#0b4d49")
        )
        style.configure(
            "Login.TLabel", 
            background=self.colors.get("content_bg", "#0b4d49"),
            foreground="white",
            font=("Segoe UI", 10)
        )
        style.configure(
            "Login.TEntry",
            fieldbackground="white",
            foreground="black",
            padding=8,
            font=("Segoe UI", 10)
        )
        style.configure(
            "Login.TButton",
            font=("Segoe UI", 10, "bold"),
            padding=10
        )
        style.configure(
            "Avatar.TLabel",
            background=self.colors.get("content_bg", "#0b4d49"),
            foreground="white"
        )
        
        # Set default background for all widgets
        for widget in [self, self.container, self.content_frame]:
            widget.configure(style="Login.TFrame")
    
    def show_store_view(self):
        """Display the store login view with store name and API key entry."""
        # Clear any existing widgets in content frame
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        self.current_view = "store"
    
        # Create form frame with padding
        form_frame = ttk.Frame(self.content_frame, style="Login.TFrame")
        form_frame.pack(expand=True, fill=tk.BOTH, padx=40, pady=20)
        
        # Create a centered frame for content, similar to employee selection screen
        centered_frame = ttk.Frame(form_frame, style="Login.TFrame")
        centered_frame.pack(expand=True, fill=tk.BOTH, padx=20, pady=20)
        
        # Add NEST logo and background
        try:
            # Try to load logo from theme assets first, then fallback to other locations
            import os
            from pathlib import Path
            
            logo_paths = [
                os.path.join(os.path.dirname(os.path.dirname(__file__)), "theme", "assets", "png_logo.png"),
                os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "images", "logo.png"),
                os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "logo.png")
            ]
            
            logo_path = None
            for path in logo_paths:
                if os.path.exists(path):
                    logo_path = path
                    break
                    
            if logo_path:
                from PIL import Image, ImageTk
                img = Image.open(logo_path)
                
                # Create a fixed-size frame for the logo to ensure consistent sizing
                logo_frame = ttk.Frame(
                    centered_frame,
                    style="Avatar.TFrame",
                    width=120,
                    height=120
                )
                logo_frame.pack(pady=(0, 20), anchor="center")
                
                # Force the frame to maintain its size
                logo_frame.pack_propagate(False)
                
                # Calculate height while maintaining aspect ratio
                width = 120  # Match avatar size
                aspect_ratio = img.width / img.height
                height = int(width / aspect_ratio)
                
                # Resize logo to appropriate dimensions
                img = img.resize((width, height), Image.LANCZOS)
                
                # Create a PhotoImage and keep a reference
                self.logo_img = ImageTk.PhotoImage(img)
                
                # Add the logo in a label
                logo_label = ttk.Label(
                    logo_frame, 
                    image=self.logo_img, 
                    style="Avatar.TLabel",
                    anchor="center"
                )
                logo_label.pack(fill=tk.BOTH, expand=True)
                
                # Add a title below the logo
                title_label = ttk.Label(
                    centered_frame,
                    text="Elite Repairs",
                    font=("Segoe UI", 16, "bold"),
                    style="Login.TLabel"
                )
                title_label.pack(pady=(0, 5), anchor="center")
                
                # Add subtitle
                subtitle_label = ttk.Label(
                    centered_frame,
                    text="Select your store:",
                    font=("Segoe UI", 11),
                    style="Login.TLabel"
                )
                subtitle_label.pack(pady=(0, 20), anchor="center")
                
                logging.info(f"Loaded logo from {logo_path}")
            else:
                # Fallback to text if no logo is found - with consistent styling
                # Create a fixed-size frame for the text avatar
                logo_frame = ttk.Frame(
                    centered_frame,
                    style="Avatar.TFrame",
                    width=120,
                    height=120
                )
                logo_frame.pack(pady=(0, 20), anchor="center")
                logo_frame.pack_propagate(False)
                
                # Text avatar (like the initials fallback)
                logo_label = ttk.Label(
                    logo_frame,
                    text="N",
                    style="Avatar.TLabel",
                    font=("Segoe UI", 48),
                    anchor="center"
                )
                logo_label.pack(fill=tk.BOTH, expand=True)
                
                # Title
                title_label = ttk.Label(
                    centered_frame,
                    text="Nest Computer Repair",
                    font=("Segoe UI", 16, "bold"),
                    style="Login.TLabel"
                )
                title_label.pack(pady=(0, 5), anchor="center")
                
                # Subtitle
                subtitle_label = ttk.Label(
                    centered_frame,
                    text="Select your store:",
                    font=("Segoe UI", 11),
                    style="Login.TLabel"
                )
                subtitle_label.pack(pady=(0, 20), anchor="center")
                
                logging.warning("No logo file found, using text fallback")
                
            # Try to load background SVG
            try:
                bg_path = Path(__file__).parent.parent / "theme" / "assets" / "background_image.svg"
                if bg_path.exists():
                    # Add a canvas or label for the background
                    logging.info(f"Found background SVG at {bg_path}")
                    # We'll implement the SVG background in a separate method
                    self.apply_background_svg(bg_path)
            except Exception as bg_error:
                logging.warning(f"Could not load background SVG: {bg_error}")
                
        except Exception as e:
            logging.warning(f"Could not load logo: {e}")
            # Fallback to text logo with styled appearance
            title_frame = ttk.Frame(form_frame, style="Login.TFrame")
            title_frame.pack(pady=(0, 30))
            
            ttk.Label(
                title_frame,
                text="NEST",
                style="Login.TLabel",
                font=("Segoe UI", 32, "bold")
            ).pack(side=tk.LEFT)
            
            ttk.Label(
                title_frame,
                text="for RepairDesk",
                style="Login.TLabel",
                font=("Segoe UI", 12)
            ).pack(side=tk.LEFT, padx=(5, 0), pady=(15, 0))
        
        # Create an info frame for form fields (similar to employee selection)
        info_frame = ttk.Frame(centered_frame, style="Login.TFrame")
        info_frame.pack(fill=tk.X, expand=True, padx=20)
        
        # Store name label
        ttk.Label(
            info_frame,
            text="Store Name:",
            style="Login.TLabel",
            font=("Segoe UI", 11)
        ).pack(anchor="center", pady=(0, 5))
        
        # Store name entry with validation - centered and consistent with employee dropdown
        self.store_name_var = tk.StringVar()
        self.store_entry = ttk.Entry(
            info_frame,
            textvariable=self.store_name_var,
            style="Login.TEntry",
            font=("Segoe UI", 11),
            justify="center",
            width=30  # Match employee dropdown width
        )
        self.store_entry.pack(pady=(0, 20), anchor="center")
        
        # Add placeholder text
        self.set_placeholder(self.store_entry, self.store_name_var, "Enter your store name")
        
        # API Key label
        ttk.Label(
            info_frame,
            text="API Key:",
            style="Login.TLabel",
            font=("Segoe UI", 11)
        ).pack(anchor="center", pady=(0, 5))
        
        # Create a frame for API key entry to center it
        api_frame = ttk.Frame(info_frame, style="Login.TFrame")
        api_frame.pack(anchor="center", pady=(0, 5))
        
        # API key entry with show/hide toggle
        self.api_key_var = tk.StringVar()
        
        # Create a wrapper frame to control the width of the API key entry
        api_entry_frame = ttk.Frame(api_frame, style="Login.TFrame")
        api_entry_frame.pack(pady=(0, 5), fill=tk.X)
        
        # API key entry with consistent styling
        self.api_entry = ttk.Entry(
            api_entry_frame,
            textvariable=self.api_key_var,
            show="•",  # Use the same bullet character as PIN
            style="Login.TEntry",
            font=("Segoe UI", 11),
            justify="center",
            width=30  # Match employee dropdown width
        )
        self.api_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Add tooltip for API key with icon
        api_tooltip = "Your RepairDesk API key can be found in your account settings"
        api_tooltip_label = ttk.Label(
            api_entry_frame,
            text="?",
            style="Tooltip.TLabel",
            cursor="question_arrow"
        )
        api_tooltip_label.pack(side=tk.RIGHT, padx=(5, 0))
        self.create_tooltip(api_tooltip_label, api_tooltip)
        
        # Error message display
        self.error_var = tk.StringVar()
        self.error_label = ttk.Label(
            info_frame,
            textvariable=self.error_var,
            style="Error.TLabel",
            font=("Segoe UI", 10),
            wraplength=350  # Wrap text to prevent window expansion
        )
        self.error_label.pack(anchor="center", pady=(2, 10))
        
        # Create a button frame to hold the connect button (similar to employee screen)
        button_frame = ttk.Frame(info_frame, style="Login.TFrame")
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Connect button with consistent styling
        self.connect_button = ttk.Button(
            button_frame,
            text="Connect",
            command=self.handle_connect,
            style="Login.TButton"
        )
        self.connect_button.pack(fill=tk.X, pady=(0, 10))
        
        # Help text
        help_text = "Don't know your API key? Please ask your manager or check your RepairDesk settings."
        help_label = ttk.Label(
            info_frame,  # Use info_frame instead of help_frame
            text=help_text,
            style="Help.TLabel",
            font=("Segoe UI", 9),
            wraplength=350,  # Prevent text from being cut off
            justify=tk.CENTER
        )
        help_label.pack(pady=(0, 10))
        
        # Set focus to store name entry
        self.after(100, self.store_entry.focus_set)
        
        # Bind Enter key to connect
        self.store_entry.bind("<Return>", lambda e: self.api_entry.focus_set())
        self.api_entry.bind("<Return>", lambda e: self.handle_connect())
        
        # Configure style for help text
        style = ttk.Style()
        style.configure(
            "Small.TLabel",
            font=("Segoe UI", 8),
            background=self.colors.get("content_bg", "#0b4d49")
        )
        
        # Apply styling to all widgets
        self.lift_interactive_elements()
    
    def normalize_store_name(self, name):
        """Convert store name to a URL-friendly slug."""
        # Convert to lowercase
        slug = name.lower()
        
        # Replace spaces with hyphens
        slug = slug.replace(' ', '-')
        
        # Remove special characters
        import re
        slug = re.sub(r'[^a-z0-9-]', '', slug)
        
        # Remove multiple hyphens
        slug = re.sub(r'-+', '-', slug)
        
        # Remove leading and trailing hyphens
        return slug.strip('-')
        
    def check_api_key_validity(self, api_key):
        """Validate the format of the RepairDesk API key.
        
        Args:
            api_key: The API key to validate
            
        Returns:
            bool: True if the API key format is valid, False otherwise
        """
        # Basic validation - RepairDesk API keys are typically 40+ characters
        if len(api_key) < 20:
            logging.warning(f"API key is too short: {len(api_key)} characters")
            return False
            
        # Check for common API key patterns (alphanumeric with possible special chars)
        import re
        # Most API keys are alphanumeric with possible dashes or underscores
        pattern = re.compile(r'^[a-zA-Z0-9_\-]{20,}$')
        
        if not pattern.match(api_key):
            logging.warning("API key contains invalid characters")
            return False
            
        return True
    
    def handle_connect(self, event=None):
        """Handle the Connect to Store button click or Enter key press."""
        # Check if we're dealing with placeholder text
        if hasattr(self.store_entry, 'placeholder') and self.store_name_var.get() == self.store_entry.placeholder:
            self.store_name_var.set("")
            
        if hasattr(self.api_entry, 'placeholder') and self.api_key_var.get() == self.api_entry.placeholder:
            self.api_key_var.set("")
            
        store_name = self.store_name_var.get().strip()
        api_key = self.api_key_var.get().strip()
        
        # Basic validation with improved error messages
        if not store_name:
            self.show_error("Store Name is required")
            self.store_entry.focus_set()
            return
            
        if not api_key:
            self.show_error("API Key is required")
            self.api_entry.focus_set()
            return
        
        # Validate API key format
        if not self.check_api_key_validity(api_key):
            self.show_error("Invalid API key format. Please check and try again.")
            self.api_entry.focus_set()
            return
        
        # Generate a store slug from the store name if needed
        store_slug = self.normalize_store_name(store_name)
        
        # Show loading indicator with more informative message
        self.show_loading(f"Connecting to {store_name}...")
        
        # Disable the connect button while connecting
        if hasattr(self, 'connect_button') and self.connect_button.winfo_exists():
            self.connect_button.config(state="disabled")

        # Connect with background thread
        import threading
        threading.Thread(
            target=self.connect_to_store,
            args=(store_name, store_slug, api_key),
            daemon=True
        ).start()
    
    def connect_to_store(self, store_name, store_slug, api_key):
        """Connect to the RepairDesk store API.
        
        Args:
            store_name: Display name of the store
            store_slug: URL slug of the store
            api_key: API key for authentication
        """
        try:
            # Save store info
            self.store_name = store_name
            self.store_slug = store_slug
            self.api_key = api_key
            
            # Always save credentials (removed checkbox as requested)
            # Prepare data for config
            config_updates = {
                "api_key": self.api_key,
                "store_slug": self.store_slug,
                "store_name": self.store_name,
                "last_store": self.store_name,
                "repairdesk": {
                    "api_key": self.api_key,
                    "store_slug": self.store_slug
                }
            }
            
            # Save to config
            self.save_config(config_updates)
            logging.info(f"Credentials saved for store: {self.store_name}")
            
            # Fetch employees from the API
            try:
                # Import the API client here to avoid circular imports
                from nest.utils.repairdesk_api import RepairDeskAPI
                
                # Initialize API client
                api = RepairDeskAPI(store_slug=store_slug, api_key=api_key)
                
                # Fetch employees
                logging.info(f"Fetching employees from {store_name} ({store_slug})...")
                employees = api.get_employees()
                
                if not employees:
                    raise ValueError("No employees found for this store. Please check your API key and store name.")
                    
                # Log success
                logging.info(f"Successfully fetched {len(employees)} employees from {store_name}")
                    
                # Update UI on the main thread
                self.after(0, lambda: self.on_store_connected(True, f"Connected successfully to {store_name}", employees))
                
            except Exception as e:
                error_msg = f"Failed to fetch employees: {str(e)}"
                logging.error(error_msg)
                self.after(0, lambda: self.on_store_connected(False, error_msg, None))
            
        except Exception as e:
            error_msg = f"Failed to connect to store: {str(e)}"
            logging.error(error_msg)
            self.after(0, lambda: self.on_store_connected(False, error_msg, None))
    
    def on_store_connected(self, success, message, employees=None):
        """Handle store connection result."""
        self.hide_loading()
        
        # Re-enable the connect button if it exists
        if hasattr(self, 'connect_button') and self.connect_button.winfo_exists():
            self.connect_button.config(state="normal")
        
        if success:
            # Show success message with store name
            self.show_success(message)
            
            # Log the successful connection
            logging.info(f"Successfully connected to store: {self.store_name} with {len(employees or [])} employees")
            
            # Show employee selection after a short delay
            self.after(500, lambda: self.show_employee_selection(employees))
        else:
            # Show error message with more details
            self.show_error(message)
            
            # Log the error
            logging.error(f"Failed to connect to store: {message}")
    
    def show_employee_selection(self, employees=None):
        """Display the employee selection view after successful store connection."""
        # Clear any existing widgets in content frame
        for widget in self.content_frame.winfo_children():
            widget.destroy()
            
        self.current_view = "employee"
        self.employees = employees or []  # Store employees for later use
        
        # Check if we have employees to show
        if not self.employees:
            self.show_error("No employees found for this store")
            self.show_store_view()
            return
        
        # Create form frame with padding
        form_frame = ttk.Frame(self.content_frame, style="Login.TFrame")
        form_frame.pack(expand=True, fill=tk.BOTH, padx=40, pady=20)
        
        # Store name header
        ttk.Label(
            form_frame,
            text=self.store_name,
            style="Login.TLabel",
            font=("Segoe UI", 16, "bold")
        ).pack(pady=(0, 30))
        
        # Create a centered frame for the vertical layout
        centered_frame = ttk.Frame(form_frame, style="Login.TFrame")
        centered_frame.pack(expand=True, fill=tk.BOTH, padx=20, pady=20)
        
        # Create a fixed-size frame for the avatar to ensure consistent sizing
        avatar_frame = ttk.Frame(
            centered_frame,
            style="Avatar.TFrame",
            width=120,
            height=120
        )
        avatar_frame.pack(pady=(0, 20), anchor="center")
        
        # Force the frame to maintain its size
        avatar_frame.pack_propagate(False)
        
        # Configure avatar frame style - make it invisible
        style = ttk.Style()
        style.configure(
            "Avatar.TFrame",
            background=self.colors.get("content_bg", "#0b4d49"),
            borderwidth=0,
            relief="flat"
        )
        
        # Avatar display at the top (initially empty)
        self.avatar_label = ttk.Label(
            avatar_frame,
            text="👤",  # Default avatar
            style="Avatar.TLabel",
            font=("Segoe UI", 48),  # Consistent font size
            anchor="center",
            justify="center"
        )
        self.avatar_label.pack(fill=tk.BOTH, expand=True)
        
        # Configure avatar label style for consistent appearance - no borders
        style.configure(
            "Avatar.TLabel",
            background=self.colors.get("content_bg", "#0b4d49"),
            foreground="white",
            anchor="center",
            justify="center",
            borderwidth=0,
            relief="flat",
            padding=0
        )
        
        # Employee info frame (vertically below avatar)
        info_frame = ttk.Frame(centered_frame, style="Login.TFrame")
        info_frame.pack(fill=tk.X, expand=True, padx=20)
        
        # Employee selection dropdown
        ttk.Label(
            info_frame,
            text="Select your name:",
            style="Login.TLabel",
            font=("Segoe UI", 11)
        ).pack(anchor="center", pady=(0, 5))
        
        self.employee_var = tk.StringVar()
        self.employee_combo = ttk.Combobox(
            info_frame,
            textvariable=self.employee_var,
            state="readonly",
            font=("Segoe UI", 11),
            style="Login.TCombobox",
            width=30  # Set a fixed width for better appearance
        )
        self.employee_combo.pack(pady=(0, 20), anchor="center")
        
        # PIN entry
        ttk.Label(
            info_frame,
            text="Enter your PIN:",
            style="Login.TLabel",
            font=("Segoe UI", 11)
        ).pack(anchor="center", pady=(0, 5))
        
        # Create a frame for PIN entry to center it
        pin_frame = ttk.Frame(info_frame, style="Login.TFrame")
        pin_frame.pack(anchor="center", pady=(0, 5))
        
        self.pin_var = tk.StringVar()
        self.pin_var.trace('w', self.restrict_pin_input)
        
        # Create a wrapper frame to control the width of the PIN entry
        pin_entry_frame = ttk.Frame(pin_frame, style="Login.TFrame")
        pin_entry_frame.pack(pady=(0, 5), fill=tk.X)
        
        # Configure the frame to match the dropdown width exactly
        pin_entry_frame.update()  # Force an update to get current dimensions
        dropdown_width = self.employee_combo.winfo_width()
        
        # Create the PIN entry with adjusted width
        self.pin_entry = ttk.Entry(
            pin_entry_frame,
            textvariable=self.pin_var,
            show="•",
            style="Login.TEntry",
            font=("Segoe UI", 16),
            justify="center",
            width=20  # Adjusted width to account for larger font
        )
        self.pin_entry.pack(pady=(0, 5), fill=tk.X)
        
        # Bind to the first visibility event to adjust width after rendering
        self.pin_entry.bind("<Map>", self.adjust_pin_entry_width)
        
        # Error message for PIN
        self.pin_error_var = tk.StringVar()
        ttk.Label(
            info_frame,
            textvariable=self.pin_error_var,
            style="Error.TLabel",
            font=("Segoe UI", 10)
        ).pack(anchor="center", pady=(2, 10))
        
        # Create a button frame to hold both buttons
        button_frame = ttk.Frame(form_frame, style="Login.TFrame")
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Login button
        self.login_button = ttk.Button(
            button_frame,
            text="Login",
            command=self.handle_login,
            style="Login.TButton"
        )
        self.login_button.pack(fill=tk.X, pady=(0, 10))
        
        # Back button with more distinct styling
        self.back_button = ttk.Button(
            button_frame,
            text="← Back to Store Selection",
            command=self.show_store_view,
            style="Secondary.TButton"
        )
        self.back_button.pack(fill=tk.X, pady=(0, 0))
        
        # Add style for the secondary button
        style = ttk.Style()
        style.configure(
            "Secondary.TButton",
            background=self.colors.get("content_bg", "#0b4d49"),
            foreground="white",
            font=("Segoe UI", 10),
            padding=8
        )
        
        # Store employees for later use
        self.employees = employees or []
        
        # Populate dropdown with employee names
        if self.employees:
            employee_names = [emp.get('fullname', '') for emp in self.employees]
            self.employee_combo['values'] = employee_names
            if employee_names:
                self.employee_combo.current(0)
                self.update_employee_avatar(0)  # Show avatar for first employee
        else:
            # If no employees provided, show a message
            self.employee_combo['values'] = ["No employees found"]
            self.employee_combo.set("No employees found")
        
        # Bind events
        self.employee_combo.bind("<<ComboboxSelected>>", self.on_employee_selected)
        self.employee_combo.bind("<Return>", lambda e: self.pin_entry.focus_set())
        self.pin_entry.bind("<Return>", lambda e: self.handle_login())
        
        # Set focus to employee dropdown
        self.after(100, self.employee_combo.focus_set)
        
        # Configure styles
        style = ttk.Style()
        style.configure(
            "Error.TLabel",
            foreground="#ff4444",
            font=("Segoe UI", 8),
            background=self.colors.get("content_bg", "#0b4d49")
        )
        
        # Apply styling to all widgets
        self.lift_interactive_elements()
    
    def update_employee_avatar(self, index):
        """Update the avatar display based on the selected employee."""
        if not self.employees or index >= len(self.employees):
            return
            
        employee = self.employees[index]
        
        # Get employee details for avatar
        user_id = str(employee.get('id', ''))
        name = employee.get('fullname', employee.get('name', ''))
        direct_url = employee.get('image', employee.get('avatar', ''))
        
        # Log the employee details we're using for the avatar
        logging.info(f"Updating avatar for employee: {name} (ID: {user_id})")
        
        # Clear PIN field when changing employees
        self.pin_var.set("")
        self.pin_error_var.set("")
        
        # Check if we have a cached avatar for this employee
        cache_key = f"avatar_{user_id}_{name}"
        if hasattr(self, '_avatar_cache') and cache_key in self._avatar_cache:
            logging.info(f"Using cached avatar for {name}")
            self.current_avatar_image = self._avatar_cache[cache_key]
            self.avatar_label.config(image=self._avatar_cache[cache_key], text='')
            return
            
        # Initialize avatar cache if it doesn't exist
        if not hasattr(self, '_avatar_cache'):
            self._avatar_cache = {}
        
        # Try to get avatar from direct URL first if available
        if direct_url and direct_url.strip():
            try:
                # Clean up URL - replace spaces with %20
                if " " in direct_url:
                    direct_url = direct_url.replace(" ", "%20")
                
                logging.info(f"Trying direct avatar URL: {direct_url}")
                
                import requests
                from PIL import Image, ImageTk
                from io import BytesIO
                
                # Fetch with increased timeout
                response = requests.get(direct_url, timeout=5)
                if response.status_code == 200:
                    # Process the image
                    self._process_avatar_image(response.content, name, cache_key)
                    return
                else:
                    logging.warning(f"Failed to fetch direct avatar: HTTP {response.status_code}")
            except Exception as e:
                logging.warning(f"Error loading direct avatar URL: {e}")
        
        # Try RepairDesk CDN URL format if we have a user ID
        if user_id:
            try:
                # RepairDesk CDN URL format
                cdn_url = f"https://dghyt15qon7us.cloudfront.net/images/productTheme/User/small/{user_id}.jpg"
                logging.info(f"Trying RepairDesk CDN URL: {cdn_url}")
                
                import requests
                from PIL import Image, ImageTk
                from io import BytesIO
                
                response = requests.get(cdn_url, timeout=5)
                if response.status_code == 200:
                    # Process the image
                    self._process_avatar_image(response.content, name, cache_key)
                    return
                else:
                    logging.warning(f"Failed to fetch from CDN: HTTP {response.status_code}")
            except Exception as e:
                logging.warning(f"Error loading from CDN: {e}")
        
        # Try DiceBear (most reliable)
        try:
            from urllib.parse import quote
            dicebear_url = f"https://api.dicebear.com/7.x/initials/png?seed={quote(name)}&backgroundColor=00897B&size=120"
            
            logging.info(f"Trying DiceBear: {dicebear_url}")
            
            import requests
            from PIL import Image, ImageTk
            from io import BytesIO
            
            response = requests.get(dicebear_url, timeout=5)
            if response.status_code == 200:
                # Process the image
                self._process_avatar_image(response.content, name, cache_key)
                return
            else:
                logging.warning(f"Failed to fetch from DiceBear: HTTP {response.status_code}")
        except Exception as e:
            logging.warning(f"Error loading DiceBear avatar: {e}")
        
        # Try UI Avatars as final fallback
        try:
            from urllib.parse import quote
            ui_avatars_url = f"https://ui-avatars.com/api/?name={quote(name)}&background=00897B&color=fff&size=120"
            
            logging.info(f"Trying UI Avatars: {ui_avatars_url}")
            
            import requests
            from PIL import Image, ImageTk
            from io import BytesIO
            
            response = requests.get(ui_avatars_url, timeout=5)
            if response.status_code == 200:
                # Process the image
                self._process_avatar_image(response.content, name, cache_key)
                return
            else:
                logging.warning(f"Failed to fetch from UI Avatars: HTTP {response.status_code}")
        except Exception as e:
            logging.warning(f"Error loading UI Avatars: {e}")
        
        # Final fallback to initials if all else fails
        if name:
            initial = name[0].upper()
            self.avatar_label.config(text=initial, image='', font=("Segoe UI", 48))
            logging.info(f"Using initials '{initial}' for {name}")
    
    def _process_avatar_image(self, image_data, name, cache_key):
        """Process avatar image data and update the UI.
        
        Args:
            image_data: Raw image data bytes
            name: Employee name for logging
            cache_key: Key for caching the processed avatar
        """
        try:
            from PIL import Image, ImageTk, ImageDraw, ImageChops
            from io import BytesIO
            import math
            
            # Convert to PIL Image
            img = Image.open(BytesIO(image_data))
            
            # Create a slightly larger canvas for the circular image
            # This ensures we have room for antialiasing at the edges
            target_size = (120, 120)
            output_size = (120, 120)
            
            # Resize the original image to fit our target dimensions
            if img.size != target_size:
                img = img.resize(target_size, Image.LANCZOS)
            
            # Create a perfectly circular mask with smooth edges
            mask = Image.new('L', output_size, 0)
            draw = ImageDraw.Draw(mask)
            
            # Draw a circle with a slight offset from edges for perfect circles
            padding = 0
            draw.ellipse((padding, padding, output_size[0]-padding, output_size[1]-padding), fill=255)
            
            # Create a transparent background image
            circle_img = Image.new('RGBA', output_size, (0, 0, 0, 0))
            
            # Paste the original image using the mask
            circle_img.paste(img, (0, 0), mask)
            
            # Use the circular image
            img = circle_img
            
            # Convert to PhotoImage
            photo = ImageTk.PhotoImage(img)
            
            # Store reference to prevent garbage collection
            self.current_avatar_image = photo
            
            # Cache the avatar
            self._avatar_cache[cache_key] = photo
            
            # Update the avatar label
            self.avatar_label.config(image=photo, text='')
            
            # Log success
            logging.info(f"Successfully loaded and processed avatar for {name}")
            
        except Exception as e:
            logging.error(f"Error processing avatar image: {e}")
            # Fallback to initials
            if name:
                initial = name[0].upper()
                self.avatar_label.config(text=initial, image='', font=("Segoe UI", 48))
                logging.info(f"Using initials '{initial}' for {name} due to processing error")

    
    def adjust_pin_entry_width(self, event=None):
        """Adjust the PIN entry width to match the dropdown width."""
        try:
            # Get the dropdown width
            dropdown_width = self.employee_combo.winfo_width()
            
            if dropdown_width > 10:  # Only adjust if we have a valid width
                # Adjust the PIN entry width to match the dropdown
                # We need to account for the different font sizes
                self.pin_entry.configure(width=max(10, int(dropdown_width / 12)))
                
                # Log the adjustment
                logging.debug(f"Adjusted PIN entry width to match dropdown: {dropdown_width}px")
        except (AttributeError, tk.TclError) as e:
            # Widget may not exist yet
            logging.debug(f"Could not adjust PIN entry width: {e}")
    
    def on_employee_selected(self, event=None):
        """Handle employee selection from dropdown."""
        index = self.employee_combo.current()
        if index >= 0:
            self.update_employee_avatar(index)
            
            # Set the selected employee
            self.selected_employee = self.employees[index] if index < len(self.employees) else None
            
            # Set focus to PIN entry
            self.pin_entry.focus_set()
            
            # Adjust PIN entry width to match dropdown
            self.after(50, self.adjust_pin_entry_width)
    
    def handle_login(self, event=None):
        """Handle the login button click or Enter key press in the PIN field."""
        # Get selected employee and PIN
        selected_name = self.employee_var.get().strip()
        pin = self.pin_var.get().strip()
        
        # Disable the login button to prevent multiple clicks
        if hasattr(self, 'login_button') and self.login_button.winfo_exists():
            self.login_button.config(state="disabled")
            
        # Show loading indicator
        self.show_loading("Verifying credentials...")
        
        # Basic validation with improved error messages
        if not selected_name or selected_name == "No employees found":
            self.pin_error_var.set("Please select an employee from the dropdown")
            self.employee_combo.focus_set()
            self.hide_loading()
            if hasattr(self, 'login_button') and self.login_button.winfo_exists():
                self.login_button.config(state="normal")
            return
            
        if not pin:
            self.pin_error_var.set("PIN is required")
            self.pin_entry.focus_set()
            self.hide_loading()
            if hasattr(self, 'login_button') and self.login_button.winfo_exists():
                self.login_button.config(state="normal")
            return
            
        # Find the selected employee
        self.selected_employee = next((emp for emp in self.employees if emp.get("fullname") == selected_name or emp.get("name") == selected_name), None)
        if not self.selected_employee:
            self.pin_error_var.set("Employee not found. Please select a valid employee.")
            self.employee_combo.focus_set()
            self.hide_loading()
            if hasattr(self, 'login_button') and self.login_button.winfo_exists():
                self.login_button.config(state="normal")
            return
            
        # Check if login is locked
        if self.is_login_locked():
            remaining = self.get_lock_remaining_time()
            self.pin_error_var.set(f"Account locked. Try again in {remaining} min")
            self.hide_loading()
            if hasattr(self, 'login_button') and self.login_button.winfo_exists():
                self.login_button.config(state="normal")
            return
            
        # Log the login attempt (without the PIN)
        logging.info(f"Login attempt for {selected_name} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
        # Validate PIN
        if self.validate_pin(pin):
            # If we get here, login is successful
            self.hide_loading()
            self.handle_successful_login(self.selected_employee)
        else:
            self.hide_loading()
            self.handle_failed_login()
            # Clear and refocus PIN field
            self.pin_var.set("")
            self.pin_entry.focus_set()
            if hasattr(self, 'login_button') and self.login_button.winfo_exists():
                self.login_button.config(state="normal")
    
    def lift_interactive_elements(self):
        """Bring interactive UI elements to the top layer."""
        try:
            # Make sure essential elements remain above the pattern
            # Only lift widgets that exist and are currently visible based on the view
            if not hasattr(self, 'current_view'):
                return  # Skip if current_view is not set yet
                
            if self.current_view == "employee":
                if hasattr(self, 'employee_combo'):
                    try:
                        if self.employee_combo.winfo_exists():
                            self.employee_combo.lift()
                    except tk.TclError:
                        pass  # Widget might be in an invalid state
                    
                if hasattr(self, 'pin_entry'):
                    try:
                        if self.pin_entry.winfo_exists():
                            self.pin_entry.lift()
                    except tk.TclError:
                        pass  # Widget might be in an invalid state
            
            elif self.current_view == "store":
                if hasattr(self, 'store_entry'):
                    try:
                        if self.store_entry.winfo_exists():
                            self.store_entry.lift()
                    except tk.TclError:
                        pass  # Widget might be in an invalid state
                    
                if hasattr(self, 'api_entry'):
                    try:
                        if self.api_entry.winfo_exists():
                            self.api_entry.lift()
                    except tk.TclError:
                        pass  # Widget might be in an invalid state
                    
                if hasattr(self, 'connect_button'):
                    try:
                        if self.connect_button.winfo_exists():
                            self.connect_button.lift()
                    except tk.TclError:
                        pass  # Widget might be in an invalid state
            
            if hasattr(self, 'login_button'):
                try:
                    if self.login_button.winfo_exists():
                        self.login_button.lift()
                except tk.TclError:
                    pass  # Widget might be in an invalid state
        except Exception as e:
            # Log the error but don't crash the application
            logging.warning(f"Error in lift_interactive_elements: {e}")
            # Continue execution without raising the exception
    
    def __init__(self, parent, on_login_success=None):
        super().__init__(parent)
        self.parent = parent
        self.on_login_success = on_login_success

        # Load saved configuration
        self.config = self.load_config()
        
        # API client state
        self.store_slug = self.config.get("store_slug")
        self.api_key = self.config.get("api_key")
        
        # Welcome message for returning users
        self.welcome_frame = None
        self.welcome_label = None
        self.welcome_avatar = None
        
        # UI theme colors
        self.colors = getattr(
            parent,  # Use parent instead of master to match constructor parameter
            "colors",
            {
                "primary": "#1976D2",
                "primary_dark": "#0D47A1",
                "background": "#F5F5F5",
                "content_bg": "#0b4d49",
                "text_primary": "#212121",
                "text_secondary": "#757575",
                "warning": "#F44336",
                "success": "#4CAF50",
            },
        )

        # Security state
        self.login_attempts = 0
        self.max_attempts = 5
        self.locked_until = None

        # Employee data
        self.employees = []
        self.selected_employee = None

        # PIN entry
        self.pin_var = tk.StringVar()
        self.pin_var.trace_add("write", self.restrict_pin_input)

        # Store entry
        self.store_var = tk.StringVar()  # Store slug
        self.store_name_var = tk.StringVar()  # Store display name
        self.api_key_var = tk.StringVar()
        # Note: remember_var removed as we now always save credentials

        # Current view state (store or employee login)
        self.current_view = "store"  # Can be "store" or "employee"

        # Loading indicator
        self.loading = False

        # Build UI
        self.setup_ui()

        # Check if we have stored credentials
        if self.store_slug and self.api_key:
            self.store_var.set(self.store_slug)
            self.api_key_var.set(self.api_key)
            self.show_loading("Connecting to store...")
            # Get store name from config or use slug as fallback
            store_name = self.config.get("store_name", self.store_slug)
            # Note: remember_var removed as we now always save credentials
            # Start connection in main thread using after to avoid threading issues
            self.after(100, lambda: self.connect_to_store(store_name, self.store_slug, self.api_key))
        else:
            self.show_store_view()
            
        # Define function to get script directory
        def get_script_dir():
            """Get the root directory of the Nest application."""
            # Start with the current directory (ui folder)
            current_dir = os.path.dirname(os.path.abspath(__file__))
            # Go up one level to the nest directory
            return os.path.dirname(current_dir)
            
        # Try to auto-populate with last logged in user from last_login.json
        try:
            last_login_path = os.path.join(get_script_dir(), "last_login.json")
            if os.path.exists(last_login_path):
                with open(last_login_path, 'r') as f:
                    try:
                        last_login_data = json.load(f)
                        if "username" in last_login_data and last_login_data["username"]:
                            self.last_user = last_login_data["username"]
                            self.last_user_id = last_login_data.get("id", "")
                            logging.info(f"Loaded last logged in user: {self.last_user}")
                        else:
                            # Fix the file by writing a proper structure with empty values
                            self._reset_last_login_file(last_login_path)
                            self.last_user = None
                            self.last_user_id = None
                    except json.JSONDecodeError:
                        # File exists but is not valid JSON, reset it
                        self._reset_last_login_file(last_login_path)
                        self.last_user = None
                        self.last_user_id = None
            else:
                logging.info("No last login file found")
                self.last_user = None
                self.last_user_id = None
        except Exception as e:
            logging.warning(f"Could not load last user from last_login.json: {e}")
            self.last_user = None
            self.last_user_id = None

        # Enter key triggers action
        self.bind_all("<Return>", self.handle_enter_key)
        
    def handle_enter_key(self, event=None):
        """Handle Enter key press in the current view."""
        if self.current_view == "store":
            self.handle_connect()
        elif self.current_view == "employee":
            self.handle_login()

    def find_config_dir(self):
        """Find the configuration directory from the current path."""
        # Start from the current directory
        current_dir = os.getcwd()
        
        # Check if config directory exists at current level
        if os.path.isdir(os.path.join(current_dir, "config")):
            return os.path.join(current_dir, "config")
            
        # Check if we're in the ui/modules directory and need to go up
        if os.path.basename(current_dir) == "modules" and os.path.basename(os.path.dirname(current_dir)) == "ui":
            # Go up two levels
            parent_dir = os.path.dirname(os.path.dirname(current_dir))
            if os.path.isdir(os.path.join(parent_dir, "config")):
                return os.path.join(parent_dir, "config")
                
        # Check for config at the parent directory
        parent_dir = os.path.dirname(current_dir)
        if os.path.isdir(os.path.join(parent_dir, "config")):
            return os.path.join(parent_dir, "config")
            
        # As a last resort, create a config directory if it doesn't exist
        os.makedirs(os.path.join(current_dir, "config"), exist_ok=True)
        return os.path.join(current_dir, "config")

    def load_config(self):
        """Load configuration from JSON file."""
        config_dir = self.find_config_dir()
        config_path = os.path.join(config_dir, "config.json")
        
        try:
            if os.path.exists(config_path):
                with open(config_path, "r") as f:
                    config = json.load(f)
                logging.info(f"Configuration loaded from {config_path}")
                return config
            else:
                logging.info(f"No config file found at {config_path}, creating new one")
                from utils.config_util import ConfigManager
                config_manager = ConfigManager()
                default_config = config_manager._get_default_config()
                with open(config_path, "w") as f:
                    json.dump(default_config, f, indent=2)
                logging.info(f"Created new config file with default configurations at {config_path}")
                return default_config
        except Exception as e:
            logging.warning(f"Failed to load config: {e}")
            return {}

    def save_config(self, updates):
        """Save configuration to JSON file."""
        config_dir = self.find_config_dir()
        config_path = os.path.join(config_dir, "config.json")
        
        try:
            # Load existing config first
            config = {}
            if os.path.exists(config_path):
                with open(config_path, "r") as f:
                    config = json.load(f)
            
            # CRITICAL PROTECTION: Preserve existing store_name when it exists and is different from slug
            if 'store_name' in config and 'store_slug' in config and config['store_name'] != config['store_slug']:
                # We already have a proper display name that's different from the slug
                existing_store_name = config['store_name']
                existing_store_slug = config['store_slug']
                
                if 'store_name' in updates and updates['store_name'] == existing_store_slug:
                    # The update is trying to set store_name to match the slug (incorrect)
                    logging.info(f"Protecting existing store display name '{existing_store_name}' from being overwritten with slug")
                    updates['store_name'] = existing_store_name
            
            # For first-time setup: Ensure store_name is not set to slug
            if 'store_name' in updates and 'store_slug' in updates:
                # Make sure store_name is the display name and not the slug
                if updates['store_name'] == updates['store_slug']:
                    logging.warning("Store name same as slug - this may be a mistake, checking for proper display name")
                    
                    # If we're in connect_to_store and have the display name from form
                    store_display_name = self.store_name_var.get().strip()
                    if store_display_name and store_display_name != updates['store_slug']:
                        logging.info(f"Using form display name '{store_display_name}' instead of slug")
                        updates['store_name'] = store_display_name
            
            # Update with new values
            config.update(updates)
            
            # Ensure the RepairDesk API key is saved in the repairdesk object too
            if 'api_key' in updates and 'repairdesk' in config:
                config['repairdesk']['api_key'] = updates['api_key']
            
            # Extra validation: NEVER allow store_name to equal store_slug if both exist
            if 'store_name' in config and 'store_slug' in config and config['store_name'] == config['store_slug']:
                # If for some reason we still have store_name = slug, check for form display name
                store_display_name = self.store_name_var.get().strip()
                if store_display_name and store_display_name != config['store_slug']:
                    config['store_name'] = store_display_name
                    logging.info(f"Final protection: Setting store_name to '{store_display_name}' to prevent slug overwrite")
            
            # Save back to file
            with open(config_path, "w") as f:
                json.dump(config, f, indent=2)
                
            logging.info(f"Configuration saved to {config_path}")
            return True
        except Exception as e:
            logging.error(f"Failed to save config: {e}")
            return False

    def setup_background(self):
        """Set up the application background with fallback options."""
        # Create a canvas for the background
        self.bg_canvas = tk.Canvas(self, highlightthickness=0)
        self.bg_canvas.pack(fill="both", expand=True)
        
        # Set a default background color that matches the theme
        default_bg = self.colors.get("content_bg", "#0b4d49")
        self.bg_canvas.config(bg=default_bg)
        
        # Try to load SVG background
        self.bg_image = self.load_svg_with_cairosvg()
        
        if self.bg_image:
            # Get window size
            width = self.winfo_width() or 800
            height = self.winfo_height() or 600
            
            # Create the background image
            self.bg_canvas.create_image(
                0, 0, 
                image=self.bg_image, 
                anchor="nw", 
                tags="svg_bg"
            )
            
            # Bind resize event
            self.bind("<Configure>", self.resize_background)
        
        # Make sure the main frame stays on top
        if hasattr(self, 'main_frame') and self.main_frame.winfo_exists():
            self.main_frame.lift()

    def load_svg_with_cairosvg(self):
        """Convert SVG to a Tkinter-compatible image using cairosvg.
        
        Returns:
            ImageTk.PhotoImage or None: The loaded image or None if loading failed
        """
        try:
            # Define possible locations for the SVG file
            base_dirs = [
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),  # project root
                os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'theme'),  # theme directory
                os.path.dirname(__file__)  # current directory
            ]
            
            possible_paths = []
            for base_dir in base_dirs:
                possible_paths.extend([
                    os.path.join(base_dir, 'theme', 'background.svg'),
                    os.path.join(base_dir, 'background.svg'),
                ])
            
            # Try to find the SVG file
            svg_path = None
            for path in possible_paths:
                if os.path.exists(path):
                    svg_path = path
                    break
                    
            if not svg_path:
                logging.warning("Background SVG not found in any expected location\n" + 
                              "\n".join(f"- {p}" for p in possible_paths))
                return None
            
            logging.info(f"Loading SVG background from: {svg_path}")
            
            # Import cairosvg here to avoid import errors if not available
            import cairosvg
            import io
            from PIL import Image, ImageTk
            
            # Get the window size for proper scaling
            width = self.winfo_screenwidth()
            height = self.winfo_screenheight()
            
            # Convert SVG to PNG in memory with proper scaling
            png_data = cairosvg.svg2png(
                url=svg_path,
                output_width=width,
                output_height=height
            )
            
            # Convert to PIL Image
            img = Image.open(io.BytesIO(png_data))
            
            # Create a PhotoImage for Tkinter
            photo_img = ImageTk.PhotoImage(img)
            logging.info("Successfully loaded and converted SVG background")
            
            # Store a reference to prevent garbage collection
            if not hasattr(self, '_bg_images'):
                self._bg_images = []
            self._bg_images.append(photo_img)
            
            return photo_img
            
        except ImportError as e:
            logging.warning(f"CairoSVG not available - SVG background will not be displayed: {e}")
            return None
        except Exception as e:
            logging.error(f"Error loading SVG background: {e}", exc_info=True)
            return None
            
    def handle_window_resize(self, event):
        """Handle window resize events to update the background."""
        if event.widget == self:  # Only handle events for the main window
            self.after_idle(self.resize_background)
    
    def resize_background(self, event=None):
        """Resize the background when window is resized."""
        try:
            if not hasattr(self, 'bg_canvas') or not self.bg_canvas.winfo_exists():
                return
                
            # Get the current window size
            window_width = self.winfo_width()
            window_height = self.winfo_height()
            
            # Skip if the window is too small or not yet mapped
            if window_width < 10 or window_height < 10:
                return
                
            # Update canvas size to match window
            self.bg_canvas.config(width=window_width, height=window_height)
            
            # Clear existing background
            self.bg_canvas.delete("svg_bg")
            
            # Only attempt to reload the SVG if we have a valid size
            if window_width > 10 and window_height > 10 and hasattr(self, 'bg_image'):
                # Remove old reference to allow garbage collection
                if hasattr(self, '_bg_images') and self._bg_images:
                    self._bg_images.pop(0)
                
                # Reload the SVG with new dimensions
                self.bg_image = self.load_svg_with_cairosvg()
                
                if self.bg_image:
                    # Create the background image
                    self.bg_canvas.create_image(
                        0, 0, 
                        image=self.bg_image, 
                        anchor="nw", 
                        tags="svg_bg"
                    )
            
            # Ensure the main frame stays on top
            if hasattr(self, 'main_frame') and self.main_frame.winfo_exists():
                self.main_frame.lift()
                
        except Exception as e:
            logging.error(f"Error in resize_background: {e}", exc_info=True)