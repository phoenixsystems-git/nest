import os
import platform
import logging
import tkinter.font as tkfont
import sys

logger = logging.getLogger(__name__)

def get_font_path():
    """Get the path to the Inter font directory"""
    # Handle both development and production environments
    if hasattr(sys, '_MEIPASS'):  # PyInstaller bundled
        base_path = sys._MEIPASS
    else:
        # Try the absolute path first
        abs_path = r"D:\Nest Development (GitHub)\Nest2.1\nest\assets\fonts\Inter"
        if os.path.exists(abs_path):
            return abs_path
        
        # Fall back to relative path resolution
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    return os.path.join(base_path, "assets", "fonts", "Inter")

def init_fonts():
    """Initialize Inter font family for application use"""
    fonts_dir = get_font_path()
    
    if not os.path.exists(fonts_dir):
        logger.warning(f"Inter font directory not found: {fonts_dir}")
        return False
    
    logger.info(f"Loading fonts from: {fonts_dir}")
    
    # Register fonts based on platform
    if platform.system() == "Windows":
        return _register_fonts_windows(fonts_dir)
    else:  # Linux or macOS
        return _register_fonts_unix(fonts_dir)

def _register_fonts_windows(fonts_dir):
    """Register Inter fonts on Windows"""
    try:
        import ctypes
        from ctypes import windll
        
        # Check for variable font files (modern Inter font distribution)
        variable_font_files = [
            "Inter-VariableFont_opsz,wght.ttf",
            "Inter-Italic-VariableFont_opsz,wght.ttf"
        ]
        
        # Check for static font files (traditional distribution)
        static_font_files = [
            "Inter-Regular.ttf",
            "Inter-Medium.ttf", 
            "Inter-SemiBold.ttf",
            "Inter-Bold.ttf"
        ]
        
        # First try variable fonts
        success_count = 0
        for font_file in variable_font_files:
            font_path = os.path.join(fonts_dir, font_file)
            if os.path.exists(font_path):
                font_path_w = ctypes.c_wchar_p(font_path)
                result = windll.gdi32.AddFontResourceW(font_path_w)
                if result > 0:
                    success_count += 1
                    logger.info(f"Registered variable font: {font_file}")
                else:
                    logger.warning(f"Failed to register variable font: {font_file}")
        
        # If variable fonts weren't found or registered, try static fonts
        if success_count == 0:
            # Check static directory if it exists
            static_dir = os.path.join(fonts_dir, "static")
            if os.path.exists(static_dir) and os.path.isdir(static_dir):
                for font_file in static_font_files:
                    font_path = os.path.join(static_dir, font_file)
                    if os.path.exists(font_path):
                        font_path_w = ctypes.c_wchar_p(font_path)
                        result = windll.gdi32.AddFontResourceW(font_path_w)
                        if result > 0:
                            success_count += 1
                            logger.info(f"Registered static font: {font_file}")
                        else:
                            logger.warning(f"Failed to register static font: {font_file}")
            
            # Fall back to looking for static fonts in the main directory
            if success_count == 0:
                for font_file in static_font_files:
                    font_path = os.path.join(fonts_dir, font_file)
                    if os.path.exists(font_path):
                        font_path_w = ctypes.c_wchar_p(font_path)
                        result = windll.gdi32.AddFontResourceW(font_path_w)
                        if result > 0:
                            success_count += 1
                            logger.info(f"Registered font: {font_file}")
                        else:
                            logger.warning(f"Failed to register font: {font_file}")
        
        # Notify Windows of font change
        windll.user32.SendMessageW(0xFFFF, 0x001D, 0, 0)  # WM_FONTCHANGE
        return success_count > 0
        
    except Exception as e:
        logger.error(f"Error registering Inter fonts on Windows: {e}")
        return False

def _register_fonts_unix(fonts_dir):
    """Register Inter fonts on Linux/Unix"""
    try:
        # User's font directory
        user_fonts_dir = os.path.expanduser("~/.local/share/fonts/Inter")
        os.makedirs(user_fonts_dir, exist_ok=True)
        
        import shutil
        success_count = 0
        
        # Check for variable font files (modern Inter font distribution)
        variable_font_files = [
            "Inter-VariableFont_opsz,wght.ttf",
            "Inter-Italic-VariableFont_opsz,wght.ttf"
        ]
        
        # Copy variable fonts if they exist
        for font_file in variable_font_files:
            src = os.path.join(fonts_dir, font_file)
            dst = os.path.join(user_fonts_dir, font_file)
            
            if os.path.exists(src):
                # Copy if not exists or is different
                if not os.path.exists(dst) or not os.path.samefile(src, dst):
                    shutil.copy2(src, dst)
                    success_count += 1
                    logger.info(f"Copied variable font to user directory: {font_file}")
        
        # If no variable fonts were found or copied, try static fonts
        if success_count == 0:
            # Traditional static font files
            static_font_files = [
                "Inter-Regular.ttf",
                "Inter-Medium.ttf", 
                "Inter-SemiBold.ttf",
                "Inter-Bold.ttf"
            ]
            
            # Check static directory if it exists
            static_dir = os.path.join(fonts_dir, "static")
            if os.path.exists(static_dir) and os.path.isdir(static_dir):
                for font_file in static_font_files:
                    src = os.path.join(static_dir, font_file)
                    dst = os.path.join(user_fonts_dir, font_file)
                    
                    if os.path.exists(src):
                        # Copy if not exists or is different
                        if not os.path.exists(dst) or not os.path.samefile(src, dst):
                            shutil.copy2(src, dst)
                            success_count += 1
                            logger.info(f"Copied static font to user directory: {font_file}")
            
            # Fall back to checking main directory for static fonts
            if success_count == 0:
                for font_file in static_font_files:
                    src = os.path.join(fonts_dir, font_file)
                    dst = os.path.join(user_fonts_dir, font_file)
                    
                    if os.path.exists(src):
                        # Copy if not exists or is different
                        if not os.path.exists(dst) or not os.path.samefile(src, dst):
                            shutil.copy2(src, dst)
                            success_count += 1
                            logger.info(f"Copied font to user directory: {font_file}")
        
        # Update font cache
        if success_count > 0:
            import subprocess
            try:
                subprocess.run(['fc-cache', '-f'], check=True)
                logger.info("Updated font cache with fc-cache")
            except (subprocess.SubprocessError, FileNotFoundError):
                logger.warning("Failed to update font cache")
        
        return success_count > 0
    
    except Exception as e:
        logger.error(f"Error registering Inter fonts on Unix: {e}")
        return False

def get_inter_font(size=10, weight="normal"):
    """Get Inter font with specified size and weight
    
    Args:
        size: Font size in points
        weight: Font weight ('normal', 'medium', 'semibold', 'bold')
        
    Returns:
        Font family and actual weight as tuple, or fallback
    """
    # Map weights to actual font families (some systems register separate families)
    weight_map = {
        "normal": ["Inter", "Inter Regular", "Inter-Regular"],
        "medium": ["Inter Medium", "Inter-Medium"],
        "semibold": ["Inter SemiBold", "Inter-SemiBold"],
        "bold": ["Inter Bold", "Inter-Bold"]
    }
    
    # Normalize weight
    if weight not in weight_map:
        weight = "normal"
    
    # Try the registered font families for this weight
    for family in weight_map[weight]:
        try:
            font = tkfont.Font(family=family, size=size)
            return (family, weight)
        except:
            pass
    
    # If specific weight fails, try generic Inter
    try:
        font = tkfont.Font(family="Inter", size=size)
        # Use Tk's weight parameter instead
        if weight == "bold" or weight == "semibold":
            return ("Inter", "bold")
        return ("Inter", "normal")
    except:
        pass
    
    # Fall back to system fonts
    fallbacks = ["Segoe UI", "Roboto", "Open Sans", "Helvetica", "Arial", "TkDefaultFont"]
    for family in fallbacks:
        try:
            font = tkfont.Font(family=family, size=size)
            if weight == "bold" or weight == "semibold":
                return (family, "bold")
            return (family, "normal")
        except:
            continue
    
    return ("TkDefaultFont", "normal")

def _patch_treeview():
    """Patch the ttk.Treeview class to force consistent styling
    
    This is a more aggressive approach to ensure all Treeview widgets use consistent fonts.
    It monkey-patches the __init__ method of ttk.Treeview to apply our styling.
    """
    try:
        import tkinter as tk
        from tkinter import ttk
        
        # Store the original __init__ method
        original_treeview_init = ttk.Treeview.__init__
        
        # Define our patched __init__ method
        def patched_treeview_init(self, master=None, **kw):
            # Call the original __init__ method
            original_treeview_init(self, master, **kw)
            
            # Force our consistent styling - smaller font size (10px)
            font_family, font_weight = get_inter_font(size=10, weight="normal")
            
            style = ttk.Style(master)
            style.configure("Treeview",
                          font=(font_family, 10, font_weight),
                          rowheight=28)
            style.configure("Treeview.Heading",
                          font=(font_family, 10, "bold"),
                          padding=(8, 4))
            
            # Apply the style to this specific instance
            try:
                self.configure(style="Treeview")
            except:
                pass  # Some options can't be changed after widget creation
        
        # Replace the original __init__ method with our patched version
        ttk.Treeview.__init__ = patched_treeview_init
        logger.info("Patched ttk.Treeview class for consistent styling")
        return True
    except Exception as e:
        logger.error(f"Failed to patch ttk.Treeview: {e}")
        return False

# Try to patch the Treeview class when this module is imported
_patch_treeview()

def enforce_global_fonts(root=None):
    """Enforce consistent fonts throughout the application
    
    This function should be called whenever a module is loaded to enforce consistent fonts
    throughout the application, especially for complex widgets like Treeview that might
    get their styling overridden.
    
    Args:
        root: The root Tk or Toplevel window (optional)
    """
    try:
        # Force Inter font where possible - using smaller 10px font
        treeview_font_family, treeview_font_weight = get_inter_font(size=10, weight="normal")
        heading_font_family, heading_font_weight = get_inter_font(size=10, weight="semibold")
        
        # Get a handle to the style object (ttk.Style)
        import tkinter as tk
        from tkinter import ttk
        style = ttk.Style(root)
        
        # Enforce treeview font and row height consistently
        style.configure("Treeview", 
                       font=(treeview_font_family, 10, treeview_font_weight),
                       rowheight=28)
                       
        # Enforce treeview headings
        style.configure("Treeview.Heading", 
                       font=(heading_font_family, 10, heading_font_weight),
                       padding=(8, 4))
        
        # Make sure sidebar styles are consistent
        sidebar_font_family, sidebar_font_weight = get_inter_font(size=11, weight="normal")
        sidebar_heading_family, sidebar_heading_weight = get_inter_font(size=11, weight="bold")
        
        # Sidebar styles
        style.configure("Sidebar.TLabel",
                       font=(sidebar_font_family, 11, sidebar_font_weight))
                       
        style.configure("SidebarHeading.TLabel",
                       font=(sidebar_heading_family, 11, sidebar_heading_weight))
                       
        style.configure("Nav.TButton",
                       font=(sidebar_font_family, 11, sidebar_font_weight))
                       
        style.configure("Brand.TLabel",
                       font=(sidebar_heading_family, 16, sidebar_heading_weight))
        
        logger.info("Enforced global font consistency")
        return True
    except Exception as e:
        logger.error(f"Error enforcing global fonts: {e}")
        return False
