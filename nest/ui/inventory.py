import tkinter as tk
from tkinter import ttk, messagebox, StringVar
import logging
import threading
import os
from datetime import datetime
from typing import Dict, List, Optional, Any

# Import the RepairDesk API client
from ..utils.repairdesk_api import RepairDeskAPI
from ..utils.ui_threading import ThreadSafeUIUpdater
from nest.main import FixedHeaderTreeview

logger = logging.getLogger(__name__)


class InventoryModule(ttk.Frame):
    """Inventory management module that integrates with RepairDesk API."""
    
    def __init__(self, parent, current_user=None):
        super().__init__(parent, padding=10)
        self.parent = parent
        self.current_user = current_user
        
        # Initialize API client
        self.api_client = RepairDeskAPI()
        
        # Inventory data storage
        self.inventory_items = []
        self.filtered_items = []
        self.current_page = 1
        self.items_per_page = 20
        self.total_pages = 1
        
        # UI state variables
        self.search_var = StringVar()
        self.category_var = StringVar(value="All Categories")
        self.status_var = StringVar(value="All")
        self.type_var = StringVar(value="All Types")
        self.sort_by_var = StringVar(value="name_asc")
        
        # Store active tooltips
        self.tooltips = {}
        
        # Create the UI components
        self.create_widgets()
        
        # Load inventory data
        self.load_inventory()

    def create_widgets(self):
        """Create the UI components for the inventory module."""
        # Create main layout frames
        self.create_header_frame()
        self.create_filters_frame()
        self.create_inventory_table()
        self.create_pagination_controls()
        self.create_status_bar()
        
        # Initial setup
        self.search_var.trace_add("write", self.on_search_changed)
        
    def create_header_frame(self):
        """Create the header with title and action buttons."""
        header_frame = ttk.Frame(self)
        header_frame.pack(fill="x", pady=(0, 10))
        
        # Title with icon
        title_frame = ttk.Frame(header_frame)
        title_frame.pack(side="left")
        
        title_label = ttk.Label(
            title_frame, 
            text="Inventory Management", 
            style="Header.TLabel"
        )
        title_label.pack(side="left", pady=5)
        
        subtitle_label = ttk.Label(
            title_frame,
            text="Manage parts and supplies from RepairDesk",
            style="Subtitle.TLabel"
        )
        subtitle_label.pack(side="left", padx=(10, 0), pady=7)
        
        # Cache status indicator
        self.cache_status_var = StringVar(value="")
        self.cache_status_label = ttk.Label(
            title_frame,
            textvariable=self.cache_status_var,
            style="SmallNote.TLabel",
            foreground="#5c6bc0"  # Light blue-purple for cache indicator
        )
        self.cache_status_label.pack(side="left", padx=(10, 0), pady=7)
        
        # Action buttons
        btn_frame = ttk.Frame(header_frame)
        btn_frame.pack(side="right")
        
        # Add cache toggle option
        self.use_cache_var = tk.BooleanVar(value=True)
        cache_check = ttk.Checkbutton(
            btn_frame,
            text="Use cache",
            variable=self.use_cache_var,
            style="Switch.TCheckbutton"
        )
        cache_check.pack(side="left", padx=5)
        
        # Add tooltip explaining cache behavior
        self.create_tooltip(cache_check, "When enabled, inventory data will be cached for 15 minutes to improve performance.")
        
        refresh_btn = ttk.Button(
            btn_frame, 
            text="↻ Refresh",
            command=self.refresh_inventory
        )
        refresh_btn.pack(side="left", padx=5)
    
    def create_filters_frame(self):
        """Create filters and search controls."""
        filters_frame = ttk.Frame(self, style="Card.TFrame")
        filters_frame.pack(fill="x", pady=10)
        
        # Add inner padding
        inner_frame = ttk.Frame(filters_frame, padding=10)
        inner_frame.pack(fill="x")
        
        # Search box
        search_frame = ttk.Frame(inner_frame)
        search_frame.pack(side="left", fill="x", expand=True)
        
        search_label = ttk.Label(
            search_frame, 
            text="Search:", 
            style="FormLabel.TLabel"
        )
        search_label.pack(side="left", padx=(0, 5))
        
        search_entry = ttk.Entry(
            search_frame, 
            textvariable=self.search_var,
            width=25
        )
        search_entry.pack(side="left", fill="x", expand=True)
        
        # Filter dropdowns
        filter_frame = ttk.Frame(inner_frame)
        filter_frame.pack(side="right")
        
        # Category filter
        ttk.Label(
            filter_frame, 
            text="Category:", 
            style="FormLabel.TLabel"
        ).pack(side="left", padx=(10, 5))
        
        category_combo = ttk.Combobox(
            filter_frame, 
            textvariable=self.category_var,
            width=15,
            state="readonly"
        )
        category_combo.pack(side="left", padx=(0, 10))
        category_combo["values"] = ["All Categories"]
        category_combo.current(0)
        category_combo.bind("<<ComboboxSelected>>", self.apply_filters)
        
        # Type filter
        ttk.Label(
            filter_frame, 
            text="Type:", 
            style="FormLabel.TLabel"
        ).pack(side="left", padx=(0, 5))
        
        type_combo = ttk.Combobox(
            filter_frame, 
            textvariable=self.type_var,
            width=15,
            state="readonly"
        )
        type_combo.pack(side="left", padx=(0, 10))
        type_combo["values"] = ["All Types", "Product", "Service"]
        type_combo.current(0)
        type_combo.bind("<<ComboboxSelected>>", self.apply_filters)
        
        # Stock Status filter
        ttk.Label(
            filter_frame, 
            text="Status:", 
            style="FormLabel.TLabel"
        ).pack(side="left", padx=(0, 5))
        
        status_combo = ttk.Combobox(
            filter_frame, 
            textvariable=self.status_var,
            width=15,
            state="readonly"
        )
        status_combo.pack(side="left")
        status_combo["values"] = ["All", "In Stock", "Low Stock", "Out of Stock"]
        status_combo.current(0)
        status_combo.bind("<<ComboboxSelected>>", self.apply_filters)
        
    def create_inventory_table(self):
        """Create the inventory table display."""
        table_frame = ttk.Frame(self)
        table_frame.pack(fill="both", expand=True, pady=10)
        
        # Create treeview with scrollbars
        tree_scroll_y = ttk.Scrollbar(table_frame)
        tree_scroll_y.pack(side="right", fill="y")
        
        tree_scroll_x = ttk.Scrollbar(table_frame, orient="horizontal")
        tree_scroll_x.pack(side="bottom", fill="x")
        
        # Configure columns
        columns = ("id", "name", "quantity", "price", "category")
        self.inventory_tree = FixedHeaderTreeview(
            table_frame, 
            columns=columns,
            yscrollcommand=tree_scroll_y.set,
            xscrollcommand=tree_scroll_x.set,
            height=15
        )
        
        # Configure scrollbars
        tree_scroll_y.config(command=self.inventory_tree.yview)
        tree_scroll_x.config(command=self.inventory_tree.xview)
        
        # Configure column headings
        self.inventory_tree.heading("#0", text="", anchor="w")
        self.inventory_tree.heading("id", text="ID", anchor="w")
        self.inventory_tree.heading("name", text="Item Name", anchor="w")
        self.inventory_tree.heading("quantity", text="Quantity", anchor="e")
        self.inventory_tree.heading("price", text="Price", anchor="e")
        self.inventory_tree.heading("category", text="Category", anchor="w")
        
        # Configure column widths
        self.inventory_tree.column("#0", width=0, stretch=False)
        self.inventory_tree.column("id", width=80, stretch=False)
        self.inventory_tree.column("name", width=300, stretch=True)
        self.inventory_tree.column("quantity", width=100, stretch=False)
        self.inventory_tree.column("price", width=100, stretch=False)
        self.inventory_tree.column("category", width=150, stretch=False)
        
        # Set up sorting
        for col in columns:
            self.inventory_tree.heading(col, command=lambda _col=col: self.sort_column(_col))
        
        # Add double-click event to view details
        self.inventory_tree.bind("<Double-1>", self.view_item_details)
        
        # Configure tags for different item states
        self.inventory_tree.tag_configure('loading', background='#f5f5f5')
        self.inventory_tree.tag_configure('out_of_stock', background='#ffebee')  # Light red
        self.inventory_tree.tag_configure('low_stock', background='#fff8e1')    # Light yellow
        self.inventory_tree.tag_configure('in_stock', background='#f1f8e9')     # Light green
        
        self.inventory_tree.pack(fill="both", expand=True)
    
    def create_pagination_controls(self):
        """Create pagination controls."""
        pagination_frame = ttk.Frame(self)
        pagination_frame.pack(fill="x", pady=(5, 10))
        
        # Page navigation buttons
        nav_frame = ttk.Frame(pagination_frame)
        nav_frame.pack(side="left")
        
        self.first_page_btn = ttk.Button(
            nav_frame, 
            text="⟨⟨",
            width=3,
            command=self.go_to_first_page
        )
        self.first_page_btn.pack(side="left", padx=2)
        
        self.prev_page_btn = ttk.Button(
            nav_frame, 
            text="⟨",
            width=3,
            command=self.go_to_prev_page
        )
        self.prev_page_btn.pack(side="left", padx=2)
        
        # Page indicator
        self.page_var = StringVar(value="Page 1 of 1")
        page_label = ttk.Label(
            nav_frame,
            textvariable=self.page_var,
            width=15,
            anchor="center"
        )
        page_label.pack(side="left", padx=5)
        
        self.next_page_btn = ttk.Button(
            nav_frame, 
            text="⟩",
            width=3,
            command=self.go_to_next_page
        )
        self.next_page_btn.pack(side="left", padx=2)
        
        self.last_page_btn = ttk.Button(
            nav_frame, 
            text="⟩⟩",
            width=3,
            command=self.go_to_last_page
        )
        self.last_page_btn.pack(side="left", padx=2)
        
        # Items per page selector
        items_frame = ttk.Frame(pagination_frame)
        items_frame.pack(side="right")
        
        ttk.Label(
            items_frame,
            text="Items per page:"
        ).pack(side="left", padx=(0, 5))
        
        self.items_per_page_var = StringVar(value="20")
        items_combo = ttk.Combobox(
            items_frame,
            textvariable=self.items_per_page_var,
            width=5,
            state="readonly"
        )
        items_combo.pack(side="left")
        items_combo["values"] = ["10", "20", "50", "100"]
        items_combo.current(1)
        items_combo.bind("<<ComboboxSelected>>", self.change_items_per_page)
    
    def create_status_bar(self):
        """Create status bar at the bottom."""
        status_frame = ttk.Frame(self)
        status_frame.pack(fill="x", pady=(10, 0))
        
        # Track refresh timestamp
        self.last_refresh_time = None
        
        # Status message on the left
        self.status_var = StringVar(value="Ready")
        status_label = ttk.Label(
            status_frame, 
            textvariable=self.status_var,
            anchor="w"
        )
        status_label.pack(side="left")
        
        # Item count in the middle
        self.count_var = StringVar(value="0 items")
        count_label = ttk.Label(
            status_frame, 
            textvariable=self.count_var,
            anchor="center"
        )
        count_label.pack(side="left", padx=(20, 0))
        
        # Progress indicator for loading
        self.progress_var = StringVar(value="")
        progress_label = ttk.Label(
            status_frame,
            textvariable=self.progress_var,
            anchor="center",
            foreground="#5c6bc0"  # Light blue-purple
        )
        progress_label.pack(side="left", padx=(20, 0))
        
        # Last updated time on the right
        self.last_updated_var = StringVar(value="Last updated: Never")
        updated_label = ttk.Label(
            status_frame, 
            textvariable=self.last_updated_var,
            anchor="e"
        )
        updated_label.pack(side="right")
        
    def create_tooltip(self, widget, text):
        """Create a tooltip for a widget.
        
        Args:
            widget: The widget to attach the tooltip to
            text: The tooltip text
        """
        tooltip = None
        
        def enter(event):
            nonlocal tooltip
            x, y, _, _ = widget.bbox("insert")
            x += widget.winfo_rootx() + 25
            y += widget.winfo_rooty() + 25
            
            # Create a toplevel window
            tooltip = tk.Toplevel(widget)
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{x}+{y}")
            
            label = ttk.Label(tooltip, text=text, justify=tk.LEFT,
                          background="#ffffe0", relief="solid", borderwidth=1,
                          wraplength=250, font=("Segoe UI", 9))
            label.pack(ipadx=5, ipady=3)
        
        def leave(event):
            nonlocal tooltip
            if tooltip:
                tooltip.destroy()
                tooltip = None
        
        # Bind events to widget
        widget.bind("<Enter>", enter)
        widget.bind("<Leave>", leave)
        
        # Store reference to avoid garbage collection
        self.tooltips[widget] = (enter, leave)
        
    def load_inventory(self):
        """Load inventory data from RepairDesk API.
        Will use cached data if available and not expired, based on user preference.
        """
        self.status_var.set("Loading inventory data...")
        
        # Clear current data
        self.inventory_tree.delete(*self.inventory_tree.get_children())
        
        # Reset inventory and filter state
        self.inventory_items = []
        self.filtered_items = []
        
        # Show loading indicator in the tree view
        self.inventory_tree.insert('', 'end', values=('Loading...', '', '', '', ''), tags=('loading',))
        
        # Check if cache should be used based on toggle setting
        use_cache = self.use_cache_var.get()
        
        # Create and start loading thread
        thread = threading.Thread(target=lambda: self._load_inventory_thread(force_refresh=not use_cache))
        thread.daemon = True
        thread.start()
    
    def refresh_inventory(self):
        """Refresh inventory data from API, bypassing cache."""
        self.status_var.set("Refreshing inventory data...")
        self.inventory_tree.delete(*self.inventory_tree.get_children())
        
        # Explicitly clear the cache before refreshing
        if hasattr(self.api_client, '_clear_cache'):
            logger.info("Clearing inventory cache before refresh")
            self.api_client._clear_cache('inventory')
            
        # Force cache toggle to off to ensure we get fresh data
        previous_cache_setting = self.use_cache_var.get()
        self.use_cache_var.set(False)
        
        # Create and start loading thread with force_refresh=True to bypass cache
        thread = threading.Thread(target=lambda: self._load_inventory_thread(force_refresh=True))
        thread.daemon = True
        thread.start()
        
        # Restore previous cache setting after refresh initiated
        self.after(1000, lambda: self.use_cache_var.set(previous_cache_setting))
    
    def _load_inventory_thread(self, force_refresh=False):
        """Background thread to fetch inventory data.
        
        Args:
            force_refresh (bool): If True, bypass cache and fetch fresh data
        """
        try:
            # Log whether we're using cache or not
            if force_refresh:
                logger.info("Fetching fresh inventory data (bypassing cache)")
            else:
                logger.info("Fetching inventory data (using cache if available)")
            
            # Define the callback function for incremental updates
            def page_callback(page_items, is_complete, total_items, pagination_info):
                # Schedule UI update on the main thread using thread-safe updater
                ThreadSafeUIUpdater.safe_update(self, lambda: self._process_inventory_page(
                    page_items, is_complete, total_items, pagination_info, is_cached=not force_refresh
                ))
                
            # Get inventory data from API, with option to bypass cache and page_callback for live updates
            inventory_data = self.api_client.get_all_inventory(
                use_cache=not force_refresh,
                page_callback=page_callback
            )
            
            # Final processing will happen through the page_callback
            
        except Exception as e:
            logger.error(f"Error loading inventory data: {e}")
            error_msg = str(e)
            ThreadSafeUIUpdater.safe_update(self, lambda: self._show_load_error(error_msg))
    
    def _process_inventory_data(self, data, is_cached=None):
        """Process the complete inventory data set and update the UI.
        Used for backward compatibility or when not using incremental loading.
        
        Args:
            data: The inventory data to process
            is_cached: Whether data came from cache. None = unknown
        """
        # Clear loading placeholder if it exists
        for item in self.inventory_tree.get_children():
            if self.inventory_tree.item(item, 'values')[0] == 'Loading...':
                self.inventory_tree.delete(item)
        
        self.inventory_items = data
        self.filtered_items = self.inventory_items.copy()
        
        # Sort items (don't apply filters yet to avoid recursion)
        self.sort_items()
        
        # Display all items (initial load)
        self.filter_and_display_items()
        
        # Update status and track refresh time
        self.last_refresh_time = datetime.now()
        now = self.last_refresh_time.strftime("%H:%M:%S")
        
        # Check cache information
        cache_status = ""
        cache_file = self.api_client.get_inventory_cache_file()
        
        if is_cached:
            try:
                # Get file modification time as a proxy for cache age
                if os.path.exists(cache_file):
                    cache_time = datetime.fromtimestamp(os.path.getmtime(cache_file))
                    cache_age_seconds = (datetime.now() - cache_time).total_seconds()
                    cache_age_minutes = cache_age_seconds / 60
                    
                    # Format for status bar
                    cache_time_str = cache_time.strftime("%H:%M:%S")
                    cache_status = f" (cached from {cache_time_str})"
                    
                    # Set cache indicator in header with friendly time format
                    if cache_age_minutes < 1:
                        age_text = "just now"
                    elif cache_age_minutes < 2:
                        age_text = "1 minute ago"
                    else:
                        age_text = f"{int(cache_age_minutes)} minutes ago"
                    
                    self.cache_status_var.set(f"Using cached data from {age_text}")
                    
                    # Add the cache file path to the tooltip of the cache status label
                    self.create_tooltip(self.cache_status_label, f"Cache file: {cache_file}")
            except Exception as e:
                logger.warning(f"Error getting cache info: {e}")
                self.cache_status_var.set("Using cached data")
        else:
            # Clear cache indicator for fresh data
            self.cache_status_var.set("Fresh data from API")
        
        # Clear progress indicator
        self.progress_var.set("")
        
        self.status_var.set(f"Inventory data loaded successfully{cache_status}")
        
        # Format timestamp to make refresh changes obvious
        timestamp_format = "%Y-%m-%d %H:%M:%S"
        now_full = self.last_refresh_time.strftime(timestamp_format)
        self.last_updated_var.set(f"Last updated: {now_full}")
        self.count_var.set(f"{len(self.inventory_items)} items")
        
        # Populate category filter
        self._update_category_filter()
        
    def _process_inventory_page(self, page_items, is_complete, total_items_so_far, pagination_info, is_cached=None):
        """Process each page of inventory data as it arrives and update the UI incrementally.
        
        Args:
            page_items: The current page of inventory items
            is_complete: Whether this is the final page of data
            total_items_so_far: Total items loaded so far
            pagination_info: Information about pagination state
            is_cached: Whether data came from cache
        """
        # Clear loading placeholder on first page
        if pagination_info.get('current_page', 1) == 1:
            for item in self.inventory_tree.get_children():
                if self.inventory_tree.item(item, 'values')[0] == 'Loading...':
                    self.inventory_tree.delete(item)
        
        # Add new items to our inventory list
        self.inventory_items.extend(page_items)
        
        # Update the progress indicator
        current_page = pagination_info.get('current_page', 1)
        total_pages = pagination_info.get('total_pages', 1)
        self.progress_var.set(f"Loading page {current_page} of {total_pages}...")
        
        # Process just the new items and add them to the tree
        for item in page_items:
            self._add_item_to_tree(item)
        
        # Update the status bar with count of items so far
        self.count_var.set(f"{total_items_so_far} items{'...' if not is_complete else ''}")
        
        # If this is the final page, finish up
        if is_complete:
            # Track refresh time for displaying accurate timestamps
            self.last_refresh_time = datetime.now()
            now = self.last_refresh_time.strftime("%H:%M:%S")
            
            # Complete the loading process
            self.filtered_items = self.inventory_items.copy()
            
            # Sort and filter all loaded items
            self.sort_items()
            self.filter_and_display_items()
            
            # Check cache information
            cache_status = ""
            cache_file = self.api_client.get_inventory_cache_file()
            
            if is_cached:
                try:
                    # Get file modification time as a proxy for cache age
                    if os.path.exists(cache_file):
                        cache_time = datetime.fromtimestamp(os.path.getmtime(cache_file))
                        cache_age_seconds = (datetime.now() - cache_time).total_seconds()
                        cache_age_minutes = cache_age_seconds / 60
                        
                        # Format for status bar
                        cache_time_str = cache_time.strftime("%H:%M:%S")
                        cache_status = f" (cached from {cache_time_str})"
                        
                        # Set cache indicator in header with friendly time format
                        if cache_age_minutes < 1:
                            age_text = "just now"
                        elif cache_age_minutes < 2:
                            age_text = "1 minute ago"
                        else:
                            age_text = f"{int(cache_age_minutes)} minutes ago"
                        
                        self.cache_status_var.set(f"Using cached data from {age_text}")
                        
                        # Add the cache file path to the tooltip of the cache status label
                        self.create_tooltip(self.cache_status_label, f"Cache file: {cache_file}")
                except Exception as e:
                    logger.warning(f"Error getting cache info: {e}")
                    self.cache_status_var.set("Using cached data")
            else:
                # Clear cache indicator for fresh data
                self.cache_status_var.set("Fresh data from API")
            
            # Clear progress indicator
            self.progress_var.set("")
            
            self.status_var.set(f"Inventory data loaded successfully{cache_status}")
            
            # Format timestamp to make refresh changes obvious
            timestamp_format = "%Y-%m-%d %H:%M:%S"
            now_full = self.last_refresh_time.strftime(timestamp_format)
            self.last_updated_var.set(f"Last updated: {now_full}")
    
    def _update_category_filter(self):
        """Update category filter dropdown with available categories."""
        categories = ["All Categories"]
        
        # Extract unique categories
        category_set = set()
        for item in self.inventory_items:
            category = item.get("category", {}).get("name", "")
            if category and category not in category_set:
                category_set.add(category)
        
        # Add sorted categories to the list
        categories.extend(sorted(category_set))
        
        # Update the combobox values
        category_combo = None
        for child in self.winfo_children():
            if isinstance(child, ttk.Frame):
                for subchild in child.winfo_children():
                    if isinstance(subchild, ttk.Frame):
                        for widget in subchild.winfo_children():
                            if isinstance(widget, ttk.Combobox) and widget.cget("width") == 15:
                                category_combo = widget
                                break
        
        if category_combo:
            current_val = self.category_var.get()
            category_combo["values"] = categories
            
            # Preserve current selection if possible
            if current_val in categories:
                self.category_var.set(current_val)
            else:
                self.category_var.set("All Categories")
    
    def _show_load_error(self, error_msg):
        """Show error message when loading fails."""
        self.status_var.set(f"Error: {error_msg}")
        messagebox.showerror(
            "Loading Error",
            f"Failed to load inventory data: {error_msg}"
        )
    
    def filter_and_display_items(self):
        """Display the filtered items with pagination."""
        # Clear current displayed items
        self.inventory_tree.delete(*self.inventory_tree.get_children())
        
        # Calculate pagination
        self.items_per_page = int(self.items_per_page_var.get())
        self.total_pages = max(1, (len(self.filtered_items) + self.items_per_page - 1) // self.items_per_page)
        self.current_page = min(self.current_page, self.total_pages)
        
        # Update page indicator
        self.page_var.set(f"Page {self.current_page} of {self.total_pages}")
        
        # Get items for current page
        start_idx = (self.current_page - 1) * self.items_per_page
        end_idx = start_idx + self.items_per_page
        page_items = self.filtered_items[start_idx:end_idx]
        
        # Add items to treeview
        for item in page_items:
            self._add_item_to_tree(item)
            
        # Update count
        self.count_var.set(f"{len(self.filtered_items)} items")
    
    def _add_item_to_tree(self, item):
        """Add an inventory item to the treeview."""
        item_id = item.get("id", "")
        name = item.get("name", "")
        # Handle potential empty string or invalid values for price
        try:
            price_value = item.get("price", 0)
            if price_value == "":
                price_value = 0
            price = f"${float(price_value):.2f}"
        except (ValueError, TypeError):
            price = "$0.00"
        quantity = item.get("quantity", 0)
        
        # Get category name from category object if available
        category = ""
        if item.get("category") and isinstance(item.get("category"), dict):
            category = item.get("category").get("name", "")
        else:
            category = item.get("category_name", "")
        
        # Determine status based on quantity and threshold
        threshold = int(item.get("low_stock_threshold", 5))
        try:
            qty = int(quantity)
        except (ValueError, TypeError):
            qty = 0
            
        if qty <= 0:
            tag = "out_of_stock"
        elif qty <= threshold:
            tag = "low_stock"
        else:
            tag = "in_stock"
        
        # Insert into treeview with appropriate tag
        self.inventory_tree.insert(
            "", 
            "end", 
            values=(item_id, name, quantity, price, category),
            tags=(tag,)
        )
    
    def _show_load_error(self, error_msg):
        """Show error message when loading fails."""
        self.status_var.set(f"Error: {error_msg}")
        messagebox.showerror(
            "Loading Error",
            f"Failed to load inventory data: {error_msg}"
        )
        
    def apply_filters(self, event=None):
        """Apply filters to the inventory items."""
        search_term = self.search_var.get().lower()
        category = self.category_var.get()
        status = self.status_var.get()
        item_type = self.type_var.get()
        
        # Filter items based on criteria
        self.filtered_items = []
        for item in self.inventory_items:
            # Skip items that don't match search term
            if search_term and not any(
                search_term in str(item.get(field, '')).lower() 
                for field in ['name', 'sku', 'barcode', 'notes']
            ):
                continue
            
            # Filter by category
            if category != 'All Categories' and item.get('category', {}).get('name', '') != category:
                continue
            
            # Filter by type
            if item_type == 'Product' and item.get('type_id', '') != '1':
                continue
            if item_type == 'Service' and item.get('type_id', '') != '2':
                continue
            
            # Filter by stock status
            quantity = int(item.get('quantity', 0))
            threshold = int(item.get('low_stock_threshold', 5))
            
            if status == 'In Stock' and (quantity <= threshold or quantity <= 0):
                continue
            if status == 'Low Stock' and (quantity > threshold or quantity <= 0):
                continue
            if status == 'Out of Stock' and quantity > 0:
                continue
            
            # Item passed all filters
            self.filtered_items.append(item)
        
        # Sort items
        self.sort_items()
        
        # Reset to first page
        self.current_page = 1
        
        # Refresh display with filtered items
        self.filter_and_display_items()
    
    def on_search_changed(self, *args):
        """Handle search term changes."""
        # Debounce search to avoid excessive filtering
        self.after(300, self.apply_filters)
    
    def sort_items(self):
        """Sort filtered items based on selected sort criteria."""
        sort_by = self.sort_by_var.get()
        field, direction = sort_by.split('_')
        
        # Define key function based on field
        if field == 'price':
            key_func = lambda x: float(x.get('price', 0))
        elif field == 'cost':
            key_func = lambda x: float(x.get('cost_price', 0))
        elif field == 'quantity':
            key_func = lambda x: int(x.get('quantity', 0))
        else:
            key_func = lambda x: str(x.get(field, '')).lower()
        
        # Sort the filtered items
        reverse = direction == 'desc'
        self.filtered_items.sort(key=key_func, reverse=reverse)
    
    def sort_column(self, column):
        """Sort by the selected column."""
        # Map column to item field
        field_map = {
            "id": "id",
            "name": "name",
            "sku": "sku",
            "price": "price",
            "cost": "cost",
            "quantity": "quantity",
            "status": "quantity"  # Status is derived from quantity
        }
        
        field = field_map.get(column, "name")
        
        # Toggle sort direction if same column clicked again
        current_sort = self.sort_by_var.get()
        current_field, current_direction = current_sort.split('_')
        
        if current_field == field:
            new_direction = 'desc' if current_direction == 'asc' else 'asc'
        else:
            new_direction = 'asc'
        
        # Set new sort criteria and refresh display
        self.sort_by_var.set(f"{field}_{new_direction}")
        self.sort_items()
        self.filter_and_display_items()
    
    def go_to_first_page(self):
        """Go to the first page of results."""
        if self.current_page > 1:
            self.current_page = 1
            self.filter_and_display_items()
    
    def go_to_prev_page(self):
        """Go to the previous page of results."""
        if self.current_page > 1:
            self.current_page -= 1
            self.filter_and_display_items()
    
    def go_to_next_page(self):
        """Go to the next page of results."""
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.filter_and_display_items()
    
    def go_to_last_page(self):
        """Go to the last page of results."""
        if self.current_page < self.total_pages:
            self.current_page = self.total_pages
            self.filter_and_display_items()
    
    def change_items_per_page(self, event=None):
        """Change number of items per page."""
        # Reset to first page when changing items per page
        self.current_page = 1
        self.filter_and_display_items()
    
    # Note: There was a duplicate refresh_inventory method that was removed
    
    def view_item_details(self, event=None):
        """View details for the selected item on double-click."""
        # Get the selected item
        selection = self.inventory_tree.selection()
        if not selection:
            return
            
        # Get item ID from the selected row
        item_id = self.inventory_tree.item(selection[0], 'values')[0]
        
        # Find the full item data
        selected_item = None
        for item in self.inventory_items:
            if str(item.get('id', '')) == str(item_id):
                selected_item = item
                break
                
        if not selected_item:
            return
            
        # Create detail window
        detail_window = tk.Toplevel(self)
        detail_window.title(f"Item Details: {selected_item.get('name', '')}")
        detail_window.geometry("600x500")
        detail_window.minsize(500, 400)
        
        # Add padding container
        container = ttk.Frame(detail_window, padding=15)
        container.pack(fill="both", expand=True)
        
        # Header with item name
        ttk.Label(
            container, 
            text=selected_item.get('name', ''),
            style="Header.TLabel"
        ).pack(anchor="w", pady=(0, 15))
        
        # Basic information section
        info_frame = ttk.LabelFrame(container, text="Basic Information", padding=10)
        info_frame.pack(fill="x", pady=(0, 15))
        
        # Create grid layout for info
        info_fields = [
            ("ID:", selected_item.get('id', '')),
            ("SKU:", selected_item.get('sku', '')),
            ("Barcode:", selected_item.get('barcode', '')),
            ("Price:", f"${float(selected_item.get('price', 0)):.2f}"),
            ("Cost:", f"${float(selected_item.get('cost_price', 0)):.2f}"),
            ("Quantity:", selected_item.get('quantity', '0')),
            ("Category:", selected_item.get('category', {}).get('name', '')),
            ("Type:", "Product" if selected_item.get('type_id') == '1' else "Service"),
        ]
        
        for i, (label_text, value) in enumerate(info_fields):
            row = i // 2
            col = (i % 2) * 2
            
            ttk.Label(
                info_frame, 
                text=label_text,
                style="FormLabel.TLabel"
            ).grid(row=row, column=col, sticky="e", padx=(10, 5), pady=5)
            
            ttk.Label(
                info_frame, 
                text=str(value)
            ).grid(row=row, column=col+1, sticky="w", padx=(0, 20), pady=5)
        
        # Stock information section
        stock_frame = ttk.LabelFrame(container, text="Stock Information", padding=10)
        stock_frame.pack(fill="x", pady=(0, 15))
        
        threshold = int(selected_item.get('low_stock_threshold', 5))
        quantity = int(selected_item.get('quantity', 0))
        
        if quantity <= 0:
            status = "Out of Stock"
        elif quantity <= threshold:
            status = "Low Stock"
        else:
            status = "In Stock"
            
        stock_fields = [
            ("Current Stock:", quantity),
            ("Low Stock Threshold:", threshold),
            ("Status:", status),
        ]
        
        for i, (label_text, value) in enumerate(stock_fields):
            ttk.Label(
                stock_frame, 
                text=label_text,
                style="FormLabel.TLabel"
            ).grid(row=i, column=0, sticky="e", padx=(10, 5), pady=5)
            
            ttk.Label(
                stock_frame, 
                text=str(value)
            ).grid(row=i, column=1, sticky="w", padx=(0, 20), pady=5)
        
        # Notes section if available
        notes = selected_item.get('notes', '')
        if notes:
            notes_frame = ttk.LabelFrame(container, text="Notes", padding=10)
            notes_frame.pack(fill="both", expand=True, pady=(0, 15))
            
            notes_text = tk.Text(notes_frame, height=5, wrap="word", borderwidth=1)
            notes_text.pack(fill="both", expand=True)
            notes_text.insert("1.0", notes)
            notes_text.config(state="disabled")
        
        # Close button
        ttk.Button(
            container,
            text="Close",
            command=detail_window.destroy
        ).pack(side="right", pady=(0, 10))
