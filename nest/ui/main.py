#!/usr/bin/env python
"""
Nest - Computer Repair Shop Management System

A comprehensive management system for computer repair shops that includes
ticket tracking, customer management, inventory control, appointment scheduling,
and diagnostic tools for various platforms.
"""

import os
import sys
import subprocess
import logging
import platform
import importlib
from functools import partial
from typing import Dict, List, Tuple, Callable, Optional, Any

# Configure basic logging first
logging.basicConfig(
    level=logging.DEBUG,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)

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
        importlib.import_module(module_name)
        return True
    except ImportError:
        return False


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
    """Install or check for required Python dependencies."""
    # Core dependencies required for all platforms
    core_dependencies = {
        "Pillow": "python3-pil",  # Required for image rendering
        "requests": "python3-requests",  # Network requests
        "psutil": "python3-psutil",  # System utilization monitoring
        "beautifulsoup4": "python3-bs4",  # HTML parsing
        "tkcalendar": None,  # Calendar widget for appointments (no direct apt package)
        "python-dateutil": "python3-dateutil",  # Date manipulation
    }

    # OS-specific dependencies
    os_info = get_os_info()
    system = os_info["system"]

    platform_dependencies = {}
    if "windows" in system:
        platform_dependencies = {
            "WMI": None,
            "pywin32": None,
        }  # Windows Management Instrumentation and Win32 API
    elif "linux" in system:
        platform_dependencies = {"pyudev": "python3-pyudev"}  # For hardware detection on Linux
    elif "darwin" in system:
        platform_dependencies = {"pyobjc": None}  # For macOS specific functionality

    # Combined dependencies
    all_dependencies = {**core_dependencies, **platform_dependencies}

    # First, check if we're in an externally managed environment (PEP 668)
    try:
        pip_cmd = [sys.executable, "-m", "pip", "install", "--dry-run", "pip"]
        output = subprocess.check_output(pip_cmd, stderr=subprocess.STDOUT, universal_newlines=True)
        externally_managed = False
    except subprocess.CalledProcessError as e:
        externally_managed = "externally-managed-environment" in e.output
        logging.info("Detected externally-managed Python environment")
    
    # Check and handle missing dependencies
    missing_packages = []
    for package, apt_package in all_dependencies.items():
        try:
            # Try to import the module to check if it's installed
            if package.lower() == "pillow":
                __import__("PIL")
            elif package.lower() == "beautifulsoup4":
                __import__("bs4")
            elif package.lower() == "python-dateutil":
                __import__("dateutil")
            else:
                __import__(package.split("==")[0].lower())
                
            logging.info(f"{package} is already installed.")
        except ImportError:
            missing_packages.append((package, apt_package))
    
    # If no missing packages, we're good
    if not missing_packages:
        logging.info("All dependencies are already installed.")
        return True
    
    # If we have missing packages but in an externally managed environment
    if externally_managed:
        # Suggest apt installation for Ubuntu/Debian systems
        if system == "linux":
            apt_cmds = []
            pip_cmds = []
            venv_pkgs = []
            
            for package, apt_package in missing_packages:
                if apt_package:
                    apt_cmds.append(f"sudo apt install -y {apt_package}")
                else:
                    pip_cmds.append(package)
                    venv_pkgs.append(package)
            
            message = "Your system uses an externally-managed Python environment.\n"
            
            if apt_cmds:
                message += "\nTo install required packages, run these commands:\n"
                message += "\n" + "\n".join(apt_cmds)
            
            if pip_cmds:
                message += "\n\nSome packages need to be installed using a virtual environment:"
                message += "\n1. Create a virtual environment: python3 -m venv ~/nest_venv"
                message += "\n2. Activate it: source ~/nest_venv/bin/activate"
                message += f"\n3. Install packages: pip install {' '.join(venv_pkgs)}"
                message += "\n4. Run the application from the virtual environment"
            
            logging.error(message)
            print("\n" + message + "\n")
            return False
    
    # If not externally managed or not Linux, try pip install normally
    failed_packages = []
    for package, _ in missing_packages:
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

        self.tk = tk
        self.ttk = ttk

        self.root = tk.Tk()
        self.root.title("Nest")

        # Start with a moderate-sized window for login - INCREASED HEIGHT
        self.root.geometry("280x480")  # Doubled the height as requested
        self.root.minsize(280, 480)  # Minimum size for login updated
        self.root.resizable(True, True)

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

        # Set up UI
        self.setup_style()
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")

        # Create notification area
        self.notification_var = tk.StringVar()
        self.notification_var.set("")

        # Show the login screen
        logging.info("NestApp initialized.")
        self.show_login()

    def set_app_icon(self):
        """Try to set app icon if available."""
        try:
            script_dir = get_script_dir()
            icon_path = os.path.join(script_dir, "resources", "icons", "nest_icon.ico")
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
            else:
                logging.debug("App icon not found. Using default.")
        except Exception as e:
            logging.debug(f"Could not set app icon: {e}")

    def setup_style(self):
        """Configure the application's visual style."""
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

        # Navigation button styles - LEFT ALIGNED TEXT
        style.configure(
            "Nav.TButton",
            font=("Segoe UI", 11),
            padding=(12, 12, 12, 12),
            background=self.colors["sidebar"],
            foreground=self.colors["sidebar_text"],
            borderwidth=0,
            anchor="w",  # Left align text
            justify="left",
        )  # Left justify text

        # IMPROVED HOVER EFFECT - prevent flickering
        style.map(
            "Nav.TButton",
            background=[
                ("active", self.colors["sidebar_highlight"]),
                ("hover", self.colors["sidebar_highlight"]),
            ],
            foreground=[
                ("active", self.colors["sidebar_text"]),
                ("hover", self.colors["sidebar_text"]),
            ],
            relief=[("pressed", "flat"), ("!pressed", "flat")],
        )

        # Active module style (for highlighting current module)
        style.configure(
            "Active.Nav.TButton",
            font=("Segoe UI", 11, "bold"),
            padding=(12, 12, 12, 12),
            background=self.colors["primary"],
            foreground=self.colors["sidebar_text"],
            borderwidth=0,
            anchor="w",  # Left align text
            justify="left",
        )  # Left justify text

        # Content frame style - ensure it has the light background
        style.configure("Content.TFrame", background=self.colors["content_bg"])

        # Card frame style (for panels)
        style.configure(
            "Card.TFrame", background=self.colors["card_bg"], borderwidth=1, relief="solid"
        )

        # Card header style
        style.configure("CardHeader.TFrame", background=self.colors["header_bg"], borderwidth=0)

        # Regular button style
        style.configure("TButton", padding=8, font=("Segoe UI", 10))

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

        # Primary button style
        style.configure(
            "Primary.TButton",
            background=self.colors["primary"],
            foreground="white",
            padding=10,
            font=("Segoe UI", 10),
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

        # Secondary button style
        style.configure(
            "Secondary.TButton",
            background=self.colors["secondary"],
            foreground="white",
            padding=10,
            font=("Segoe UI", 10),
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

        # Keep dark headers for the treeview but ensure the background of the cells is light
        style.configure(
            "Treeview.Heading",
            font=("Segoe UI", 10, "bold"),
            padding=6,
            background=self.colors["sidebar"],  # Dark header background
            foreground=self.colors["sidebar_text"],
        )  # Light text for contrast

        # Update the map settings to only highlight when selected, not on hover
        style.map(
            "Treeview",
            background=[
                ("selected", self.colors["primary_light"])
            ],  # Only change background when selected
            foreground=[("selected", self.colors["text_primary"])],
        )  # Only change text when selected

        # Consistent hover states for treeview headings
        style.map(
            "Treeview.Heading",
            background=[
                ("active", self.colors["sidebar_highlight"]),
                ("hover", self.colors["sidebar_highlight"]),
            ],
            foreground=[
                ("active", self.colors["sidebar_text"]),
                ("hover", self.colors["sidebar_text"]),
            ],
        )

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
        self.show_main_ui()

    def show_main_ui(self):
        """Set up the main application UI after login."""
        # Resize the window to full size for the main application
        self.root.geometry("1400x900")  # Resize to large window for main app
        self.root.minsize(800, 600)  # Update minimum size for main app

        # Clear current UI
        for widget in self.root.winfo_children():
            widget.destroy()

        # Create main container with regular tk.Frame to allow background setting
        self.main_container = self.tk.Frame(self.root, bg=self.colors["content_bg"])
        self.main_container.pack(fill="both", expand=True)

        # Create top menu bar with custom styling
        self.create_menu_bar()

        # Create main split between navigation and content
        self.nav_frame = self.ttk.Frame(self.main_container, style="Sidebar.TFrame", width=240)
        self.nav_frame.pack(side="left", fill="y", padx=0, pady=0)

        # Make nav_frame keep its width
        self.nav_frame.pack_propagate(False)

        # Create a regular tk Frame for content container to allow background settings
        self.content_container = self.tk.Frame(self.main_container, bg=self.colors["content_bg"])
        self.content_container.pack(side="right", fill="both", expand=True, padx=0, pady=0)

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
            bg=self.colors["background"],
            fg=self.colors["text_primary"],
            activebackground=self.colors["primary"],
            activeforeground="white",
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
        file_menu.add_command(label="Exit", command=self.root.quit)

        # Edit menu
        edit_menu = self.tk.Menu(
            menubar,
            tearoff=0,
            bg=self.colors["background"],
            fg=self.colors["text_primary"],
            activebackground=self.colors["primary"],
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
        # Add logo or app name - now using Brand.TLabel style with center alignment
        brand_label = self.ttk.Label(
            self.nav_frame, text="Nest App", style="Brand.TLabel"  # Use the specialized Brand style
        )
        brand_label.pack(pady=(10, 20), fill="x")

        # User info section
        if self.current_user:
            user_frame = self.ttk.Frame(self.nav_frame, style="Sidebar.TFrame")
            user_frame.pack(fill="x", padx=8, pady=5)

            username = self.current_user.get("fullname", "User")
            role = self.current_user.get("role", "Staff")

            user_label = self.ttk.Label(
                user_frame,
                text=f"{username}",
                font=("Segoe UI", 11, "bold"),
                foreground=self.colors["sidebar_text"],
                background=self.colors["sidebar"],
            )
            user_label.pack(anchor="w")

            role_label = self.ttk.Label(
                user_frame,
                text=f"Role: {role}",
                font=("Segoe UI", 9),
                foreground=self.colors["sidebar_text"],
                background=self.colors["sidebar"],
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
            ("💬 Chat with AI", "chat_ai", "Chat with AI assistant"),
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

    def create_status_bar(self):
        """Create an enhanced status bar with additional utilities."""
        status_frame = self.ttk.Frame(self.root, style="Status.TLabel")
        status_frame.pack(side="bottom", fill="x")

        # Left side: Status message
        status_label = self.ttk.Label(
            status_frame, textvariable=self.status_var, style="Status.TLabel", anchor="w"
        )
        status_label.pack(side="left", padx=10, fill="y")

        # Right side: additional status indicators
        indicators_frame = self.ttk.Frame(status_frame, style="Status.TLabel")
        indicators_frame.pack(side="right", fill="y")

        # Pending tickets indicator
        self.pending_tickets_var = self.tk.StringVar()
        self.pending_tickets_var.set("Pending: 12")

        pending_tickets_label = self.ttk.Label(
            indicators_frame, textvariable=self.pending_tickets_var, style="Status.TLabel"
        )
        pending_tickets_label.pack(side="left", padx=10, fill="y")

        # Today's appointments
        self.appointments_var = self.tk.StringVar()
        self.appointments_var.set("Today's Appts: 5")

        appointments_label = self.ttk.Label(
            indicators_frame, textvariable=self.appointments_var, style="Status.TLabel"
        )
        appointments_label.pack(side="left", padx=10, fill="y")

        # User indicator
        if self.current_user:
            username = self.current_user.get("fullname", "User")
            user_var = self.tk.StringVar()
            user_var.set(f"User: {username}")

            user_label = self.ttk.Label(
                indicators_frame, textvariable=user_var, style="Status.TLabel"
            )
            user_label.pack(side="left", padx=10, fill="y")

        # Current date and time - moved to be part of the right-side indicators
        # This way it will be at the far right of the status bar
        self.datetime_var = self.tk.StringVar()
        self.datetime_var.set("2025-04-19 05:45:02")

        datetime_label = self.ttk.Label(
            indicators_frame,  # Now part of indicators_frame instead of status_frame
            textvariable=self.datetime_var,
            style="Status.TLabel",
        )
        datetime_label.pack(
            side="left", padx=10, fill="y"
        )  # Left aligned in indicators (which is right aligned overall)

        # Update time periodically
        self.update_time()

    def update_time(self):
        """Update the time display in the status bar."""
        from datetime import datetime

        # Update time
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.datetime_var.set(current_time)

        # Schedule next update
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
        # Clear current content
        for widget in self.content_frame.winfo_children():
            widget.destroy()

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
            elif module_name == "chat_ai":
                from nest.ui.chat_ai import ChatAIModule

                module = ChatAIModule(self.content_frame, current_user=self.current_user)
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

            logging.info(f"Loaded module: {module_name}")

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
        # Clear existing notification if any
        for widget in self.notification_frame.winfo_children():
            widget.destroy()

        if self.notification_timer:
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
            command=lambda: self.clear_notification(),
        )
        close_btn.pack(side="right", padx=5, pady=5)

        # Make the notification appear with a fade-in effect
        def animate_in(step=0):
            if step < 10:
                notification.place_configure(
                    relx=1.0, rely=0, anchor="ne", width=300, height=step * 5
                )
                self.root.after(15, lambda: animate_in(step + 1))

        # Start animation
        animate_in()

        # Auto-dismiss after 5 seconds for info and success messages
        if message_type in ["info", "success"]:
            self.notification_timer = self.root.after(5000, self.clear_notification)

        # Store this as the last notification
        self.last_notification = notification

    def clear_notification(self):
        """Clear the current notification with a fade-out effect."""
        for widget in self.notification_frame.winfo_children():
            # Animate the removal
            def animate_out(widget, step=10):
                if step > 0:
                    widget.place_configure(
                        relx=1.0, rely=0, anchor="ne", width=300, height=step * 5
                    )
                    self.root.after(15, lambda: animate_out(widget, step - 1))
                else:
                    widget.destroy()

            animate_out(widget)

        if self.notification_timer:
            self.root.after_cancel(self.notification_timer)
            self.notification_timer = None

    def show_settings(self):
        """Show application settings dialog."""
        # Try to import and show the settings dialog
        try:
            from nest.ui.settings import SettingsDialog

            SettingsDialog(self.root, self)
        except ImportError:
            from tkinter import messagebox

            messagebox.showinfo("Settings", "Settings dialog is not implemented yet.")

    def show_documentation(self):
        """Show application documentation."""
        from tkinter import messagebox

        messagebox.showinfo("Documentation", "Documentation is not implemented yet.")

    def show_about(self):
        """Show about dialog."""
        from tkinter import messagebox

        messagebox.showinfo(
            "About Nest",
            "Nest - Computer Repair Shop Management System\n\n"
            "Version: 1.0.0\n"
            " 2025 Your Company\n\n"
            "A comprehensive management system for computer repair shops.",
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
            from nest.ui.help import HelpDialog

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

    def log_out(self):
        """Log out the current user and return to the login screen."""
        logging.info(f"User '{self.current_user.get('fullname', 'unknown')}' logged out")
        self.current_user = None

        # Resize window back to login size - now taller
        self.root.geometry("280x480")
        self.root.minsize(280, 480)

        # Show login screen
        self.show_login()

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
    """Check if dependency installation is needed."""
    # Skip dependency check if we've explicitly set the environment variable
    if os.environ.get("DEP_INSTALLED") == "1":
        return False
        
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
    required_packages = {
        'tkinter': None,  # Built into Python, no separate import needed
        'requests': 'requests',
        'PIL': 'Pillow',  # PIL is the import name for Pillow
        'psutil': 'psutil',
        'bs4': 'beautifulsoup4',  # bs4 is the import name for beautifulsoup4
        'tkcalendar': 'tkcalendar',
        'dateutil': 'python-dateutil'  # dateutil is the import name for python-dateutil
    }
    
    if platform.system().lower() == 'windows':
        required_packages.update({
            'win32com': 'pywin32',  # win32com is part of pywin32
            'wmi': 'WMI'
        })
    elif platform.system().lower() == 'linux':
        required_packages.update({
            'pyudev': 'pyudev'
        })
    
    # Check if dependency marker file exists and is recent (< 1 day old)
    dep_marker = os.path.join(get_script_dir(), '.dep_check_passed')
    if os.path.exists(dep_marker):
        # Check if marker is recent (less than 24 hours old)
        if time.time() - os.path.getmtime(dep_marker) < 86400:  # 24 hours
            return False  # Dependencies recently verified, skip check
    
    # Check essential packages by attempting to import them
    missing_packages = []
    for import_name, package_name in required_packages.items():
        if import_name == 'tkinter':
            # Special case for tkinter which is built into Python
            if not check_module_installed('tkinter'):
                missing_packages.append(package_name or import_name)
            continue
            
        try:
            __import__(import_name)
        except ImportError:
            missing_packages.append(package_name or import_name)
    
    if not missing_packages:
        # Create or update dependency marker file
        with open(dep_marker, 'w') as f:
            f.write(f"Dependencies verified on {time.ctime()}")
        # Set environment variable to avoid repeating checks in this session
        os.environ["DEP_INSTALLED"] = "1"
        return False  # All dependencies installed
    
    logging.info(f"Missing packages detected: {', '.join(missing_packages)}")
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

        # Create required folders
        create_required_folders()

        # Check if dependencies are already installed
        if os.environ.get("DEP_INSTALLED") is None:
            # First check for tkinter which is special
            if not check_module_installed('tkinter'):
                logging.info("Installing Tkinter...")
                if not install_tkinter():
                    logging.error("Failed to install Tkinter. Exiting.")
                    pause_exit()
                    sys.exit(1)
                    
            # Then check for other dependencies
            if check_dependencies_needed():
                logging.info("Checking required dependencies...")
                
                if not install_dependencies():
                    # install_dependencies will display appropriate messages
                    # for externally-managed environments
                    pause_exit()
                    sys.exit(1)

                # Restart with updated environment
                restart_script()

        logging.info("Starting Nest application...")
        app = NestApp()
        app.start()

    except Exception as e:
        logging.error("Application encountered a critical error:")
        logging.exception(e)
        pause_exit()
        sys.exit(1)


if __name__ == "__main__":
    main()
