"""UI Styles for the Nest application."""

import tkinter as tk
from tkinter import ttk

# Default style constants
BG_COLOR = "#f9f9f9"
TEXT_COLOR = "#333333"
ACCENT_COLOR = "#2ecc71"  # RepairDesk green
BORDER_COLOR = "#dddddd"
HOVER_COLOR = "#27ae60"  # Darker green

def get_style(theme_name="default"):
    """Return style dictionary for the specified theme.
    
    Args:
        theme_name: The name of the theme to get styles for
        
    Returns:
        dict: Style dictionary containing colors and settings
    """
    styles = {
        "default": {
            "bg_color": BG_COLOR,
            "text_color": TEXT_COLOR,
            "accent_color": ACCENT_COLOR,
            "border_color": BORDER_COLOR,
            "hover_color": HOVER_COLOR,
            "font": ("Inter", 10),
            "header_font": ("Inter", 12, "bold"),
            "title_font": ("Inter", 14, "bold"),
        }
    }
    
    return styles.get(theme_name, styles["default"])
