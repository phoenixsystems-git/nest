import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import threading
import json
import os
import time
from nest.utils.config_util import load_config
import logging
from nest.utils.repairdesk_api import RepairDeskAPI
from nest.utils.ui_threading import ThreadSafeUIUpdater
from nest.main import FixedHeaderTreeview

# Cache configuration
from ..utils.cache_utils import get_cache_directory

# Use centralized cache directory for customer cache
CACHE_FILE = os.path.join(get_cache_directory(), "customers.cache")
CACHE_EXPIRY_HOURS = 24  # Cache expiry time in hours




def save_cache(data):
    """Save customer data to unencrypted JSON cache with timestamp."""
    try:
        cache_data = {
            'data': data,
            'timestamp': time.time(),
            'count': len(data)
        }
        
        with open(CACHE_FILE, 'w') as f:
            json.dump(cache_data, f, indent=2)
        
        logging.debug(f"Saved {len(data)} customers to cache")
        logging.info("Customer data cache saved successfully")
        return True
        
    except Exception as e:
        logging.error(f"Error saving customer cache: {e}")
        return False


def load_cache():
    """Load customer data from JSON cache if not expired."""
    try:
        if not os.path.exists(CACHE_FILE):
            logging.debug("No cache file found")
            return []
        
        with open(CACHE_FILE, 'r') as f:
            cache_data = json.load(f)
        
        # Check if cache is expired (24 hours)
        cache_age = time.time() - cache_data.get('timestamp', 0)
        max_age = CACHE_EXPIRY_HOURS * 3600  # Convert hours to seconds
        
        if cache_age > max_age:
            logging.debug(f"Cache expired ({cache_age/3600:.1f} hours old)")
            return []
        
        data = cache_data.get('data', [])
        logging.debug(f"Loaded {len(data)} customers from cache")
        logging.info("Customer data loaded from cache")
        return data
        
    except Exception as e:
        logging.error(f"Error loading customer cache: {e}")
        return []




def fetch_customers_page(page):
    """
    Fetch a single page of customer data from the API.
    """
    # Create RepairDeskAPI client instance
    api_client = RepairDeskAPI()
    
    print(f"[Customers] Fetching page {page}")
    # Use the customers endpoint with proper pagination
    params = {"page": page, "per_page": 100}  # Request up to 100 per page
    
    # Get the raw response instead of extracted data to see full structure
    response = api_client.request("customers", params=params, raw_response=True)
    
    # Log the response structure for debugging
    print(f"[DEBUG] Response structure: {type(response)}")
    if isinstance(response, dict):
        print(f"[DEBUG] Response keys: {list(response.keys())}")
        
    # Extract customer data from response with better handling of different formats
    customers = []
    
    # Case 1: Standard format with 'data.customerData'
    if isinstance(response, dict) and 'data' in response:
        if isinstance(response['data'], dict) and 'customerData' in response['data']:
            customers = response['data']['customerData']
            print(f"[DEBUG] Found customers in data.customerData")
            
        # Case 2: Data is directly a list of customers
        elif isinstance(response['data'], list):
            customers = response['data']
            print(f"[DEBUG] Found customers in data list")
            
    # Case 3: Response is directly a list of customers
    elif isinstance(response, list):
        customers = response
        print(f"[DEBUG] Response is directly a list of customers")
    
    # Case 4: Results in a different field like 'customers' or 'results'
    elif isinstance(response, dict):
        for key in ['customers', 'results', 'items']:
            if key in response and isinstance(response[key], list):
                customers = response[key]
                print(f"[DEBUG] Found customers in '{key}' field")
                break
                
    print(f"[DEBUG] Fetched {len(customers)} customers from page {page}")
    return customers


class CustomersModule(ttk.Frame):
    def __init__(
        self, parent, current_user=None
    ):  # Changed to accept current_user parameter with default None
        super().__init__(parent, padding=10)
        self.current_user = current_user  # Store the current user
        self.parent = parent
        self.customer_data = []
        self.filtered_data = []
        self._lock = threading.Lock()
        self._is_destroyed = False  # Add a flag to track if module is destroyed
        self.create_widgets()
        # Load cache first
        cached = load_cache()
        if cached:
            self.customer_data = cached
            self.refresh_tree()
        # Start background fetch
        threading.Thread(target=self._fetch_background, daemon=True).start()

    # Add a proper destroy method to safely clean up resources
    def destroy(self):
        """Clean up resources when widget is destroyed."""
        # Set the destroyed flag first to prevent new operations from starting
        self._is_destroyed = True
        
        try:
            logging.info("Properly destroying module: customers")
            
            # Clear data to release memory
            self.customer_data = []
            self.filtered_data = []
            
        except Exception as e:
            logging.error(f"Error during customer module cleanup in destroy: {e}")
        
        # Finally destroy the widget
        try:
            super().destroy()
        except Exception as e:
            logging.error(f"Error destroying customer module widget: {e}")

    def create_widgets(self):
        ttk.Label(self, text="Customers", style="Header.TLabel").pack(anchor="w", pady=(0, 5))
        # Search
        search_frame = ttk.Frame(self)
        search_frame.pack(fill="x", pady=(0, 10))
        
        # Search label with improved styling
        search_label = ttk.Label(
            search_frame, 
            text="Search:", 
            style="Bold.TLabel"
        )
        search_label.pack(side="left", padx=(0, 5))
        
        # Search entry with improved styling
        self.search_var = tk.StringVar()
        entry = ttk.Entry(
            search_frame, 
            textvariable=self.search_var, 
            font=("Segoe UI", 10),
            width=40
        )
        entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        entry.bind("<Return>", lambda e: self.search())
        
        # Use the application's color scheme for consistency
        # Define colors directly to avoid dependency issues
        colors = {
            "primary": "#1976D2",  # Blue
            "primary_dark": "#0D47A1",
            "secondary": "#43A047",  # Green
            "secondary_dark": "#2E7D32"
        }
        
        # Search button with improved styling
        search_button = tk.Button(
            search_frame, 
            text="Search", 
            command=self.search, 
            bg=colors["secondary"],
            fg="white",
            font=("Segoe UI", 10, "bold"),
            width=20,
            borderwidth=0,
            padx=10,
            pady=5,
            cursor="hand2"
        )
        search_button.pack(side="left", padx=(0, 5))
        
        # Refresh button with improved styling
        refresh_button = tk.Button(
            search_frame, 
            text="Refresh", 
            command=self._fetch_background, 
            bg=colors["primary"],
            fg="white",
            font=("Segoe UI", 10, "bold"),
            width=20,
            borderwidth=0,
            padx=10,
            pady=5,
            cursor="hand2"
        )
        refresh_button.pack(side="left")
        
        # Add hover effects to buttons
        def on_enter(e, button, color):
            button["bg"] = colors[color + "_dark"] if color + "_dark" in colors else color
        
        def on_leave(e, button, color):
            button["bg"] = colors[color]
        
        search_button.bind("<Enter>", lambda e: on_enter(e, search_button, "secondary"))
        search_button.bind("<Leave>", lambda e: on_leave(e, search_button, "secondary"))
        refresh_button.bind("<Enter>", lambda e: on_enter(e, refresh_button, "primary"))
        refresh_button.bind("<Leave>", lambda e: on_leave(e, refresh_button, "primary"))
        
        # Tree + scrollbars
        container = ttk.Frame(self)
        container.pack(fill="both", expand=True)
        self.tree = FixedHeaderTreeview(
            container,
            columns=("ID", "Name", "Phone", "Email", "Address", "Created"),
            show="headings",
            style="Custom.Treeview"
        )
        # Use improved column widths for better visibility
        column_widths = {
            "ID": 100,
            "Name": 250,
            "Phone": 150, 
            "Email": 250,
            "Address": 300,
            "Created": 150
        }
        
        # Apply column settings
        for col in self.tree["columns"]:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=column_widths[col], anchor="w", minwidth=75)
        vsb = ttk.Scrollbar(container, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(container, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscroll=vsb.set, xscroll=hsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        container.rowconfigure(0, weight=1)
        container.columnconfigure(0, weight=1)
        # Status
        self.status = ttk.Label(self, text="Loading...")
        self.status.pack(anchor="w", pady=(5, 0))

    def refresh_tree(self, data=None):
        """
        Refresh the data displayed in the tree view.
        """
        with self._lock:
            display = data if data is not None else self.customer_data
        print(f"[DEBUG] Refreshing Treeview with {len(display)} records")  # Debug log
        
        # Check if tree widget still exists
        try:
            # First check if the widget exists
            if not self.tree.winfo_exists():
                print("[DEBUG] Tree widget no longer exists, skipping refresh")
                return
                
            self.tree.delete(*self.tree.get_children())
            for cust in display:
                self.tree.insert(
                    "",
                    "end",
                    values=(
                        cust.get("cid"),
                        cust.get("fullName"),
                        cust.get("mobile"),
                        cust.get("email"),
                        cust.get("address1"),
                        cust.get("created_on"),
                    ),
                )
        except (tk.TclError, RuntimeError, AttributeError) as e:
            print(f"[DEBUG] Error refreshing tree: {e}")
            return

    def search(self):
        """
        Filter customers based on a search query.
        """
        q = self.search_var.get().lower()
        if not q:
            self.refresh_tree()
            return
        with self._lock:
            self.filtered_data = [
                c
                for c in self.customer_data
                if q in c.get("fullName", "").lower()
                or q in c.get("email", "").lower()
                or q in c.get("mobile", "")
            ]
        self.refresh_tree(self.filtered_data)
        self.status.config(text=f"Found {len(self.filtered_data)} matches")

    def _fetch_background(self):
        """
        Fetch all customer data in the background while preventing duplicates.
        Implements incremental caching for efficient handling of large datasets.
        """
        # Create the API client instance
        api_client = RepairDeskAPI()
        
        # Check if API client has valid credentials
        if not api_client.api_key:
            ThreadSafeUIUpdater.safe_update(self, lambda: messagebox.showerror(
                "Config Error", "RepairDesk API key missing from configuration."
            ))
            return
            
        try:
            # Try to load data from cache first for faster startup
            cached_data = load_cache()
            if cached_data:
                self.customer_data = cached_data
                ThreadSafeUIUpdater.safe_update(self, self.refresh_tree)
                ThreadSafeUIUpdater.safe_update(self, lambda: self.status.config(
                    text=f"Loaded {len(self.customer_data)} cached customers"
                ))
                logging.info(f"Using {len(self.customer_data)} customers from cache")
            else:
                self.customer_data = []
                
            # Dictionary to track customers by ID for faster duplicate checking
            customer_dict = {cust["cid"]: True for cust in self.customer_data}
            
            # Start fetching with incremental caching
            page = 1
            cache_updates = 0
            customer_count_at_last_save = len(self.customer_data)
            
            while True:
                rows = fetch_customers_page(page)
                if not rows:  # Stop fetching when no more data is returned
                    logging.info(f"No more customer data after page {page}")
                    break
                    
                new_customers_in_page = 0
                for cust in rows:
                    cust_id = cust.get("cid", "")
                    # More efficient duplicate check using dictionary
                    if cust_id and cust_id not in customer_dict:
                        customer_dict[cust_id] = True
                        self.customer_data.append(
                            {
                                "cid": cust_id,
                                "fullName": cust.get("fullName", ""),
                                "mobile": cust.get("mobile", ""),
                                "email": cust.get("email", ""),
                                "address1": cust.get("address1", ""),
                                "created_on": cust.get("created_on", ""),
                            }
                        )
                        new_customers_in_page += 1
                        
                logging.debug(f"Added {new_customers_in_page} new customers from page {page}")
                logging.debug(f"Total customers: {len(self.customer_data)}")
                
                # Check if module is destroyed before updating UI
                if hasattr(self, '_is_destroyed') and self._is_destroyed:
                    logging.debug("Skipping UI update - customers module has been destroyed")
                    break  # Exit the fetch loop if module has been destroyed
                    
                # Update UI with progress
                ThreadSafeUIUpdater.safe_update(self, self.refresh_tree)
                
                # Add safe status update with error handling
                def safe_status_update(p):
                    try:
                        # Double-check if module is destroyed or if status widget still exists
                        if hasattr(self, '_is_destroyed') and self._is_destroyed:
                            return
                        if hasattr(self, 'status') and self.status.winfo_exists():
                            self.status.config(text=f"Loading: {len(self.customer_data)} customers (page {p})")
                        else:
                            print(f"[DEBUG] Status widget no longer exists, skipping update for page {p}")
                    except (tk.TclError, RuntimeError, AttributeError) as e:
                        print(f"[DEBUG] Error updating status label: {e}")
                
                ThreadSafeUIUpdater.safe_update(self, lambda p=page: safe_status_update(p))
                
                # Incremental cache update - save every 5 pages or 100+ new customers
                new_customers = len(self.customer_data) - customer_count_at_last_save
                if page % 5 == 0 or new_customers >= 100:
                    # Save incremental progress to cache
                    if save_cache(self.customer_data):
                        cache_updates += 1
                        customer_count_at_last_save = len(self.customer_data)
                        logging.info(f"Incremental cache update #{cache_updates}: Saved {len(self.customer_data)} customers")
                    
                page += 1
            
            # Final cache save to ensure we have the most recent data
            if len(self.customer_data) > customer_count_at_last_save:
                if save_cache(self.customer_data):
                    logging.info(f"Final cache update: Saved {len(self.customer_data)} customers")
            
            # Update status with completion message, but check if destroyed first
            if not hasattr(self, '_is_destroyed') or not self._is_destroyed:
                ThreadSafeUIUpdater.safe_update(self, lambda: self.status.config(
                    text=f"Done: {len(self.customer_data)} customers"
                ) if hasattr(self, 'status') and self.status.winfo_exists() else None)
            
        except Exception as e:
            error_message = f"Failed fetch: {e}"
            logging.error(f"Customer fetch error: {e}")
            # Only show error message if module is not destroyed
            if not hasattr(self, '_is_destroyed') or not self._is_destroyed:
                ThreadSafeUIUpdater.safe_update(self, lambda msg=error_message: messagebox.showerror("Error", msg))
