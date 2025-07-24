import tkinter as tk
from tkinter import ttk
from tkinter import font as tkfont
from nest.utils.font_manager import init_fonts, get_inter_font
import logging

logger = logging.getLogger(__name__)

def apply_styles(root):
    """Apply RepairDesk-branded styles with Inter font"""
    # Initialize Inter fonts
    init_fonts()
    
    style = ttk.Style(root)
    
    # RepairDesk brand colors
    repairdesk_colors = {
        "primary_green": "#0B614B",     # Main brand teal green
        "dark_green": "#095140",        # Darker teal for hover states
        "light_green": "#18a383",       # Lighter teal accent
        "accent_green": "#7BBCB0",      # Very light teal accent
        "button_green": "#18A88C",      # Website button green
        "bg_color": "#f9f9f9",          # Light background
        "white": "#FFFFFF",             # Pure white
        "text_dark": "#333333",         # Dark text
        "text_light": "#FFFFFF",        # Light text
        "text_secondary": "#757575",    # Secondary text
        "border": "#e0e0e0",            # Light border
        "warning": "#ff9800",           # Orange for warnings
        "error": "#e74c3c",             # Red for errors
        "success": "#18A88C",           # Green for success messages
        "info": "#3498db",              # Blue for info messages
        
        # Backward compatibility mappings
        "primary": "#0B614B",
        "primary_light": "#18a383",
        "primary_dark": "#095140",
        "secondary": "#3498db",
        "secondary_light": "#bbdefb",
        "secondary_dark": "#1976d2",
        "header_bg": "#0B614B",
        "footer_bg": "#f0f0f0",
        "heading_text": "#0B614B",
        "button_bg": "#0B614B", 
        "button_fg": "#FFFFFF",
        "hover_bg": "#18a383",
        "hover": "#18a383",
        "background": "#f9f9f9",
        "content_bg": "#ffffff",
        "card_bg": "#FFFFFF",
        "text_primary": "#333333",
        "sidebar": "#0B614B",
        "sidebar_highlight": "#18a383",
        "sidebar_text": "#FFFFFF",
        "login_button": "#0B614B",
    }
    
    # Initialize Inter font combinations
    fonts = {
        "default": get_inter_font(size=12, weight="normal"),  # Increased from 10 to 12
        "medium": get_inter_font(size=12, weight="medium"),    # Increased from 10 to 12
        "semibold": get_inter_font(size=12, weight="semibold"),  # Increased from 10 to 12
        "bold": get_inter_font(size=12, weight="bold"),      # Increased from 10 to 12
        "heading": get_inter_font(size=14, weight="semibold"),  # Increased from 12 to 14
        "title": get_inter_font(size=16, weight="bold"),      # Increased from 14 to 16
        "small": get_inter_font(size=11, weight="normal"),     # Increased from 9 to 11
    }
    
    logger.info(f"Using font: {fonts['default'][0]} for default text")
    
    # Configure the root background
    if root:
        # Check if this is a ttk widget or a regular tk widget
        if isinstance(root, ttk.Widget):
            # For ttk widgets, use the style system
            style.configure(f"{root.winfo_class()}.TFrame", background=repairdesk_colors["bg_color"])
        else:
            # For regular tk widgets, we can set background directly
            root.configure(background=repairdesk_colors["bg_color"])
    
    # Base styles with Inter font
    style.configure(".", 
                   font=(fonts['default'][0], 12, fonts['default'][1]),
                   background=repairdesk_colors["bg_color"])
    
    style.configure("TFrame", background=repairdesk_colors["bg_color"])
    
    style.configure("TLabel", 
                   background=repairdesk_colors["bg_color"],
                   font=(fonts['default'][0], 12, fonts['default'][1]))
    
    # Create custom dialog styles
    style.configure("Dialog.TFrame", background=repairdesk_colors["white"])
    
    # MessageBox dialog styles for better appearance
    style.configure("TMessageBox", background=repairdesk_colors["white"])
    
    # Fix dialog buttons styling - critical for messagebox buttons
    style.configure('Dialog.TButton', 
                   font=(fonts['medium'][0], 11),
                   padding=(15, 8),
                   background=repairdesk_colors["button_green"],
                   foreground=repairdesk_colors["white"],
                   width=8)
    
    # Override Tkinter's default button styling for message boxes
    root.option_add('*Dialog.msg.font', (fonts['medium'][0], 12))
    root.option_add('*Dialog.msg.wrapLength', '6i')
    root.option_add('*Dialog.msg.background', repairdesk_colors["white"])
    root.option_add('*Dialog.msg.foreground', repairdesk_colors["text_dark"])
    
    # TK dialog buttons (applies to message boxes)
    root.option_add('*Dialog.default.width', 8)  # Ensure minimum width
    root.option_add('*Dialog.default.background', repairdesk_colors["button_green"])
    root.option_add('*Dialog.default.foreground', repairdesk_colors["white"])
    root.option_add('*Dialog.default.font', (fonts['medium'][0], 11))
    root.option_add('*Dialog.default.padX', 15)
    root.option_add('*Dialog.default.padY', 8)
    
    # Card style for content areas
    style.configure("Card.TFrame", background=repairdesk_colors["white"])
    
    # Table styles with Inter font
    style.configure("Treeview", 
                    font=(fonts['default'][0], 11),  # Reduced from 12 to a more balanced 11
                    background=repairdesk_colors["white"],
                    fieldbackground=repairdesk_colors["white"], 
                    rowheight=30,  # Adjusted back to 30 for the smaller font
                    borderwidth=0)  # Remove default border for cleaner look

    style.configure("Treeview.Heading", 
                    font=(fonts['semibold'][0], 11, fonts['semibold'][1]),  # Reduced to match treeview
                    background=repairdesk_colors["primary_green"],  # Match sidebar color
                    foreground=repairdesk_colors["white"],          # White text for better contrast
                    relief="flat",
                    padding=(8, 5),  # Adjusted padding for better balance
                    borderwidth=0)  # Remove border for modern clean look
    
    # Sidebar styles - ensure consistent Inter font across all modules
    sidebar_font_family, sidebar_font_weight = get_inter_font(size=11, weight="normal")
    sidebar_heading_family, sidebar_heading_weight = get_inter_font(size=11, weight="bold")
    
    # Create sidebar styles using Inter font
    style.configure("Sidebar.TFrame",
                    background=repairdesk_colors["sidebar"])
                    
    style.configure("Sidebar.TLabel",
                    font=(sidebar_font_family, 11, sidebar_font_weight),
                    background=repairdesk_colors["sidebar"],
                    foreground=repairdesk_colors["sidebar_text"])
                    
    style.configure("SidebarHeading.TLabel",
                    font=(sidebar_heading_family, 11, sidebar_heading_weight),
                    background=repairdesk_colors["sidebar"],
                    foreground=repairdesk_colors["sidebar_text"])
    
    style.configure("Nav.TButton",
                    font=(sidebar_font_family, 11, sidebar_font_weight),
                    background=repairdesk_colors["sidebar"],
                    foreground=repairdesk_colors["sidebar_text"],
                    padding=(10, 8),
                    relief="flat")
                    
    style.map("Nav.TButton",
             background=[('active', repairdesk_colors["sidebar_highlight"])],
             foreground=[('active', repairdesk_colors["sidebar_text"])])
                    
    style.configure("Brand.TLabel",
                    font=(sidebar_heading_family, 16, sidebar_heading_weight),
                    background=repairdesk_colors["sidebar"],
                    foreground=repairdesk_colors["sidebar_text"])
    
    # Custom tags for alternating row colors
    style.map("Treeview", 
              background=[("selected", repairdesk_colors["light_green"]),  # Selection
                           ("alternate", "#f5f5f5"),                        # Alternate rows
                           ("hover", "#f0f7f4")],                          # Hover effect (light green tint)
              foreground=[("selected", repairdesk_colors["white"])])      # White text on selection
    
    # Create custom tags for different row types
    style._treeview_alternate_color = "#f5f5f5"  # Very light gray for alternate rows
    style._treeview_hover_color = "#f0f7f4"      # Very light green tint for hover
    
    # Form input styles to match website login form
    style.configure("TEntry", 
                    padding=8, 
                    relief="solid", 
                    borderwidth=1, 
                    background="white",
                    fieldbackground="white")
    style.configure("TCombobox", padding=8)
    
    # Button styles with RepairDesk teal
    style.configure("TButton", 
                    background=repairdesk_colors["primary_green"], 
                    foreground=repairdesk_colors["text_light"],
                    borderwidth=0,
                    focusthickness=0,
                    padding=(12, 8),
                    font=(fonts['medium'][0], 10, fonts['medium'][1]))
    style.map("TButton", 
              background=[("active", repairdesk_colors["dark_green"]), 
                          ("disabled", "#cccccc")],
              foreground=[("disabled", "#999999")])
    
    # Primary action button - like the Login button
    style.configure("Primary.TButton", 
                    background=repairdesk_colors["primary_green"], 
                    foreground=repairdesk_colors["text_light"],
                    font=(fonts['semibold'][0], 10, fonts['semibold'][1]))
    style.map("Primary.TButton",
              background=[("active", repairdesk_colors["dark_green"]), 
                          ("disabled", "#cccccc")])
    
    # Green accent button - like the "Learn more" button
    style.configure("Accent.TButton", 
                    background=repairdesk_colors["button_green"], 
                    foreground=repairdesk_colors["text_light"],
                    padding=(15, 8),
                    font=(fonts['medium'][0], 10, fonts['medium'][1]))
    style.map("Accent.TButton",
              background=[("active", repairdesk_colors["light_green"]), 
                          ("disabled", "#cccccc")])
    
    # Secondary button (outline style)
    style.configure("Secondary.TButton",
                    background=repairdesk_colors["bg_color"],
                    foreground=repairdesk_colors["primary_green"],
                    borderwidth=1,
                    relief="solid")
    style.map("Secondary.TButton",
              background=[("active", "#f0f0f0")],
              foreground=[("active", repairdesk_colors["dark_green"])])
    
    # Configure the sidebar style with RepairDesk teal
    style.configure("Sidebar.TFrame",
                    background=repairdesk_colors["sidebar"])
                    
    # Configure navigation buttons in the sidebar
    style.configure("Nav.TButton",
                    background=repairdesk_colors["sidebar"],
                    foreground=repairdesk_colors["sidebar_text"],
                    font=("Segoe UI", 10),
                    anchor="w",
                    padding=(15, 10),
                    relief="flat",
                    borderwidth=0)
    style.map("Nav.TButton",
              background=[("active", repairdesk_colors["sidebar_highlight"])],
              foreground=[("active", "white")])
              
    # Style for active navigation button
    style.configure("Active.Nav.TButton",
                    background=repairdesk_colors["sidebar_highlight"],
                    foreground="white",
                    font=("Segoe UI", 10, "bold"),
                    anchor="w",
                    padding=(15, 10),
                    relief="flat",
                    borderwidth=0)
    
    # Section styles (to be applied to Labelframes)
    style.configure("TLabelframe", 
                    background=repairdesk_colors["white"],
                    borderwidth=1,
                    relief="solid")
    style.configure("TLabelframe.Label", 
                    background=repairdesk_colors["white"],
                    foreground=repairdesk_colors["primary_green"],
                    font=(fonts['heading'][0], 12, fonts['heading'][1]))
    
    # Header Style - teal background with white text
    style.configure("Header.TFrame", 
                    background=repairdesk_colors["header_bg"])
    style.configure("Header.TLabel", 
                    background=repairdesk_colors["header_bg"],
                    foreground=repairdesk_colors["white"],
                    font=(fonts['semibold'][0], 12, fonts['semibold'][1]))
    
    # Notebook styles for tabs
    style.configure("TNotebook", background=repairdesk_colors["bg_color"])
    style.configure("TNotebook.Tab", 
                    background=repairdesk_colors["bg_color"],
                    padding=(10, 5))
    style.map("TNotebook.Tab",
              background=[("selected", repairdesk_colors["primary_green"])],
              foreground=[("selected", repairdesk_colors["text_light"])])
    
    # Status styles - will be applied to labels with specific tags
    status_styles = {
        "waiting": {"background": "#fff4de", "foreground": "#ff9800", "padding": (4, 2)},
        "pending": {"background": "#e8f4fd", "foreground": "#3498db", "padding": (4, 2)},
        "in_progress": {"background": "#e1f5fe", "foreground": "#0288d1", "padding": (4, 2)},
        "completed": {"background": "#e8f5e9", "foreground": repairdesk_colors["primary_green"], "padding": (4, 2)},
        "cancelled": {"background": "#fafafa", "foreground": "#9e9e9e", "padding": (4, 2)}
    }
    
    # Login form styles
    style.configure("Login.TFrame", background="white", relief="solid", borderwidth=1)
    style.configure("Login.TLabel", 
                    background="white", 
                    foreground="#333333",
                    font=(fonts['default'][0], 10, fonts['default'][1]))
    style.configure("Login.TButton", 
                   background=repairdesk_colors["login_button"],
                   foreground="white",
                   font=(fonts['semibold'][0], 11, fonts['semibold'][1]),
                   padding=(20, 8))
    
    return {
        "colors": repairdesk_colors,
        "fonts": {
            "family": fonts['default'][0],
            "default": (fonts['default'][0], 10, fonts['default'][1]),
            "medium": (fonts['medium'][0], 10, fonts['medium'][1]),
            "semibold": (fonts['semibold'][0], 10, fonts['semibold'][1]),
            "bold": (fonts['bold'][0], 10, fonts['bold'][1]),
            "heading": (fonts['heading'][0], 12, fonts['heading'][1]),
            "title": (fonts['title'][0], 14, fonts['title'][1]),
            "small": (fonts['small'][0], 9, fonts['small'][1])
        },
        "status_styles": status_styles
    }


def create_status_label(parent, status, text=None):
    """Create a styled status label with rounded corners effect"""
    if text is None:
        text = status.replace('_', ' ').title()
        
    # Create a frame with specific background color for the status
    status_styles = {
        "waiting": {"bg": "#fff4de", "fg": "#ff9800"},
        "pending": {"bg": "#e8f4fd", "fg": "#2196f3"},
        "in_progress": {"bg": "#e1f5fe", "fg": "#0288d1"},
        "completed": {"bg": "#e8f5e9", "fg": "#18a383"},  # Updated to match RepairDesk teal
        "cancelled": {"bg": "#fafafa", "fg": "#9e9e9e"}
    }
    
    style = status_styles.get(status.lower(), {"bg": "#f5f5f5", "fg": "#757575"})
    
    # Create the label with appropriate styling
    frame = tk.Frame(parent, bg=style["bg"], padx=8, pady=2)
    
    # Get Inter font in medium weight for the status badge
    font_family, weight = get_inter_font(size=9, weight="medium")
    
    label = tk.Label(frame, text=text, bg=style["bg"], fg=style["fg"], 
                    font=(font_family, 9, weight))
    label.pack()
    
    return frame


def create_login_form(parent):
    """Create a styled login form that matches the RepairDesk website"""
    # Create a white card for the login form
    login_frame = ttk.Frame(parent, style="Login.TFrame", padding=20)
    
    # Add the RepairDesk logo
    logo_label = ttk.Label(login_frame, text="RepairDesk", 
                         font=(get_font_family(), 22, "bold"),
                         foreground="#0B614B",
                         background="white")
    logo_label.pack(pady=(0, 20), anchor="w")
    
    # Welcome text
    welcome_label = ttk.Label(login_frame, text="Welcome Back!",
                            font=(get_font_family(), 20, "bold"),
                            background="white",
                            foreground="#333333")
    welcome_label.pack(pady=(0, 5), anchor="w")
    
    please_login = ttk.Label(login_frame, text="Please login to your account.",
                           background="white",
                           foreground="#666666",
                           font=(get_font_family(), 10))
    please_login.pack(pady=(0, 20), anchor="w")
    
    # Email field
    email_label = ttk.Label(login_frame, text="Email", 
                          background="white",
                          foreground="#333333",
                          font=(get_font_family(), 10))
    email_label.pack(anchor="w", pady=(0, 5))
    
    email_entry = ttk.Entry(login_frame, width=40)
    email_entry.pack(fill="x", pady=(0, 15))
    
    # Password field
    password_label = ttk.Label(login_frame, text="Password", 
                             background="white",
                             foreground="#333333", 
                             font=(get_font_family(), 10))
    password_label.pack(anchor="w", pady=(0, 5))
    
    password_entry = ttk.Entry(login_frame, width=40, show="*")
    password_entry.pack(fill="x", pady=(0, 10))
    
    # Show password checkbox and forgot password
    options_frame = ttk.Frame(login_frame, style="Login.TFrame")
    options_frame.pack(fill="x", pady=(0, 15))
    
    show_var = tk.BooleanVar()
    show_check = ttk.Checkbutton(options_frame, text="Show password", 
                               variable=show_var, 
                               style="Login.TCheckbutton")
    show_check.pack(side="left")
    
    forgot_link = ttk.Label(options_frame, text="Forgot your password?",
                          foreground="#0B614B",
                          background="white",
                          cursor="hand2",
                          font=(get_font_family(), 10))
    forgot_link.pack(side="right")
    
    # Login button
    login_button = ttk.Button(login_frame, text="Login", 
                             style="Login.TButton",
                             width=15)
    login_button.pack(pady=(5, 15))
    
    # Sign up link
    signup_frame = ttk.Frame(login_frame, style="Login.TFrame")
    signup_frame.pack()
    
    no_account = ttk.Label(signup_frame, text="Don't have an account? ",
                          background="white",
                          foreground="#666666",
                          font=(get_font_family(), 10))
    no_account.pack(side="left")
    
    signup_link = ttk.Label(signup_frame, text="SignUp",
                          foreground="#0B614B",
                          background="white",
                          cursor="hand2",
                          font=(get_font_family(), 10))
    signup_link.pack(side="left")
    
    return login_frame