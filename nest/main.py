#!/usr/bin/env python
"""
Nest - Computer Repair Shop Management System

A comprehensive management system for computer repair shops that includes
ticket tracking, customer management, inventory control, appointment scheduling,
and diagnostic tools for various platforms.
"""

import os
import sys

# Add the project root to the Python path before any other imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import subprocess
import logging
import platform
import importlib
import time
from functools import partial
from typing import Dict, List, Tuple, Callable, Optional, Any
import tkinter as tk
from tkinter import ttk, messagebox, font as tkfont

# Custom Treeview with fixed header height
class FixedHeaderTreeview(ttk.Treeview):    
    def __init__(self, master=None, **kw):
        super().__init__(master, **kw)
        self._setup_style()
        
    def _setup_style(self):
        # Create a style for the Treeview
        style = ttk.Style()
        
        # Configure the Treeview style
        style.configure("Custom.Treeview",
            background="#ffffff",
            foreground="#000000",
            fieldbackground="#ffffff",
            rowheight=35,
            font=("Segoe UI", 10),
            borderwidth=0,
            relief="flat"
        )
        
        # Configure the Treeview Heading style with fixed height
        style.configure("Custom.Treeview.Heading",
            background="#2e7d32",
            foreground="white",
            relief="flat",
            borderwidth=0,
            font=("Segoe UI", 11, "bold"),
            padding=(10, 15)
        )
        
        # Layout for the heading to ensure height is respected
        style.layout("Custom.Treeview.Heading", [
            ("Treeheading.cell", {
                'sticky': 'nswe',
                'children': [
                    ('Treeheading.padding', {
                        'sticky': 'nswe',
                        'children': [
                            ('Treeheading.text', {'sticky': 'nswe'}),
                        ]
                    })
                ]
            })
        ])
        
        # Apply the custom style to this treeview
        self.configure(style="Custom.Treeview")
        
    def _create_heading(self, cnf, **kw):
        # Override _create_heading to ensure our style is used
        return ttk.Label(self, style="Custom.Treeview.Heading", **kw)

# Fix module import issues when running directly
if __name__ == '__main__':
    # Add the parent directory to the Python path so 'nest' can be found
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, parent_dir)
    # Now imports of nest.* will work correctly

# Configure basic logging first
logging.basicConfig(
    level=logging.DEBUG,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)

# Set PIL logging to INFO to prevent verbose debug logs
logging.getLogger('PIL').setLevel(logging.INFO)

# Set matplotlib logging to INFO to prevent verbose font debug logs
logging.getLogger('matplotlib').setLevel(logging.INFO)

# --- Utility Functions for Dependency Management ---

    
def setup_logging():
    """Set up proper logging with both file and console handlers."""
    script_dir = get_script_dir()
    log_dir = os.path.join(script_dir, "logs")

    # Create logs directory if it doesn't exist
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    log_file = os.path.join(log_dir, "app.log")

    # Clear previous handlers
    root_logger = logging.getLogger()
    root_logger.handlers = []

    # Add file handler
    file_handler = logging.FileHandler(log_file, mode="a")
    file_handler.setFormatter(
        logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s", "%Y-%m-%d %H:%M:%S")
    )
    root_logger.addHandler(file_handler)

    # Add console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(
        logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s", "%Y-%m-%d %H:%M:%S")
    )
    root_logger.addHandler(console_handler)

    logging.info("Logging initialized.")


def get_script_dir() -> str:
    """Get the directory where the script is located."""
    return os.path.dirname(os.path.abspath(__file__))


def pause_exit():
    """Wait for user input or show a message box before exiting."""
    try:
        if sys.stdin.isatty():
            input("Press Enter to exit...")
        else:
            try:
                # Import inside function to avoid issues during dependency installation
                import tkinter as tk
                from tkinter import messagebox

                root = tk.Tk()
                root.withdraw()
                messagebox.showerror("Error", "An error occurred. Check logs for details.")
                root.destroy()
            except Exception as e:
                logging.error(f"Failed to show error dialog: {e}")
    except Exception as e:
        logging.error(f"Failed during exit handling: {e}")


def get_os_info() -> Dict[str, str]:
    """Get detailed OS information."""
    os_info = {
        "system": platform.system().lower(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python_version": platform.python_version(),
    }
    logging.info(f"OS detected: {os_info['system']} {os_info['release']} {os_info['version']}")
    return os_info


def check_module_installed(module_name: str) -> bool:
    """Check if a Python module is installed."""
    try:
        # Handle special case for tkinter which has a different import name
        if module_name.lower() == 'tkinter':
            # Try importing tk directly
            import tkinter
            return True
        elif module_name.lower() == 'tk':
            # Try importing tk directly
            import tkinter
            return True
        # Handle pywin32 special case
        elif module_name.lower() == 'pywin32':
            # Check for win32com which is part of pywin32
            import win32com.client
            return True
        # Handle WMI special case
        elif module_name.lower() == 'wmi':
            try:
                import wmi
                return True
            except ImportError:
                # WMI depends on pywin32, if pywin32 is installed but WMI isn't,
                # we might treat both as 'installed' since WMI will be installed automatically
                try:
                    import win32com.client
                    return True
                except:
                    return False
        # General case
        else:
            importlib.import_module(module_name)
            return True
    except ImportError:
        return False
    except Exception as e:
        logging.warning(f"Error checking if {module_name} is installed: {e}")
        # Be optimistic to avoid reinstall loops
        return True


def install_tkinter():
    """Install Tkinter based on the current platform."""
    if check_module_installed("tkinter"):
        logging.info("Tkinter is already installed.")
        return True

    logging.info("Attempting to install Tkinter...")
    os_info = get_os_info()
    system = os_info["system"]

    try:
        if "windows" in system:
            logging.info("Windows detected. Installing tk via pip...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "tk"])
        elif "linux" in system:
            distro = ""
            try:
                import distro

                distro = distro.id()
            except ImportError:
                # Try to get distribution info from /etc/os-release
                if os.path.exists("/etc/os-release"):
                    with open("/etc/os-release") as f:
                        for line in f:
                            if line.startswith("ID="):
                                distro = line.split("=")[1].strip().strip('"')
                                break

            if distro in ["ubuntu", "debian", "linuxmint"]:
                logging.info(
                    f"{distro.capitalize()} detected. Installing python3-tk using apt-get..."
                )
                subprocess.check_call(["sudo", "apt-get", "update"])
                subprocess.check_call(["sudo", "apt-get", "install", "-y", "python3-tk"])
            elif distro in ["fedora", "centos", "rhel"]:
                logging.info(
                    f"{distro.capitalize()} detected. Installing python3-tkinter using dnf..."
                )
                subprocess.check_call(["sudo", "dnf", "install", "-y", "python3-tkinter"])
            else:
                logging.warning(
                    f"Unsupported Linux distribution '{distro}' for automatic Tkinter installation."
                )
                logging.info("Please install Tkinter manually for your distribution.")
        elif "darwin" in system:
            logging.info("macOS detected. Tkinter should be bundled with Python.")
            logging.info(
                "If Tkinter is missing, install Python from python.org with tcl/tk support."
            )
        else:
            logging.warning(f"Unsupported platform '{system}' for automatic Tkinter installation.")
            return False

        # Verify installation
        import tkinter

        logging.info("Tkinter installed successfully.")
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to install Tkinter: {e}")
        return False
    except ImportError:
        logging.error("Could not import Tkinter even after attempted installation.")
        return False


def install_dependencies():
    """Install all required Python dependencies."""
    # First, always install from requirements.txt if it exists
    script_dir = get_script_dir()
    req_path = os.path.join(script_dir, "requirements.txt")
    if os.path.exists(req_path):
        try:
            logging.info(f"Installing dependencies from {req_path} via pip...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", req_path])
            logging.info("requirements.txt dependencies installed successfully.")
        except subprocess.CalledProcessError as e:
            logging.error(f"Failed to install requirements.txt dependencies: {e}")
    # Core dependencies required for all platforms
    core_dependencies = [
        "Pillow",  # Required for image rendering
        "requests==2.32.3",  # Network requests with specific version
        "psutil",  # System utilization monitoring
        "beautifulsoup4",  # HTML parsing
        "tkcalendar",  # Calendar widget for appointments
        "python-dateutil",  # Date manipulation
    ]

    # OS-specific dependencies
    os_info = get_os_info()
    system = os_info["system"]

    platform_dependencies = []
    if "windows" in system:
        platform_dependencies = [
            "WMI",
            "pywin32",
        ]  # Windows Management Instrumentation and Win32 API
    elif "linux" in system:
        platform_dependencies = ["pyudev"]  # For hardware detection on Linux
    elif "darwin" in system:
        platform_dependencies = ["pyobjc"]  # For macOS specific functionality

    # Combined dependencies
    all_dependencies = core_dependencies + platform_dependencies

    # Install dependencies one by one
    failed_packages = []
    for package in all_dependencies:
        logging.info(f"Installing dependency: {package}...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            logging.info(f"{package} installed successfully.")
        except subprocess.CalledProcessError as e:
            logging.error(f"Failed to install {package}: {e}")
            failed_packages.append(package)

    # Check for any failed installations
    if failed_packages:
        logging.error(f"Failed to install these packages: {', '.join(failed_packages)}")
        return False

    logging.info("All dependencies installed successfully.")
    return True


def restart_script():
    """Restart the script to load newly installed dependencies."""
    env = os.environ.copy()
    env["DEP_INSTALLED"] = "1"
    logging.info("Restarting application to load installed dependencies...")
    args = [sys.executable, os.path.abspath(__file__)] + sys.argv[1:]
    try:
        subprocess.check_call(args, env=env)
        sys.exit(0)
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to restart the script: {e}")
        return False


def create_required_folders():
    """Create required folder structure if it doesn't exist."""
    script_dir = get_script_dir()
    required_folders = [
        "ui",
        "utils",
        "logs",
        "data",
        "config",
        "resources",
        "resources/icons",
        "resources/images",
        "data/customers",
        "data/tickets",
        "data/inventory",
        "reports",
        "templates",
    ]

    for folder in required_folders:
        folder_path = os.path.join(script_dir, folder)
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            logging.info(f"Created missing directory: {folder}")
        else:
            logging.debug(f"Directory '{folder}' already exists.")

    # Create placeholder files in empty directories to ensure they're tracked by git
    for folder in required_folders:
        folder_path = os.path.join(script_dir, folder)
        placeholder_file = os.path.join(folder_path, ".gitkeep")
        if not os.listdir(folder_path) and not os.path.exists(placeholder_file):
            with open(placeholder_file, "w") as f:
                f.write("# This file ensures the directory is tracked by git\n")


# --- GUI Application Using Tkinter ---
class NestApp:
    """Main application class for the Nest application."""

    def __init__(self):
        """Initialize the application."""
        # Defer importing tkinter until we're sure it's installed
        import tkinter as tk
        from tkinter import ttk
        from tkinter import font as tkfont

        self.tk = tk
        self.ttk = ttk
        self.tkfont = tkfont

        self.root = tk.Tk()
        self.root.title("Nest")
        
        # Create a custom font for the title with RepairDesk green
        title_font = self.tkfont.Font(family="Segoe UI", size=12, weight="bold")
        self.root.option_add("*Font", title_font)
        
        # Change the title bar text color to RepairDesk green - this requires a custom title bar
        # We'll implement a custom title in the login screen instead

        # Get screen dimensions
        self.screen_width = self.root.winfo_screenwidth()
        self.screen_height = self.root.winfo_screenheight()
        logging.info(f"Detected screen resolution: {self.screen_width}x{self.screen_height}")
        
        # Calculate appropriate login window size (35% of screen width, 70% of screen height)
        login_width = min(int(self.screen_width * 0.35), 500)  # Cap at 500px
        login_height = min(int(self.screen_height * 0.7), 800)  # Cap at 800px
        
        # Ensure login window isn't smaller than minimum usable size
        login_width = max(login_width, 370)
        login_height = max(login_height, 680)
        
        # Center the window on screen
        x_position = (self.screen_width - login_width) // 2
        y_position = (self.screen_height - login_height) // 2
        
        # Set geometry with position
        self.root.geometry(f"{login_width}x{login_height}+{x_position}+{y_position}")
        self.root.minsize(370, 680)  # Minimum size for login screen
        self.root.resizable(True, True)  # Allow resizing

        # Try to set app icon
        self.set_app_icon()

        # Define app color scheme (professional, repair-shop oriented)
        self.colors = {
            "primary": "#1976D2",  # Primary accent color (blue)
            "primary_dark": "#0D47A1",  # Darker version of primary
            "primary_light": "#BBDEFB",  # Lighter version of primary
            "secondary": "#43A047",  # Secondary accent (green)
            "secondary_dark": "#2E7D32",  # Darker version of secondary
            "secondary_light": "#C8E6C9",  # Lighter version of secondary
            "background": "#F5F5F5",  # Light background color
            "card_bg": "#FFFFFF",  # Card/panel background
            "sidebar": "#263238",  # Dark sidebar color
            "sidebar_highlight": "#37474F",  # Sidebar highlight
            "sidebar_text": "#ECEFF1",  # Light text for dark background
            "hover": "#455A64",  # Hover effect color
            "text_primary": "#212121",  # Main text color
            "text_secondary": "#757575",  # Secondary text color
            "border": "#E0E0E0",  # Border color
            "warning": "#F44336",  # Warning/error color
            "success": "#4CAF50",  # Success color
            "info": "#2196F3",  # Info color
            "header_bg": "#FAFAFA",  # Header background - light
            "footer_bg": "#EEEEEE",  # Footer background - light
            "content_bg": "#F9F9F9",  # Main content background - light
            "heading_text": "#2E7D32",  # Dark green text for headings
        }

        # Set window background color
        self.root.configure(bg=self.colors["content_bg"])

        # Application state
        self.current_user = None
        self.modules = {}  # Store loaded module instances
        self.active_module = None
        self.last_notification = None
        self.notification_timer = None
        
        # Session timeout handling
        self.inactivity_timeout = 15 * 60 * 1000  # 15 minutes in milliseconds
        self.activity_timer_id = None
        self.locked = False

        # Set up UI
        self.setup_style()
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")

        # Create notification area
        self.notification_var = tk.StringVar()
        self.notification_var.set("")
        
        # Initialize notification frame
        self.notification_frame = ttk.Frame(self.root, style="Notification.TFrame")
        self.notification_frame.place(relx=1.0, rely=0, anchor="ne", width=300, height=0)
        self.notification_frame.place_forget()  # Hide initially

        # Show the login screen
        logging.info("NestApp initialized.")
        self.show_login()

    def set_app_icon(self):
        """Try to set app icon if available."""
        try:
            script_dir = get_script_dir()
            icon_path = os.path.join(script_dir, "resources", "icons", "nest_icon.ico")
            
            if not os.path.exists(icon_path):
                logging.debug("App icon not found at %s. Using default.", icon_path)
                return
                
            # Try different methods to set the icon
            try:
                # Method 1: Direct iconbitmap (works on Windows and some Linux)
                self.root.iconbitmap(icon_path)
                logging.debug("Icon set using iconbitmap")
                return
            except Exception as e1:
                logging.debug("iconbitmap failed: %s", str(e1))
                try:
                    # Method 2: Using PhotoImage (works on some Linux systems)
                    from PIL import Image, ImageTk
                    img = Image.open(icon_path)
                    photo = ImageTk.PhotoImage(img)
                    self.root.iconphoto(True, photo)
                    logging.debug("Icon set using PhotoImage")
                    return
                except Exception as e2:
                    logging.debug("PhotoImage failed: %s", str(e2))
                    # Method 3: Try with Tk's photo image (works on some systems)
                    try:
                        self.root.tk.call('wm', 'iconphoto', self.root._w, self.tk.PhotoImage(file=icon_path))
                        logging.debug("Icon set using Tk photo")
                    except Exception as e3:
                        logging.debug("All icon setting methods failed: %s", str(e3))
                        
        except Exception as e:
            logging.debug("Could not set app icon: %s", str(e))

    def setup_style(self):
        """Configure the application styling with RepairDesk brand theme."""
        from nest.ui.theme.styles import apply_styles
        
        # Apply the RepairDesk green theme to the entire application
        self.style_data = apply_styles(self.root)
        
        # Store colors for easy access throughout the app
        self.colors = self.style_data["colors"]
        
        # Log theme application
        logging.info("Applied RepairDesk green theme to application")

        # Store a reference to the style object
        style = self.ttk.Style()
        
        # Try to use a modern theme if available
        available_themes = style.theme_names()
        preferred_themes = ["clam", "vista", "winnative"]

        for theme in preferred_themes:
            if theme in available_themes:
                style.theme_use(theme)
                logging.info(f"Using '{theme}' UI theme")
                break

        # Configure colors for all elements to match the app color scheme
        style.configure(
            ".",
            background=self.colors["background"],
            foreground=self.colors["text_primary"],
            font=("Segoe UI", 10),
        )

        # Header style - remove background and set text color to match sidebar
        style.configure(
            "Header.TLabel",
            font=("Segoe UI", 16, "bold"),
            padding=10,
            background=self.colors["content_bg"],  # Match content background
            foreground=self.colors["sidebar"],
        )  # Match sidebar color

        # Special style for the brand label in navbar
        style.configure(
            "Brand.TLabel",
            font=("Segoe UI", 18, "bold"),  # Slightly bigger
            padding=10,
            background=self.colors["sidebar"],
            foreground="white",  # White text
            anchor="center",
        )  # Centered

        # Sidebar frame style
        style.configure("Sidebar.TFrame", background=self.colors["sidebar"])

        # Navigation button styles - LEFT ALIGNED TEXT - INCREASED SIZE
        style.configure(
            "Nav.TButton",
            font=("Segoe UI", 12),  # Larger font for better readability
            padding=(20, 15, 20, 15),  # Increased padding for larger buttons
            background=self.colors["sidebar"],
            foreground=self.colors["sidebar_text"],
            borderwidth=0,
            anchor="w",  # Left align text
            justify="left",
            width=15  # Minimum width to prevent tiny buttons
        )  # Left justify text

        # IMPROVED HOVER EFFECT - prevent flickering
        style.map(
            "Nav.TButton",
            background=[
                ("active", self.colors["sidebar_highlight"]),
                ("hover", self.colors["sidebar_highlight"]),
            ],
            foreground=[
                ("active", "white"),
                ("hover", self.colors["sidebar_text"]),
            ],
            relief=[("pressed", "flat"), ("!pressed", "flat")],
        )

        # Detail Section Label Frame Style
        style.configure(
            "DetailSection.TLabelframe",
            background="white",
            borderwidth=1,
            relief="solid",
        )

        style.configure(
            "DetailSection.TLabelframe.Label",
            font=("Segoe UI", 9, "bold"),
            background="white",
            foreground=self.colors["primary"],
        )
        
        # Action button style
        style.configure(
            "Action.TButton",
            font=("Segoe UI", 9),
            padding=(10, 5),
            relief="raised",
            background=self.colors["primary"],
            foreground="white",
        )

        style.map(
            "Action.TButton",
            background=[("active", self.colors["primary_dark"]), ("disabled", "#cccccc")],
            foreground=[("active", "white"), ("disabled", "#999999")]
        )

        # Active module style (for highlighting current module) - INCREASED SIZE
        style.configure(
            "Active.Nav.TButton",
            font=("Segoe UI", 12, "bold"),  # Larger font for better readability
            padding=(20, 15, 20, 15),  # Increased padding for larger buttons
            background=self.colors["primary"],
            foreground=self.colors["sidebar_text"],
            borderwidth=0,
            anchor="w",  # Left align text
            justify="left",
            width=15  # Minimum width to prevent tiny buttons
        )  # Left justify text

        # Content frame style - ensure it has the light background
        style.configure("Content.TFrame", background=self.colors["content_bg"])

        # Card frame style (for panels)
        style.configure(
            "Card.TFrame", background=self.colors["card_bg"], borderwidth=1, relief="solid"
        )

        # Card header style
        style.configure("CardHeader.TFrame", background=self.colors["header_bg"], borderwidth=0)

        # Configure the style for all button types
        # Regular button style - INCREASED SIZE
        style.configure(
            "TButton", 
            padding=(15, 10),  # Wider horizontal padding for bigger buttons
            font=("Segoe UI", 11),  # Slightly larger font
            width=10  # Minimum width to avoid tiny buttons
        )

        # Improve button hover states - prevent flickering
        style.map(
            "TButton",
            background=[
                ("active", self.colors["primary_light"]),
                ("hover", self.colors["primary_light"]),
            ],
            foreground=[
                ("active", self.colors["text_primary"]),
                ("hover", self.colors["text_primary"]),
            ],
        )

        # Primary button style - INCREASED SIZE
        style.configure(
            "Primary.TButton",
            background=self.colors["primary"],
            foreground="white",
            padding=(20, 12),  # Larger padding for primary buttons
            font=("Segoe UI", 11),  # Slightly larger font
            width=12  # Minimum width to ensure buttons aren't tiny
        )

        # Improve primary button hover
        style.map(
            "Primary.TButton",
            background=[
                ("active", self.colors["primary_dark"]),
                ("hover", self.colors["primary_dark"]),
            ],
            foreground=[("active", "white"), ("hover", "white")],
        )

        # Secondary button style - INCREASED SIZE
        style.configure(
            "Secondary.TButton",
            background=self.colors["secondary"],
            foreground="white",
            padding=(20, 12),  # Larger padding
            font=("Segoe UI", 11),  # Slightly larger font
            width=12  # Minimum width to ensure buttons aren't tiny
        )

        style.map(
            "Secondary.TButton",
            background=[
                ("active", self.colors["secondary_dark"]),
                ("hover", self.colors["secondary_dark"]),
            ],
            foreground=[("active", "white"), ("hover", "white")],
        )

        # Danger/warning button style
        style.configure(
            "Danger.TButton",
            background=self.colors["warning"],
            foreground="white",
            padding=10,
            font=("Segoe UI", 10),
        )

        # Icon button style (smaller, square)
        style.configure("Icon.TButton", padding=2, width=3, font=("Segoe UI", 10))

        # Status bar style
        style.configure(
            "Status.TLabel",
            padding=6,
            font=("Segoe UI", 9),
            background=self.colors["footer_bg"],
            relief="sunken",
        )

        # Regular label style
        style.configure(
            "TLabel", padding=4, font=("Segoe UI", 10), background=self.colors["background"]
        )

        # Header label style without background box
        style.configure(
            "Title.TLabel",
            font=("Segoe UI", 18, "bold"),
            padding=10,
            foreground=self.colors["heading_text"],
            background=self.colors["content_bg"],
        )

        # Subtitle label style
        style.configure(
            "Subtitle.TLabel",
            font=("Segoe UI", 14),
            padding=6,
            foreground=self.colors["heading_text"],
            background=self.colors["content_bg"],
        )

        # Card title label style
        style.configure(
            "CardTitle.TLabel",
            font=("Segoe UI", 12, "bold"),
            padding=8,
            background=self.colors["header_bg"],
        )

        # Entry fields
        style.configure("TEntry", padding=8, font=("Segoe UI", 10))

        # Combobox
        style.configure("TCombobox", padding=8, font=("Segoe UI", 10))

        # Spinbox
        style.configure("TSpinbox", padding=8, font=("Segoe UI", 10))

        # Checkbutton
        style.configure("TCheckbutton", font=("Segoe UI", 10), background=self.colors["background"])

        # Radiobutton
        style.configure("TRadiobutton", font=("Segoe UI", 10), background=self.colors["background"])

        # Treeview (for tables) with improved styling
        style.configure(
            "Treeview",
            font=("Segoe UI", 10),
            rowheight=30,
            background=self.colors["card_bg"],
            fieldbackground=self.colors["card_bg"],
        )

        # Configure Treeview with basic styling
        style.configure("Treeview",
            background="#ffffff",
            foreground="#000000",
            fieldbackground="#ffffff",
            rowheight=35,
            font=("Segoe UI", 10),
            borderwidth=0,
            relief="flat"
        )
        
        # Configure Treeview Heading with explicit height and styling
        style.configure("Treeview.Heading",
            background="#2e7d32",
            foreground="white",
            relief="flat",
            borderwidth=0,
            font=("Segoe UI", 11, "bold"),
            padding=(10, 15),  # Increased vertical padding for better height
        )
        
        # Update the map settings for Treeview
        style.map(
            "Treeview",
            background=[("selected", "#e0e0e0")],
            foreground=[("selected", "#000000")],
            fieldbackground=[("selected", "#e0e0e0")]
        )
        
        # Force update all Treeview widgets
        for widget in self.root.winfo_children():
            if isinstance(widget, ttk.Treeview):
                widget.update()

        # Separator
        style.configure("TSeparator", background=self.colors["border"])

        # Progressbar
        style.configure("TProgressbar", background=self.colors["primary"])

        # Notebook (tabs)
        style.configure("TNotebook", background=self.colors["background"], tabmargins=[2, 5, 2, 0])

        style.configure("TNotebook.Tab", padding=[12, 6, 12, 6], font=("Segoe UI", 10))

        # Improve tab hover states
        style.map(
            "TNotebook.Tab",
            background=[
                ("selected", self.colors["primary"]),
                ("active", self.colors["hover"]),
                ("hover", self.colors["hover"]),
            ],
            foreground=[("selected", "white"), ("active", "white"), ("hover", "white")],
        )

        # Scrollbar
        style.configure(
            "TScrollbar",
            arrowsize=13,
            background=self.colors["background"],
            borderwidth=1,
            relief="flat",
        )

        # Info Message
        style.configure(
            "Info.TLabel",
            background=self.colors["primary_light"],
            foreground=self.colors["text_primary"],
            padding=10,
            font=("Segoe UI", 10),
        )

        # Warning Message
        style.configure(
            "Warning.TLabel",
            background="#FFECB3",
            foreground="#FF6F00",
            padding=10,
            font=("Segoe UI", 10),
        )

        # Error Message
        style.configure(
            "Error.TLabel",
            background="#FFCDD2",
            foreground="#B71C1C",
            padding=10,
            font=("Segoe UI", 10),
        )

        # Success Message
        style.configure(
            "Success.TLabel",
            background=self.colors["secondary_light"],
            foreground=self.colors["secondary_dark"],
            padding=10,
            font=("Segoe UI", 10),
        )

    def on_close(self):
        """Handle application close event, closing resources properly"""
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            # Clear any cached security credentials from memory
            try:
                from nest.ui.customers import clear_pin_from_memory
                clear_pin_from_memory()
                logging.info("Cleared security PINs from memory on exit")
            except Exception as e:
                logging.warning(f"Failed to clear security PINs: {e}")
            
            # Set a flag to indicate application is closing
            self.is_closing = True
            
            # Cancel all 'after' callbacks to prevent errors
            for after_id in self.root.tk.call('after', 'info'):
                try:
                    self.root.after_cancel(after_id)
                except Exception as e:
                    logging.debug(f"Could not cancel after_id {after_id}: {e}")
                    
            self.root.destroy()

    def reset_activity_timer(self, event=None):
        """Reset the inactivity timer when user performs an action."""
        # Cancel the existing timer if there is one
        if self.activity_timer_id is not None:
            self.root.after_cancel(self.activity_timer_id)
            
        # Set a new timer
        self.activity_timer_id = self.root.after(self.inactivity_timeout, self.lock_session)
    
    def lock_session(self):
        """Lock the session after inactivity timeout."""
        # Don't lock if already locked or if still on login screen
        if self.locked or self.current_user is None:
            return
            
        logging.info("Locking session due to inactivity")
        self.locked = True
        
        # Clear the cached PIN for security
        try:
            from nest.ui.customers import clear_pin_from_memory
            clear_pin_from_memory()
        except Exception as e:
            logging.error(f"Error clearing PIN from memory: {e}")
            
        # Save all module states if needed before locking
        # This would be a good place to save any unsaved data
        
        # Create the lock screen overlay
        self.lock_overlay = self.tk.Frame(self.root, bg="#0b4d49")
        self.lock_overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        
        # Add lock screen content
        lock_frame = self.tk.Frame(self.lock_overlay, bg="#0b4d49", padx=50, pady=50)
        lock_frame.place(relx=0.5, rely=0.5, anchor="center")
        
        # Lock icon
        lock_label = self.tk.Label(
            lock_frame, 
            text="🔒", 
            font=("Segoe UI", 64), 
            bg="#0b4d49", 
            fg=self.colors["secondary"]
        )
        lock_label.pack(pady=(0, 20))
        
        # Lock message
        message_label = self.tk.Label(
            lock_frame, 
            text="""Session Locked

Your session was locked due to inactivity""", 
            font=("Segoe UI", 16), 
            bg="#0b4d49", 
            fg="white",
            justify="center"
        )
        message_label.pack(pady=(0, 30))
        
        # Unlock button
        unlock_button = self.tk.Button(
            lock_frame, 
            text="Unlock Session", 
            font=("Segoe UI", 12, "bold"), 
            bg=self.colors["secondary"], 
            fg="white",
            padx=20, 
            pady=10,
            command=self.show_unlock_dialog
        )
        unlock_button.pack(pady=(0, 10))
        
        # Logout button
        logout_button = self.tk.Button(
            lock_frame, 
            text="Log Out", 
            font=("Segoe UI", 12), 
            bg="#424242", 
            fg="white",
            padx=20, 
            pady=10,
            command=self.logout
        )
        logout_button.pack()
        
    def show_unlock_dialog(self):
        """Show dialog to unlock the session."""
        # Import login module dynamically
        try:
            from nest.ui.login import verify_credentials
            from tkinter import simpledialog
            
            # Get username from current user
            username = self.current_user.get("username", "")
            
            # Create custom dialog for password
            password = simpledialog.askstring(
                "Unlock Session", 
                f"Enter password for {username}:", 
                parent=self.root, 
                show="*"
            )
            
            if password:
                # Verify credentials
                success, user = verify_credentials(username, password)
                if success:
                    self.unlock_session()
                else:
                    messagebox.showerror("Authentication Failed", "Incorrect password. Session remains locked.")
            
        except Exception as e:
            logging.error(f"Error in unlock dialog: {e}")
            messagebox.showerror("Error", f"Could not verify credentials: {e}")
    
    def unlock_session(self):
        """Unlock the session after successful authentication."""
        if not self.locked:
            return
            
        logging.info("Unlocking session after authentication")
        
        # Remove lock overlay
        if hasattr(self, 'lock_overlay'):
            self.lock_overlay.destroy()
            
        # Reset inactivity timer
        self.locked = False
        self.reset_activity_timer()
        
        # Show welcome back notification
        self.show_notification(
            f"Welcome back, {self.current_user.get('fullname', 'User')}!", "info"
        )
    
    def logout(self):
        """Log out the current user."""
        logging.info("User logging out")
        
        # Clear user data and session
        self.current_user = None
        if self.activity_timer_id is not None:
            self.root.after_cancel(self.activity_timer_id)
            self.activity_timer_id = None
        
        # Clear any sensitive data from memory
        try:
            from nest.ui.customers import clear_pin_from_memory
            clear_pin_from_memory()
        except Exception as e:
            logging.error(f"Error clearing PIN from memory during logout: {e}")
            
        # Clean up any open modules
        for module_name, module_instance in list(self.modules.items()):
            try:
                if hasattr(module_instance, 'destroy'):
                    module_instance.destroy()
                    logging.info(f"Properly destroying module: {module_name}")
            except Exception as e:
                logging.error(f"Error destroying module {module_name}: {e}")
        
        self.modules.clear()
        self.active_module = None
        
        # Return to login screen
        self.show_login()
        
    def show_login(self):
        """Show the login screen."""
        # Clear current UI
        for widget in self.root.winfo_children():
            widget.destroy()

        # Import login module using lazy loading
        try:
            from nest.ui.login import LoginFrame

            login_frame = LoginFrame(self.root, on_login_success=self.on_login_success)
            login_frame.pack(expand=True, fill="both")
        except ImportError as e:
            logging.error(f"Failed to import login module: {e}")
            self.show_error(f"Could not load the login module: {e}")

    def on_login_success(self, user):
        """Handle successful login."""
        self.current_user = user
        logging.info(f"User '{user.get('fullname', 'unknown')}' logged in successfully")
        
        # Update config with current user info
        import json
        import os
        import datetime
        config_path = os.path.join(os.path.dirname(__file__), 'config', 'config.json')
        try:
            with open(config_path, 'r') as file:
                config = json.load(file)
                
            # Update current user info
            config['current_user'] = {
                'id': user.get('id', ''),
                'name': user.get('fullname', user.get('name', 'Unknown')),
                'role': user.get('role', ''),
                'last_login': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # Save updated config
            with open(config_path, 'w') as file:
                json.dump(config, file, indent=2)
                
            # Generate personalized knowledge file for NestBot
            try:
                from nest.knowledge.user_context import generate_user_knowledge_file
                knowledge_path = generate_user_knowledge_file()
                logging.info(f"Generated personalized knowledge file for NestBot at {knowledge_path}")
            except Exception as e:
                logging.error(f"Error generating NestBot knowledge file: {str(e)}")
        except Exception as e:
            logging.error(f"Error updating user in config: {str(e)}")
        
        # Show main UI
        self.show_main_ui()
        self.reset_activity_timer()

    def show_main_ui(self):
        """Set up the main application UI after login."""
        # Configure window with dynamic size based on screen resolution
        self.root.title("Nest 2.4 - Device Repair Management")
        
        # Get current screen dimensions to ensure accurate sizing
        self.screen_width = self.root.winfo_screenwidth()
        self.screen_height = self.root.winfo_screenheight()
        
        # Bind events to reset inactivity timer
        self.root.bind("<Motion>", self.reset_activity_timer)  # Mouse movement
        self.root.bind("<Key>", self.reset_activity_timer)  # Keyboard activity
        self.root.bind("<Button>", self.reset_activity_timer)  # Mouse clicks
        
        # Enable responsive UI for the main window
        self.root.resizable(True, True)
        
        # Calculate main window size (100% of screen width, 100% of screen height)
        main_width = int(self.screen_width * 1)
        main_height = int(self.screen_height * 1)
        
        # Cap size for very large screens to prevent UI elements being too spread out
        main_width = min(main_width, 1920)  # Cap at 1920px
        main_height = min(main_height, 1200)  # Cap at 1200px
        
        # Center the window on screen
        x_position = (self.screen_width - main_width) // 2
        y_position = (self.screen_height - main_height) // 2
        
        # DIRECT APPROACH: No fancy window manager tricks, just brute force
        
        # 1. REMOVE ALL SIZE CONSTRAINTS
        self.root.maxsize(10000, 10000)  # Set absurdly large max size
        self.root.minsize(10, 10)        # Set very small min size
        
        # 2. Update tasks to ensure geometry manager has processed everything
        self.root.update_idletasks()
        
        # 3. Set window to PRECISELY full screen dimensions (no borders/decorations)
        # Subtract small amount for window decorations to ensure it fits
        self.root.geometry(f"{self.screen_width}x{self.screen_height-30}+0+0")
        
        # 4. Force an update
        self.root.update()

        # 5. Add a delayed action to reset geometry in case something overrides it
        def force_size():
            # Get actual screen dimensions again
            sw = self.root.winfo_screenwidth()
            sh = self.root.winfo_screenheight()
            # Force window to fill screen completely
            self.root.geometry(f"{sw}x{sh-30}+0+0")
            
        # Schedule multiple attempts to force the correct size
        self.root.after(100, force_size)
        self.root.after(500, force_size)  # Second attempt if first fails

        # Clear current UI
        for widget in self.root.winfo_children():
            widget.destroy()

        # Create main container with regular tk.Frame to allow background setting
        self.main_container = self.tk.Frame(self.root, bg=self.colors["content_bg"])
        self.main_container.pack(fill="both", expand=True)

        # Create top menu bar with custom styling
        self.create_menu_bar()

        # Main frame that will hold nav, content, and AI panel frames
        self.three_panel_frame = self.tk.Frame(self.main_container, bg=self.colors["content_bg"])
        self.three_panel_frame.pack(fill="both", expand=True, pady=0, padx=0)

        # Create main split between navigation and content
        self.nav_frame = self.ttk.Frame(self.three_panel_frame, style="Sidebar.TFrame", width=240)
        self.nav_frame.pack(side="left", fill="y", padx=0, pady=0)

        # Make nav_frame keep its width
        self.nav_frame.pack_propagate(False)

        # Create a regular tk Frame for content container to allow background settings
        self.content_container = self.tk.Frame(self.three_panel_frame, bg=self.colors["content_bg"])
        self.content_container.pack(side="left", fill="both", expand=True, padx=0, pady=0)

        # Create AI panel (NestBot) on the right side with fixed width
        self.ai_panel_width = 300  # Fixed width for AI panel
        self.ai_panel = self.ttk.Frame(self.three_panel_frame, style="Sidebar.TFrame", width=self.ai_panel_width)
        self.ai_panel.pack(side="right", fill="y", padx=0, pady=0)
        self.ai_panel.pack_propagate(False)  # Maintain fixed width

        # Create corner notification area (top right) instead of full-width notification area
        self.notification_frame = self.tk.Frame(
            self.content_container, bg=self.colors["content_bg"]
        )

        # Create actual content frame - use regular tk.Frame for background control
        self.content_frame = self.tk.Frame(self.content_container, bg=self.colors["content_bg"])
        self.content_frame.pack(fill="both", expand=True, padx=15, pady=15)

        # Now place the notification frame in the top-right corner
        self.notification_frame.place(relx=1.0, rely=0, anchor="ne", width=300, x=-15, y=15)

        # Create the navigation sidebar
        self.setup_navigation()

        # Set up the AI panel contents
        self.setup_ai_panel()


        # Create status bar with extra utilities
        self.create_status_bar()

        # Show the dashboard as default
        self.show_module("dashboard")

        # Show welcome notification
        self.show_notification(
            f"Welcome back, {self.current_user.get('fullname', 'User')}!", "info"
        )

        logging.info("Main UI loaded.")

    def create_menu_bar(self):
        """Create the application's top menu bar with matching color."""
        menubar = self.tk.Menu(
            self.root,
            bg=self.colors["bg_color"],  # Use bg_color instead of background
            fg=self.colors["text_dark"],  # Use text_dark instead of text_primary
            activebackground=self.colors["primary_green"],  # Use the RepairDesk green
            activeforeground=self.colors["white"],
            relief="flat",
            borderwidth=0,
        )
        self.root.config(menu=menubar)

        # File menu - match color scheme
        file_menu = self.tk.Menu(
            menubar,
            tearoff=0,
            bg=self.colors["background"],
            fg=self.colors["text_primary"],
            activebackground=self.colors["primary"],
            activeforeground="white",
            relief="flat",
            borderwidth=1,
        )
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(
            label="New Ticket", command=lambda: self.show_module("tickets", action="new")
        )
        file_menu.add_command(
            label="New Customer", command=lambda: self.show_module("customers", action="new")
        )
        file_menu.add_separator()
        file_menu.add_command(label="Print...", command=self.show_print_dialog)
        file_menu.add_command(label="Export Data...", command=self.show_export_dialog)
        file_menu.add_command(label="Import Data...", command=self.show_import_dialog)
        file_menu.add_separator()
        file_menu.add_command(label="Settings", command=self.show_settings)
        file_menu.add_separator()
        file_menu.add_command(label="Log Out", command=self.log_out)
        file_menu.add_command(label="Exit", command=self.on_close)

        # Edit menu
        edit_menu = self.tk.Menu(
            menubar,
            tearoff=0,
            bg=self.colors["bg_color"],
            fg=self.colors["text_dark"],
            activebackground=self.colors["primary_green"],
            activeforeground="white",
            relief="flat",
            borderwidth=1,
        )
        menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Undo", command=lambda: self.perform_edit_action("undo"))
        edit_menu.add_command(label="Redo", command=lambda: self.perform_edit_action("redo"))
        edit_menu.add_separator()
        edit_menu.add_command(label="Cut", command=lambda: self.perform_edit_action("cut"))
        edit_menu.add_command(label="Copy", command=lambda: self.perform_edit_action("copy"))
        edit_menu.add_command(label="Paste", command=lambda: self.perform_edit_action("paste"))
        edit_menu.add_separator()
        edit_menu.add_command(label="Find...", command=lambda: self.perform_edit_action("find"))

        # View menu
        view_menu = self.tk.Menu(
            menubar,
            tearoff=0,
            bg=self.colors["background"],
            fg=self.colors["text_primary"],
            activebackground=self.colors["primary"],
            activeforeground="white",
            relief="flat",
            borderwidth=1,
        )
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Refresh", command=self.refresh_current_view)
        view_menu.add_separator()

        # View submenu for display options
        display_menu = self.tk.Menu(
            view_menu,
            tearoff=0,
            bg=self.colors["background"],
            fg=self.colors["text_primary"],
            activebackground=self.colors["primary"],
            activeforeground="white",
            relief="flat",
            borderwidth=1,
        )
        view_menu.add_cascade(label="Display Options", menu=display_menu)

        # Create display option checkboxes
        self.show_completed = self.tk.BooleanVar(value=True)
        self.show_archived = self.tk.BooleanVar(value=False)
        self.compact_view = self.tk.BooleanVar(value=False)

        display_menu.add_checkbutton(
            label="Show Completed Items",
            variable=self.show_completed,
            command=self.refresh_current_view,
        )
        display_menu.add_checkbutton(
            label="Show Archived Items",
            variable=self.show_archived,
            command=self.refresh_current_view,
        )
        display_menu.add_checkbutton(
            label="Compact View", variable=self.compact_view, command=self.toggle_compact_view
        )

        # Tools menu
        tools_menu = self.tk.Menu(
            menubar,
            tearoff=0,
            bg=self.colors["background"],
            fg=self.colors["text_primary"],
            activebackground=self.colors["primary"],
            activeforeground="white",
            relief="flat",
            borderwidth=1,
        )
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="PC Tools", command=lambda: self.show_module("pc_tools"))
        tools_menu.add_command(label="iOS Tools", command=lambda: self.show_module("ios_tools"))
        tools_menu.add_command(
            label="Android Tools", command=lambda: self.show_module("android_tools")
        )
        tools_menu.add_separator()
        tools_menu.add_command(label="Hardware Diagnostics", command=self.show_hardware_diagnostics)
        tools_menu.add_command(label="Software Diagnostics", command=self.show_software_diagnostics)
        tools_menu.add_command(label="Network Tools", command=self.show_network_tools)
        tools_menu.add_separator()
        tools_menu.add_command(label="Barcode Scanner", command=self.show_barcode_scanner)
        tools_menu.add_command(label="Serial Number Lookup", command=self.show_serial_lookup)

        # Reports menu
        reports_menu = self.tk.Menu(
            menubar,
            tearoff=0,
            bg=self.colors["background"],
            fg=self.colors["text_primary"],
            activebackground=self.colors["primary"],
            activeforeground="white",
            relief="flat",
            borderwidth=1,
        )
        menubar.add_cascade(label="Reports", menu=reports_menu)
        reports_menu.add_command(label="Daily Summary", command=lambda: self.show_report("daily"))
        reports_menu.add_command(label="Weekly Summary", command=lambda: self.show_report("weekly"))
        reports_menu.add_command(
            label="Monthly Summary", command=lambda: self.show_report("monthly")
        )
        reports_menu.add_separator()
        reports_menu.add_command(
            label="Revenue Report", command=lambda: self.show_report("revenue")
        )
        reports_menu.add_command(
            label="Service Metrics", command=lambda: self.show_report("service")
        )
        reports_menu.add_command(
            label="Inventory Status", command=lambda: self.show_report("inventory")
        )
        reports_menu.add_command(
            label="Customer Analysis", command=lambda: self.show_report("customers")
        )
        reports_menu.add_separator()
        reports_menu.add_command(
            label="Custom Report...", command=lambda: self.show_report("custom")
        )

        # Help menu
        help_menu = self.tk.Menu(
            menubar,
            tearoff=0,
            bg=self.colors["background"],
            fg=self.colors["text_primary"],
            activebackground=self.colors["primary"],
            activeforeground="white",
            relief="flat",
            borderwidth=1,
        )
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="View Help", command=self.show_help)
        help_menu.add_command(label="Tutorials", command=self.show_tutorials)
        help_menu.add_command(label="Keyboard Shortcuts", command=self.show_shortcuts)
        help_menu.add_separator()
        help_menu.add_command(label="Check for Updates", command=self.check_updates)
        help_menu.add_separator()
        help_menu.add_command(label="About Nest", command=self.show_about)

    def setup_navigation(self):
        """Set up the navigation sidebar."""
        from nest.utils.config_util import ConfigManager
        config = ConfigManager()
        store_name = config.get("store_name", config.get("store_slug", ""))
        
        if store_name:
            # Create a distinctive background frame for the store name
            store_frame = self.tk.Frame(
                self.nav_frame, 
                bg="#005F56",  # Slightly lighter than the sidebar for contrast
                highlightthickness=1,
                highlightbackground="#009688"
            )
            store_frame.pack(fill="x", padx=5, pady=(0, 15))
            
            # First add the descriptor label (Connected to:)
            store_descriptor = self.tk.Label(
                store_frame,
                text="Connected to:",
                font=self.tkfont.Font(family="Arial", size=8),
                bg="#005F56",
                fg="#A5D6A7"  # Light green text
            )
            store_descriptor.pack(fill="x")
            
            # Then add the store name below it
            store_label = self.tk.Label(
                store_frame,
                text=store_name,
                font=self.tkfont.Font(family="Arial", size=11, weight="bold"),
                bg="#005F56",
                fg="white",
                pady=5
            )
            store_label.pack(fill="x")

        # User info section
        if self.current_user:
            user_frame = self.ttk.Frame(self.nav_frame, style="Sidebar.TFrame")
            user_frame.pack(fill="x", padx=8, pady=5)

            username = self.current_user.get("fullname", "User")
            role = self.current_user.get("role", "Staff")

            # Use the new SidebarHeading style for username
            user_label = self.ttk.Label(
                user_frame,
                text=f"{username}",
                style="SidebarHeading.TLabel"
            )
            user_label.pack(anchor="w")

            # Use the new Sidebar style for role
            role_label = self.ttk.Label(
                user_frame,
                text=f"Role: {role}",
                style="Sidebar.TLabel"
            )
            role_label.pack(anchor="w")

            # Create a separator with custom styling
            separator = self.ttk.Separator(self.nav_frame, orient="horizontal")
            separator.pack(fill="x", padx=20, pady=10)

        # Define navigation modules with better icons - all LEFT ALIGNED
        nav_modules = [
            ("🏠 Dashboard", "dashboard", "Daily stats and overview"),
            ("🎫 Tickets", "tickets", "Manage repair tickets"),
            ("👥 Customers", "customers", "Manage customer information"),
            ("📦 Inventory", "inventory", "Track parts and supplies"),
            ("📅 Appointments", "appointments", "Schedule appointments"),
            ("📊 Reports", "reports", "Generate reports"),
            ("💻 PC Tools", "pc_tools", "PC diagnostics and tools"),
            ("📱 iOS Tools", "ios_tools", "iOS diagnostics and tools"),
            ("🤖 Android Tools", "android_tools", "Android diagnostics and tools"),
        ]

        # Create a frame for the module buttons
        modules_frame = self.ttk.Frame(self.nav_frame, style="Sidebar.TFrame")
        modules_frame.pack(fill="x", padx=0, pady=0)

        # Store navigation buttons for active highlighting
        self.nav_buttons = {}

        # Create navigation buttons with LEFT ALIGNED text
        for label, module_name, tooltip in nav_modules:
            btn = self.ttk.Button(
                modules_frame,
                text=label,
                style="Nav.TButton",
                command=lambda m=module_name: self.show_module(m),
            )
            btn.pack(fill="x", padx=0, pady=1)
            
            # Store the button reference
            self.nav_buttons[module_name] = btn
            
            # Add tooltip capability
            self.create_tooltip(btn, tooltip)
            
        # Add spacing before logout button
        self.ttk.Frame(self.nav_frame, style="Sidebar.TFrame").pack(fill="both", expand=True)
        
        # Add bottom buttons - keeping only essential ones
        bottom_frame = self.ttk.Frame(self.nav_frame, style="Sidebar.TFrame")
        bottom_frame.pack(fill="x", padx=0, pady=(10, 0))

        separator = self.ttk.Separator(bottom_frame, orient="horizontal")
        separator.pack(fill="x", padx=15, pady=10)

        # Keep the help, settings, and logout buttons with left-aligned text
        self.ttk.Button(
            bottom_frame, text="❓ Help", style="Nav.TButton", command=self.show_help
        ).pack(fill="x", padx=0, pady=1)

        self.ttk.Button(
            bottom_frame, text="⚙️ Settings", style="Nav.TButton", command=self.show_settings
        ).pack(fill="x", padx=0, pady=1)

        self.ttk.Button(
            bottom_frame, text="🚪 Log Out", style="Nav.TButton", command=self.log_out
        ).pack(fill="x", padx=0, pady=(1, 15))
        
    def setup_ai_panel(self):
        """Set up the NestBot AI panel on the right side of the application using the NestBotPanel class."""
        # Import the NestBot module
        from nest.ai.nestbot import NestBotPanel
        
        # Create the NestBot panel instance and integrate with the main app
        self.nestbot = NestBotPanel(self.ai_panel, self)
        self.nestbot.integrate_with_app()

    def create_status_bar(self):
        """Create an enhanced status bar with additional utilities."""
        # Create a frame for the status bar at the bottom of the window
        self.status_bar = self.tk.Frame(
            self.main_container,
            bg=self.colors["sidebar"],
            height=30
        )
        self.status_bar.pack(side="bottom", fill="x", padx=0, pady=0)
        
        # Make sure the height is maintained
        self.status_bar.pack_propagate(False)
        
        # Left side: display status info
        self.status_label = self.tk.Label(
            self.status_bar,
            text="Ready",
            bg=self.colors["sidebar"],
            fg=self.colors["sidebar_text"],
            font=("Segoe UI", 9)
        )
        self.status_label.pack(side="left", padx=10)
        
        # Software version label
        version_label = self.ttk.Label(
            self.status_bar,
            text="Nest 2.4",
            style="StatusBar.TLabel",
            padding=(10, 0)
        )
        version_label.pack(side="left", padx=(5, 0))
        
        # Create a label for the time
        self.time_label = self.ttk.Label(
            self.status_bar,
            text="",
            style="StatusBar.TLabel",
            padding=(10, 0)
        )
        self.time_label.pack(side="right")
        
        # Update the time immediately and schedule updates
    
    def update_time(self):
        """Update the time display in the status bar."""
        from datetime import datetime

        # Update time
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.datetime_var.set(current_time)

        # Only schedule next update if application is not closing
        if not hasattr(self, 'is_closing') or not self.is_closing:
            self.root.after(1000, self.update_time)

    def create_tooltip(self, widget, text):
        """Create a tooltip for a widget."""

        def enter(event):
            x, y, _, _ = widget.bbox("insert")
            x += widget.winfo_rootx() + 25
            y += widget.winfo_rooty() + 25

            # Creates a toplevel window
            self.tooltip = self.tk.Toplevel(widget)
            self.tooltip.wm_overrideredirect(True)
            self.tooltip.wm_geometry(f"+{x}+{y}")

            tooltip_frame = self.ttk.Frame(self.tooltip, style="Card.TFrame")
            tooltip_frame.pack(fill="both", expand=True)

            label = self.ttk.Label(
                tooltip_frame,
                text=text,
                background=self.colors["card_bg"],
                foreground=self.colors["text_primary"],
                font=("Segoe UI", 9),
                padding=6,
            )
            label.pack()

        def leave(event):
            if hasattr(self, "tooltip"):
                self.tooltip.destroy()

        widget.bind("<Enter>", enter)
        widget.bind("<Leave>", leave)

    def show_module(self, module_name: str, **kwargs):
        """Load and display a specific module."""
        # First properly clean up any existing modules
        if hasattr(self, 'modules') and self.active_module in self.modules:
            try:
                # Try to properly destroy the module if it exists
                old_module = self.modules.get(self.active_module)
                if old_module and hasattr(old_module, 'destroy'):
                    logging.info(f"Properly destroying module: {self.active_module}")
                    old_module.destroy()
                    # Allow time for proper cleanup
                    self.root.update_idletasks()
            except Exception as e:
                logging.error(f"Error cleaning up module {self.active_module}: {e}")
                
        # Now clear any remaining content to be safe
        for widget in self.content_frame.winfo_children():
            try:
                widget.destroy()
            except Exception as e:
                logging.error(f"Error destroying widget: {e}")
                
        # Allow destroyed widgets to be fully processed
        self.root.update_idletasks()

        # Update active module
        self.active_module = module_name

        # Update status
        self.status_var.set(f"Loading {module_name} module...")

        # Update active navigation button
        for mod, btn in self.nav_buttons.items():
            if mod == module_name:
                btn.configure(style="Active.Nav.TButton")
            else:
                btn.configure(style="Nav.TButton")

        try:
            # Use dynamic import to load module class
            if module_name == "dashboard":
                from nest.ui.dashboard import DashboardModule

                module = DashboardModule(self.content_frame, current_user=self.current_user)
            elif module_name == "tickets":
                from nest.ui.tickets import TicketsModule

                action = kwargs.get("action", None)
                module = TicketsModule(
                    self.content_frame, current_user=self.current_user, action=action
                )
            elif module_name == "customers":
                from nest.ui.customers import CustomersModule

                # Pass current_user but don't pass action to CustomersModule
                module = CustomersModule(self.content_frame, current_user=self.current_user)
            elif module_name == "inventory":
                from nest.ui.inventory import InventoryModule

                module = InventoryModule(self.content_frame)
            elif module_name == "appointments":
                from nest.ui.appointments import AppointmentsModule

                module = AppointmentsModule(self.content_frame)
            elif module_name == "pc_tools":
                from nest.ui.pc_tools import PCToolsModule

                module = PCToolsModule(self.content_frame, current_user=self.current_user)
            elif module_name == "ios_tools":
                from nest.ui.ios_tools import IOSToolsModule

                module = IOSToolsModule(self.content_frame)
            elif module_name == "android_tools":
                from nest.ui.android_tools import AndroidToolsModule

                module = AndroidToolsModule(self.content_frame)
            elif module_name == "reports":
                from nest.ui.reports import ReportsModule

                report_type = kwargs.get("report_type", None)
                module = ReportsModule(self.content_frame, report_type=report_type)
            else:
                # Generic placeholder for unknown modules
                module = self.create_placeholder_module(f"{module_name.title()} Module")

            # Store module instance
            self.modules[module_name] = module

            # Display the module
            if hasattr(module, "pack"):
                module.pack(expand=True, fill="both")
                
            # Update status
            self.status_var.set(f"{module_name.title()} module loaded")

            # Enforce consistent fonts after module is loaded
            try:
                from nest.utils.font_manager import enforce_global_fonts
                enforce_global_fonts(self.root)
                logging.info(f"Enforced consistent fonts for {module_name} module")
            except Exception as font_error:
                logging.warning(f"Failed to enforce global fonts: {font_error}")
                
            logging.info(f"Loaded module: {module_name}")
            return module
            
        except ImportError as e:
            logging.error(f"Failed to import {module_name} module: {e}")
            self.show_error(f"Could not load the {module_name} module: {e}")
            self.status_var.set(f"Error loading {module_name} module")
            
        except Exception as e:
            logging.error(f"Error in {module_name} module: {e}")
            logging.exception(e)
            self.show_error(f"Error in {module_name} module: {e}")
            self.status_var.set(f"Error in {module_name} module")

    def create_placeholder_module(self, title):
        """Create a placeholder UI for modules under development."""
        frame = self.tk.Frame(self.content_frame, bg=self.colors["content_bg"])

        # Create card layout
        card = self.tk.Frame(frame, bg=self.colors["card_bg"], relief="solid", borderwidth=1)
        card.pack(fill="both", expand=True, padx=20, pady=20)

        # Card header
        header_frame = self.tk.Frame(card, bg=self.colors["header_bg"])
        header_frame.pack(fill="x")

        header = self.tk.Label(
            header_frame,
            text=title,
            font=("Segoe UI", 12, "bold"),
            bg=self.colors["header_bg"],
            fg=self.colors["text_primary"],
            padx=15,
            pady=10,
        )
        header.pack(anchor="w")

        # Card content
        content = self.tk.Frame(card, bg=self.colors["card_bg"])
        content.pack(fill="both", expand=True, padx=15, pady=15)

        # Icon or placeholder image
        icon_label = self.tk.Label(
            content,
            text="🔧",
            font=("Segoe UI", 48),
            bg=self.colors["card_bg"],
            fg=self.colors["text_primary"],
        )
        icon_label.pack(pady=30)

        # Message with better styling
        message = self.tk.Label(
            content,
            text="This module is currently under development.",
            font=("Segoe UI", 12),
            bg=self.colors["card_bg"],
            fg=self.colors["text_secondary"],
        )
        message.pack(pady=5)

        # Additional info
        info = self.tk.Label(
            content,
            text="Check back soon for updates!",
            font=("Segoe UI", 11),
            bg=self.colors["card_bg"],
            fg=self.colors["text_secondary"],
        )
        info.pack(pady=5)

        # Add a progress bar to indicate development progress
        progress_frame = self.tk.Frame(content, bg=self.colors["card_bg"])
        progress_frame.pack(fill="x", pady=20)

        progress_label = self.tk.Label(
            progress_frame,
            text="Development Progress:",
            font=("Segoe UI", 10),
            bg=self.colors["card_bg"],
            fg=self.colors["text_primary"],
        )
        progress_label.pack(side="left", padx=(0, 10))

        progress = self.ttk.Progressbar(
            progress_frame, orient="horizontal", length=300, mode="determinate", value=60
        )
        progress.pack(side="left")

        percent_label = self.tk.Label(
            progress_frame,
            text="60%",
            font=("Segoe UI", 10),
            bg=self.colors["card_bg"],
            fg=self.colors["text_primary"],
        )
        percent_label.pack(side="left", padx=10)

        return frame

    def show_notification(self, message, message_type="info"):
        """Show a notification in the top-right corner."""
        # Initialize notification frame if it doesn't exist
        if not hasattr(self, 'notification_frame') or not self.notification_frame.winfo_exists():
            self.notification_frame = ttk.Frame(self.root, style="Notification.TFrame")
            self.notification_frame.place(relx=1.0, rely=0, anchor="ne", width=300, height=0)
            self.notification_frame.place_forget()

        # Clear existing notification if any
        for widget in self.notification_frame.winfo_children():
            widget.destroy()

        if hasattr(self, 'notification_timer') and self.notification_timer:
            self.root.after_cancel(self.notification_timer)
            self.notification_timer = None

        # Set up colors based on message type
        color_map = {
            "info": (self.colors["primary_light"], self.colors["text_primary"]),
            "warning": ("#FFECB3", "#FF6F00"),
            "error": ("#FFCDD2", "#B71C1C"),
            "success": (self.colors["secondary_light"], self.colors["secondary_dark"]),
        }

        bg_color, fg_color = color_map.get(message_type, color_map["info"])

        # Create notification container with rounded corners and shadow effect
        notification = self.tk.Frame(
            self.notification_frame, bg=self.colors["card_bg"], relief="solid", borderwidth=1
        )
        notification.pack(fill="x", pady=(0, 5))

        # Make the notification appear with a slide-in effect
        # First position it off-screen
        notification.place(relx=1.0, rely=0, width=300, height=0)

        # Icon based on message type
        icon_map = {"info": "ℹ️", "warning": "⚠️", "error": "❌", "success": "✅"}
        icon = icon_map.get(message_type, "ℹ️")

        # Inner frame with colored background for the message
        colored_frame = self.tk.Frame(notification, bg=bg_color)
        colored_frame.pack(fill="both", expand=True, padx=1, pady=1)

        # Icon label
        icon_label = self.tk.Label(
            colored_frame, text=icon, bg=bg_color, fg=fg_color, padx=5, pady=5
        )
        icon_label.pack(side="left", padx=(5, 0), pady=5)

        # Message with word wrap
        msg_label = self.tk.Label(
            colored_frame,
            text=message,
            bg=bg_color,
            fg=fg_color,
            wraplength=230,  # Allow wrapping for longer messages
            justify="left",
            padx=5,
            pady=5,
        )
        msg_label.pack(side="left", fill="x", expand=True)

        # Close button
        close_btn = self.tk.Button(
            colored_frame,
            text="×",
            font=("Segoe UI", 10, "bold"),
            bg=bg_color,
            fg=fg_color,
            relief="flat",
            borderwidth=0,
            padx=5,
            pady=0,
            command=lambda: self.clear_notification()
        )
        close_btn.pack(side="right", padx=5, pady=5)

        # Make the notification appear with a fade-in effect
        def animate_in(step=0):
            try:
                if step < 10 and notification.winfo_exists():
                    notification.place_configure(
                        relx=1.0, rely=0, width=300, height=step * 5, anchor="ne"
                    )
                    self.root.after(15, lambda: animate_in(step + 1))
            except Exception as e:
                logging.debug(f"Animation error: {e}")  # Log error but don't crash
                
        # Start animation
        animate_in()
        
        # Auto-dismiss after 5 seconds for info and success messages
        if message_type in ["info", "success"]:
            self.notification_timer = self.root.after(5000, self.clear_notification)

        # Store this as the last notification
        self.last_notification = notification


    

            
    def clear_notification(self):
        """Clear the current notification with a fade-out effect."""
        if not hasattr(self, 'notification_frame') or not self.notification_frame.winfo_exists():
            return
            
        for widget in self.notification_frame.winfo_children():
            # Animate the removal
            def animate_out(widget, step=10):
                if step > 0:
                    try:
                        widget.place_configure(
                            relx=1.0, rely=0, anchor="ne", width=300, height=step * 5
                        )
                        self.root.after(15, lambda: animate_out(widget, step - 1))
                    except tk.TclError:
                        # Widget was destr
                        # oyed during animation
                        pass
                else:
                    try:
                        widget.destroy()
                    except tk.TclError:
                        # Widget already destroyed
                        pass

            animate_out(widget)

        if hasattr(self, 'notification_timer') and self.notification_timer:
            try:
                self.root.after_cancel(self.notification_timer)
            except ValueError:
                # Timer was already cancelled
                pass
            self.notification_timer = None

    def show_settings(self):
        """Show settings dialog."""
        # Placeholder for settings dialog
        from tkinter import messagebox
        messagebox.showinfo("Settings", "Settings dialog will be implemented soon.")
        
    def log_out(self):
        """Log out the current user and return to the login screen."""
        # Ask for confirmation
        from tkinter import messagebox
        if messagebox.askyesno("Log Out", "Are you sure you want to log out?"):
            # Clear any cached PINs from memory for security
            try:
                from nest.ui.customers import clear_pin_from_memory
                clear_pin_from_memory()
                logging.info("Cleared security PINs from memory on logout")
            except Exception as e:
                logging.warning(f"Failed to clear security PINs: {e}")
                
            # Reset user state
            self.current_user = None
            
            # Hide the main UI
            self.main_container.pack_forget()
            
            # Clear any loaded modules
            if hasattr(self, 'modules'):
                for module_name, module in self.modules.items():
                    if module and hasattr(module, 'destroy'):
                        try:
                            module.destroy()
                        except Exception as e:
                            logging.error(f"Error destroying {module_name}: {e}")
                            
            # Show the login UI again
            from nest.ui.login import LoginFrame
            self.login_frame = LoginFrame(self.root, self.on_login_success)
            self.login_frame.pack(fill="both", expand=True)
            
            # Update the window title
            
        logging.info("User logged out")

    def show_about(self):
        """Show about dialog."""
        from tkinter import messagebox

        messagebox.showinfo(
            "About Nest",
            "Nest - Computer Repair Shop Management System\n\n"
            "Version: 2.4\n"
            "© 2025 Phoenix Systems\n\n"
            "A comprehensive management system for computer repair shops.\n"
            "Features include repair tracking, inventory management, \n"
            "customer database, and AI-powered chat assistance.",
        )

    def check_updates(self):
        """Check for application updates."""
        # Simulated update check
        self.show_notification("Checking for updates...", "info")

        # Simulate network delay
        def after_check():
            self.show_notification("Your software is up to date!", "success")

        self.root.after(2000, after_check)

    def show_help(self):
        """Show help information."""
        # Try to import and show the help dialog
        try:
            from ui.help import HelpDialog

            HelpDialog(self.root)
        except ImportError:
            from tkinter import messagebox

            help_text = (
                "Welcome to Nest - Computer Repair Shop Management!\n\n"
                "Modules:\n"
                "- Dashboard: Your daily progress and shop stats overview.\n"
                "- Tickets: Create and manage repair tickets.\n"
                "- Customers: Manage customer information.\n"
                "- Inventory: Track parts and supplies.\n"
                "- Appointments: Schedule and manage appointments.\n"
                "- Reports: Generate analytics and reports.\n\n"
                "Tools:\n"
                "- PC Tools: Diagnostics and utilities for PC repairs.\n"
                "- iOS Tools: Tools for iOS device diagnostics.\n"
                "- Android Tools: Tools for Android device diagnostics.\n\n"
                "Tips:\n"
                "- Click on column headers to sort data.\n"
                "- Double-click on items for detailed information.\n"
                "- Right-click for context-specific actions.\n"
                "- For further support, contact system administrator."
            )

            messagebox.showinfo("Help & Information", help_text)

    def show_tutorials(self):
        """Show tutorials."""
        self.show_notification("Opening tutorials...", "info")
        # Placeholder - would normally open an interactive tutorial system

    def show_shortcuts(self):
        """Show keyboard shortcuts."""
        from tkinter import messagebox

        shortcuts_text = (
            "Keyboard Shortcuts\n\n"
            "General:\n"
            "Ctrl+N - New Ticket\n"
            "Ctrl+Shift+N - New Customer\n"
            "Ctrl+F - Find\n"
            "Ctrl+S - Save\n"
            "Ctrl+P - Print\n"
            "F1 - Help\n"
            "F5 - Refresh\n\n"
            "Navigation:\n"
            "Alt+1 - Dashboard\n"
            "Alt+2 - Tickets\n"
            "Alt+3 - Customers\n"
            "Alt+4 - Inventory\n"
            "Alt+5 - Appointments\n"
            "Alt+6 - Reports"
        )

        messagebox.showinfo("Keyboard Shortcuts", shortcuts_text)

    def show_error(self, message):
        """Show an error message to the user."""
        from tkinter import messagebox
        
        messagebox.showerror("Error", message)
        
        # Also show as notification
        self.show_notification(message, "error")
        
    def keyboard_shortcut_help(self):
        """Show keyboard shortcuts help dialog."""
        from tkinter import messagebox
        
        shortcuts_text = (
            "Keyboard Shortcuts\n\n"
            "General:\n"
            "Ctrl+N - New Ticket\n"
            "Ctrl+Shift+N - New Customer\n"
            "Ctrl+F - Find\n"
            "Ctrl+S - Save\n"
            "Ctrl+P - Print\n"
            "F1 - Help\n"
            "F5 - Refresh\n\n"
            "Navigation:\n"
            "Alt+1 - Dashboard\n"
            "Alt+2 - Tickets\n"
            "Alt+3 - Customers\n"
            "Alt+4 - Inventory\n"
            "Alt+5 - Appointments\n"
            "Alt+6 - Reports"
        )
        
        messagebox.showinfo("Keyboard Shortcuts", shortcuts_text)

    def show_print_dialog(self):
        """Show print dialog."""
        self.show_notification("Opening print dialog...", "info")

    def show_export_dialog(self):
        """Show export data dialog."""
        self.show_notification("Opening export dialog...", "info")

    def show_import_dialog(self):
        """Show import data dialog."""
        self.show_notification("Opening import dialog...", "info")

    def perform_edit_action(self, action):
        """Perform edit actions on the current focused widget."""
        self.show_notification(f"Performing {action} operation...", "info")

    def refresh_current_view(self):
        """Refresh the current active module."""
        if self.active_module:
            self.show_module(self.active_module)
            self.show_notification("View refreshed", "info")

    def toggle_compact_view(self):
        """Toggle between compact and regular view."""
        is_compact = self.compact_view.get()
        self.show_notification(f"Switched to {'compact' if is_compact else 'regular'} view", "info")
        # Would normally adjust the layout of the current module

    def show_search(self):
        """Show the global search dialog."""
        self.show_notification("Opening search...", "info")

    def show_hardware_diagnostics(self):
        """Show hardware diagnostics tools."""
        self.show_notification("Opening hardware diagnostics...", "info")

    def show_software_diagnostics(self):
        """Show software diagnostics tools."""
        self.show_notification("Opening software diagnostics...", "info")

    def show_network_tools(self):
        """Show network diagnostic tools."""
        self.show_notification("Opening network tools...", "info")

    def show_barcode_scanner(self):
        """Show barcode scanner interface."""
        self.show_notification("Opening barcode scanner...", "info")

    def show_serial_lookup(self):
        """Show serial number lookup tool."""
        self.show_notification("Opening serial number lookup...", "info")

    def show_report(self, report_type):
        """Show a specific type of report."""
        self.show_module("reports", report_type=report_type)

    def start(self):
        """Start the application's main event loop."""
        self.root.mainloop()


def check_dependencies_needed():
    """Check if we need to install dependencies or if they're already installed."""
    # Use environment variable as immediate check to avoid reinstall loops
    if os.environ.get("DEP_INSTALLED") == "1":
        return False  # Skip check if we've already been through the installation process
    
    # Skip dependency check if we're in a restart loop (more than 3 restarts)
    restart_count_file = os.path.join(get_script_dir(), '.restart_count')
    restart_count = 0
    if os.path.exists(restart_count_file):
        try:
            with open(restart_count_file, 'r') as f:
                restart_count = int(f.read().strip() or '0')
        except:
            restart_count = 0
    
    # If we've restarted more than 3 times, assume dependencies are installed
    # to break out of any potential infinite loops
    if restart_count >= 3:
        logging.warning("Multiple restart attempts detected. Assuming dependencies are installed.")
        # Set the environment variable to avoid checks on the next run
        os.environ["DEP_INSTALLED"] = "1"
        return False
    
    # Increment restart count
    with open(restart_count_file, 'w') as f:
        f.write(str(restart_count + 1))
    
    # Basic dependencies required for the app to function
    required_packages = [
        'tkinter', 'requests', 'Pillow', 'psutil', 'beautifulsoup4',
        'tkcalendar', 'python-dateutil'
    ]
    if platform.system().lower() == 'windows':
        required_packages.extend(['pywin32', 'WMI'])
    
    # Check if dependency marker file exists and is recent (< 1 day old)
    dep_marker = os.path.join(get_script_dir(), '.dep_check_passed')
    if os.path.exists(dep_marker):
        # Check if marker is recent (less than 24 hours old)
        if time.time() - os.path.getmtime(dep_marker) < 86400:  # 24 hours
            return False  # Dependencies recently verified, skip check
    
    # Check if all essential packages are installed
    # We'll be optimistic and only report missing if we're sure
    all_good = True
    for package in required_packages:
        if not check_module_installed(package):
            all_good = False
            break
    
    if all_good:
        # Create or update dependency marker file
        with open(dep_marker, 'w') as f:
            f.write(f"Dependencies verified on {time.ctime()}")
        # Set environment variable to avoid repeating checks in this session
        os.environ["DEP_INSTALLED"] = "1"
        return False  # All dependencies installed
    
    # If we get here, we need to install some dependencies
    return True


def main():
    """Main entry point for the application."""
    try:
        # Change working directory to the script directory
        script_dir = get_script_dir()
        os.chdir(script_dir)

        # Set up proper logging
        setup_logging()

        # Only create folders if they don't exist (minimal check)
        if not all(os.path.exists(os.path.join(script_dir, d)) for d in 
                   ['config', 'logs', 'data', 'resources']):
            create_required_folders()
        
        # Smart dependency check - only runs installer if needed
        if check_dependencies_needed():
            logging.info("Installing required dependencies...")
            if not install_tkinter():
                logging.error("Failed to install Tkinter. Exiting.")
                pause_exit()
                sys.exit(1)

            if not install_dependencies():
                logging.error("Failed to install required dependencies. Exiting.")
                pause_exit()
                sys.exit(1)

            # Restart with updated environment
            restart_script()

        logging.info("Starting Nest application...")
        
        # Initialize custom fonts
        try:
            from nest.utils.font_manager import init_fonts
            init_fonts()
            logging.info("Custom fonts initialized")
        except Exception as font_error:
            logging.warning(f"Could not initialize custom fonts: {font_error}")
            
        app = NestApp()
        app.start()

    except Exception as e:
        logging.error("Application encountered a critical error:")
        logging.exception(e)
        pause_exit()
        sys.exit(1)


if __name__ == "__main__":
    main()
