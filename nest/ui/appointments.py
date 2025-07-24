import tkinter as tk
from tkinter import ttk, messagebox
import os
import json
import threading
import datetime
from tkcalendar import Calendar
from dateutil.parser import parse
from PIL import Image, ImageTk

# Conditionally import Google Calendar client
try:
    from api.google_calendar import GoogleCalendarClient
    GOOGLE_CALENDAR_AVAILABLE = True
except ImportError:
    GOOGLE_CALENDAR_AVAILABLE = False

class AppointmentsModule(ttk.Frame):
    """Google Calendar based appointments module for Nest 2.3"""
    
    def __init__(self, parent):
        super().__init__(parent, padding=10)
        self.parent = parent
        
        # Initialize variables
        self.calendar_client = None
        self.events = []
        self.selected_event = None
        self.calendar_id = 'primary'  # Default to primary calendar
        self.loading = False
        
        # Store images as instance variables to prevent garbage collection
        self.icons = {}
        
        # Create the UI structure
        self._create_ui()
        
        # Initialize Google Calendar connection
        self._initialize_google_calendar()
    
    def _create_ui(self):
        """Create the main appointments UI"""
        # Main header
        header_frame = ttk.Frame(self)
        header_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(
            header_frame, 
            text="Appointments", 
            style="Header.TLabel"
        ).pack(side="left", anchor="w")
        
        # Add buttons for primary actions
        actions_frame = ttk.Frame(header_frame)
        actions_frame.pack(side="right", padx=5)
        
        # New Appointment button
        self.new_btn = ttk.Button(
            actions_frame,
            text="New Appointment",
            command=self._create_appointment,
            style="Accent.TButton"
        )
        self.new_btn.pack(side="left", padx=5)
        
        # Refresh button
        self.refresh_btn = ttk.Button(
            actions_frame,
            text="Refresh",
            command=lambda: self._load_events(force_refresh=True)
        )
        self.refresh_btn.pack(side="left", padx=5)
        
        # Settings button
        self.settings_btn = ttk.Button(
            actions_frame,
            text="Settings",
            command=self._show_settings
        )
        self.settings_btn.pack(side="left", padx=5)
        
        # Main content area with calendar and event list in a PanedWindow
        self.main_paned = ttk.PanedWindow(self, orient="horizontal")
        self.main_paned.pack(fill="both", expand=True, pady=5)
        
        # Left panel with calendar
        self.calendar_frame = ttk.LabelFrame(self.main_paned, text="Calendar")
        
        # Right panel with event list and details
        self.events_frame = ttk.LabelFrame(self.main_paned, text="Appointments")
        
        self.main_paned.add(self.calendar_frame, weight=4)
        self.main_paned.add(self.events_frame, weight=6)
        
        # Create calendar widget
        today = datetime.datetime.now()
        self.calendar = Calendar(
            self.calendar_frame,
            selectmode='day',
            year=today.year,
            month=today.month,
            day=today.day,
            showweeknumbers=False,
            background='#FFFFFF',
            foreground='#333333',
            bordercolor='#CCCCCC',
            headersbackground='#2e7d32',
            headersforeground='white',
            selectbackground='#4caf50',
            weekendbackground='#f5f5f5',
            weekendforeground='#333333',
            othermonthforeground='#999999',
            othermonthbackground='#f9f9f9',
            othermonthweforeground='#999999',
            othermonthwebackground='#f9f9f9',
        )
        self.calendar.pack(fill="both", expand=True, padx=10, pady=10)
        self.calendar.bind("<<CalendarSelected>>", self._on_date_selected)
        
        # Navigation buttons for calendar
        cal_nav_frame = ttk.Frame(self.calendar_frame)
        cal_nav_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        ttk.Button(
            cal_nav_frame, 
            text="Previous Month",
            command=self._prev_month
        ).pack(side="left")
        
        ttk.Button(
            cal_nav_frame, 
            text="Today",
            command=self._goto_today
        ).pack(side="left", padx=5)
        
        ttk.Button(
            cal_nav_frame, 
            text="Next Month",
            command=self._next_month
        ).pack(side="left")
        
        # Events section
        # Create a frame for the appointment list
        events_top_frame = ttk.Frame(self.events_frame)
        events_top_frame.pack(fill="x", padx=10, pady=5)
        
        # Search entry
        ttk.Label(events_top_frame, text="Search:").pack(side="left", padx=(0, 5))
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(events_top_frame, textvariable=self.search_var)
        self.search_entry.pack(side="left", fill="x", expand=True)
        self.search_var.trace("w", lambda name, index, mode: self._filter_events())
        
        # Create listbox with scrollbar for events
        list_frame = ttk.Frame(self.events_frame)
        list_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.events_list = tk.Listbox(
            list_frame, 
            bg="white", 
            fg="#333333",
            selectbackground="#4caf50",
            selectforeground="white",
            font=("Segoe UI", 10),
            activestyle="none",
            height=15
        )
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.events_list.yview)
        self.events_list.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side="right", fill="y")
        self.events_list.pack(side="left", fill="both", expand=True)
        self.events_list.bind('<<ListboxSelect>>', self._on_event_selected)
        
        # Event details frame
        self.details_frame = ttk.LabelFrame(self.events_frame, text="Appointment Details")
        self.details_frame.pack(fill="x", padx=10, pady=10)
        
        # Details content (initially empty)
        self.details_content = ttk.Frame(self.details_frame)
        self.details_content.pack(fill="both", expand=True, padx=10, pady=10)
        
        ttk.Label(
            self.details_content,
            text="Select an appointment to view details",
            style="Italic.TLabel"
        ).pack(pady=20)
        
        # Status bar
        self.status_frame = ttk.Frame(self)
        self.status_frame.pack(fill="x", pady=(5, 0))
        
        self.status_var = tk.StringVar(value="Ready")
        self.status_label = ttk.Label(
            self.status_frame, 
            textvariable=self.status_var,
            font=("Segoe UI", 9)
        )
        self.status_label.pack(side="left", padx=5)
        
        # Connection status indicator
        self.connection_var = tk.StringVar(value="Not connected")
        self.connection_label = ttk.Label(
            self.status_frame, 
            textvariable=self.connection_var,
            font=("Segoe UI", 9)
        )
        self.connection_label.pack(side="right", padx=5)
    
    def _initialize_google_calendar(self):
        """Initialize the Google Calendar client"""
        if not GOOGLE_CALENDAR_AVAILABLE:
            self.status_var.set("Google Calendar API not available")
            self.connection_var.set("Not connected")
            messagebox.showwarning(
                "Google Calendar Not Available", 
                "The Google Calendar API is not available. Please ensure the required libraries are installed."
            )
            return
        
        # Initialize the client in a separate thread to avoid UI freezing
        threading.Thread(target=self._connect_to_google, daemon=True).start()
    
    def _connect_to_google(self):
        """Connect to Google Calendar in a separate thread"""
        self.status_var.set("Connecting to Google Calendar...")
        
        try:
            self.calendar_client = GoogleCalendarClient()
            
            if self.calendar_client.is_authenticated():
                # Get the user's calendars
                calendars = self.calendar_client.get_calendar_list()
                primary = self.calendar_client.get_primary_calendar()
                
                if primary:
                    self.calendar_id = primary['id']
                
                # Update UI from the main thread
                self.after(0, lambda: self._update_connection_status(True))
                # Load events
                self.after(0, self._load_events)
            else:
                # Update UI from the main thread
                self.after(0, lambda: self._update_connection_status(False))
        except Exception as e:
            # Update UI from the main thread
            self.after(0, lambda: self._handle_connection_error(str(e)))
    
    def _update_connection_status(self, connected):
        """Update the connection status in the UI"""
        if connected:
            self.connection_var.set("Connected to Google Calendar")
            self.status_var.set("Ready")
        else:
            self.connection_var.set("Not connected")
            self.status_var.set("Authentication failed")
            messagebox.showerror(
                "Authentication Failed", 
                "Failed to authenticate with Google Calendar. Please check your credentials."
            )
    
    def _handle_connection_error(self, error_msg):
        """Handle connection errors"""
        self.connection_var.set("Connection error")
        self.status_var.set(f"Error: {error_msg}")
        messagebox.showerror(
            "Connection Error", 
            f"Error connecting to Google Calendar: {error_msg}"
        )
    
    def _load_events(self, force_refresh=False):
        """Load events from Google Calendar"""
        if not self.calendar_client or not self.calendar_client.is_authenticated():
            return
        
        if self.loading:
            return
            
        self.loading = True
        self.status_var.set("Loading appointments...")
        self.events_list.delete(0, tk.END)
        
        # Get the current month's start and end dates
        current_date = self.calendar.selection_get()
        year = current_date.year
        month = current_date.month
        
        # Create start and end dates for the current month
        if month == 12:
            next_month = 1
            next_year = year + 1
        else:
            next_month = month + 1
            next_year = year
            
        start_date = datetime.datetime(year, month, 1)
        end_date = datetime.datetime(next_year, next_month, 1)
        
        # Load events in a separate thread
        threading.Thread(
            target=self._fetch_events_thread,
            args=(start_date, end_date, force_refresh),
            daemon=True
        ).start()
    
    def _fetch_events_thread(self, start_date, end_date, force_refresh):
        """Fetch events in a separate thread"""
        try:
            events = self.calendar_client.get_events(
                self.calendar_id,
                time_min=start_date,
                time_max=end_date,
                max_results=100
            )
            
            # Store events
            self.events = events
            
            # Update UI in the main thread
            self.after(0, self._update_events_ui)
        except Exception as e:
            self.after(0, lambda: self._handle_loading_error(str(e)))
        finally:
            self.after(0, lambda: setattr(self, 'loading', False))
    
    def _update_events_ui(self):
        """Update the events UI with loaded events"""
        self.events_list.delete(0, tk.END)
        
        if not self.events:
            self.status_var.set("No appointments found")
            return
            
        # Sort events by start time
        self.events.sort(key=lambda e: e['start'])
        
        # Add to listbox
        for event in self.events:
            title = event['summary']
            
            # Format the date/time
            start_time = self._format_event_time(event['start'])
            
            # Add to listbox
            self.events_list.insert(tk.END, f"{start_time} - {title}")
        
        self.status_var.set(f"Loaded {len(self.events)} appointments")
        
        # Mark dates with events on the calendar
        self._highlight_event_dates()
    
    def _format_event_time(self, time_str):
        """Format an event time string for display"""
        try:
            dt = parse(time_str)
            return dt.strftime("%I:%M %p")
        except:
            return "All day"
    
    def _highlight_event_dates(self):
        """Highlight dates with events on the calendar"""
        # TODO: Implement date highlighting once we get a better understanding
        # of how to manipulate the calendar widget's appearance
        pass
    
    def _handle_loading_error(self, error_msg):
        """Handle errors when loading events"""
        self.status_var.set(f"Error loading appointments: {error_msg}")
        messagebox.showerror(
            "Loading Error", 
            f"Error loading appointments: {error_msg}"
        )
    
    def _filter_events(self):
        """Filter events based on search text"""
        search_text = self.search_var.get().lower()
        
        self.events_list.delete(0, tk.END)
        
        for event in self.events:
            title = event['summary'].lower()
            description = event.get('description', '').lower()
            location = event.get('location', '').lower()
            
            if search_text in title or search_text in description or search_text in location:
                # Format the date/time
                start_time = self._format_event_time(event['start'])
                
                # Add to listbox
                self.events_list.insert(tk.END, f"{start_time} - {event['summary']}")
    
    def _on_date_selected(self, event):
        """Handle date selection on the calendar"""
        selected_date = self.calendar.selection_get()
        
        # Filter events for the selected date
        self.events_list.delete(0, tk.END)
        
        # Keep track of whether we found any events
        found_events = False
        
        for event in self.events:
            event_date = parse(event['start']).date()
            
            if event_date == selected_date:
                # Format the date/time
                start_time = self._format_event_time(event['start'])
                
                # Add to listbox
                self.events_list.insert(tk.END, f"{start_time} - {event['summary']}")
                found_events = True
        
        if found_events:
            self.status_var.set(f"Showing appointments for {selected_date.strftime('%B %d, %Y')}")
        else:
            self.status_var.set(f"No appointments for {selected_date.strftime('%B %d, %Y')}")
    
    def _on_event_selected(self, event):
        """Handle event selection in the listbox"""
        if not self.events_list.curselection():
            return
            
        # Get selected index
        selected_idx = self.events_list.curselection()[0]
        
        # Filter to only visible events (in case of search/date filtering)
        visible_events = []
        for event in self.events:
            # Filtering logic based on current view state
            search_text = self.search_var.get().lower()
            selected_date = self.calendar.selection_get()
            
            title = event['summary'].lower()
            description = event.get('description', '').lower()
            location = event.get('location', '').lower()
            event_date = parse(event['start']).date()
            
            if ((search_text and (search_text in title or search_text in description or search_text in location)) or 
                (not search_text and event_date == selected_date)):
                visible_events.append(event)
        
        if selected_idx >= len(visible_events):
            return
            
        self.selected_event = visible_events[selected_idx]
        self._display_event_details(self.selected_event)
    
    def _display_event_details(self, event):
        """Display details for the selected event"""
        # Clear existing content
        for widget in self.details_content.winfo_children():
            widget.destroy()
        
        # Create a grid layout for details
        details_grid = ttk.Frame(self.details_content)
        details_grid.pack(fill="both", expand=True)
        
        # Event title
        ttk.Label(details_grid, text="Title:", font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w", pady=2)
        ttk.Label(details_grid, text=event['summary'], wraplength=300).grid(row=0, column=1, sticky="w", pady=2)
        
        # Start time
        ttk.Label(details_grid, text="Start:", font=("Segoe UI", 10, "bold")).grid(row=1, column=0, sticky="w", pady=2)
        start_time = parse(event['start'])
        ttk.Label(details_grid, text=start_time.strftime("%B %d, %Y %I:%M %p")).grid(row=1, column=1, sticky="w", pady=2)
        
        # End time
        ttk.Label(details_grid, text="End:", font=("Segoe UI", 10, "bold")).grid(row=2, column=0, sticky="w", pady=2)
        end_time = parse(event['end'])
        ttk.Label(details_grid, text=end_time.strftime("%B %d, %Y %I:%M %p")).grid(row=2, column=1, sticky="w", pady=2)
        
        # Location if available
        if event.get('location'):
            ttk.Label(details_grid, text="Location:", font=("Segoe UI", 10, "bold")).grid(row=3, column=0, sticky="w", pady=2)
            ttk.Label(details_grid, text=event['location'], wraplength=300).grid(row=3, column=1, sticky="w", pady=2)
        
        # Description if available
        if event.get('description'):
            ttk.Label(details_grid, text="Description:", font=("Segoe UI", 10, "bold")).grid(row=4, column=0, sticky="nw", pady=2)
            
            # Use Text widget for multi-line description
            desc_text = tk.Text(details_grid, wrap="word", height=5, width=40, font=("Segoe UI", 9))
            desc_text.insert("1.0", event['description'])
            desc_text.configure(state="disabled")  # Make read-only
            desc_text.grid(row=4, column=1, sticky="w", pady=2)
        
        # Action buttons
        action_frame = ttk.Frame(details_grid)
        action_frame.grid(row=5, column=0, columnspan=2, sticky="ew", pady=10)
        
        ttk.Button(
            action_frame,
            text="Edit",
            command=lambda: self._edit_appointment(event),
            style="Accent.TButton"
        ).pack(side="left", padx=5)
        
        ttk.Button(
            action_frame,
            text="Delete",
            command=lambda: self._delete_appointment(event),
            style="Danger.TButton"
        ).pack(side="left", padx=5)
    
    def _prev_month(self):
        """Go to previous month in calendar"""
        self.calendar._prev_month()
        self._load_events()
    
    def _next_month(self):
        """Go to next month in calendar"""
        self.calendar._next_month()
        self._load_events()
    
    def _goto_today(self):
        """Go to today in calendar"""
        today = datetime.datetime.now().date()
        self.calendar.selection_set(today)
        # Force calendar to update to current month
        self.calendar._date = today
        self.calendar._build_calendar()
        self._load_events()
    
    def _create_appointment(self):
        """Show dialog to create a new appointment"""
        # For now, just show a message that this feature is coming soon
        messagebox.showinfo(
            "Feature Coming Soon", 
            "The appointment creation feature is coming soon. This will allow you to create appointments directly in Google Calendar."
        )
        
    def _edit_appointment(self, event):
        """Show dialog to edit an appointment"""
        # For now, just show a message that this feature is coming soon
        messagebox.showinfo(
            "Feature Coming Soon", 
            "The appointment editing feature is coming soon. This will allow you to edit appointments directly in Google Calendar."
        )
    
    def _delete_appointment(self, event):
        """Show dialog to delete an appointment"""
        # For now, just show a message that this feature is coming soon
        messagebox.showinfo(
            "Feature Coming Soon", 
            "The appointment deletion feature is coming soon. This will allow you to delete appointments directly from Google Calendar."
        )
    
    def _show_settings(self):
        """Show Google Calendar settings dialog"""
        # For now, just show a message that this feature is coming soon
        messagebox.showinfo(
            "Feature Coming Soon", 
            "The Google Calendar settings feature is coming soon. This will allow you to configure your Google Calendar integration."
        )
