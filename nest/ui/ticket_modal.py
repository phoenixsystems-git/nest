import tkinter as tk
from tkinter import ttk, messagebox
import webbrowser
import os
from datetime import datetime


class TicketModal(tk.Toplevel):
    def __init__(self, parent, ticket_data, customer_folder_path=None):
        super().__init__(parent)
        self.title("Ticket Details")
        self.geometry("600x400")
        self.resizable(True, True)

        self.ticket_data = ticket_data
        self.customer_folder_path = customer_folder_path

        self.configure_gui()
        self.create_widgets()

    def configure_gui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        
    def _get_normalized_data(self):
        """Normalize ticket data regardless of its structure (list or dict).
        
        Returns:
            dict: Normalized ticket data in a consistent dictionary format
        """
        # First, handle different input data structures
        base_data = {}
        
        # Handle case where ticket_data is a list
        if isinstance(self.ticket_data, list):
            if len(self.ticket_data) > 0:
                # Take the first ticket item if it's a list
                base_data = self.ticket_data[0] if isinstance(self.ticket_data[0], dict) else {}
        # Handle case where ticket_data is already a dictionary
        elif isinstance(self.ticket_data, dict):
            base_data = self.ticket_data
            
        # Now handle nested structure of API response
        if 'data' in base_data:
            # This is the full API response structure
            normalized = base_data['data']
            return normalized
        else:
            # This might already be the data part
            return base_data

    def create_widgets(self):
        # Create main frame
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create notebook for tabs
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        # Create tabs
        details_tab = ttk.Frame(notebook, padding=10)
        notebook.add(details_tab, text="Details")
        
        activity_tab = ttk.Frame(notebook, padding=10)
        notebook.add(activity_tab, text="Activity History")
        
        repair_tab = ttk.Frame(notebook, padding=10)
        notebook.add(repair_tab, text="Repair Items")
        
        # Create two columns in details tab
        left_column = ttk.Frame(details_tab)
        left_column.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        right_column = ttk.Frame(details_tab)
        right_column.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        # Customer information
        customer_frame = ttk.LabelFrame(left_column, text="Customer Information")
        customer_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Get normalized data with correct structure
        ticket_data_normalized = self._get_normalized_data()
        
        # Find customer info in the nested structure
        customer = {}
        
        # Check if data is in the API response format (with summary)
        if 'summary' in ticket_data_normalized and isinstance(ticket_data_normalized['summary'], dict):
            summary = ticket_data_normalized['summary']
            # Get customer from summary
            if 'customer' in summary and isinstance(summary['customer'], dict):
                customer = summary['customer']
        # Check direct customer field
        elif 'customer' in ticket_data_normalized and isinstance(ticket_data_normalized['customer'], dict):
            customer = ticket_data_normalized['customer']
            
        # Extract customer details
        customer_name = customer.get('fullName', 'N/A')
        customer_phone = customer.get('mobile', customer.get('phone', 'N/A'))
        customer_email = customer.get('email', 'N/A')
        
        ttk.Label(customer_frame, text=f"Name: {customer_name}", anchor="w").pack(fill=tk.X, pady=2, padx=10)
        ttk.Label(customer_frame, text=f"Phone: {customer_phone}", anchor="w").pack(fill=tk.X, pady=2, padx=10)
        ttk.Label(customer_frame, text=f"Email: {customer_email}", anchor="w").pack(fill=tk.X, pady=2, padx=10)
        
        # Device information
        device_frame = ttk.LabelFrame(left_column, text="Device Information")
        device_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Get normalized ticket data
        ticket_data_normalized = self._get_normalized_data()
        
        # Extract device info from the proper location in the nested structure
        devices = []
        device = {}
        
        # Devices are in the main data or under summary
        if 'devices' in ticket_data_normalized and isinstance(ticket_data_normalized['devices'], list):
            devices = ticket_data_normalized['devices']
        
        # Get the first device if available
        if devices and len(devices) > 0:
            device = devices[0]
            
        # Extract device details
        device_name = 'N/A'
        if 'device' in device and isinstance(device['device'], dict):
            device_name = device['device'].get('name', 'N/A')
            
        # Get status
        device_status = 'N/A'
        if 'status' in device and isinstance(device['status'], dict):
            device_status = device['status'].get('name', 'N/A')
            
        # Get serial number
        device_serial = device.get('serial', 'N/A')
        if device_serial == '' and 'device' in device and isinstance(device['device'], dict):
            device_serial = device['device'].get('serial', 'N/A')
            
        # Get condition
        device_condition = device.get('condition', 'N/A')
        
        # Get issue/repair type
        device_issue = "N/A"
        if 'repairProdItems' in device and device['repairProdItems'] and len(device['repairProdItems']) > 0:
            first_item = device['repairProdItems'][0]
            if isinstance(first_item, dict):
                device_issue = first_item.get('name', 'N/A')
        
        ttk.Label(device_frame, text=f"Type: {device_name}", anchor="w").pack(fill=tk.X, pady=2, padx=10)
        ttk.Label(device_frame, text=f"Issue: {device_issue}", anchor="w").pack(fill=tk.X, pady=2, padx=10)
        ttk.Label(device_frame, text=f"Serial: {device_serial}", anchor="w").pack(fill=tk.X, pady=2, padx=10)
        ttk.Label(device_frame, text=f"Condition: {device_condition}", anchor="w").pack(fill=tk.X, pady=2, padx=10)
        
        # Status information
        status_frame = ttk.LabelFrame(right_column, text="Ticket Status")
        status_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Extract ticket status information
        summary = {}
        if 'summary' in ticket_data_normalized and isinstance(ticket_data_normalized['summary'], dict):
            summary = ticket_data_normalized['summary']
            
        # Get basic ticket info
        ticket_id = summary.get('order_id', 'N/A')
        
        # Get assigned technician
        assigned_to = 'Unassigned'
        if 'assigned_to' in device and isinstance(device['assigned_to'], dict):
            assigned_to = device['assigned_to'].get('fullname', 'Unassigned')
            if not assigned_to or assigned_to == '':
                assigned_to = 'Unassigned'
                
        # Format dates with proper error handling
        created_date = "N/A"
        updated_date = "N/A"
        
        # Get created date
        try:
            if 'created_date' in summary and summary['created_date']:
                ts = float(summary['created_date'])
                created_date = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
        except (ValueError, TypeError) as e:
            print(f"Error formatting created_date: {e}")
            
        # Get updated date
        try:
            if 'modified_on' in summary and summary['modified_on']:
                ts = float(summary['modified_on'])
                updated_date = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
            elif 'updated_at' in summary and summary['updated_at']:
                ts = float(summary['updated_at'])
                updated_date = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
        except (ValueError, TypeError) as e:
            print(f"Error formatting updated_date: {e}")
        
        ttk.Label(status_frame, text=f"Ticket #: {ticket_id}", anchor="w").pack(fill=tk.X, pady=2, padx=10)
        ttk.Label(status_frame, text=f"Status: {device_status}", anchor="w").pack(fill=tk.X, pady=2, padx=10)
        ttk.Label(status_frame, text=f"Assigned To: {assigned_to}", anchor="w").pack(fill=tk.X, pady=2, padx=10)
        ttk.Label(status_frame, text=f"Created: {created_date}", anchor="w").pack(fill=tk.X, pady=2, padx=10)
        ttk.Label(status_frame, text=f"Last Updated: {updated_date}", anchor="w").pack(fill=tk.X, pady=2, padx=10)
        
        # Activity history tab
        activities = []
        notes = []
        
        # Try to find activities in the nested data structure
        if 'activities' in ticket_data_normalized and isinstance(ticket_data_normalized['activities'], list):
            activities = ticket_data_normalized['activities']
        # Sometimes activities are in data.activities
        elif 'data' in ticket_data_normalized and isinstance(ticket_data_normalized['data'], dict):
            if 'activities' in ticket_data_normalized['data']:
                activities = ticket_data_normalized['data']['activities']
                
        # Also collect notes, which are stored separately from activities
        if 'notes' in ticket_data_normalized and isinstance(ticket_data_normalized['notes'], list):
            notes = ticket_data_normalized['notes']
        # Check if we have either activities or notes to display
        if activities or notes:
            # Create scrollable frame
            activity_canvas = tk.Canvas(activity_tab)
            scrollbar = ttk.Scrollbar(activity_tab, orient="vertical", command=activity_canvas.yview)
            scrollable_frame = ttk.Frame(activity_canvas)
            
            scrollable_frame.bind(
                "<Configure>",
                lambda e: activity_canvas.configure(scrollregion=activity_canvas.bbox("all"))
            )
            
            activity_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
            activity_canvas.configure(yscrollcommand=scrollbar.set)
            
            activity_canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
            
            # Process and display notes first (as they often contain more detailed information)
            for note in notes:
                activity_frame = ttk.Frame(scrollable_frame, padding=(5, 10))
                activity_frame.pack(fill=tk.X, pady=5, padx=5)
                
                # Format timestamp
                timestamp = "N/A"
                if 'created_on' in note and note['created_on']:
                    try:
                        ts = float(note['created_on'])
                        timestamp = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
                    except (ValueError, TypeError):
                        pass
                
                # Get user who made the note
                username = note.get("user", "System")
                note_type = "Note"
                if note.get("type") == 1:
                    note_type = "Diagnostic Note"
                elif note.get("tittle"):
                    note_type = note.get("tittle")
                
                # Create a header with the timestamp and username
                header = ttk.Frame(activity_frame)
                header.pack(fill=tk.X, pady=(0, 5))
                
                ttk.Label(
                    header, 
                    text=f"{timestamp} - {username} ({note_type})",
                    font=("" , 9, "bold")
                ).pack(side="left")
                
                # Note content
                content = note.get("msg_text", "").strip()
                if content:
                    ttk.Label(
                        activity_frame,
                        text=content,
                        wraplength=500,
                        justify="left"
                    ).pack(fill=tk.X)
                else:
                    ttk.Label(
                        activity_frame,
                        text="[No description provided]",
                        foreground="gray"
                    ).pack(fill=tk.X)
                    
                ttk.Separator(scrollable_frame, orient="horizontal").pack(fill=tk.X, padx=5, pady=5)
            
            # Then process regular activities
            for activity in activities:
                activity_frame = ttk.Frame(scrollable_frame, padding=(5, 10))
                activity_frame.pack(fill=tk.X, pady=5, padx=5)
                
                # Format timestamp
                timestamp = "N/A"
                if activity.get("created_at"):
                    try:
                        ts = float(activity["created_at"])
                        timestamp = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
                    except (ValueError, TypeError):
                        pass
                
                # Get user who made the comment
                username = activity.get("user", {}).get("fullname", "System")
                
                header = ttk.Frame(activity_frame)
                header.pack(fill=tk.X, pady=(0, 5))
                
                ttk.Label(
                    header, 
                    text=f"{timestamp} - {username} (Activity)",
                    font=("" , 9, "bold")
                ).pack(side="left")
                
                # Activity content
                content = activity.get("description", "").strip()
                if content:
                    ttk.Label(
                        activity_frame,
                        text=content,
                        wraplength=500,
                        justify="left"
                    ).pack(fill=tk.X)
                else:
                    ttk.Label(
                        activity_frame,
                        text="[No description provided]",
                        foreground="gray"
                    ).pack(fill=tk.X)
                    
                ttk.Separator(scrollable_frame, orient="horizontal").pack(fill=tk.X, padx=5, pady=5)
        else:
            ttk.Label(
                activity_tab,
                text="No activity history available for this ticket.",
                foreground="gray"
            ).pack(pady=20)
        
        # Add buttons at the bottom
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(button_frame, text="Open in RepairDesk", command=self.open_repairdesk_url).pack(
            side=tk.LEFT, padx=(0, 5)
        )
        ttk.Button(button_frame, text="Open Customer Folder", command=self.open_customer_folder).pack(
            side=tk.LEFT
        )

    def open_repairdesk_url(self):
        # Get normalized data structure
        ticket_data_normalized = self._get_normalized_data()
        ticket_id = ticket_data_normalized.get("order_id")
        # If not found at root level, check in summary
        if not ticket_id:
            ticket_id = ticket_data_normalized.get("summary", {}).get("order_id")
        if ticket_id:
            url = f"https://app.repairdesk.co/tickets/{ticket_id}"
            webbrowser.open(url)

    def open_customer_folder(self):
        if self.customer_folder_path and os.path.exists(self.customer_folder_path):
            os.startfile(self.customer_folder_path)
        else:
            tk.messagebox.showerror(
                "Folder Not Found", "The customer folder path is invalid or missing."
            )
