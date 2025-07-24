#!/usr/bin/env python3
"""
Styles for PC Tools Module

Provides consistent RepairDesk styling for the PC Tools module UI elements,
including colors, fonts, and component-specific styles.
"""

import tkinter as tk
from tkinter import ttk
from typing import Dict, Any

# RepairDesk brand colors
COLORS = {
    "primary": "#017E84",      # RepairDesk teal (official brand color)
    "primary_dark": "#016169", # Darker teal for hover states
    "secondary": "#4CAF50",    # Success green
    "warning": "#FF9800",      # Warning orange
    "danger": "#F44336",       # Error/danger red
    "background": "#F5F5F5",   # Light background
    "card_bg": "#FFFFFF",      # Card/panel background
    "text_primary": "#212121", # Primary text color
    "text_secondary": "#757575", # Secondary text color
    "border": "#E0E0E0",       # Border color
    "highlight": "#E6F7F7",    # Highlight color (very light teal)
    "accent": "#00B8D4"        # Accent color for special elements
}

# Font configurations
FONTS = {
    "heading": ("Segoe UI", 14, "bold"),
    "subheading": ("Segoe UI", 12, "bold"),
    "normal": ("Segoe UI", 10),
    "small": ("Segoe UI", 9),
    "monospace": ("Consolas", 10)
}

class PCToolsStyles:
    """Styles manager for PC Tools module."""
    
    def __init__(self, root=None):
        """Initialize styles for PC Tools.
        
        Args:
            root: Optional root Tk instance
        """
        self.root = root
        self.style = ttk.Style()
        self.colors = COLORS
        self.fonts = FONTS
        
        # Create styles
        self.configure_styles()
    
    def configure_styles(self):
        """Configure ttk styles for the application."""
        # Configure base theme
        self.style.theme_use("clam")
        
        # Create common element configurations to reduce duplicate style settings
        # This improves performance by reducing the number of redundant style configurations
        
        # Set up common background colors
        common_bg = self.colors["background"]
        card_bg = self.colors["card_bg"]
        primary = self.colors["primary"]
        primary_dark = self.colors["primary_dark"]
        
        # Set up common text colors
        text_primary = self.colors["text_primary"]
        text_secondary = self.colors["text_secondary"]
        
        # Configure frame styles
        self.style.configure("TFrame", background=common_bg)
        self.style.configure("Card.TFrame", background=card_bg)
        self.style.configure("Highlight.TFrame", background=self.colors["highlight"])
        
        # Configure labels with various styles
        self.style.configure("TLabel", 
                          background=common_bg,
                          foreground=text_primary,
                          font=self.fonts["normal"])
        
        # Card labels (for white card backgrounds)
        self.style.configure("Card.TLabel", background=card_bg)
        
        # Primary heading (RepairDesk teal)
        self.style.configure("Heading.TLabel",
                          font=self.fonts["heading"],
                          foreground=primary)
        
        # Secondary headings
        self.style.configure("Subheading.TLabel",
                          font=self.fonts["subheading"],
                          foreground=text_primary)
        
        # Status labels for system health indicators
        self.style.configure("Good.TLabel",
                          foreground=self.colors["secondary"])
        
        self.style.configure("Warning.TLabel",
                          foreground=self.colors["warning"])
        
        self.style.configure("Critical.TLabel",
                          foreground=self.colors["danger"])
        
        # Data source indicator style
        self.style.configure("DataSource.TLabel",
                          font=self.fonts["small"],
                          foreground=text_secondary)
        
        # Button styles - Primary RepairDesk teal button
        self.style.configure("TButton",
                          background=primary,
                          foreground="white",
                          font=self.fonts["normal"])
        
        self.style.map("TButton",
                     background=[("active", primary_dark)],
                     relief=[("pressed", "sunken")])
        
        # Secondary button style (outlined style)
        self.style.configure("Secondary.TButton",
                          background=card_bg,
                          foreground=text_primary)
        
        self.style.map("Secondary.TButton",
                     background=[("active", self.colors["border"])],
                     foreground=[("active", text_primary)])
        
        # Warning button style
        self.style.configure("Warning.TButton",
                          background=self.colors["warning"],
                          foreground="white")
        
        self.style.map("Warning.TButton",
                     background=[("active", "#E68A00")])
        
        # Danger button style
        self.style.configure("Danger.TButton",
                          background=self.colors["danger"],
                          foreground="white")
        
        self.style.map("Danger.TButton",
                     background=[("active", "#D32F2F")])
        
        # Accent button style
        self.style.configure("Accent.TButton",
                          background=self.colors["accent"],
                          foreground="white")
        
        self.style.map("Accent.TButton",
                     background=[("active", "#0095A8")])
        
        # Entry style
        self.style.configure("TEntry",
                          fieldbackground=card_bg,
                          foreground=text_primary,
                          padding=5)
        
        # Notebook style (tabs)
        self.style.configure("TNotebook", 
                          background=self.colors["background"])
        
        self.style.configure("TNotebook.Tab",
                          background=self.colors["background"],
                          foreground=self.colors["text_primary"],
                          padding=[10, 2],
                          font=self.fonts["normal"])
        
        self.style.map("TNotebook.Tab",
                     background=[("selected", self.colors["primary"])],
                     foreground=[("selected", "white")])
        
        # Progressbar styles
        self.style.configure("Horizontal.TProgressbar",
                          troughcolor=self.colors["border"],
                          background=self.colors["primary"],
                          thickness=15)
        
        self.style.configure("Success.Horizontal.TProgressbar",
                          troughcolor=self.colors["border"],
                          background=self.colors["secondary"],
                          thickness=15)
        
        self.style.configure("Warning.Horizontal.TProgressbar",
                          troughcolor=self.colors["border"],
                          background=self.colors["warning"],
                          thickness=15)
        
        self.style.configure("Danger.Horizontal.TProgressbar",
                          troughcolor=self.colors["border"],
                          background=self.colors["danger"],
                          thickness=15)
        
        # Treeview styles
        self.style.configure("Treeview",
                          background=self.colors["card_bg"],
                          foreground=self.colors["text_primary"],
                          rowheight=25,
                          fieldbackground=self.colors["card_bg"])
        
        self.style.configure("Treeview.Heading",
                          background=self.colors["primary"],
                          foreground="white",
                          font=self.fonts["normal"])
        
        self.style.map("Treeview",
                     background=[("selected", self.colors["primary"])],
                     foreground=[("selected", "white")])
        
        # LabelFrame style
        self.style.configure("TLabelframe",
                          background=self.colors["background"],
                          foreground=self.colors["text_primary"])
        
        self.style.configure("TLabelframe.Label",
                          background=self.colors["background"],
                          foreground=self.colors["primary"],
                          font=self.fonts["subheading"])
    
    def get_colors(self) -> Dict[str, str]:
        """Get color dictionary.
        
        Returns:
            Dict containing color definitions
        """
        return self.colors
    
    def get_fonts(self) -> Dict[str, tuple]:
        """Get font dictionary.
        
        Returns:
            Dict containing font definitions
        """
        return self.fonts
    
    def apply_to_widgets(self, parent):
        """Apply styles to existing widgets.
        
        Args:
            parent: Parent widget to start applying styles from
        """
        # Apply background color to all frames
        for widget in parent.winfo_children():
            widget_type = widget.winfo_class()
            
            if widget_type in ("Frame", "TFrame"):
                if hasattr(widget, "configure"):
                    widget.configure(background=self.colors["background"])
            elif widget_type in ("Label", "TLabel"):
                if hasattr(widget, "configure"):
                    widget.configure(background=self.colors["background"],
                                   foreground=self.colors["text_primary"])
            
            # Recursively apply to children
            if hasattr(widget, "winfo_children"):
                self.apply_to_widgets(widget)


# For testing
if __name__ == "__main__":
    root = tk.Tk()
    root.title("PC Tools Styles Test")
    root.geometry("800x600")
    
    # Apply styles
    styles = PCToolsStyles(root)
    
    # Test frame
    frame = ttk.Frame(root, padding=20)
    frame.pack(fill="both", expand=True)
    
    # Heading
    heading = ttk.Label(frame, text="PC Tools Style Test", style="Heading.TLabel")
    heading.pack(pady=10)
    
    # Buttons
    button_frame = ttk.Frame(frame)
    button_frame.pack(pady=10)
    
    ttk.Button(button_frame, text="Primary Button").pack(side="left", padx=5)
    ttk.Button(button_frame, text="Secondary Button", style="Secondary.TButton").pack(side="left", padx=5)
    ttk.Button(button_frame, text="Warning Button", style="Warning.TButton").pack(side="left", padx=5)
    ttk.Button(button_frame, text="Danger Button", style="Danger.TButton").pack(side="left", padx=5)
    
    # Progress bars
    progress_frame = ttk.LabelFrame(frame, text="Progress Bars")
    progress_frame.pack(fill="x", pady=10, padx=10)
    
    ttk.Progressbar(progress_frame, value=75).pack(fill="x", pady=5, padx=10)
    ttk.Progressbar(progress_frame, value=50, style="Success.Horizontal.TProgressbar").pack(fill="x", pady=5, padx=10)
    ttk.Progressbar(progress_frame, value=60, style="Warning.Horizontal.TProgressbar").pack(fill="x", pady=5, padx=10)
    ttk.Progressbar(progress_frame, value=90, style="Danger.Horizontal.TProgressbar").pack(fill="x", pady=5, padx=10)
    
    # Treeview
    tree_frame = ttk.LabelFrame(frame, text="Treeview")
    tree_frame.pack(fill="both", expand=True, pady=10, padx=10)
    
    tree = ttk.Treeview(tree_frame, columns=("Name", "Value"), show="headings")
    tree.heading("Name", text="Name")
    tree.heading("Value", text="Value")
    tree.pack(fill="both", expand=True)
    
    tree.insert("", "end", values=("Item 1", "Value 1"))
    tree.insert("", "end", values=("Item 2", "Value 2"))
    tree.insert("", "end", values=("Item 3", "Value 3"))
    
    root.mainloop()
