import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
import logging


class NotificationsModule(ttk.Frame):
    def __init__(self, parent, current_user=None, app=None):
        super().__init__(parent, padding=15, style="RepairDesk.TFrame")
        self.current_user = current_user
        self.app = app
        self.notifications = []
        
        self.colors = {
            "primary": "#017E84",
            "secondary": "#2ecc71",
            "warning": "#f39c12",
            "error": "#e74c3c",
            "background": "#f9f9f9",
            "card_bg": "#ffffff",
            "text_primary": "#212121",
            "text_secondary": "#666666"
        }
        
        self._setup_styles()
        self.create_widgets()
        self._load_sample_notifications()
    
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
        
        style.configure("Info.TLabel",
                       background=self.colors["card_bg"],
                       foreground=self.colors["primary"],
                       font=("Segoe UI", 9))
        style.configure("Warning.TLabel",
                       background=self.colors["card_bg"],
                       foreground=self.colors["warning"],
                       font=("Segoe UI", 9))
        style.configure("Error.TLabel",
                       background=self.colors["card_bg"],
                       foreground=self.colors["error"],
                       font=("Segoe UI", 9))
        style.configure("Success.TLabel",
                       background=self.colors["card_bg"],
                       foreground=self.colors["secondary"],
                       font=("Segoe UI", 9))
    
    def create_widgets(self):
        """Create the notifications UI"""
        header_frame = ttk.Frame(self, style="RepairDesk.TFrame")
        header_frame.pack(fill="x", pady=(0, 20))
        
        ttk.Label(header_frame, text="Notifications Center", 
                 style="Header.TLabel").pack(anchor="w")
        ttk.Label(header_frame, text="System alerts, updates, and important messages", 
                 style="RepairDesk.TLabel").pack(anchor="w", pady=(5, 0))
        
        controls_frame = ttk.Frame(self, style="RepairDesk.TFrame")
        controls_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Button(controls_frame, text="Mark All Read", 
                  style="RepairDesk.TButton",
                  command=self._mark_all_read).pack(side="left", padx=(0, 10))
        ttk.Button(controls_frame, text="Clear All", 
                  style="RepairDesk.TButton",
                  command=self._clear_all).pack(side="left", padx=(0, 10))
        ttk.Button(controls_frame, text="Refresh", 
                  style="RepairDesk.TButton",
                  command=self._refresh_notifications).pack(side="left")
        
        self.unread_count_var = tk.StringVar()
        ttk.Label(controls_frame, textvariable=self.unread_count_var, 
                 style="RepairDesk.TLabel").pack(side="right")
        
        main_container = ttk.Frame(self, style="RepairDesk.TFrame")
        main_container.pack(fill="both", expand=True)
        
        main_container.grid_columnconfigure(0, weight=2)
        main_container.grid_columnconfigure(1, weight=1)
        main_container.grid_rowconfigure(0, weight=1)
        
        self._create_notifications_list(main_container)
        self._create_details_panel(main_container)
    
    def _create_notifications_list(self, parent):
        """Create notifications list"""
        list_card = ttk.Frame(parent, style="Card.TFrame", padding=10)
        list_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        
        ttk.Label(list_card, text="Recent Notifications", 
                 style="Subheader.TLabel").pack(anchor="w", pady=(0, 10))
        
        list_frame = ttk.Frame(list_card, style="Card.TFrame")
        list_frame.pack(fill="both", expand=True)
        
        self.notifications_listbox = tk.Listbox(list_frame, font=("Segoe UI", 9),
                                               bg="white", relief="solid", borderwidth=1)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", 
                                 command=self.notifications_listbox.yview)
        self.notifications_listbox.configure(yscrollcommand=scrollbar.set)
        
        self.notifications_listbox.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        self.notifications_listbox.bind("<<ListboxSelect>>", self._on_notification_select)
    
    def _create_details_panel(self, parent):
        """Create notification details panel"""
        details_card = ttk.Frame(parent, style="Card.TFrame", padding=10)
        details_card.grid(row=0, column=1, sticky="nsew")
        
        ttk.Label(details_card, text="Notification Details", 
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
        
        self.details_text.insert("1.0", "Select a notification to view details...")
        self.details_text.configure(state="disabled")
        
        action_frame = ttk.Frame(details_card, style="Card.TFrame")
        action_frame.pack(fill="x", pady=(10, 0))
        
        ttk.Button(action_frame, text="Mark as Read", 
                  style="RepairDesk.TButton",
                  command=self._mark_selected_read).pack(side="left", padx=(0, 5))
        ttk.Button(action_frame, text="Delete", 
                  style="RepairDesk.TButton",
                  command=self._delete_selected).pack(side="left")
    
    def _load_sample_notifications(self):
        """Load sample notifications for demo"""
        now = datetime.now()
        sample_notifications = [
            {
                "id": 1,
                "title": "System Update Available",
                "message": "A new system update (v2.1.3) is available with bug fixes and performance improvements.",
                "type": "info",
                "timestamp": now - timedelta(minutes=15),
                "read": False,
                "category": "System"
            },
            {
                "id": 2,
                "title": "High Priority Ticket Assigned",
                "message": "Ticket #12345 has been assigned to you. Customer: John Smith - Issue: Computer won't boot",
                "type": "warning",
                "timestamp": now - timedelta(hours=1),
                "read": False,
                "category": "Tickets"
            },
            {
                "id": 3,
                "title": "Appointment Reminder",
                "message": "You have an appointment with Sarah Johnson at 2:00 PM today for laptop repair consultation.",
                "type": "info",
                "timestamp": now - timedelta(hours=2),
                "read": True,
                "category": "Appointments"
            },
            {
                "id": 4,
                "title": "API Connection Error",
                "message": "Failed to connect to RepairDesk API. Please check your internet connection and API credentials.",
                "type": "error",
                "timestamp": now - timedelta(hours=3),
                "read": False,
                "category": "System"
            },
            {
                "id": 5,
                "title": "Backup Completed Successfully",
                "message": "Daily backup of customer data completed successfully. 1,247 records backed up.",
                "type": "success",
                "timestamp": now - timedelta(days=1),
                "read": True,
                "category": "System"
            }
        ]
        
        self.notifications = sample_notifications
        self._update_notifications_list()
    
    def _update_notifications_list(self):
        """Update the notifications list display"""
        self.notifications_listbox.delete(0, tk.END)
        
        unread_count = 0
        for notification in self.notifications:
            status = "●" if not notification["read"] else "○"
            type_indicator = {
                "info": "ℹ",
                "warning": "⚠",
                "error": "✗",
                "success": "✓"
            }.get(notification["type"], "•")
            
            timestamp_str = notification["timestamp"].strftime("%H:%M")
            display_text = f"{status} {type_indicator} {notification['title']} ({timestamp_str})"
            
            self.notifications_listbox.insert(tk.END, display_text)
            
            if not notification["read"]:
                unread_count += 1
        
        self.unread_count_var.set(f"{unread_count} unread notifications")
    
    def _on_notification_select(self, event):
        """Handle notification selection"""
        selection = self.notifications_listbox.curselection()
        if not selection:
            return
            
        selected_notification = self.notifications[selection[0]]
        self._show_notification_details(selected_notification)
    
    def _show_notification_details(self, notification):
        """Show detailed information for selected notification"""
        self.details_text.configure(state="normal")
        self.details_text.delete("1.0", "end")
        
        type_colors = {
            "info": "blue",
            "warning": "orange", 
            "error": "red",
            "success": "green"
        }
        
        details = f"""NOTIFICATION DETAILS
{'=' * 30}

Title: {notification['title']}
Type: {notification['type'].upper()}
Category: {notification['category']}
Status: {'READ' if notification['read'] else 'UNREAD'}
Timestamp: {notification['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}

MESSAGE
{'=' * 30}

{notification['message']}

ACTIONS
{'=' * 30}

• Mark as read/unread
• Delete notification
• View related items (if applicable)

METADATA
{'=' * 30}

Notification ID: {notification['id']}
Created: {notification['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}
Priority: {'High' if notification['type'] in ['error', 'warning'] else 'Normal'}
"""
        
        self.details_text.insert("1.0", details)
        self.details_text.configure(state="disabled")
    
    def _mark_all_read(self):
        """Mark all notifications as read"""
        for notification in self.notifications:
            notification["read"] = True
        self._update_notifications_list()
        messagebox.showinfo("Success", "All notifications marked as read.")
    
    def _clear_all(self):
        """Clear all notifications"""
        result = messagebox.askyesno("Confirm", "Are you sure you want to clear all notifications?")
        if result:
            self.notifications.clear()
            self._update_notifications_list()
            self.details_text.configure(state="normal")
            self.details_text.delete("1.0", "end")
            self.details_text.insert("1.0", "No notifications to display.")
            self.details_text.configure(state="disabled")
    
    def _refresh_notifications(self):
        """Refresh notifications"""
        self._load_sample_notifications()
        messagebox.showinfo("Refreshed", "Notifications refreshed successfully.")
    
    def _mark_selected_read(self):
        """Mark selected notification as read"""
        selection = self.notifications_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a notification first.")
            return
            
        selected_notification = self.notifications[selection[0]]
        selected_notification["read"] = not selected_notification["read"]
        self._update_notifications_list()
        self._show_notification_details(selected_notification)
    
    def _delete_selected(self):
        """Delete selected notification"""
        selection = self.notifications_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a notification first.")
            return
            
        result = messagebox.askyesno("Confirm", "Are you sure you want to delete this notification?")
        if result:
            del self.notifications[selection[0]]
            self._update_notifications_list()
            self.details_text.configure(state="normal")
            self.details_text.delete("1.0", "end")
            self.details_text.insert("1.0", "Select a notification to view details...")
            self.details_text.configure(state="disabled")
