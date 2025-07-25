import tkinter as tk
from tkinter import ttk, messagebox
import threading
import logging
from nest.utils.config_util import load_config
from nest.utils.api_client import RepairDeskClient
from nest.utils.ui_threading import ThreadSafeUIUpdater
from nest.main import FixedHeaderTreeview


class TechniciansModule(ttk.Frame):
    def __init__(self, parent, current_user=None):
        super().__init__(parent, padding=15, style="RepairDesk.TFrame")
        self.current_user = current_user
        self.technicians = []
        self.loading = False
        
        self.colors = {
            "primary": "#017E84",
            "secondary": "#2ecc71", 
            "background": "#f9f9f9",
            "card_bg": "#ffffff",
            "text_primary": "#212121",
            "text_secondary": "#666666"
        }
        
        try:
            config = load_config()
            api_key = config.get("repairdesk", {}).get("api_key")
            if api_key:
                self.client = RepairDeskClient(api_key=api_key)
            else:
                self.client = None
                logging.warning("No RepairDesk API key found in config")
        except Exception as e:
            self.client = None
            logging.error(f"Failed to initialize RepairDesk client: {e}")
        
        self._setup_styles()
        self.create_widgets()
        self._load_technicians()
    
    def _setup_styles(self):
        """Configure RepairDesk styling"""
        style = ttk.Style()
        
        style.configure("RepairDesk.TFrame", background=self.colors["background"])
        style.configure("Card.TFrame", 
                       background=self.colors["card_bg"],
                       relief="solid", 
                       borderwidth=1)
        style.configure("RepairDesk.TLabel", 
                       background=self.colors["background"],
                       foreground=self.colors["text_primary"],
                       font=("Segoe UI", 9))
        style.configure("Header.TLabel",
                       background=self.colors["background"],
                       foreground=self.colors["text_primary"],
                       font=("Segoe UI", 16, "bold"))
        style.configure("Subheader.TLabel",
                       background=self.colors["card_bg"],
                       foreground=self.colors["primary"],
                       font=("Segoe UI", 12, "bold"))
        style.configure("RepairDesk.TButton", 
                       background=self.colors["primary"], 
                       foreground="white", 
                       font=("Segoe UI", 9),
                       padding=(8, 4))
    
    def create_widgets(self):
        """Create the technicians UI"""
        header_frame = ttk.Frame(self, style="RepairDesk.TFrame")
        header_frame.pack(fill="x", pady=(0, 20))
        
        ttk.Label(header_frame, text="Technicians Management", 
                 style="Header.TLabel").pack(anchor="w")
        ttk.Label(header_frame, text="View and manage technician information and performance", 
                 style="RepairDesk.TLabel").pack(anchor="w", pady=(5, 0))
        
        controls_frame = ttk.Frame(self, style="RepairDesk.TFrame")
        controls_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Button(controls_frame, text="Refresh", 
                  style="RepairDesk.TButton",
                  command=self._load_technicians).pack(side="left", padx=(0, 10))
        
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(controls_frame, textvariable=self.status_var, 
                 style="RepairDesk.TLabel").pack(side="left")
        
        main_container = ttk.Frame(self, style="RepairDesk.TFrame")
        main_container.pack(fill="both", expand=True)
        
        main_container.grid_columnconfigure(0, weight=2)
        main_container.grid_columnconfigure(1, weight=1)
        main_container.grid_rowconfigure(0, weight=1)
        
        self._create_technicians_list(main_container)
        self._create_details_panel(main_container)
    
    def _create_technicians_list(self, parent):
        """Create technicians list"""
        list_card = ttk.Frame(parent, style="Card.TFrame", padding=10)
        list_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        
        ttk.Label(list_card, text="Technicians List", 
                 style="Subheader.TLabel").pack(anchor="w", pady=(0, 10))
        
        tree_frame = ttk.Frame(list_card, style="Card.TFrame")
        tree_frame.pack(fill="both", expand=True)
        
        columns = ("name", "email", "role", "status", "tickets")
        self.tree = FixedHeaderTreeview(tree_frame, columns=columns, show="headings")
        
        self.tree.heading("name", text="Name")
        self.tree.heading("email", text="Email")
        self.tree.heading("role", text="Role")
        self.tree.heading("status", text="Status")
        self.tree.heading("tickets", text="Active Tickets")
        
        self.tree.column("name", width=150, anchor="w")
        self.tree.column("email", width=200, anchor="w")
        self.tree.column("role", width=100, anchor="w")
        self.tree.column("status", width=80, anchor="center")
        self.tree.column("tickets", width=100, anchor="center")
        
        scrollbar_v = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        scrollbar_h = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=scrollbar_v.set, xscrollcommand=scrollbar_h.set)
        
        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar_v.grid(row=0, column=1, sticky="ns")
        scrollbar_h.grid(row=1, column=0, sticky="ew")
        
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        
        self.tree.bind("<<TreeviewSelect>>", self._on_technician_select)
    
    def _create_details_panel(self, parent):
        """Create technician details panel"""
        details_card = ttk.Frame(parent, style="Card.TFrame", padding=10)
        details_card.grid(row=0, column=1, sticky="nsew")
        
        ttk.Label(details_card, text="Technician Details", 
                 style="Subheader.TLabel").pack(anchor="w", pady=(0, 10))
        
        self.details_frame = ttk.Frame(details_card, style="Card.TFrame")
        self.details_frame.pack(fill="both", expand=True)
        
        self.details_text = tk.Text(self.details_frame, wrap="word", height=15, width=30,
                                   font=("Segoe UI", 9), bg="white", relief="solid", borderwidth=1)
        details_scrollbar = ttk.Scrollbar(self.details_frame, orient="vertical", 
                                         command=self.details_text.yview)
        self.details_text.configure(yscrollcommand=details_scrollbar.set)
        
        self.details_text.pack(side="left", fill="both", expand=True)
        details_scrollbar.pack(side="right", fill="y")
        
        self.details_text.insert("1.0", "Select a technician to view details...")
        self.details_text.configure(state="disabled")
    
    def _load_technicians(self):
        """Load technicians from RepairDesk API"""
        if self.loading:
            return
            
        if not self.client:
            self.status_var.set("Error: No API client available")
            self._show_sample_data()
            return
            
        self.loading = True
        self.status_var.set("Loading technicians...")
        
        def fetch_data():
            try:
                employees = self.client.get_employees() if self.client else None
                if employees:
                    self.technicians = employees
                    ThreadSafeUIUpdater.safe_update(self, self._update_technicians_list)
                else:
                    ThreadSafeUIUpdater.safe_update(self, lambda: self.status_var.set("No technicians found"))
                    ThreadSafeUIUpdater.safe_update(self, self._show_sample_data)
            except Exception as e:
                logging.error(f"Failed to load technicians: {e}")
                error_msg = str(e)
                ThreadSafeUIUpdater.safe_update(self, lambda: self.status_var.set(f"Error: {error_msg}"))
                ThreadSafeUIUpdater.safe_update(self, self._show_sample_data)
            finally:
                self.loading = False
        
        threading.Thread(target=fetch_data, daemon=True).start()
    
    def _show_sample_data(self):
        """Show sample technician data for demo purposes"""
        sample_technicians = [
            {
                "id": 1,
                "name": "John Smith",
                "email": "john.smith@repairshop.com",
                "role": "Senior Technician",
                "status": "Active",
                "active_tickets": 8,
                "completed_tickets": 156,
                "avg_resolution_time": "2.3 hours",
                "specialties": ["Hardware Repair", "Data Recovery", "Network Issues"]
            },
            {
                "id": 2,
                "name": "Sarah Johnson",
                "email": "sarah.johnson@repairshop.com", 
                "role": "Lead Technician",
                "status": "Active",
                "active_tickets": 12,
                "completed_tickets": 203,
                "avg_resolution_time": "1.8 hours",
                "specialties": ["Mobile Devices", "Software Issues", "Virus Removal"]
            },
            {
                "id": 3,
                "name": "Mike Davis",
                "email": "mike.davis@repairshop.com",
                "role": "Junior Technician", 
                "status": "Training",
                "active_tickets": 3,
                "completed_tickets": 45,
                "avg_resolution_time": "4.1 hours",
                "specialties": ["Basic Repairs", "Customer Service"]
            }
        ]
        
        self.technicians = sample_technicians
        self._update_technicians_list()
        self.status_var.set("Showing sample data (API unavailable)")
    
    def _update_technicians_list(self):
        """Update the technicians list display"""
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        for tech in self.technicians:
            self.tree.insert("", "end", values=(
                tech.get("name", "Unknown"),
                tech.get("email", ""),
                tech.get("role", "Technician"),
                tech.get("status", "Unknown"),
                tech.get("active_tickets", 0)
            ))
        
        self.status_var.set(f"Loaded {len(self.technicians)} technicians")
    
    def _on_technician_select(self, event):
        """Handle technician selection"""
        selection = self.tree.selection()
        if not selection:
            return
            
        item = self.tree.item(selection[0])
        tech_name = item["values"][0]
        
        selected_tech = None
        for tech in self.technicians:
            if tech.get("name") == tech_name:
                selected_tech = tech
                break
        
        if selected_tech:
            self._show_technician_details(selected_tech)
    
    def _show_technician_details(self, technician):
        """Show detailed information for selected technician"""
        self.details_text.configure(state="normal")
        self.details_text.delete("1.0", "end")
        
        details = f"""TECHNICIAN PROFILE
{'=' * 30}

Name: {technician.get('name', 'Unknown')}
Email: {technician.get('email', 'N/A')}
Role: {technician.get('role', 'Technician')}
Status: {technician.get('status', 'Unknown')}

PERFORMANCE METRICS
{'=' * 30}

Active Tickets: {technician.get('active_tickets', 0)}
Completed Tickets: {technician.get('completed_tickets', 0)}
Average Resolution Time: {technician.get('avg_resolution_time', 'N/A')}

SPECIALTIES
{'=' * 30}
"""
        
        specialties = technician.get('specialties', [])
        if specialties:
            for specialty in specialties:
                details += f"• {specialty}\n"
        else:
            details += "No specialties listed\n"
        
        details += f"""
ADDITIONAL INFO
{'=' * 30}

Employee ID: {technician.get('id', 'N/A')}
Department: Technical Services
Hire Date: N/A
Last Login: N/A

RECENT ACTIVITY
{'=' * 30}

• Ticket updates and completions
• Customer interactions
• Training completions
• Performance reviews

(Detailed activity logs would be available in the full implementation)
"""
        
        self.details_text.insert("1.0", details)
        self.details_text.configure(state="disabled")
