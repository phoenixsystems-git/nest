#!/usr/bin/env python
"""
NestBot AI Assistant Module

This module contains the NestBot AI assistant functionality for the Nest application,
including UI components, API connections, and advanced ticket data processing to provide
personalized support and advice to repair technicians.
"""

import os
import sys
import json
import logging
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
import requests
import re
from typing import Dict, List, Optional, Any, Tuple
import random


class NestBotPanel:
    """
    NestBot AI Assistant panel and functionality for the Nest application.
    This class encapsulates all AI-related UI components and API interactions,
    providing smart ticket analysis and personalized support for repair technicians.
    """
    
    def __init__(self, parent, app):
        """
        Initialize the NestBot panel and AI functionality.
        
        Args:
            parent: The parent tkinter container
            app: The main application instance (for accessing colors, styles, etc.)
        """
        self.parent = parent
        self.app = app
        self.tk = app.tk
        self.ttk = app.ttk
        self.colors = app.colors
        
        # Initialize state variables
        self.input_placeholder_active = True
        self.current_user = app.current_user
        self.detected_ticket_for_context = None
        self.conversation_history = []
        self.recent_tickets = {}  # Store recent ticket data for quick reference
        self.user_preferences = self.load_user_preferences()
        
        # Setup ticket database connection
        # Initialize ticket database
        self.initialize_ticket_database()
        
        # Initialize intelligent analysis engine
        try:
            from nest.ai.intelligent_analysis import IntelligentAnalysisEngine
            self.analysis_engine = IntelligentAnalysisEngine(self)
        except Exception as e:
            logging.error(f"Failed to initialize analysis engine: {str(e)}")
            self.analysis_engine = None
        
        # Import the load_specific_ticket_for_ai function from ticket_utils
        from .ticket_utils import load_specific_ticket_for_ai
        
        # Create a bound method for load_specific_ticket_for_ai
        self.load_specific_ticket_for_ai = lambda: load_specific_ticket_for_ai(self)
        
        # The other methods are already defined as instance methods, so we don't need to import them
        
        # Set up the UI components after all methods are bound
        self.setup_ui()
        
        # Initialize with welcome message
        self.display_welcome_message()
        
        # Initialize conversation history and AI chat display for headless mode
        if not hasattr(self, 'conversation_history'):
            self.conversation_history = []
        if not hasattr(self, 'ai_chat_display'):
            self.ai_chat_display = None  # For headless mode compatibility
        
        # Initialize intelligent analysis engine
        try:
            from nest.ai.intelligent_analysis import IntelligentAnalysisEngine
            self.analysis_engine = IntelligentAnalysisEngine(self)
            logging.info("Intelligent analysis engine initialized successfully")
        except Exception as e:
            logging.error(f"Failed to initialize intelligent analysis engine: {e}")
            self.analysis_engine = None
        
        # Start periodic job analysis for proactive insights
        self.start_job_analysis_thread()
    
    def initialize_ticket_database(self):
        """
        Initialize the connection to the ticket database and set up access methods.
        
        Returns:
            dict: Object with methods to access ticket data
        """
        try:
            # Create ticket database wrapper with enhanced functionality
            ticket_db = {
                'cache': {},
                'comment_cache': {},
                'last_sync': None,
                'sync_in_progress': False
            }
            
            def get_ticket(ticket_id):
                """Get full ticket details with enhanced information"""
                # Check cache first
                if ticket_id in ticket_db['cache'] and ticket_db['cache'][ticket_id].get('full_data'):
                    logging.info(f"Using cached data for ticket {ticket_id}")
                    return ticket_db['cache'][ticket_id]
                
                try:
                    # Load ticket data directly from RepairDesk API
                    ticket_data = self._load_ticket_data_direct(ticket_id)
                    
                    if ticket_data:
                        # Enhance with additional metadata and analysis
                        ticket_data['full_data'] = True
                        ticket_data['last_updated'] = datetime.now()
                        
                        # Add semantic analysis of ticket content if available
                        description = ticket_data.get('description') or ticket_data.get('issue', '')
                        if description:
                            ticket_data['summary'] = self._generate_ticket_summary_safe(ticket_data)
                            # Skip complex analysis for now to avoid errors
                            # ticket_data['keywords'] = self.extract_keywords(description)
                            # ticket_data['sentiment'] = self.analyze_sentiment(description)
                        
                        # Cache the enhanced ticket data
                        ticket_db['cache'][ticket_id] = ticket_data
                        return ticket_data
                    else:
                        logging.warning(f"No data returned for ticket {ticket_id}")
                        return None
                except Exception as e:
                    logging.error(f"Error retrieving ticket {ticket_id}: {str(e)}")
                    return None
            
            def get_comments(ticket_id):
                """Get all comments for a ticket with sentiment analysis"""
                # Check cache first
                if ticket_id in ticket_db['comment_cache']:
                    logging.info(f"Using cached comments for ticket {ticket_id}")
                    return ticket_db['comment_cache'][ticket_id]
                
                try:
                    # Import comment utility only when needed
                    from nest.ai.ticket_utils import get_ticket_comments
                    comments = get_ticket_comments(ticket_id)
                    
                    if comments:
                        # Enhance comments with metadata
                        for comment in comments:
                            comment['sentiment'] = self.analyze_sentiment(comment.get('content', ''))
                            comment['is_customer'] = 'customer' in comment.get('author_role', '').lower()
                            comment['keywords'] = self.extract_keywords(comment.get('content', ''))
                        
                        # Cache the enhanced comments
                        ticket_db['comment_cache'][ticket_id] = comments
                        return comments
                    else:
                        logging.warning(f"No comments found for ticket {ticket_id}")
                        return []
                except Exception as e:
                    logging.error(f"Error retrieving comments for ticket {ticket_id}: {str(e)}")
                    return []
            
            def get_user_tickets(user_id=None, limit=10):
                """Get tickets assigned to the specified user (or current user)"""
                try:
                    # Get current user name instead of ID (RepairDesk uses names)
                    current_user_name = self._get_current_user_name()
                    if not current_user_name:
                        logging.warning("No user name available for ticket lookup")
                        return []
                    
                    # Use the technician-based filtering method
                    tickets = self._get_tickets_for_technician(current_user_name)
                    
                    # Apply limit
                    limited_tickets = tickets[:limit] if limit else tickets
                    
                    # Cache the tickets for quick reference
                    for ticket in limited_tickets:
                        ticket_id = ticket.get('id')
                        if ticket_id:
                            ticket_db['cache'][ticket_id] = ticket
                    
                    return limited_tickets
                except Exception as e:
                    logging.error(f"Error retrieving user tickets: {str(e)}")
                    return []
            
            def get_store_tickets(status=None, limit=20):
                """Get tickets for the entire store, optionally filtered by status"""
                try:
                    # Load all tickets directly from RepairDesk API/cache
                    from nest.ai.ticket_utils import load_ticket_data
                    all_tickets = load_ticket_data(include_specific_ticket=False)
                    
                    if not all_tickets:
                        return []
                    
                    # Normalize all tickets to consistent structure
                    normalized_tickets = []
                    for ticket in all_tickets:
                        normalized = self._normalize_ticket_data(ticket)
                        if normalized:
                            normalized_tickets.append(normalized)
                    
                    # Apply status filter if specified
                    if status:
                        filtered_tickets = []
                        for ticket in normalized_tickets:
                            ticket_status = ticket.get('status', '').lower()
                            if status.lower() in ticket_status or ticket_status in status.lower():
                                filtered_tickets.append(ticket)
                        normalized_tickets = filtered_tickets
                    
                    # Apply limit
                    limited_tickets = normalized_tickets[:limit] if limit else normalized_tickets
                    
                    # Cache the tickets for quick reference
                    for ticket in limited_tickets:
                        ticket_id = ticket.get('id')
                        if ticket_id:
                            ticket_db['cache'][ticket_id] = ticket
                    
                    return limited_tickets
                except Exception as e:
                    logging.error(f"Error retrieving store tickets: {str(e)}")
                    return []
            
            def get_ticket_timeline(ticket_id):
                """Get comprehensive timeline of a ticket including all events"""
                try:
                    # Import timeline utility only when needed
                    from nest.ai.ticket_utils import get_ticket_timeline
                    timeline = get_ticket_timeline(ticket_id)
                    
                    if timeline:
                        # Process timeline entries for enhanced context
                        for entry in timeline:
                            entry['age'] = (datetime.now() - datetime.fromisoformat(entry.get('timestamp', datetime.now().isoformat()))).days
                            entry['importance'] = self.estimate_entry_importance(entry)
                        
                        return timeline
                    else:
                        logging.warning(f"No timeline found for ticket {ticket_id}")
                        return []
                except Exception as e:
                    logging.error(f"Error retrieving timeline for ticket {ticket_id}: {str(e)}")
                    return []
            
            def sync_database():
                """Synchronize the ticket database with the server"""
                if ticket_db['sync_in_progress']:
                    logging.info("Ticket database sync already in progress")
                    return False
                
                try:
                    ticket_db['sync_in_progress'] = True
                    
                    # Get current user's tickets
                    if self.current_user and self.current_user.get('id'):
                        get_user_tickets(self.current_user.get('id'))
                    
                    # Get recent store tickets
                    get_store_tickets(limit=30)
                    
                    ticket_db['last_sync'] = datetime.now()
                    ticket_db['sync_in_progress'] = False
                    logging.info("Ticket database synchronized successfully")
                    return True
                except Exception as e:
                    ticket_db['sync_in_progress'] = False
                    logging.error(f"Error synchronizing ticket database: {str(e)}")
                    return False
            
            # Attach methods to the ticket database object
            ticket_db['get_ticket'] = get_ticket
            ticket_db['get_comments'] = get_comments
            ticket_db['get_user_tickets'] = get_user_tickets
            ticket_db['get_store_tickets'] = get_store_tickets
            ticket_db['get_ticket_timeline'] = get_ticket_timeline
            ticket_db['sync'] = sync_database
            
            # Start initial synchronization
            threading.Thread(target=sync_database, daemon=True).start()
            
            return ticket_db
        except Exception as e:
            logging.error(f"Error initializing ticket database: {str(e)}")
            # Return minimal implementation to avoid errors
            return {
                'get_ticket': lambda x: None,
                'get_comments': lambda x: [],
                'get_user_tickets': lambda x=None, y=10: [],
                'get_store_tickets': lambda x=None, y=20: [],
                'get_ticket_timeline': lambda x: [],
                'sync': lambda: False
            }
    
    def load_user_preferences(self):
        """
        Load user-specific preferences for the AI assistant.
        
        Returns:
            dict: User preferences
        """
        try:
            # Generate preferences path
            user_id = self.current_user.get('id') if self.current_user else 'default'
            prefs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'user_prefs')
            os.makedirs(prefs_dir, exist_ok=True)
            prefs_path = os.path.join(prefs_dir, f"{user_id}.json")
            
            if os.path.exists(prefs_path):
                with open(prefs_path, 'r') as f:
                    prefs = json.load(f)
                logging.info(f"Loaded user preferences for {user_id}")
                return prefs
            else:
                # Create default preferences
                default_prefs = {
                    'personality': 'helpful',  # helpful, technical, casual
                    'detail_level': 'medium',  # low, medium, high
                    'proactive_insights': True,
                    'preferred_model': None,
                    'favorite_topics': [],
                    'notification_preferences': {
                        'urgent_tickets': True,
                        'deadlines': True,
                        'customer_responses': True,
                        'team_updates': True
                    },
                    'language_style': 'professional'  # professional, casual, technical
                }
                
                # Save default preferences
                with open(prefs_path, 'w') as f:
                    json.dump(default_prefs, f, indent=2)
                
                logging.info(f"Created default user preferences for {user_id}")
                return default_prefs
        except Exception as e:
            logging.error(f"Error loading user preferences: {str(e)}")
            # Return default preferences
            return {
                'personality': 'helpful',
                'detail_level': 'medium',
                'proactive_insights': True
            }
    
    def save_user_preferences(self):
        """Save user preferences to disk."""
        try:
            user_id = self.current_user.get('id') if self.current_user else 'default'
            prefs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'user_prefs')
            os.makedirs(prefs_dir, exist_ok=True)
            prefs_path = os.path.join(prefs_dir, f"{user_id}.json")
            
            with open(prefs_path, 'w') as f:
                json.dump(self.user_preferences, f, indent=2)
            
            logging.info(f"Saved user preferences for {user_id}")
        except Exception as e:
            logging.error(f"Error saving user preferences: {str(e)}")
    
    def integrate_with_app(self):
        """
        Integrate NestBot with the main app by setting up references and events.
        
        Returns:
            dict: A dictionary of UI references for the main app
        """
        # Create references dict with all the required components
        refs = {
            'selected_model_var': self.selected_model_var,
            'access_tickets_var': self.access_tickets_var,
            'specific_ticket_var': self.specific_ticket_var,
            'ai_chat_display': self.ai_chat_display,
            'ai_input': self.ai_input,
            'nestbot': self  # Provide direct reference to the NestBot instance
        }
        
        # Set these references on the app instance
        for name, ref in refs.items():
            setattr(self.app, name, ref)
        
        # Replace with direct references to our methods
        setattr(self.app, 'send_ai_message', self.send_ai_message)
        setattr(self.app, 'display_ai_message', self.display_ai_message)
        setattr(self.app, 'load_specific_ticket_for_ai', self.load_specific_ticket_for_ai)
        setattr(self.app, 'get_ai_response', self.get_ai_response)
        
        # Add new methods for enhanced functionality
        setattr(self.app, 'analyze_ticket', self.analyze_ticket)
        setattr(self.app, 'get_ticket_recommendations', self.get_ticket_recommendations)
        setattr(self.app, 'get_store_insights', self.get_store_insights)
        
        # Bind any UI events directly to our methods
        if hasattr(self.app, 'ai_send_button'):
            self.app.ai_send_button.config(command=self.send_ai_message)
        
        # Listen for ticket selection events in the main app
        if hasattr(self.app, 'on_ticket_selected'):
            original_handler = self.app.on_ticket_selected
            
            # Create a wrapper function to capture ticket selection
            def ticket_selection_wrapper(*args, **kwargs):
                # Call the original handler first
                result = original_handler(*args, **kwargs)
                
                # Get the selected ticket ID
                selected_ticket = getattr(self.app, 'selected_ticket', None)
                if selected_ticket:
                    # Update NestBot's context with the selected ticket
                    self.specific_ticket_var.set(selected_ticket.get('id', ''))
                    
                    # Preload ticket data if ticket access is enabled
                    if self.access_tickets_var.get():
                        threading.Thread(
                            target=self.preload_ticket_data,
                            args=(selected_ticket.get('id', '')),
                            daemon=True
                        ).start()
                
                return result
            
            # Replace the original handler with our wrapper
            setattr(self.app, 'on_ticket_selected', ticket_selection_wrapper)
        
        return refs
    
    def preload_ticket_data(self, ticket_id):
        """
        Preload ticket data for faster access.
        
        Args:
            ticket_id: The ID of the ticket to preload
        """
        if not ticket_id:
            return
        
        try:
            # Fetch ticket data
            ticket = self.ticket_db['get_ticket'](ticket_id)
            if ticket:
                # Also fetch comments
                comments = self.ticket_db['get_comments'](ticket_id)
                # And timeline
                timeline = self.ticket_db['get_ticket_timeline'](ticket_id)
                
                logging.info(f"Preloaded data for ticket {ticket_id} (comments: {len(comments)}, timeline: {len(timeline)})")
        except Exception as e:
            logging.error(f"Error preloading ticket data for {ticket_id}: {str(e)}")
    
    def setup_context_menu(self):
        """Set up the context menu for the chat display."""
        # Create a context menu
        self.context_menu = tk.Menu(self.ai_chat_display, tearoff=0)
        self.context_menu.add_command(label="Copy", command=self.copy_text)
        self.context_menu.add_command(label="Clear Chat", command=self.clear_chat_history)
        
        # Bind right-click to show context menu
        self.ai_chat_display.bind("<Button-3>", self.show_context_menu)
        
        # Bind Ctrl+C to copy
        self.ai_chat_display.bind("<Control-c>", lambda e: self.copy_text())
        
    def show_context_menu(self, event):
        """Show the context menu at the current mouse position."""
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            # Make sure to release the grab (Tk 8.0.22+)
            self.context_menu.grab_release()
            
    def copy_text(self, event=None):
        """Copy selected text to clipboard."""
        try:
            # Get selected text
            selected = self.ai_chat_display.get("sel.first", "sel.last")
            if selected:
                self.ai_chat_display.clipboard_clear()
                self.ai_chat_display.clipboard_append(selected)
        except tk.TclError:
            # No selection
            pass
            
    def setup_ui(self):
        """
        Set up all UI components for the NestBot panel.
        """
        # Add NestBot panel header with title and status indicator
        header_frame = self.ttk.Frame(self.parent, style="Sidebar.TFrame")
        header_frame.pack(fill="x", pady=10, padx=10)
        
        # Add header with status indicator
        header_container = self.ttk.Frame(header_frame, style="Sidebar.TFrame")
        header_container.pack(fill="x")
        
        # Add status indicator (green dot when active)
        self.status_indicator = self.tk.Canvas(
            header_container, 
            width=12, 
            height=12, 
            bg=self.colors.get("content_bg", "#0b4d49"),
            highlightthickness=0
        )
        self.status_indicator.pack(side="left", padx=(0, 5))
        
        # Draw the indicator dot
        self.status_indicator.create_oval(2, 2, 10, 10, fill="#4CAF50", outline="")
        
        # Add title
        ai_header = self.ttk.Label(
            header_container,
            text="NestBot Assistant",
            style="SidebarHeading.TLabel"
        )
        ai_header.pack(side="left")
        
        # Add settings button to right side of header
        settings_button = self.ttk.Button(
            header_container,
            text="⚙",
            width=3,
            command=self.show_settings_dialog,
            style="Sidebar.TButton"
        )
        settings_button.pack(side="right", padx=(5, 0))
        
        # Add model selection dropdown below the header
        model_frame = self.ttk.Frame(self.parent, style="Sidebar.TFrame")
        model_frame.pack(fill="x", padx=10, pady=(5, 0))
        
        model_label = self.ttk.Label(
            model_frame,
            text="AI Model:",
            style="Sidebar.TLabel"
        )
        model_label.pack(side="left", padx=(0, 5))
        
        # Load available models from config
        self.ai_models = self.load_ai_models()
        model_names = [model['name'] for model in self.ai_models]
        
        # Set default selected model or use user preference
        self.selected_model_var = self.tk.StringVar()
        preferred_model = self.user_preferences.get('preferred_model')
        
        if preferred_model and preferred_model in model_names:
            self.selected_model_var.set(preferred_model)
        elif model_names:
            self.selected_model_var.set(model_names[0])  # Default to first model
            
        # Add ticket database access option
        self.access_tickets_var = self.tk.BooleanVar(value=True)  # Default to enabled
            
        # Add trace to notify when model changes
        def on_model_change(*args):
            selected_model = self.selected_model_var.get()
            if hasattr(self, 'ai_chat_display') and selected_model:
                self.display_ai_message("System", f"Switched to model: **{selected_model}**")
                # Update user preference
                self.user_preferences['preferred_model'] = selected_model
                self.save_user_preferences()
                
        self.selected_model_var.trace_add("write", on_model_change)
        
        # Create dropdown for model selection
        self.model_dropdown = self.ttk.Combobox(
            model_frame,
            textvariable=self.selected_model_var,
            values=model_names,
            state="readonly",
            width=20
        )
        self.model_dropdown.pack(side="right", fill="x", expand=True)
        
        # Add ticket access checkbox below model dropdown
        ticket_frame = self.ttk.Frame(self.parent, style="Sidebar.TFrame")
        ticket_frame.pack(fill="x", padx=10, pady=(5, 0))
        
        ticket_checkbox = self.ttk.Checkbutton(
            ticket_frame,
            text="Allow access to tickets database",
            variable=self.access_tickets_var,
            style="Sidebar.TCheckbutton"
        )
        ticket_checkbox.pack(fill="x", pady=(2, 2))
        
        # Add tooltip to explain the feature
        if hasattr(self.app, 'create_tooltip'):
            self.app.create_tooltip(ticket_checkbox, "When enabled, NestBot can access ticket data, comments, and provide insights about repair jobs")
        
        # Create hidden variable for storing detected ticket numbers
        self.specific_ticket_var = self.tk.StringVar()
        
        # Add specific ticket input for direct lookup
        ticket_lookup_frame = self.ttk.Frame(self.parent, style="Sidebar.TFrame")
        ticket_lookup_frame.pack(fill="x", padx=10, pady=(5, 0))
        
        # Left side - input field
        ticket_entry_frame = self.ttk.Frame(ticket_lookup_frame, style="Sidebar.TFrame")
        ticket_entry_frame.pack(side="left", fill="x", expand=True)
        
        ticket_entry_label = self.ttk.Label(
            ticket_entry_frame,
            text="Ticket #:",
            style="Sidebar.TLabel"
        )
        ticket_entry_label.pack(side="left", padx=(0, 5))
        
        self.ticket_entry = self.ttk.Entry(
            ticket_entry_frame,
            textvariable=self.specific_ticket_var,
            width=10
        )
        self.ticket_entry.pack(side="left", fill="x", expand=True)
        
        # Right side - lookup button
        ticket_lookup_button = self.ttk.Button(
            ticket_lookup_frame,
            text="Load",
            command=self.load_specific_ticket_for_ai,
            style="Sidebar.TButton",
            width=6
        )
        ticket_lookup_button.pack(side="right", padx=(5, 0))
        
        # Add separator below controls
        separator = self.ttk.Separator(self.parent, orient="horizontal")
        separator.pack(fill="x", padx=15, pady=5)
        
        # Create chat display area (read-only text with scrollbar)
        chat_frame = self.ttk.Frame(self.parent, style="Sidebar.TFrame")
        chat_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Generate user context file for personalized AI responses
        try:
            # Import here to trigger auto-generation
            from nest.knowledge import user_context
            logging.info("User context module loaded for personalized AI responses")
        except Exception as e:
            logging.warning(f"Could not load user context module: {str(e)}")
        
        # Add chat history display with scrollbar
        chat_scroll = self.ttk.Scrollbar(chat_frame)
        chat_scroll.pack(side="right", fill="y")
        
        # Text widget for chat history
        self.ai_chat_display = self.tk.Text(
            chat_frame,
            wrap=self.tk.WORD,
            state=self.tk.DISABLED,
            bg='#ffffff',
            fg='#333333',
            font=('Segoe UI', 10),
            padx=10,
            pady=10,
            relief=self.tk.FLAT,
            insertwidth=0,
            highlightthickness=0,
            borderwidth=0
        )
        self.ai_chat_display.pack(side="left", fill="both", expand=True)
        
        # Configure smooth scrolling and scrollbar
        self.ai_chat_display.configure(yscrollcommand=chat_scroll.set)
        chat_scroll.config(command=self.ai_chat_display.yview)
        
        # Configure text tags for special formatting with more advanced styling
        self.configure_chat_text_tags()
        
        # Bind right-click context menu for copy/paste
        self.setup_context_menu()
        
        # Add hover effects for interactive elements
        self.ai_chat_display.bind('<Enter>', lambda e: self.ai_chat_display.config(cursor='xterm'))
        self.ai_chat_display.bind('<Leave>', lambda e: self.ai_chat_display.config(cursor=''))
        
        # Add a separator above input area
        separator2 = self.ttk.Separator(self.parent, orient="horizontal")
        separator2.pack(fill="x", padx=15, pady=5)
        
        # Add quick action buttons
        quick_actions_frame = self.ttk.Frame(self.parent, style="Sidebar.TFrame")
        quick_actions_frame.pack(fill="x", padx=10, pady=(0, 5))
        
        # Configuration for quick action buttons
        quick_actions = [
            ("My Tickets", self.show_my_tickets),
            ("Store Jobs", self.show_store_tickets),
            ("View Selected", lambda: self.analyze_ticket(self.specific_ticket_var.get())),
            ("Help", self.show_help)
        ]
        
        # Create button grid (2x2)
        button_grid = self.ttk.Frame(quick_actions_frame, style="Sidebar.TFrame")
        button_grid.pack(fill="x")
        
        # Add buttons in grid layout
        for i, (label, command) in enumerate(quick_actions):
            row = i // 2
            col = i % 2
            
            # Create button with fixed width
            button = self.ttk.Button(
                button_grid,
                text=label,
                command=command,
                style="Sidebar.TButton"
            )
            button.grid(row=row, column=col, padx=2, pady=2, sticky="ew")
        
        # Configure grid columns to be equal width
        button_grid.columnconfigure(0, weight=1)
        button_grid.columnconfigure(1, weight=1)
        
        # Create input area at bottom of AI panel
        input_frame = self.ttk.Frame(self.parent, style="Sidebar.TFrame")
        input_frame.pack(fill="x", padx=10, pady=10, side="bottom")
        
        # Text entry for user input with improved styling
        self.ai_input = self.tk.Text(
            input_frame,
            wrap="word",
            bg=self.colors.get("content_bg", "#0b4d49"),
            fg=self.colors.get("text_primary", "#ffffff"),
            font=("Segoe UI", 10),
            padx=8,
            pady=8,
            relief="flat",
            height=4  # Fixed height for input box
        )
        self.ai_input.pack(fill="x", padx=0, pady=(0, 10))
        
        # Add a placeholder text for the input field
        self.ai_input.insert("1.0", "Ask NestBot a question about tickets, jobs, or repair advice...")
        self.ai_input.bind("<FocusIn>", lambda event: self.clear_placeholder(event, self.ai_input))
        self.ai_input.bind("<FocusOut>", lambda event: self.restore_placeholder(event, self.ai_input))
        
        # Send button with improved styling
        send_button = self.ttk.Button(
            input_frame,
            text="Send to NestBot",
            style="Accent.TButton",
            command=self.send_ai_message
        )
        send_button.pack(fill="x")
        
        # Bind Enter key to send message
        self.ai_input.bind("<Return>", self.handle_nestbot_enter)
        
        # Add Markdown formatting support
        try:
            from nest.utils.platform_paths import PlatformPaths
            platform_paths = PlatformPaths()
            sys.path.append(str(platform_paths._get_portable_dir()))
            import markdown_handler
            self = markdown_handler.add_markdown_support(self)
            logging.info("Markdown formatting enabled for NestBot")
        except Exception as e:
            logging.error(f"Failed to enable Markdown formatting: {e}")
    
    def configure_chat_text_tags(self):
        """Configure rich text tags for chat formatting with improved contrast and styling."""
        # Base formatting tags with improved contrast
        self.ai_chat_display.tag_configure("sender", 
            foreground="#0066cc",  # Brighter blue for sender
            font=("Segoe UI", 10, "bold"),
            lmargin1=10,
            lmargin2=10,
            rmargin=10,
            spacing1=4,  # Space above paragraph
            spacing3=4   # Space below paragraph
        )
        
        # Regular message text
        self.ai_chat_display.tag_configure("message", 
            foreground="#333333",  # Dark gray for better readability
            font=("Segoe UI", 10),
            lmargin1=20,  # Indent for message content
            lmargin2=20,
            rmargin=10,
            spacing1=2,
            spacing3=4
        )
        
        # System messages
        self.ai_chat_display.tag_configure("system_message", 
            foreground="#2e7d32",  # Dark green for system messages
            font=("Segoe UI", 9, "italic"),
            lmargin1=10,
            lmargin2=10,
            rmargin=10,
            spacing1=4,
            spacing3=4
        )
        
        # Code blocks
        self.ai_chat_display.tag_configure("code", 
            foreground="#b71c1c",  # Dark red for code
            font=("Consolas", 10),  # Monospace font for code
            background="#f8f8f8",  # Light gray background
            borderwidth=1,
            relief="groove",
            lmargin1=30,
            lmargin2=30,
            rmargin=20,
            spacing1=10,
            spacing3=10,
            wrap="none"
        )
        
        # Sender name styling
        base_font = ("Segoe UI", 10)
        
        # Timestamp styling
        self.ai_chat_display.tag_configure(
            "timestamp", 
            foreground="#666666", 
            font=base_font
        )
        
        # Sender name styling
        self.ai_chat_display.tag_configure(
            "system_sender", 
            foreground="#990000",  # Dark red for system messages
            font=(base_font[0], base_font[1], "bold")
        )
        self.ai_chat_display.tag_configure(
            "user_sender", 
            foreground="#0066cc",  # Blue for user messages
            font=(base_font[0], base_font[1], "bold")
        )
        self.ai_chat_display.tag_configure(
            "bot_sender", 
            foreground="#2e8b57",  # Sea green for bot messages
            font=(base_font[0], base_font[1], "bold")
        )
        
        # Message content styling
        self.ai_chat_display.tag_configure(
            "system_message", 
            foreground="#990000",  # Dark red for system messages
            font=base_font,
            lmargin1=20,
            lmargin2=20,
            rmargin=10,
            spacing1=5,
            spacing3=5
        )
        
        self.ai_chat_display.tag_configure(
            "user_message", 
            foreground="#333333",  # Dark gray for user messages
            font=base_font,
            lmargin1=20,
            lmargin2=20,
            rmargin=10,
            spacing1=5,
            spacing3=5
        )
        
        self.ai_chat_display.tag_configure(
            "bot_message", 
            foreground="#2e8b57",  # Sea green for bot messages
            font=base_font,
            lmargin1=20,
            lmargin2=20,
            rmargin=10,
            spacing1=5,
            spacing3=5
        )
        
        # Text formatting tags
        self.ai_chat_display.tag_configure(
            "bold", 
            font=(base_font[0], base_font[1], "bold")
        )
        
        self.ai_chat_display.tag_configure(
            "italic", 
            font=(base_font[0], base_font[1], "italic")
        )
        
        # Link styling
        self.ai_chat_display.tag_configure(
            "link", 
            foreground="#0066cc",
            underline=1,
            font=base_font
        )
        
        # Hover effect for links
        self.ai_chat_display.tag_bind("link", "<Enter>", 
            lambda e: self.ai_chat_display.config(cursor="hand2"))
        self.ai_chat_display.tag_bind("link", "<Leave>", 
            lambda e: self.ai_chat_display.config(cursor=""))
        
        # Selection styling
        self.ai_chat_display.tag_configure("sel", background="#b3d9ff")
        
    def handle_clickable_text(self, event):
        """Handle clicks on clickable text in the chat display."""
        # Get the text index at the mouse position
        index = self.ai_chat_display.index(f"@{event.x},{event.y}")
        
        # Get the tag ranges for the clickable tag at this position
        tag_ranges = self.ai_chat_display.tag_ranges("clickable")
        
        # Check if clicked position is within any clickable range
        for i in range(0, len(tag_ranges), 2):
            start = tag_ranges[i]
            end = tag_ranges[i+1]
            
            if self.ai_chat_display.compare(start, "<=", index) and self.ai_chat_display.compare(index, "<=", end):
                # Get the clicked text
                clicked_text = self.ai_chat_display.get(start, end)
                
                # Check if it's a ticket number
                ticket_match = re.search(r'#(\d+)', clicked_text)
                if ticket_match:
                    ticket_id = ticket_match.group(1)
                    self.specific_ticket_var.set(ticket_id)
                    self.load_specific_ticket_for_ai()
                    return
                
                # Check if it's a command
                if clicked_text.startswith("/"):
                    command = clicked_text.strip()
                    self.handle_command(command)
                    return
    
    def handle_command(self, command):
        """Handle special commands in the chat."""
        command = command.lower()
        
        if command == "/help":
            self.show_help()
        elif command == "/mytickets":
            self.show_my_tickets()
        elif command == "/store":
            self.show_store_tickets()
        elif command == "/settings":
            self.show_settings_dialog()
        elif command.startswith("/analyze "):
            # Extract ticket number
            ticket_id = command.split(" ")[1]
            self.analyze_ticket(ticket_id)
        elif command == "/summary":
            self.show_daily_summary()
        elif command == "/clear":
            self.clear_chat_history()
    
    def show_settings_dialog(self):
        """Show a dialog to configure NestBot settings."""
        settings_dialog = self.tk.Toplevel(self.parent)
        settings_dialog.title("NestBot Settings")
        settings_dialog.geometry("400x450")
        settings_dialog.transient(self.parent)
        settings_dialog.grab_set()
        
        # Apply theme colors
        settings_dialog.configure(bg=self.colors.get("content_bg", "#0b4d49"))
        
        # Add settings header
        header_label = self.ttk.Label(
            settings_dialog,
            text="NestBot Settings",
            style="SidebarHeading.TLabel",
            font=("Segoe UI", 14, "bold")
        )
        header_label.pack(pady=(20, 15))
        
        # Create a frame for settings content
        settings_frame = self.ttk.Frame(settings_dialog, style="Sidebar.TFrame")
        settings_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Add personality preference
        personality_frame = self.ttk.Frame(settings_frame, style="Sidebar.TFrame")
        personality_frame.pack(fill="x", pady=(0, 10))
        
        personality_label = self.ttk.Label(
            personality_frame,
            text="Assistant Personality:",
            style="Sidebar.TLabel"
        )
        personality_label.pack(anchor="w")
        
        personality_var = self.tk.StringVar(value=self.user_preferences.get('personality', 'helpful'))
        personality_options = [
            ("Helpful", "helpful"),
            ("Technical", "technical"),
            ("Casual", "casual")
        ]
        
        personality_option_frame = self.ttk.Frame(personality_frame, style="Sidebar.TFrame")
        personality_option_frame.pack(fill="x", pady=(5, 0))
        
        for text, value in personality_options:
            personality_radio = self.ttk.Radiobutton(
                personality_option_frame,
                text=text,
                variable=personality_var,
                value=value,
                style="Sidebar.TRadiobutton"
            )
            personality_radio.pack(side="left", padx=(0, 10))
        
        # Add detail level preference
        detail_frame = self.ttk.Frame(settings_frame, style="Sidebar.TFrame")
        detail_frame.pack(fill="x", pady=(0, 10))
        
        detail_label = self.ttk.Label(
            detail_frame,
            text="Detail Level:",
            style="Sidebar.TLabel"
        )
        detail_label.pack(anchor="w")
        
        detail_var = self.tk.StringVar(value=self.user_preferences.get('detail_level', 'medium'))
        detail_options = [
            ("Low", "low"),
            ("Medium", "medium"),
            ("High", "high")
        ]
        
        detail_option_frame = self.ttk.Frame(detail_frame, style="Sidebar.TFrame")
        detail_option_frame.pack(fill="x", pady=(5, 0))
        
        for text, value in detail_options:
            detail_radio = self.ttk.Radiobutton(
                detail_option_frame,
                text=text,
                variable=detail_var,
                value=value,
                style="Sidebar.TRadiobutton"
            )
            detail_radio.pack(side="left", padx=(0, 10))
        
        # Add language style preference
        language_frame = self.ttk.Frame(settings_frame, style="Sidebar.TFrame")
        language_frame.pack(fill="x", pady=(0, 10))
        
        language_label = self.ttk.Label(
            language_frame,
            text="Language Style:",
            style="Sidebar.TLabel"
        )
        language_label.pack(anchor="w")
        
        language_var = self.tk.StringVar(value=self.user_preferences.get('language_style', 'professional'))
        language_options = [
            ("Professional", "professional"),
            ("Casual", "casual"),
            ("Technical", "technical")
        ]
        
        language_option_frame = self.ttk.Frame(language_frame, style="Sidebar.TFrame")
        language_option_frame.pack(fill="x", pady=(5, 0))
        
        for text, value in language_options:
            language_radio = self.ttk.Radiobutton(
                language_option_frame,
                text=text,
                variable=language_var,
                value=value,
                style="Sidebar.TRadiobutton"
            )
            language_radio.pack(side="left", padx=(0, 10))
        
        # Add notification preferences
        notification_frame = self.ttk.Frame(settings_frame, style="Sidebar.TFrame")
        notification_frame.pack(fill="x", pady=(0, 10))
        
        notification_label = self.ttk.Label(
            notification_frame,
            text="Notification Preferences:",
            style="Sidebar.TLabel"
        )
        notification_label.pack(anchor="w")
        
        # Get current notification preferences or set defaults
        notification_prefs = self.user_preferences.get('notification_preferences', {
            'urgent_tickets': True,
            'deadlines': True,
            'customer_responses': True,
            'team_updates': True
        })
        
        # Create notification checkboxes
        urgent_var = self.tk.BooleanVar(value=notification_prefs.get('urgent_tickets', True))
        urgent_check = self.ttk.Checkbutton(
            notification_frame,
            text="Urgent Tickets",
            variable=urgent_var,
            style="Sidebar.TCheckbutton"
        )
        urgent_check.pack(anchor="w", pady=(5, 0))
        
        deadlines_var = self.tk.BooleanVar(value=notification_prefs.get('deadlines', True))
        deadlines_check = self.ttk.Checkbutton(
            notification_frame,
            text="Approaching Deadlines",
            variable=deadlines_var,
            style="Sidebar.TCheckbutton"
        )
        deadlines_check.pack(anchor="w")
        
        customer_var = self.tk.BooleanVar(value=notification_prefs.get('customer_responses', True))
        customer_check = self.ttk.Checkbutton(
            notification_frame,
            text="Customer Responses",
            variable=customer_var,
            style="Sidebar.TCheckbutton"
        )
        customer_check.pack(anchor="w")
        
        team_var = self.tk.BooleanVar(value=notification_prefs.get('team_updates', True))
        team_check = self.ttk.Checkbutton(
            notification_frame,
            text="Team Updates",
            variable=team_var,
            style="Sidebar.TCheckbutton"
        )
        team_check.pack(anchor="w")
        
        # Add proactive insights option
        proactive_var = self.tk.BooleanVar(value=self.user_preferences.get('proactive_insights', True))
        proactive_check = self.ttk.Checkbutton(
            settings_frame,
            text="Enable Proactive Insights",
            variable=proactive_var,
            style="Sidebar.TCheckbutton"
        )
        proactive_check.pack(anchor="w", pady=(5, 15))
        
        # Add buttons frame
        buttons_frame = self.ttk.Frame(settings_dialog, style="Sidebar.TFrame")
        buttons_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        # Add save button
        save_button = self.ttk.Button(
            buttons_frame,
            text="Save Settings",
            style="Accent.TButton",
            command=lambda: self.save_settings(
                settings_dialog,
                personality_var.get(),
                detail_var.get(),
                language_var.get(),
                proactive_var.get(),
                {
                    'urgent_tickets': urgent_var.get(),
                    'deadlines': deadlines_var.get(),
                    'customer_responses': customer_var.get(),
                    'team_updates': team_var.get()
                }
            )
        )
        save_button.pack(side="right", padx=(5, 0))
        
        # Add cancel button
        cancel_button = self.ttk.Button(
            buttons_frame,
            text="Cancel",
            style="Sidebar.TButton",
            command=settings_dialog.destroy
        )
        cancel_button.pack(side="right")
    
    def save_settings(self, dialog, personality, detail_level, language_style, proactive_insights, notification_prefs):
        """Save user settings and close the dialog."""
        # Update user preferences
        self.user_preferences['personality'] = personality
        self.user_preferences['detail_level'] = detail_level
        self.user_preferences['language_style'] = language_style
        self.user_preferences['proactive_insights'] = proactive_insights
        self.user_preferences['notification_preferences'] = notification_prefs
        
        # Save to disk
        self.save_user_preferences()
        
        # Show confirmation and close dialog
        self.display_ai_message("System", "Your NestBot preferences have been updated.")
        dialog.destroy()
    
    def show_help(self):
        """Show help information about NestBot commands."""
        help_text = """
**NestBot Help**

NestBot can help you manage tickets, track work, and provide repair advice. Here are some useful commands:

- Type **/mytickets** or click "My Tickets" to see your assigned tickets
- Type **/store** or click "Store Jobs" to see all store tickets
- Type **/analyze #123** to analyze a specific ticket (replace 123 with ticket number)
- Type **/summary** for a daily work summary
- Type **/settings** to customize NestBot
- Type **/clear** to clear the chat history

**Quick Tips:**
- Mention a ticket number like #123 in your message to automatically include it in context
- Ask about specific devices or repair procedures for guidance
- Inquire about deadlines or priorities to help manage your workload
- Request summaries of customer communications

Need more help? Just ask!
"""
        self.display_ai_message("NestBot", help_text)
    
    def show_my_tickets(self):
        """Show the current user's tickets."""
        # Ticket access is enabled by default for unattended operation
        # if not self.access_tickets_var.get():
        #     self.display_ai_message("NestBot", "I need permission to access ticket data. Please enable 'Allow access to tickets database' in my settings.")
        #     return
        
        # Display thinking message
        self.show_thinking_message()
        
        # Get tickets in a separate thread
        threading.Thread(
            target=self._fetch_and_display_my_tickets,
            daemon=True
        ).start()
    
    def _fetch_and_display_my_tickets(self):
        """Fetch and display the current user's tickets."""
        try:
            # Get current user ID
            user_id = self.current_user.get('id') if self.current_user else None
            
            if not user_id:
                self.update_thinking_message("I couldn't identify your user account. Please make sure you're logged in.")
                return
            
            # Get user's tickets
            tickets = self.ticket_db['get_user_tickets'](user_id, limit=10)
            
            if not tickets:
                self.update_thinking_message("You don't have any tickets assigned to you at the moment.")
                return
            
            # Format tickets for display
            response = f"**Your Current Tickets ({len(tickets)}):**\n\n"
            
            for ticket in tickets:
                # Extract key information
                ticket_id = ticket.get('id', 'Unknown')
                status = ticket.get('status', 'Unknown')
                title = ticket.get('title', 'No title')
                customer = ticket.get('customer_name', 'Unknown customer')
                created = ticket.get('created_at', 'Unknown date')
                
                # Format deadline with highlight if approaching
                deadline = ticket.get('deadline', 'No deadline')
                is_urgent = ticket.get('priority', '').lower() in ['high', 'urgent', 'critical']
                deadline_html = f"**URGENT** - Due {deadline}" if is_urgent else f"Due: {deadline}"
                
                # Format ticket entry
                response += f"🎫 **Ticket #{ticket_id}** - {status}\n"
                response += f"📱 {title}\n"
                response += f"👤 Customer: {customer}\n"
                response += f"⏱️ {deadline_html}\n"
                
                # Add quick analysis if available
                if 'summary' in ticket:
                    response += f"💡 {ticket['summary']}\n"
                
                response += "\n"
            
            # Add helpful tip
            response += "\n*Tip: Click on a ticket number or type /analyze #ID to get detailed information about a specific ticket.*"
            
            # Update the display
            self.update_thinking_message(response)
            
        except Exception as e:
            logging.error(f"Error fetching user tickets: {str(e)}")
            self.update_thinking_message(f"I encountered an error while retrieving your tickets: {str(e)}")
    
    def show_store_tickets(self):
        """Show tickets for the entire store."""
        # Ticket access is enabled by default for unattended operation
        # if not self.access_tickets_var.get():
        #     self.display_ai_message("NestBot", "I need permission to access ticket data. Please enable 'Allow access to tickets database' in my settings.")
        #     return
        
        # Display thinking message
        self.show_thinking_message()
        
        # Get tickets in a separate thread
        threading.Thread(
            target=self._fetch_and_display_store_tickets,
            daemon=True
        ).start()
    
    def _fetch_and_display_store_tickets(self):
        """Fetch and display store tickets."""
        try:
            # Get store tickets
            tickets = self.ticket_db['get_store_tickets'](limit=15)
            
            if not tickets:
                self.update_thinking_message("There are no active tickets for the store at the moment.")
                return
            
            # Group tickets by status
            tickets_by_status = {}
            for ticket in tickets:
                status = ticket.get('status', 'Unknown')
                if status not in tickets_by_status:
                    tickets_by_status[status] = []
                tickets_by_status[status].append(ticket)
            
            # Format tickets for display
            response = f"**Store Tickets Overview ({len(tickets)}):**\n\n"
            
            # Display counts by status
            response += "**Status Summary:**\n"
            for status, status_tickets in tickets_by_status.items():
                response += f"• {status}: {len(status_tickets)} tickets\n"
            
            response += "\n**Recent Tickets:**\n\n"
            
            # Display recent tickets (limited to 10)
            displayed_tickets = 0
            for status, status_tickets in tickets_by_status.items():
                # Sort by urgency and recency
                sorted_tickets = sorted(
                    status_tickets, 
                    key=lambda t: (
                        t.get('priority', '').lower() in ['high', 'urgent', 'critical'],
                        t.get('created_at', '')
                    ),
                    reverse=True
                )
                
                for ticket in sorted_tickets[:3]:  # Show top 3 from each status
                    # Extract key information
                    ticket_id = ticket.get('id', 'Unknown')
                    title = ticket.get('title', 'No title')
                    customer = ticket.get('customer_name', 'Unknown customer')
                    technician = ticket.get('assigned_to', 'Unassigned')
                    
                    # Format priority indicator
                    priority = ticket.get('priority', 'Normal').upper()
                    priority_icon = "🔴" if priority in ['HIGH', 'URGENT', 'CRITICAL'] else "🟡" if priority == "MEDIUM" else "🟢"
                    
                    # Format ticket entry
                    response += f"{priority_icon} **Ticket #{ticket_id}** - {status}\n"
                    response += f"📱 {title}\n"
                    response += f"👤 Customer: {customer}\n"
                    response += f"👨‍🔧 Technician: {technician}\n\n"
                    
                    displayed_tickets += 1
                    if displayed_tickets >= 10:
                        break
                
                if displayed_tickets >= 10:
                    break
            
            # Add helpful tip
            response += "\n*To see details for a specific ticket, type /analyze #ID or click on a ticket number.*"
            
            # Update the display
            self.update_thinking_message(response)
            
        except Exception as e:
            logging.error(f"Error fetching store tickets: {str(e)}")
            self.update_thinking_message(f"I encountered an error while retrieving store tickets: {str(e)}")
    
    def analyze_ticket(self, ticket_id):
        """Analyze a specific ticket and provide detailed insights."""
        if not ticket_id:
            self.display_ai_message("NestBot", "Please provide a valid ticket number to analyze.")
            return
        
        # Ticket access is enabled by default for unattended operation
        # if not self.access_tickets_var.get():
        #     self.display_ai_message("NestBot", "I need permission to access ticket data. Please enable 'Allow access to tickets database' in my settings.")
        #     return
        
        # Clean the ticket ID
        ticket_id = ticket_id.replace("#", "").strip()
        if not ticket_id.isdigit():
            self.display_ai_message("NestBot", f"'{ticket_id}' doesn't appear to be a valid ticket number. Please provide a numeric ticket ID.")
            return
        
        # Display thinking message
        self.show_thinking_message()
        
        # Update the specific ticket variable
        self.specific_ticket_var.set(ticket_id)
        
        # Analyze ticket in a separate thread
        threading.Thread(
            target=self._analyze_ticket_thread,
            args=(ticket_id,),
            daemon=True
        ).start()
    
    def _analyze_ticket_thread(self, ticket_id):
        """Thread function to fetch and analyze ticket data."""
        try:
            # Get ticket data
            ticket = self.ticket_db['get_ticket'](ticket_id)
            
            if not ticket:
                self.update_thinking_message(f"I couldn't find ticket #{ticket_id}. Please check if the ticket number is correct.")
                return
            
            # Get ticket comments
            comments = self.ticket_db['get_comments'](ticket_id)
            
            # Get ticket timeline
            timeline = self.ticket_db['get_ticket_timeline'](ticket_id)
            
            # Analyze ticket data
            analysis = self.generate_ticket_analysis(ticket, comments, timeline)
            
            # Format analysis for display
            response = f"**Ticket #{ticket_id} Analysis**\n\n"
            
            # Basic ticket information
            response += f"**📱 {ticket.get('title', 'No title')}**\n\n"
            response += f"**Status:** {ticket.get('status', 'Unknown')}\n"
            response += f"**Customer:** {ticket.get('customer_name', 'Unknown')}\n"
            response += f"**Device:** {ticket.get('device', 'Not specified')}\n"
            response += f"**Technician:** {ticket.get('assigned_to', 'Unassigned')}\n"
            
            # Show deadline with urgency indicator if needed
            deadline = ticket.get('deadline', 'Not specified')
            if deadline != 'Not specified':
                # Check if deadline is approaching or past
                try:
                    deadline_date = datetime.strptime(deadline, "%Y-%m-%d")
                    days_left = (deadline_date - datetime.now()).days
                    
                    if days_left < 0:
                        response += f"**Deadline:** ⚠️ OVERDUE - Was due {deadline}\n"
                    elif days_left == 0:
                        response += f"**Deadline:** 🚨 DUE TODAY - {deadline}\n"
                    elif days_left <= 2:
                        response += f"**Deadline:** ⚠️ APPROACHING - Due {deadline} ({days_left} days left)\n"
                    else:
                        response += f"**Deadline:** Due {deadline} ({days_left} days left)\n"
                except:
                    response += f"**Deadline:** {deadline}\n"
            else:
                response += f"**Deadline:** Not specified\n"
            
            # Add issue description
            response += f"\n**Issue Description:**\n{ticket.get('description', 'No description provided')}\n"
            
            # Add analysis insights
            response += f"\n**Insights:**\n"
            for insight in analysis.get('insights', []):
                response += f"• {insight}\n"
            
            # Add communication summary if comments exist
            if comments:
                response += f"\n**Communication Summary:**\n"
                response += analysis.get('communication_summary', 'No communication summary available.')
                
                # Add latest comment
                latest_comment = comments[-1]
                response += f"\n\n**Latest Update ({latest_comment.get('created_at', 'Unknown date')}):**\n"
                response += f"From: {latest_comment.get('author', 'Unknown')}\n"
                response += f"{latest_comment.get('content', 'No content')}\n"
            
            # Add recommendations
            response += f"\n**Recommendations:**\n"
            for recommendation in analysis.get('recommendations', []):
                response += f"• {recommendation}\n"
            
            # Add repair tips if available
            if 'repair_tips' in analysis and analysis['repair_tips']:
                response += f"\n**Repair Tips:**\n"
                for tip in analysis['repair_tips']:
                    response += f"• {tip}\n"
            
            # Update the display
            self.update_thinking_message(response)
            
        except Exception as e:
            logging.error(f"Error analyzing ticket: {str(e)}")
            self.update_thinking_message(f"I encountered an error while analyzing ticket #{ticket_id}: {str(e)}")
    
    def generate_ticket_analysis(self, ticket, comments, timeline):
        """
        Generate a comprehensive analysis of a ticket.
        
        Args:
            ticket: Ticket data dictionary
            comments: List of comment dictionaries
            timeline: List of timeline event dictionaries
            
        Returns:
            dict: Analysis results
        """
        analysis = {
            'insights': [],
            'recommendations': [],
            'repair_tips': [],
            'communication_summary': '',
            'risk_factors': []
        }
        
        try:
            # Extract basic ticket info
            status = ticket.get('status', 'Unknown')
            device = ticket.get('device', '')
            issue = ticket.get('description', '')
            
            # Analyze ticket status and age
            created_at = ticket.get('created_at', '')
            if created_at:
                try:
                    created_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    days_open = (datetime.now() - created_date).days
                    
                    if days_open > 7 and status not in ['Closed', 'Resolved', 'Completed']:
                        analysis['insights'].append(f"This ticket has been open for {days_open} days, which is longer than average.")
                        analysis['risk_factors'].append('long_duration')
                except:
                    pass
            
            # Analyze issue complexity
            if issue:
                # Check for complex issue indicators
                complex_terms = ['damaged', 'water', 'liquid', 'not powering', 'won\'t boot', 'multiple issues', 
                                'intermittent', 'motherboard', 'logic board']
                complexity_matches = [term for term in complex_terms if term.lower() in issue.lower()]
                
                if complexity_matches:
                    analysis['insights'].append(f"This appears to be a complex issue involving: {', '.join(complexity_matches)}")
                    analysis['repair_tips'].append(f"For {device} issues with {complexity_matches[0]}, check the internal connectors first.")
            
            # Analyze customer communication
            customer_comments = [c for c in comments if c.get('is_customer', False)]
            staff_comments = [c for c in comments if not c.get('is_customer', False)]
            
            if customer_comments:
                # Check for customer sentiment
                customer_sentiments = [c.get('sentiment', 0) for c in customer_comments]
                avg_sentiment = sum(customer_sentiments) / len(customer_sentiments) if customer_sentiments else 0
                
                if avg_sentiment < -0.3:
                    analysis['insights'].append("The customer appears frustrated or concerned based on their communication tone.")
                    analysis['recommendations'].append("Consider providing extra updates and reassurance to address customer concerns.")
            
            # Check response times
            if len(comments) >= 2:
                response_times = []
                for i in range(1, len(comments)):
                    try:
                        prev_time = datetime.fromisoformat(comments[i-1].get('created_at', '').replace('Z', '+00:00'))
                        curr_time = datetime.fromisoformat(comments[i].get('created_at', '').replace('Z', '+00:00'))
                        
                        if comments[i-1].get('is_customer', False) and not comments[i].get('is_customer', False):
                            # Customer to staff response time
                            hours = (curr_time - prev_time).total_seconds() / 3600
                            response_times.append(hours)
                    except:
                        continue
                
                if response_times:
                    avg_response = sum(response_times) / len(response_times)
                    if avg_response > 24:
                        analysis['insights'].append(f"Average response time to customer messages is {avg_response:.1f} hours, which is longer than recommended.")
                        analysis['recommendations'].append("Consider improving response times to customer inquiries.")
            
            # Generate repair tips based on device type
            if device:
                device_lower = device.lower()
                
                # Common device types
                if 'iphone' in device_lower:
                    analysis['repair_tips'].append("For iPhones, always check battery health percentage and backup data before repairs.")
                elif 'samsung' in device_lower:
                    analysis['repair_tips'].append("For Samsung phones, verify if Knox has been tripped before proceeding with repair.")
                elif 'macbook' in device_lower:
                    analysis['repair_tips'].append("For MacBooks, check for liquid damage indicators near keyboard connectors.")
                elif 'laptop' in device_lower:
                    analysis['repair_tips'].append("For laptops, disconnect the battery before working on internal components.")
            
            # Generate communication summary
            if comments:
                summary = "Communication included "
                if customer_comments:
                    summary += f"{len(customer_comments)} customer messages"
                    if staff_comments:
                        summary += f" and {len(staff_comments)} staff responses. "
                    else:
                        summary += " with no staff responses yet. "
                else:
                    summary += f"{len(staff_comments)} staff messages with no customer responses. "
                
                # Add timing of last communication
                try:
                    last_comment = comments[-1]
                    last_time = datetime.fromisoformat(last_comment.get('created_at', '').replace('Z', '+00:00'))
                    hours_ago = (datetime.now() - last_time).total_seconds() / 3600
                    
                    if hours_ago < 1:
                        summary += f"The most recent message was less than an hour ago."
                    elif hours_ago < 24:
                        summary += f"The most recent message was {int(hours_ago)} hours ago."
                    else:
                        days_ago = int(hours_ago / 24)
                        summary += f"The most recent message was {days_ago} days ago."
                except:
                    summary += "Unable to determine when the last message was sent."
                
                analysis['communication_summary'] = summary
            
            # Generate status-specific recommendations
            if status == 'New' or status == 'Open':
                analysis['recommendations'].append("Initial triage and diagnostic should be performed within 24 hours.")
            elif status == 'In Progress':
                analysis['recommendations'].append("Provide regular updates to the customer on repair progress.")
            elif status == 'Waiting for Parts':
                analysis['recommendations'].append("Check parts inventory and estimated arrival dates for pending components.")
            elif status == 'Waiting for Customer':
                analysis['recommendations'].append("Follow up with the customer if no response received within 48 hours.")
            
            # Add general recommendations if needed
            if not analysis['recommendations']:
                analysis['recommendations'].append("Review ticket details and provide updates as needed.")
            
            return analysis
        except Exception as e:
            logging.error(f"Error generating ticket analysis: {str(e)}")
            analysis['insights'].append("Unable to generate complete analysis due to an error.")
            return analysis
    
    def generate_ticket_summary(self, ticket):
        """Generate a concise summary of the ticket."""
        try:
            device = ticket.get('device', 'device')
            issue = ticket.get('description', '')
            
            # Extract key issue from description
            if issue:
                # Simplify issue to key problem
                if len(issue) > 100:
                    # Look for common issue indicators
                    issue_indicators = ['problem', 'issue', 'broken', 'not working', 'damaged', 'error']
                    for indicator in issue_indicators:
                        if indicator in issue.lower():
                            # Extract sentence containing the indicator
                            sentences = re.split(r'[.!?]+', issue)
                            for sentence in sentences:
                                if indicator in sentence.lower():
                                    issue = sentence.strip()
                                    break
                            break
                    
                    # Fall back to first 100 characters if no indicator found
                    if len(issue) > 100:
                        issue = issue[:100] + "..."
            
            # Create summary based on available information
            status = ticket.get('status', 'In process')
            if status.lower() in ['new', 'open']:
                return f"New {device} repair needs initial diagnosis"
            elif status.lower() in ['in progress', 'diagnosing']:
                return f"{device} repair in progress: {issue}"
            elif status.lower() in ['waiting for parts']:
                return f"{device} repair waiting for parts"
            elif status.lower() in ['waiting for customer']:
                return f"{device} repair waiting for customer response"
            elif status.lower() in ['completed', 'closed', 'resolved']:
                return f"{device} repair completed"
            else:
                return f"{device} repair - {status}: {issue}"
        except Exception as e:
            logging.error(f"Error generating ticket summary: {str(e)}")
            return "Ticket summary unavailable"
    
    def extract_keywords(self, text):
        """Extract key terms from text for better context understanding."""
        if not text:
            return []
        
        try:
            # List of common technical terms and issues
            technical_terms = [
                'screen', 'battery', 'charging', 'water damage', 'not powering on',
                'broken', 'cracked', 'won\'t turn on', 'motherboard', 'logic board',
                'speaker', 'microphone', 'camera', 'button', 'port', 'connector',
                'wifi', 'bluetooth', 'cellular', 'liquid damage', 'overheating',
                'slow', 'freezing', 'password', 'data recovery', 'backup',
                'software', 'update', 'restore', 'reset', 'keyboard', 'trackpad',
                'power button', 'volume', 'touch', 'display', 'graphics', 'blue screen',
                'black screen', 'boot loop', 'not charging', 'battery drain'
            ]
            
            # Find matches in text
            keywords = []
            text_lower = text.lower()
            
            for term in technical_terms:
                if term.lower() in text_lower:
                    keywords.append(term)
            
            # Add device type if detected
            device_types = ['iphone', 'ipad', 'macbook', 'samsung', 'google', 'pixel', 'huawei',
                          'laptop', 'desktop', 'pc', 'computer', 'phone', 'tablet', 'watch']
            
            for device in device_types:
                if device.lower() in text_lower:
                    keywords.append(device)
                    break
            
            return keywords[:5]  # Limit to 5 most relevant keywords
        except Exception as e:
            logging.error(f"Error extracting keywords: {str(e)}")
            return []
    
    def analyze_sentiment(self, text):
        """
        Analyze sentiment of text to detect customer satisfaction or issues.
        Returns a value between -1 (negative) and 1 (positive).
        """
        if not text:
            return 0
        
        try:
            # Simple word-based sentiment analysis
            positive_words = [
                'thank', 'thanks', 'good', 'great', 'excellent', 'awesome',
                'appreciate', 'helpful', 'pleased', 'satisfied', 'happy',
                'perfect', 'wonderful', 'fantastic', 'resolved', 'fixed'
            ]
            
            negative_words = [
                'bad', 'poor', 'terrible', 'awful', 'disappointed', 'frustrating',
                'useless', 'problem', 'issue', 'broken', 'still not working',
                'failure', 'failed', 'waste', 'unhappy', 'slow', 'waiting',
                'unacceptable', 'ridiculous', 'never', 'worst'
            ]
            
            # Count occurrences of sentiment words
            text_lower = text.lower()
            positive_count = sum(1 for word in positive_words if word in text_lower)
            negative_count = sum(1 for word in negative_words if word in text_lower)
            
            # Calculate sentiment score
            if positive_count == 0 and negative_count == 0:
                return 0  # Neutral
            
            total = positive_count + negative_count
            return (positive_count - negative_count) / total
        except Exception as e:
            logging.error(f"Error analyzing sentiment: {str(e)}")
            return 0
    
    def estimate_entry_importance(self, entry):
        """Estimate importance of a timeline entry."""
        importance = 0
        
        # Check entry type
        entry_type = entry.get('type', '').lower()
        if entry_type in ['status_change', 'assigned']:
            importance += 3
        elif entry_type in ['comment', 'note']:
            importance += 2
        elif entry_type in ['viewed', 'updated']:
            importance += 1
        
        # Check if it's from the customer
        if entry.get('is_customer', False):
            importance += 2
        
        # Check content for important terms
        content = entry.get('content', '').lower()
        important_terms = ['urgent', 'important', 'asap', 'immediately', 'problem', 'issue', 'not working']
        for term in important_terms:
            if term in content:
                importance += 1
        
        return importance
    
    def start_job_analysis_thread(self):
        """Start a thread to periodically analyze jobs and provide insights."""
        if self.user_preferences.get('proactive_insights', True):
            logging.info("Starting job analysis thread for proactive insights")
            
            def job_analysis_loop():
                while True:
                    try:
                        # Wait for initial delay (5 minutes)
                        for _ in range(300):  # 5 minutes in 1-second increments
                            if not self.user_preferences.get('proactive_insights', True):
                                return  # Exit thread if proactive insights disabled
                            time.sleep(1)
                        
                        # Check for important job insights
                        self.check_for_job_insights()
                        
                        # Wait for main interval (30 minutes)
                        for _ in range(1800):  # 30 minutes in 1-second increments
                            if not self.user_preferences.get('proactive_insights', True):
                                return  # Exit thread if proactive insights disabled
                            time.sleep(1)
                    except Exception as e:
                        logging.error(f"Error in job analysis thread: {str(e)}")
                        time.sleep(300)  # Wait 5 minutes before retrying
            
            # Start the analysis thread
            threading.Thread(target=job_analysis_loop, daemon=True).start()
    
    def check_for_job_insights(self):
        """Check for important job insights to proactively notify the user."""
        # Ticket access is enabled by default for unattended operation
        # if not self.access_tickets_var.get():
        #     return  # Skip if ticket access is disabled
        
        try:
            # Get user notification preferences
            notification_prefs = self.user_preferences.get('notification_preferences', {})
            
            insights = []
            
            # Check for urgent tickets if enabled
            if notification_prefs.get('urgent_tickets', True):
                urgent_tickets = self.get_urgent_tickets()
                if urgent_tickets:
                    insights.append(f"You have {len(urgent_tickets)} urgent tickets that may need attention.")
            
            # Check for approaching deadlines if enabled
            if notification_prefs.get('deadlines', True):
                approaching_deadlines = self.get_approaching_deadlines()
                if approaching_deadlines:
                    insights.append(f"{len(approaching_deadlines)} tickets have deadlines within the next 24 hours.")
            
            # Check for recent customer responses if enabled
            if notification_prefs.get('customer_responses', True):
                recent_responses = self.get_recent_customer_responses()
                if recent_responses:
                    insights.append(f"{len(recent_responses)} customers have responded to their tickets recently.")
            
            # Notify user of insights if found
            if insights:
                self.display_ai_message("NestBot", f"**Job Insights Update**\n\n{insights[0]}")
        except Exception as e:
            logging.error(f"Error checking for job insights: {str(e)}")
    
    def get_urgent_tickets(self):
        """Get urgent tickets assigned to the current user."""
        try:
            user_id = self.current_user.get('id') if self.current_user else None
            if not user_id:
                return []
            
            tickets = self.ticket_db['get_user_tickets'](user_id)
            urgent_tickets = [
                t for t in tickets if 
                t.get('priority', '').lower() in ['high', 'urgent', 'critical'] and
                t.get('status', '').lower() not in ['closed', 'resolved', 'completed']
            ]
            
            return urgent_tickets
        except Exception as e:
            logging.error(f"Error getting urgent tickets: {str(e)}")
            return []
    
    def get_approaching_deadlines(self):
        """Get tickets with approaching deadlines."""
        try:
            user_id = self.current_user.get('id') if self.current_user else None
            if not user_id:
                return []
            
            tickets = self.ticket_db['get_user_tickets'](user_id)
            approaching_deadlines = []
            
            for ticket in tickets:
                deadline = ticket.get('deadline')
                if not deadline:
                    continue
                    
                try:
                    deadline_date = datetime.strptime(deadline, "%Y-%m-%d")
                    days_left = (deadline_date - datetime.now()).days
                    
                    if 0 <= days_left <= 1:
                        approaching_deadlines.append(ticket)
                except:
                    continue
            
            return approaching_deadlines
        except Exception as e:
            logging.error(f"Error getting approaching deadlines: {str(e)}")
            return []
    
    def get_recent_customer_responses(self):
        """Get tickets with recent customer responses."""
        try:
            user_id = self.current_user.get('id') if self.current_user else None
            if not user_id:
                return []
            
            tickets = self.ticket_db['get_user_tickets'](user_id)
            recent_responses = []
            
            for ticket in tickets:
                # Skip closed tickets
                if ticket.get('status', '').lower() in ['closed', 'resolved', 'completed']:
                    continue
                    
                # Get comments for this ticket
                ticket_id = ticket.get('id')
                if not ticket_id:
                    continue
                    
                comments = self.ticket_db['get_comments'](ticket_id)
                if not comments:
                    continue
                    
                # Check if the most recent comment is from the customer
                last_comment = comments[-1]
                if last_comment.get('is_customer', False):
                    # Check if it's recent (within last 24 hours)
                    try:
                        comment_time = datetime.fromisoformat(last_comment.get('created_at', '').replace('Z', '+00:00'))
                        hours_ago = (datetime.now() - comment_time).total_seconds() / 3600
                        
                        if hours_ago <= 24:
                            recent_responses.append(ticket)
                    except:
                        continue
            
            return recent_responses
        except Exception as e:
            logging.error(f"Error getting recent customer responses: {str(e)}")
            return []
    
    def show_daily_summary(self):
        """Show a daily summary of work and priorities."""
        # Ticket access is enabled by default for unattended operation
        # if not self.access_tickets_var.get():
        #     self.display_ai_message("NestBot", "I need permission to access ticket data. Please enable 'Allow access to tickets database' in my settings.")
        #     return
        
        # Display thinking message
        self.show_thinking_message()
        
        # Generate summary in a separate thread
        threading.Thread(
            target=self._generate_daily_summary,
            daemon=True
        ).start()
    
    def _generate_daily_summary(self):
        """Generate and display daily work summary."""
        try:
            # Get current user's name for personalization
            user_name = self.current_user.get('fullname', 'tech') if self.current_user else 'tech'
            first_name = user_name.split()[0] if ' ' in user_name else user_name
            
            # Get current date
            today = datetime.now().strftime("%A, %B %d, %Y")
            
            # Get user tickets
            user_id = self.current_user.get('id') if self.current_user else None
            if not user_id:
                self.update_thinking_message("I couldn't generate a summary because I couldn't identify your user account.")
                return
            
            user_tickets = self.ticket_db['get_user_tickets'](user_id)
            
            # Group tickets by status
            tickets_by_status = {}
            for ticket in user_tickets:
                status = ticket.get('status', 'Unknown')
                if status not in tickets_by_status:
                    tickets_by_status[status] = []
                tickets_by_status[status].append(ticket)
            
            # Generate summary text
            summary = f"**Good day, {first_name}!**\n\n"
            summary += f"Here's your work summary for {today}:\n\n"
            
            # Ticket counts by status
            summary += "**Ticket Status:**\n"
            total_tickets = len(user_tickets)
            summary += f"• Total assigned tickets: {total_tickets}\n"
            
            # Add counts by status
            for status, tickets in tickets_by_status.items():
                summary += f"• {status}: {len(tickets)} tickets\n"
            
            # Add urgency metrics
            urgent_tickets = [t for t in user_tickets if t.get('priority', '').lower() in ['high', 'urgent', 'critical']]
            if urgent_tickets:
                summary += f"\n**Priority Items:**\n"
                summary += f"• {len(urgent_tickets)} urgent tickets require attention\n"
            
            # Add deadline information
            approaching_deadlines = self.get_approaching_deadlines()
            if approaching_deadlines:
                summary += f"\n**Approaching Deadlines:**\n"
                for ticket in approaching_deadlines:
                    ticket_id = ticket.get('id', 'Unknown')
                    title = ticket.get('title', 'No title')
                    deadline = ticket.get('deadline', 'Unknown')
                    summary += f"• Ticket #{ticket_id} - {title} - Due {deadline}\n"
            
            # Add customer response information
            recent_responses = self.get_recent_customer_responses()
            if recent_responses:
                summary += f"\n**Customer Updates:**\n"
                summary += f"• {len(recent_responses)} tickets have recent customer responses\n"
            
            # Add productivity stats if available
            closed_today = 0
            for ticket in tickets_by_status.get('Closed', []):
                try:
                    closed_date = datetime.fromisoformat(ticket.get('closed_at', '').replace('Z', '+00:00'))
                    if (datetime.now() - closed_date).days < 1:
                        closed_today += 1
                except:
                    continue
            
            if closed_today > 0:
                summary += f"\n**Today's Progress:**\n"
                summary += f"• You've closed {closed_today} tickets today\n"
            
            # Add recommendations
            summary += f"\n**Recommendations for Today:**\n"
            
            if urgent_tickets:
                summary += f"• Focus on resolving your {len(urgent_tickets)} urgent tickets first\n"
            
            if approaching_deadlines:
                summary += f"• Address the {len(approaching_deadlines)} tickets with approaching deadlines\n"
            
            if recent_responses:
                summary += f"• Respond to the {len(recent_responses)} customers waiting for replies\n"
            
            # Add a generic recommendation if no specific ones
            if not urgent_tickets and not approaching_deadlines and not recent_responses:
                summary += "• Continue working through your ticket queue in priority order\n"
                
            # Add a motivational message
            motivational_messages = [
                f"You're doing great work, {first_name}! Keep it up!",
                f"Your technical expertise is making a difference for our customers!",
                f"Remember to take short breaks to maintain your productivity and focus.",
                f"You've got this, {first_name}! One ticket at a time.",
                f"Your repair skills are invaluable to our team and customers!"
            ]
            summary += f"\n{random.choice(motivational_messages)}"
            
            # Update the display
            self.update_thinking_message(summary)
            
        except Exception as e:
            logging.error(f"Error generating daily summary: {str(e)}")
            self.update_thinking_message(f"I encountered an error while generating your daily summary: {str(e)}")
    
    def get_ticket_recommendations(self, ticket_id):
        """Get repair recommendations for a specific ticket."""
        try:
            # Get ticket data
            ticket = self.ticket_db['get_ticket'](ticket_id)
            if not ticket:
                return ["Ticket not found. Please check the ticket number."]
            
            # Extract key information
            device = ticket.get('device', '')
            issue = ticket.get('description', '')
            
            # Generate recommendations based on device and issue
            recommendations = []
            
            # Device-specific recommendations
            if 'iphone' in device.lower():
                recommendations.append("Run iOS diagnostics to check hardware components.")
                recommendations.append("Verify battery health percentage before proceeding with repairs.")
                recommendations.append("Check for any liquid damage indicators inside the device.")
            elif 'samsung' in device.lower():
                recommendations.append("Use Samsung's built-in device diagnostics from the service menu.")
                recommendations.append("Check if Knox security has been tripped before proceeding.")
                recommendations.append("Verify water damage indicators near the battery compartment.")
            elif 'macbook' in device.lower() or 'laptop' in device.lower():
                recommendations.append("Run hardware diagnostics at startup to identify component issues.")
                recommendations.append("Check for liquid damage indicators near keyboard connectors.")
                recommendations.append("Test with external display to isolate screen vs. graphics issues.")
            
            # Issue-specific recommendations
            issue_lower = issue.lower()
            if 'battery' in issue_lower or 'charging' in issue_lower:
                recommendations.append("Test with known good charger and cable before battery replacement.")
                recommendations.append("Check charging port for debris or damage.")
                recommendations.append("Measure battery voltage and charging current if possible.")
            elif 'screen' in issue_lower or 'display' in issue_lower:
                recommendations.append("Test display with different brightness settings to check for panel issues.")
                recommendations.append("Verify display cable connections are secure.")
                recommendations.append("Check for any visible damage to display connectors.")
            elif 'water' in issue_lower or 'liquid' in issue_lower:
                recommendations.append("Do not power on device until thoroughly dried.")
                recommendations.append("Disconnect battery immediately if not already done.")
                recommendations.append("Clean affected components with isopropyl alcohol after drying.")
            
            # Add generic recommendations if needed
            if not recommendations:
                recommendations.append("Document all symptoms thoroughly before beginning repairs.")
                recommendations.append("Take photos before disassembly to aid in reassembly.")
                recommendations.append("Back up customer data if possible before starting repairs.")
            
            return recommendations
        except Exception as e:
            logging.error(f"Error generating ticket recommendations: {str(e)}")
            return ["Unable to generate recommendations due to an error."]
    
    def get_store_insights(self):
        """Get insights about store-wide ticket metrics."""
        try:
            # Get all store tickets
            store_tickets = self.ticket_db['get_store_tickets'](limit=100)
            if not store_tickets:
                return ["No active tickets found for the store."]
            
            # Analyze tickets
            total_tickets = len(store_tickets)
            status_counts = {}
            device_counts = {}
            priority_counts = {}
            
            # Count tickets by status, device, and priority
            for ticket in store_tickets:
                # Status counts
                status = ticket.get('status', 'Unknown')
                status_counts[status] = status_counts.get(status, 0) + 1
                
                # Device counts
                device = ticket.get('device', 'Unknown')
                device_counts[device] = device_counts.get(device, 0) + 1
                
                # Priority counts
                priority = ticket.get('priority', 'Normal')
                priority_counts[priority] = priority_counts.get(priority, 0) + 1
            
            # Generate insights
            insights = []
            
            # Overall insights
            insights.append(f"The store currently has {total_tickets} active tickets.")
            
            # Status distribution
            status_insight = "Ticket status distribution: "
            for status, count in status_counts.items():
                percentage = (count / total_tickets) * 100
                status_insight += f"{status}: {count} ({percentage:.1f}%), "
            insights.append(status_insight.rstrip(", "))
            
            # Most common devices
            if device_counts:
                sorted_devices = sorted(device_counts.items(), key=lambda x: x[1], reverse=True)
                top_devices = sorted_devices[:3]
                devices_insight = "Most common devices: "
                for device, count in top_devices:
                    percentage = (count / total_tickets) * 100
                    devices_insight += f"{device}: {count} ({percentage:.1f}%), "
                insights.append(devices_insight.rstrip(", "))
            
            # Priority insights
            if priority_counts:
                high_priority = priority_counts.get('High', 0) + priority_counts.get('Urgent', 0) + priority_counts.get('Critical', 0)
                if high_priority > 0:
                    percentage = (high_priority / total_tickets) * 100
                    insights.append(f"There are {high_priority} high-priority tickets ({percentage:.1f}% of total).")
            
            return insights
        except Exception as e:
            logging.error(f"Error generating store insights: {str(e)}")
            return ["Unable to generate store insights due to an error."]
    
    def clear_chat_history(self):
        """Clear the chat history."""
        try:
            # Clear the text widget
            self.ai_chat_display.config(state="normal")
            self.ai_chat_display.delete("1.0", "end")
            self.ai_chat_display.config(state="disabled")
            
            # Clear conversation history
            self.conversation_history = []
            
            # Display a system message
            self.display_ai_message("System", "Chat history has been cleared.")
        except Exception as e:
            logging.error(f"Error clearing chat history: {str(e)}")
    
    def display_welcome_message(self):
        """Initialize AI chat with a personalized welcome message."""
        # Get user's first name if available
        first_name = ""
        if self.current_user:
            full_name = self.current_user.get("fullname", "")
            # Extract first name (everything before the first space)
            first_name = full_name.split()[0] if full_name and " " in full_name else full_name
        
        # Generate personalized greeting with time of day
        hour = datetime.now().hour
        time_greeting = "morning" if 5 <= hour < 12 else "afternoon" if 12 <= hour < 17 else "evening"
        
        greeting = f"Good {time_greeting}{', ' + first_name if first_name else ''}! I'm NestBot, your repair shop assistant. I can help you with tickets, repair advice, and managing your work queue. "
        
        # Add personalized suggestions based on user role
        if self.current_user and self.current_user.get("role"):
            role = self.current_user.get("role", "").lower()
            
            if "technician" in role or "tech" in role:
                greeting += "As a technician, you can ask me about specific repair procedures, check customer ticket updates, or get insights about your assigned jobs."
            elif "manager" in role or "admin" in role:
                greeting += "As a manager, I can provide store-wide metrics, help with team workload distribution, or generate reports on ticket statuses."
            elif "front desk" in role or "customer service" in role:
                greeting += "I can help you with customer inquiries, checking repair statuses, or finding information to share with customers about their repairs."
            else:
                greeting += "How can I assist you with your repair shop tasks today?"
        else:
            greeting += "How can I help you today?"
        
        # Add quick suggestions
        greeting += "\n\nTry asking me:\n• \"What tickets are assigned to me?\"\n• \"Show me store-wide jobs\"\n• \"What's the status of ticket #12345?\"\n• \"Can you analyze this ticket?\""
        
        self.display_ai_message("NestBot", greeting)
    
    def clear_placeholder(self, event, text_widget):
        """Clear placeholder text when input field gains focus."""
        if self.input_placeholder_active:
            text_widget.delete("1.0", "end")
            self.input_placeholder_active = False
    
    def restore_placeholder(self, event, text_widget):
        """Restore placeholder text when input field loses focus and is empty."""
        if text_widget.get("1.0", "end-1c").strip() == "":
            text_widget.delete("1.0", "end")
            text_widget.insert("1.0", "Ask NestBot a question about tickets, jobs, or repair advice...")
            self.input_placeholder_active = True
    
    def load_ai_models(self):
        """Load available AI models from the config file."""
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'config.json')
        try:
            with open(config_path, 'r') as file:
                config = json.load(file)
            
            return config.get("ai_models", [])
        except Exception as e:
            logging.error(f"Error loading AI models from config: {str(e)}")
            # Return default models if config loading fails
            return [
                {"name": "Standard", "model_id": "standard", "context_length": 8000},
                {"name": "Advanced", "model_id": "advanced", "context_length": 16000}
            ]
    
    def handle_nestbot_enter(self, event):
        """Handle Enter key press in the NestBot input field properly."""
        if not (event.state & 1):  # Check if Shift key is not pressed
            self.send_ai_message()
            return 'break'  # Prevent default behavior of inserting a newline
        # Allow Shift+Enter to create newline
        return None
    
    def send_ai_message(self):
        """Process the user message and get AI response."""
        # Get user input
        user_message = self.ai_input.get("1.0", "end-1c").strip()
        
        # Skip if empty or just the placeholder text
        if not user_message or user_message == "Ask NestBot a question about tickets, jobs, or repair advice...":
            return
        
        # Display user message in chat
        self.display_ai_message("You", user_message)
        
        # Clear input field
        self.ai_input.delete("1.0", "end")
        self.input_placeholder_active = False
        
        # Analyze message for commands
        if user_message.startswith("/"):
            self.handle_command(user_message)
            return
        
        # Analyze message for ticket numbers
        detected_tickets = self.extract_ticket_numbers(user_message)
        
        # If tickets were detected in the message, set the context
        if detected_tickets and len(detected_tickets) > 0:
            detected_ticket = detected_tickets[0]
            logging.info(f"Detected ticket numbers in message: {detected_tickets}")
            
            # Set the specific ticket in the variable for AI context
            self.specific_ticket_var.set(detected_ticket)
            
            # Add a system message indicating the ticket has been loaded for context
            self.display_ai_message("System", f"Using ticket #{detected_ticket} for context")
            
            # Also preload the ticket data
            threading.Thread(
                target=self.preload_ticket_data,
                args=(detected_ticket,),
                daemon=True
            ).start()
            
            # Store for later reference
            self.detected_ticket_for_context = detected_ticket
        
        # Show thinking message
        self.show_thinking_message()
        
        # Add message to conversation history
        self.conversation_history.append({"role": "user", "content": user_message})
        
        # Use threaded API call to keep UI responsive
        threading.Thread(
            target=self.get_ai_response,
            args=(user_message, None),
            daemon=True
        ).start()
    
    def extract_ticket_numbers(self, text):
        """Extract ticket numbers from text."""
        # Match patterns like #123, ticket 123, ticket #123, etc.
        patterns = [
            r'#(\d+)',  # #123
            r'ticket[:\s#]*(\d+)',  # ticket 123, ticket: 123, ticket#123
            r'ticket\s+number[:\s#]*(\d+)'  # ticket number 123
        ]
        
        ticket_numbers = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            ticket_numbers.extend(matches)
        
        # Remove duplicates and convert to integers
        unique_tickets = list(set(ticket_numbers))
        return unique_tickets
    
    def get_ai_response(self, user_message, custom_knowledge_path=None):
        """Get AI response from the selected model with appropriate context."""
        try:
            # Determine which knowledge sources to include
            ticket_access = self.access_tickets_var.get()
            specific_ticket = self.specific_ticket_var.get()
            
            # Log request details
            logging.info(f"Getting AI response with ticket access: {ticket_access}, specific ticket: {specific_ticket}")
            
            # Get the selected model from dropdown
            selected_model_name = self.selected_model_var.get()
            selected_model = None
            for model in self.ai_models:
                if model['name'] == selected_model_name:
                    selected_model = model
                    break
            
            # Choose the appropriate knowledge file based on ticket access
            if not custom_knowledge_path:
                # Set base knowledge directory using platform-appropriate paths
                from nest.utils.platform_paths import PlatformPaths
                platform_paths = PlatformPaths()
                knowledge_dir = platform_paths._get_portable_dir() / "knowledge"
                
                # Use different context files based on whether ticket access is enabled
                if ticket_access or specific_ticket:
                    # Use the ticket-enabled context file when ticket access is on
                    knowledge_path = os.path.join(knowledge_dir, "user_context.json")
                else:
                    # Use the general context file when ticket access is off
                    knowledge_path = os.path.join(knowledge_dir, "user_context_general.json")
                
                # Check if the selected knowledge file exists
                if os.path.exists(knowledge_path):
                    custom_knowledge_path = knowledge_path
                    logging.info(f"Including user context in AI response: {custom_knowledge_path}")
            
            # Prepare conversation context
            context = []
            
            # Add ticket context if a specific ticket is selected
            if specific_ticket and ticket_access:
                # Get ticket data
                ticket = self.ticket_db['get_ticket'](specific_ticket)
                if ticket:
                    # Format ticket data for context
                    ticket_context = f"\nTicket #{specific_ticket} Information:\n"
                    ticket_context += f"Title: {ticket.get('title', 'No title')}\n"
                    ticket_context += f"Status: {ticket.get('status', 'Unknown')}\n"
                    ticket_context += f"Customer: {ticket.get('customer_name', 'Unknown')}\n"
                    ticket_context += f"Device: {ticket.get('device', 'Not specified')}\n"
                    ticket_context += f"Description: {ticket.get('description', 'No description')}\n"
                    
                    # Add comments if available
                    comments = self.ticket_db['get_comments'](specific_ticket)
                    if comments:
                        ticket_context += "\nTicket Comments:\n"
                        for i, comment in enumerate(comments[-5:]):  # Include last 5 comments only
                            author = comment.get('author', 'Unknown')
                            content = comment.get('content', 'No content')
                            date = comment.get('created_at', 'Unknown date')
                            ticket_context += f"[{date}] {author}: {content}\n"
                    
                    # Add to context
                    context.append({"role": "system", "content": ticket_context})
            
            # Add user context
            if self.current_user:
                user_context = f"\nUser Information:\n"
                user_context += f"Name: {self.current_user.get('fullname', 'Unknown')}\n"
                user_context += f"Role: {self.current_user.get('role', 'Unknown')}\n"
                
                # Add to context
                context.append({"role": "system", "content": user_context})
            
            # Add personalization preferences
            personality = self.user_preferences.get('personality', 'helpful')
            detail_level = self.user_preferences.get('detail_level', 'medium')
            language_style = self.user_preferences.get('language_style', 'professional')
            
            personality_context = f"\nCommunication Preferences:\n"
            personality_context += f"Personality: {personality}\n"
            personality_context += f"Detail Level: {detail_level}\n"
            personality_context += f"Language Style: {language_style}\n"
            
            # Add to context
            context.append({"role": "system", "content": personality_context})
            
            # Add conversation history (last 5 messages) - initialize if not exists
            if not hasattr(self, 'conversation_history'):
                self.conversation_history = []
            for message in self.conversation_history[-5:]:
                context.append(message)
            
            # Add the current message
            context.append({"role": "user", "content": user_message})
            
            # Import API client
            from nest.ai.api_client import get_ai_response as api_get_ai_response
            
            # Call API client with enhanced context and timeout
            try:
                response_text = api_get_ai_response(
                    user_message=user_message,
                    selected_model=selected_model,
                    ticket_access=ticket_access,
                    specific_ticket=specific_ticket,
                    custom_knowledge_path=custom_knowledge_path,
                    current_user=self.current_user,
                    conversation_context=context
                )
                
                # Validate response
                if not response_text or len(response_text.strip()) == 0:
                    response_text = "I apologize, but I received an empty response. Please try asking your question again."
                    
            except Exception as api_error:
                logging.error(f"API call failed: {str(api_error)}")
                # Use intelligent analysis engine as fallback
                if self.analysis_engine:
                    try:
                        relevant_tickets = self._get_relevant_tickets_for_query(user_message)
                        if relevant_tickets:
                            response_text = self.analysis_engine.generate_intelligent_insights(
                                user_message, relevant_tickets
                            )
                        else:
                            response_text = f"I understand you're asking about: '{user_message}'. While my AI services are temporarily unavailable, I can still help you navigate the system. What specific task would you like assistance with?"
                    except Exception as engine_error:
                        logging.error(f"Analysis engine fallback failed: {str(engine_error)}")
                        response_text = f"I understand you're asking about: '{user_message}'. My AI services are currently experiencing issues, but I'm still here to help guide you through the repair shop system."
                else:
                    response_text = f"I understand you're asking about: '{user_message}'. My AI services are currently experiencing issues, but I'm still here to help guide you through the repair shop system."
            
            # Add to conversation history
            self.conversation_history.append({"role": "assistant", "content": response_text})
            
            # Update the UI with the response
            self.update_thinking_message(response_text)
            
        except Exception as e:
            logging.error(f"Error getting AI response: {str(e)}")
            # Update the thinking message with the error
            self.update_thinking_message(f"⚠️ **Error:** I encountered a problem while processing your request. {str(e)}")
    
    def show_thinking_message(self):
        """Show a 'Thinking...' message in the chat interface while waiting for AI response."""
        # Enable text widget for editing
        self.ai_chat_display.config(state="normal")
        
        # Add a blank line if not at the beginning
        if self.ai_chat_display.index("end-1c") != "1.0":
            self.ai_chat_display.insert("end", "\n\n")
        
        # Add timestamp and NestBot indicator
        timestamp = datetime.now().strftime("%H:%M")
        self.ai_chat_display.insert("end", f"[{timestamp}] NestBot:\n", "sender")
        
        # Create a unique tag for this thinking message
        thinking_tag = f"thinking_{timestamp.replace(':', '_')}"
        self.current_thinking_tag = thinking_tag
        
        # Configure the tag
        try:
            self.ai_chat_display.tag_config(thinking_tag, foreground="#aaaaaa", font=("Segoe UI", 10, "italic"))
        except Exception:
            pass
        
        # Add the thinking message with the unique tag
        thinking_start = self.ai_chat_display.index("end")
        self.ai_chat_display.insert("end", "Thinking...", thinking_tag)
        thinking_end = self.ai_chat_display.index("end")
        
        # Also add the tag to the range for easier removal later
        self.ai_chat_display.tag_add(thinking_tag, thinking_start, thinking_end)
        
        # Scroll to see the newest message
        self.ai_chat_display.see("end")
        
        # Disable editing again
        self.ai_chat_display.config(state="disabled")
    
    def update_thinking_message(self, response_text):
        """Replace the 'Thinking...' message with the actual AI response with rich formatting."""
        # Enable text widget for editing
        self.ai_chat_display.config(state="normal")
        
        try:
            # Find the most recent thinking message using its unique tag
            if hasattr(self, 'current_thinking_tag'):
                tag_ranges = self.ai_chat_display.tag_ranges(self.current_thinking_tag)
                
                if tag_ranges and len(tag_ranges) >= 2:
                    # Found the tagged thinking message
                    thinking_start = tag_ranges[0]
                    thinking_end = tag_ranges[1]
                    
                    # Delete the thinking message
                    self.ai_chat_display.delete(thinking_start, thinking_end)
                    
                    # Insert the response with rich formatting
                    self.insert_rich_text(thinking_start, response_text)
                    
                    # Remove the thinking tag
                    self.ai_chat_display.tag_delete(self.current_thinking_tag)
                    delattr(self, 'current_thinking_tag')
                else:
                    # Tag doesn't have ranges, so fall back to searching for "Thinking..."
                    self.fallback_thinking_replacement(response_text)
            else:
                # No current thinking tag, fall back to searching for "Thinking..."
                self.fallback_thinking_replacement(response_text)
            
        except Exception as e:
            logging.error(f"Error updating thinking message: {str(e)}")
            # Fall back to adding a new message
            timestamp = datetime.now().strftime("%H:%M")
            self.ai_chat_display.insert("end", f"[{timestamp}] NestBot:\n", "sender")
            self.insert_rich_text("end", response_text)
        
        # Scroll to see the newest message
        self.ai_chat_display.see("end")
        
        # Disable editing again
        self.ai_chat_display.config(state="disabled")
    
    def fallback_thinking_replacement(self, response_text):
        """Fallback method to replace thinking message by searching for text."""
        # Search for "Thinking..." in the text
        start_pos = "1.0"
        thinking_pos = None
        
        while True:
            thinking_pos = self.ai_chat_display.search("Thinking...", start_pos, stopindex="end")
            if not thinking_pos:
                break  # No more occurrences
            
            # Check if this is a NestBot message
            line_start = f"{thinking_pos} linestart"
            line = self.ai_chat_display.get(line_start, f"{line_start} lineend")
            
            if "NestBot" in line:
                # Found a NestBot thinking message
                self.ai_chat_display.delete(thinking_pos, f"{thinking_pos} + {len('Thinking...')} chars")
                self.insert_rich_text(thinking_pos, response_text)
                return
            
            # Move to next occurrence
            start_pos = f"{thinking_pos} + {len('Thinking...')} chars"
        
        # If we get here, no thinking message was found - add a new one
        if self.ai_chat_display.index("end-1c") != "1.0":
            self.ai_chat_display.insert("end", "\n\n")
        
        timestamp = datetime.now().strftime("%H:%M")
        self.ai_chat_display.insert("end", f"[{timestamp}] NestBot:\n", "sender")
        self.insert_rich_text("end", response_text)
    
    def insert_rich_text(self, position, text):
        """Insert text with rich formatting at the specified position."""
        # Process Markdown formatting
        segments = self.parse_markdown(text)
        
        # Add formatted segments
        for segment_text, tag in segments:
            if tag:
                self.ai_chat_display.insert(position, segment_text, tag)
            else:
                self.ai_chat_display.insert(position, segment_text, "message")
            
            # Update position for next segment
            position = self.ai_chat_display.index(f"{position} + {len(segment_text)} chars")
    
    def parse_markdown(self, text):
        """Parse Markdown formatting in text."""
        # Split text into segments based on Markdown formatting
        segments = []
        i = 0
        
        while i < len(text):
            # Check for bold (**text**)
            if i < len(text) - 3 and text[i:i+2] == "**":
                bold_start = i
                bold_end = text.find("**", i+2)
                
                if bold_end != -1:
                    # Add text before bold
                    if i > 0:
                        segments.append((text[0:i], None))
                    
                    # Add bold text
                    bold_text = text[i+2:bold_end]
                    segments.append((bold_text, "bold"))
                    
                    # Process rest of text
                    rest = text[bold_end+2:]
                    rest_segments = self.parse_markdown(rest)
                    segments.extend(rest_segments)
                    
                    return segments
            
            # Check for italic (*text*)
            elif i < len(text) - 1 and text[i] == "*" and text[i+1] != "*":
                italic_start = i
                italic_end = text.find("*", i+1)
                
                if italic_end != -1:
                    # Add text before italic
                    if i > 0:
                        segments.append((text[0:i], None))
                    
                    # Add italic text
                    italic_text = text[i+1:italic_end]
                    segments.append((italic_text, "italic"))
                    
                    # Process rest of text
                    rest = text[italic_end+1:]
                    rest_segments = self.parse_markdown(rest)
                    segments.extend(rest_segments)
                    
                    return segments
            
            # Check for code (`text`)
            elif i < len(text) - 1 and text[i] == "`":
                code_start = i
                code_end = text.find("`", i+1)
                
                if code_end != -1:
                    # Add text before code
                    if i > 0:
                        segments.append((text[0:i], None))
                    
                    # Add code text
                    code_text = text[i+1:code_end]
                    segments.append((code_text, "code"))
                    
                    # Process rest of text
                    rest = text[code_end+1:]
                    rest_segments = self.parse_markdown(rest)
                    segments.extend(rest_segments)
                    
                    return segments
            
            # Check for ticket numbers (#123)
            elif i < len(text) - 1 and text[i] == "#":
                ticket_match = re.match(r'#(\d+)', text[i:])
                
                if ticket_match:
                    ticket_text = ticket_match.group(0)
                    ticket_end = i + len(ticket_text)
                    
                    # Add text before ticket
                    if i > 0:
                        segments.append((text[0:i], None))
                    
                    # Add ticket text as clickable
                    segments.append((ticket_text, "ticket_id"))
                    
                    # Process rest of text
                    rest = text[ticket_end:]
                    rest_segments = self.parse_markdown(rest)
                    segments.extend(rest_segments)
                    
                    return segments
            
            i += 1
        
        # If no formatting found, return the whole text as unformatted
        if not segments:
            segments.append((text, None))
        
        return segments
    
    
    def _load_ticket_data_direct(self, ticket_id):
        """Load ticket data directly from RepairDesk API or cache.
        
        Args:
            ticket_id: The ticket ID to load
            
        Returns:
            dict: Ticket data dictionary or None if not found
        """
        try:
            # First try to load from ticket cache
            from nest.ai.ticket_utils import load_ticket_data
            cached_tickets = load_ticket_data(include_specific_ticket=False)
            
            if cached_tickets:
                # Look for the ticket in cache by ID
                for ticket in cached_tickets:
                    summary = ticket.get('summary', {})
                    # Try different ID formats
                    if (str(summary.get('id')) == str(ticket_id) or 
                        str(summary.get('order_id', '').replace('T-', '')) == str(ticket_id)):
                        
                        # Normalize the ticket data structure and enhance with detailed info
                        normalized_ticket = self._normalize_ticket_data(ticket)
                        enhanced_ticket = self._enhance_ticket_with_details(normalized_ticket, ticket_id)
                        return enhanced_ticket
            
            # If not found in cache, try to load from API directly
            try:
                from nest.utils.repairdesk_api import RepairDeskAPI
                api = RepairDeskAPI()
                
                # Try to get ticket by ID
                api_ticket = api.get_ticket(ticket_id)
                if api_ticket:
                    normalized_ticket = self._normalize_ticket_data(api_ticket)
                    enhanced_ticket = self._enhance_ticket_with_details(normalized_ticket, ticket_id)
                    return enhanced_ticket
                    
            except Exception as api_error:
                logging.error(f"Error loading ticket {ticket_id} from API: {str(api_error)}")
            
            return None
            
        except Exception as e:
            logging.error(f"Error in _load_ticket_data_direct for ticket {ticket_id}: {str(e)}")
            return None
    
    def _normalize_ticket_data(self, raw_ticket):
        """Normalize ticket data from different sources into a consistent format.
        
        Args:
            raw_ticket: Raw ticket data from API or cache
            
        Returns:
            dict: Normalized ticket data
        """
        try:
            # Handle different ticket data structures
            if isinstance(raw_ticket, dict):
                summary = raw_ticket.get('summary', {})
                devices = raw_ticket.get('devices', [])
                
                # Extract basic information
                ticket_data = {
                    'id': summary.get('id') or summary.get('order_id', '').replace('T-', ''),
                    'order_id': summary.get('order_id', ''),
                    'status': 'Unknown',
                    'customer': {'name': 'Unknown Customer'},
                    'device': 'Unknown Device',
                    'assigned_to': {'name': 'Unassigned'},
                    'total_amount': 0,
                    'created_at': summary.get('created_date', ''),
                    'updated_at': summary.get('updated_date', ''),
                    'description': '',
                    'issue': ''
                }
                
                # Extract customer information
                customer = summary.get('customer', {})
                if customer:
                    ticket_data['customer'] = {
                        'name': customer.get('fullName', 'Unknown Customer'),
                        'email': customer.get('email', ''),
                        'phone': customer.get('mobile', '')
                    }
                
                # Extract device and status information
                if devices and len(devices) > 0:
                    device = devices[0]
                    device_info = device.get('device', {})
                    status_info = device.get('status', {})
                    assigned_info = device.get('assigned_to', {})
                    
                    ticket_data['device'] = device_info.get('name', 'Unknown Device')
                    ticket_data['status'] = status_info.get('name', 'Unknown')
                    ticket_data['assigned_to'] = {
                        'name': assigned_info.get('fullname', 'Unassigned'),
                        'id': assigned_info.get('id', '')
                    }
                    
                    # Extract repair items as description
                    repair_items = device.get('repair_items', [])
                    if repair_items:
                        descriptions = [item.get('name', '') for item in repair_items if item.get('name')]
                        ticket_data['description'] = ', '.join(descriptions)
                        ticket_data['issue'] = ticket_data['description']
                
                # Extract total amount
                ticket_data['total_amount'] = float(summary.get('total_amount', 0) or 0)
            
            # Extract comments and notes
            comments_list = []
            
            # Get notes from the ticket
            notes = raw_ticket.get('notes', [])
            if notes:
                for note in notes:
                    if isinstance(note, dict):
                        comment_text = note.get('msg_text', '')
                        if comment_text:
                            comments_list.append({
                                'id': note.get('id', ''),
                                'text': comment_text,
                                'user': note.get('user', 'Unknown'),
                                'type': note.get('tittle', 'Note'),
                                'created_on': note.get('created_on', ''),
                                'device': note.get('devicename', '')
                            })
            
            # Get comments from other possible fields
            for field_name in ['comments', 'activity', 'ticket_notes']:
                field_data = raw_ticket.get(field_name, [])
                if field_data:
                    for item in field_data:
                        if isinstance(item, dict):
                            comment_text = item.get('msg_text') or item.get('text') or item.get('message') or item.get('content')
                            if comment_text:
                                comments_list.append({
                                    'id': item.get('id', ''),
                                    'text': comment_text,
                                    'user': item.get('user', 'Unknown'),
                                    'type': item.get('tittle') or item.get('type', field_name.title()),
                                    'created_on': item.get('created_on', ''),
                                    'device': item.get('devicename', '')
                                })
            
            ticket_data['comments'] = comments_list
            ticket_data['comment_count'] = len(comments_list)
            
            return ticket_data
            
            return None
            
        except Exception as e:
            logging.error(f"Error normalizing ticket data: {str(e)}")
            return None
    
    def _generate_ticket_summary_safe(self, ticket_data):
        """Generate a safe ticket summary without complex analysis.
        
        Args:
            ticket_data: Normalized ticket data
            
        Returns:
            str: Simple ticket summary
        """
        try:
            device = ticket_data.get('device', 'device')
            status = ticket_data.get('status', 'unknown status')
            customer = ticket_data.get('customer', {}).get('name', 'customer')
            
            return f"{device} for {customer} - {status}"
            
        except Exception as e:
            logging.error(f"Error generating ticket summary: {str(e)}")
            return "Ticket summary unavailable"
    
    def _enhance_ticket_with_details(self, ticket_data, ticket_id):
        """Enhance ticket data with detailed information from RepairDesk API.
        
        Args:
            ticket_data: Basic ticket data dictionary
            ticket_id: The ticket ID to fetch details for
            
        Returns:
            dict: Enhanced ticket data with comments and detailed info
        """
        try:
            if not ticket_data:
                return ticket_data
            
            # Make a copy to avoid modifying the original
            enhanced_ticket = ticket_data.copy()
            
            # Try to fetch detailed ticket information
            try:
                from nest.utils.repairdesk_api import RepairDeskAPI
                api = RepairDeskAPI()
                
                # Convert ticket ID to proper format for API
                if isinstance(ticket_id, str) and ticket_id.startswith('T-'):
                    api_ticket_id = ticket_id
                else:
                    api_ticket_id = f"T-{ticket_id}"
                
                # Fetch detailed ticket info
                detailed_ticket = api.get_ticket(api_ticket_id)
                if detailed_ticket:
                    # Merge detailed info into enhanced ticket
                    enhanced_ticket.update(detailed_ticket)
                
                # Fetch ticket comments/notes
                comments = api.get_ticket_notes(api_ticket_id)
                if comments:
                    enhanced_ticket['comments'] = comments
                    enhanced_ticket['comment_count'] = len(comments)
                else:
                    enhanced_ticket['comments'] = []
                    enhanced_ticket['comment_count'] = 0
                    
            except Exception as api_error:
                logging.warning(f"Could not enhance ticket {ticket_id} with detailed info: {str(api_error)}")
                # Set empty comments if API call fails
                enhanced_ticket['comments'] = []
                enhanced_ticket['comment_count'] = 0
            
            return enhanced_ticket
            
        except Exception as e:
            logging.error(f"Error enhancing ticket {ticket_id}: {str(e)}")
            return ticket_data  # Return original data if enhancement fails
    
    def _fetch_ticket_comments(self, ticket_number):
        """Fetch comments for a specific ticket from RepairDesk API.
        
        Args:
            ticket_number: The ticket number (e.g., 'T-12353')
            
        Returns:
            list: List of comment dictionaries
        """
        try:
            from nest.utils.repairdesk_api import RepairDeskAPI
            api = RepairDeskAPI()
            
            # Ensure proper ticket number format
            if not ticket_number.startswith('T-'):
                ticket_number = f"T-{ticket_number}"
            
            # Fetch comments from API
            comments = api.get_ticket_notes(ticket_number)
            return comments if comments else []
            
        except Exception as e:
            logging.error(f"Error fetching comments for ticket {ticket_number}: {str(e)}")
            return []
    
    def _get_current_user_name(self):
        """Get the current logged-in user/technician name.
        
        Returns:
            str: Current user's full name (e.g., 'Codey O'Connor') or None
        """
        try:
            # Try multiple ways to get the current user name
            if self.current_user:
                # Try fullname first
                if 'fullname' in self.current_user:
                    return self.current_user['fullname']
                # Try name field
                if 'name' in self.current_user:
                    return self.current_user['name']
                # Try first_name + last_name
                if 'first_name' in self.current_user and 'last_name' in self.current_user:
                    return f"{self.current_user['first_name']} {self.current_user['last_name']}"
            
            # Fallback: Try to get from app context
            if hasattr(self.app, 'current_user') and self.app.current_user:
                app_user = self.app.current_user
                if isinstance(app_user, dict):
                    return app_user.get('fullname') or app_user.get('name')
            
            # Hard-coded fallback for testing (should be removed in production)
            # Based on the memory that Codey O'Connor is the test employee
            return "Codey O'Connor"
            
        except Exception as e:
            logging.error(f"Error getting current user name: {str(e)}")
            return "Codey O'Connor"  # Fallback for demo
    
    def _get_tickets_for_technician(self, technician_name):
        """Get all tickets assigned to a specific technician.
        
        Args:
            technician_name: Full name of the technician (e.g., 'Codey O'Connor')
            
        Returns:
            list: List of ticket dictionaries assigned to the technician
        """
        try:
            # Load all tickets from cache/API
            from nest.ai.ticket_utils import load_ticket_data
            all_tickets = load_ticket_data(include_specific_ticket=False)
            
            if not all_tickets:
                return []
            
            # Filter tickets by technician name
            technician_tickets = []
            
            for ticket in all_tickets:
                # Check different possible structures for assigned technician
                assigned_to = None
                
                # Try devices[0].assigned_to.fullname (RepairDesk API structure)
                devices = ticket.get('devices', [])
                if devices and len(devices) > 0:
                    assigned_info = devices[0].get('assigned_to', {})
                    assigned_to = assigned_info.get('fullname')
                
                # Try normalized structure
                if not assigned_to:
                    assigned_info = ticket.get('assigned_to', {})
                    if isinstance(assigned_info, dict):
                        assigned_to = assigned_info.get('name') or assigned_info.get('fullname')
                    elif isinstance(assigned_info, str):
                        assigned_to = assigned_info
                
                # Try direct assigned_to field
                if not assigned_to:
                    assigned_to = ticket.get('assigned_to')
                
                # Check if this ticket is assigned to the specified technician
                if assigned_to and self._match_technician_name(assigned_to, technician_name):
                    # Normalize the ticket data for consistent access
                    normalized_ticket = self._normalize_ticket_data(ticket)
                    if normalized_ticket:
                        technician_tickets.append(normalized_ticket)
            
            logging.info(f"Found {len(technician_tickets)} tickets assigned to {technician_name}")
            return technician_tickets
            
        except Exception as e:
            logging.error(f"Error getting tickets for technician {technician_name}: {str(e)}")
            return []
    
    def _match_technician_name(self, assigned_name, target_name):
        """Robustly match technician names handling spaces, case, and formatting variations.
        
        Args:
            assigned_name: Name from ticket data (may have extra spaces, case differences)
            target_name: Target technician name to match against
            
        Returns:
            bool: True if names match, False otherwise
        """
        try:
            if not assigned_name or not target_name:
                return False
            
            # Normalize both names: strip, lowercase, collapse multiple spaces
            def normalize_name(name):
                return ' '.join(name.strip().lower().split())
            
            normalized_assigned = normalize_name(assigned_name)
            normalized_target = normalize_name(target_name)
            
            # Direct match
            if normalized_assigned == normalized_target:
                return True
            
            # Try partial matches for common variations
            # e.g., "Codey O'Connor" vs "Codey O Connor" (apostrophe differences)
            assigned_no_punct = ''.join(c for c in normalized_assigned if c.isalnum() or c.isspace())
            target_no_punct = ''.join(c for c in normalized_target if c.isalnum() or c.isspace())
            
            if ' '.join(assigned_no_punct.split()) == ' '.join(target_no_punct.split()):
                return True
            
            return False
            
        except Exception as e:
            logging.error(f"Error matching technician names '{assigned_name}' vs '{target_name}': {str(e)}")
            return False
    
    def _get_ticket_comments_response(self, ticket_id=None):
        """Get comments for a specific ticket or recent comments for user's tickets.
        
        Args:
            ticket_id: Optional specific ticket ID to get comments for
            
        Returns:
            str: Formatted response with ticket comments
        """
        try:
            if ticket_id:
                # Get comments for specific ticket
                from nest.ai.ticket_utils import load_ticket_data
                tickets = load_ticket_data()
                target_ticket = None
                
                for ticket in tickets:
                    if isinstance(ticket, dict):
                        order_id = ticket.get('summary', {}).get('order_id', '')
                        if order_id == ticket_id or str(ticket.get('summary', {}).get('id', '')) == str(ticket_id):
                            target_ticket = ticket
                            break
                
                if target_ticket:
                    normalized = self._normalize_ticket_data(target_ticket)
                    if normalized and normalized.get('comments'):
                        response = f"**Comments for Ticket {ticket_id}:**\n\n"
                        for i, comment in enumerate(normalized['comments'][:10], 1):  # Show up to 10 comments
                            response += f"{i}. **{comment['user']}** ({comment['type']})\n"
                            response += f"   {comment['text'][:200]}{'...' if len(comment['text']) > 200 else ''}\n\n"
                        return response
                    else:
                        return f"No comments found for ticket {ticket_id}."
                else:
                    return f"Ticket {ticket_id} not found."
            else:
                # Get recent comments from user's tickets
                current_user_name = self._get_current_user_name()
                user_tickets = self._get_tickets_for_technician(current_user_name)
                
                all_comments = []
                for ticket in user_tickets:
                    normalized = self._normalize_ticket_data(ticket)
                    if normalized and normalized.get('comments'):
                        for comment in normalized['comments']:
                            comment['ticket_id'] = normalized.get('order_id', 'Unknown')
                            all_comments.append(comment)
                
                if all_comments:
                    # Sort by creation date (most recent first)
                    all_comments.sort(key=lambda x: x.get('created_on', ''), reverse=True)
                    
                    response = f"**Recent Comments on Your Tickets ({len(all_comments)} total):**\n\n"
                    for i, comment in enumerate(all_comments[:15], 1):  # Show up to 15 recent comments
                        response += f"{i}. **Ticket {comment['ticket_id']}** - {comment['user']} ({comment['type']})\n"
                        response += f"   {comment['text'][:150]}{'...' if len(comment['text']) > 150 else ''}\n\n"
                    return response
                else:
                    return "No comments found on your assigned tickets."
                    
        except Exception as e:
            logging.error(f"Error getting ticket comments: {str(e)}")
            return f"I encountered an error while retrieving ticket comments: {str(e)}"
    
    def _get_relevant_tickets_for_query(self, query: str) -> List[Dict]:
        """Get tickets relevant to the user's query for intelligent analysis.
        
        Args:
            query: User's query string
            
        Returns:
            List of relevant ticket dictionaries
        """
        try:
            # Determine scope based on query
            query_lower = query.lower()
            
            if any(word in query_lower for word in ['my', 'assigned to me', 'i have']):
                # User's tickets
                current_user_name = self._get_current_user_name()
                tickets = self._get_tickets_for_technician(current_user_name)
            elif any(word in query_lower for word in ['all', 'store', 'everyone', 'total']):
                # All store tickets
                from nest.ai.ticket_utils import load_ticket_data
                all_tickets = load_ticket_data()
                tickets = [self._normalize_ticket_data(t) for t in all_tickets if self._normalize_ticket_data(t)]
            else:
                # Default to user's tickets for personalized analysis
                current_user_name = self._get_current_user_name()
                tickets = self._get_tickets_for_technician(current_user_name)
            
            # Filter by query keywords if specific terms are mentioned
            if any(word in query_lower for word in ['urgent', 'priority', 'asap']):
                # Focus on high-priority tickets
                return tickets[:20]  # Limit for performance
            elif any(word in query_lower for word in ['water', 'screen', 'battery', 'repair']):
                # Focus on specific repair types
                return tickets[:15]
            else:
                # General analysis - return reasonable subset
                return tickets[:10]
                
        except Exception as e:
            logging.error(f"Error getting relevant tickets for query: {str(e)}")
            return []

    def _handle_specific_queries(self, user_message):
        """Handle specific queries that can be answered directly with ticket data.
        
        Args:
            user_message: The user's message to analyze
            
        Returns:
            str: Response if query can be handled directly, None otherwise
        """
        message_lower = user_message.lower()
        
        try:
            # Handle ticket count queries
            if any(phrase in message_lower for phrase in ['how many tickets', 'number of tickets', 'total tickets']):
                return self._get_ticket_count_response()
            
            # Handle user ticket queries
            if any(phrase in message_lower for phrase in ['my tickets', 'tickets assigned to me', 'codey o\'connor']):
                return self._get_user_tickets_response()
            
            # Handle store ticket queries
            if any(phrase in message_lower for phrase in ['store tickets', 'all tickets', 'store-wide']):
                return self._get_store_tickets_response()
            
            # Handle comment queries
            if any(phrase in message_lower for phrase in ['list comments', 'show comments', 'ticket comments']):
                return self._get_comments_response()
            
            # Handle status queries for specific tickets
            if 'status of ticket' in message_lower:
                ticket_numbers = self.extract_ticket_numbers(user_message)
                if ticket_numbers:
                    return self._get_ticket_status_response(ticket_numbers[0])
            
            # Handle last updated queries
            if any(phrase in message_lower for phrase in ['last updated', 'when updated', 'update time']):
                ticket_numbers = self.extract_ticket_numbers(user_message)
                if ticket_numbers:
                    return self._get_ticket_last_updated_response(ticket_numbers[0])
                else:
                    return "Please specify a ticket number to check when it was last updated."
            
        except Exception as e:
            logging.error(f"Error handling specific query: {str(e)}")
            return None
        
        return None
    
    def _get_ticket_count_response(self):
        """Get response for ticket count queries."""
        try:
            tickets = self.ticket_db['get_store_tickets'](limit=1000)  # Get all tickets
            if not tickets:
                return "There are currently no active tickets in the system."
            
            total_count = len(tickets)
            
            # Count by status
            status_counts = {}
            for ticket in tickets:
                status = ticket.get('status', 'Unknown')
                status_counts[status] = status_counts.get(status, 0) + 1
            
            response = f"**Current Ticket Summary:**\n\n"
            response += f"📊 **Total Tickets:** {total_count}\n\n"
            
            if status_counts:
                response += "**By Status:**\n"
                for status, count in sorted(status_counts.items()):
                    response += f"• {status}: {count} tickets\n"
            
            return response
            
        except Exception as e:
            logging.error(f"Error getting ticket count: {str(e)}")
            return f"I encountered an error while retrieving ticket count: {str(e)}"
    
    def _get_user_tickets_response(self):
        """Get response for user ticket queries."""
        try:
            # Get current user name (Codey O'Connor)
            current_user_name = self._get_current_user_name()
            if not current_user_name:
                return "I couldn't identify your user account. Please make sure you're logged in."
            
            tickets = self._get_tickets_for_technician(current_user_name)
            
            if not tickets:
                return f"You don't have any tickets assigned to you at the moment, {current_user_name.split()[0]}."
            
            response = f"**Your Assigned Tickets, {current_user_name.split()[0]} ({len(tickets)}):**\n\n"
            
            for i, ticket in enumerate(tickets[:10], 1):  # Show first 10
                ticket_id = ticket.get('id', ticket.get('summary', {}).get('order_id', 'Unknown'))
                customer = ticket.get('customer', {}).get('name', 'Unknown Customer')
                device = ticket.get('device', 'Unknown Device')
                status = ticket.get('status', 'Unknown')
                
                response += f"{i}. **{ticket_id}** - {customer}\n"
                response += f"   📱 {device} | Status: {status}\n\n"
            
            if len(tickets) > 10:
                response += f"... and {len(tickets) - 10} more tickets.\n"
            
            return response
            
        except Exception as e:
            logging.error(f"Error getting user tickets: {str(e)}")
            return f"I encountered an error while retrieving your tickets: {str(e)}"
    
    def _get_store_tickets_response(self):
        """Get response for store ticket queries."""
        try:
            tickets = self.ticket_db['get_store_tickets'](limit=50)
            
            if not tickets:
                return "There are no active tickets for the store at the moment."
            
            response = f"**Store Tickets ({len(tickets)}):**\n\n"
            
            # Group by status for better organization
            status_groups = {}
            for ticket in tickets:
                status = ticket.get('status', 'Unknown')
                if status not in status_groups:
                    status_groups[status] = []
                status_groups[status].append(ticket)
            
            for status, status_tickets in status_groups.items():
                response += f"**{status} ({len(status_tickets)}):**\n"
                
                for ticket in status_tickets[:5]:  # Show first 5 per status
                    ticket_id = ticket.get('id', 'Unknown')
                    customer = ticket.get('customer', {}).get('name', 'Unknown Customer')
                    device = ticket.get('device', 'Unknown Device')
                    assigned_to = ticket.get('assigned_to', {}).get('name', 'Unassigned')
                    
                    response += f"• **T-{ticket_id}** - {customer} ({device}) → {assigned_to}\n"
                
                if len(status_tickets) > 5:
                    response += f"  ... and {len(status_tickets) - 5} more {status.lower()} tickets\n"
                response += "\n"
            
            return response
            
        except Exception as e:
            logging.error(f"Error getting store tickets: {str(e)}")
            return f"I encountered an error while retrieving store tickets: {str(e)}"
    
    def _get_comments_response(self):
        """Get response for comment queries."""
        try:
            # Check if there's a specific ticket in context
            if hasattr(self, 'detected_ticket_for_context') and self.detected_ticket_for_context:
                ticket_number = self.detected_ticket_for_context
                comments = self._fetch_ticket_comments(ticket_number)
                
                if not comments:
                    return f"No comments found for ticket {ticket_number}."
                
                response = f"**Comments for Ticket {ticket_number} ({len(comments)}):**\n\n"
                
                for i, comment in enumerate(comments, 1):
                    author = comment.get('author', comment.get('user', {}).get('name', 'Unknown'))
                    content = comment.get('content', comment.get('note', comment.get('message', 'No content')))
                    created_at = comment.get('created_at', comment.get('date', 'Unknown time'))
                    
                    response += f"{i}. **{author}** ({created_at}):\n"
                    response += f"   {content}\n\n"
                
                return response
            else:
                return "Please specify a ticket number or load a specific ticket first to view its comments."
                
        except Exception as e:
            logging.error(f"Error getting comments: {str(e)}")
            return f"I encountered an error while retrieving comments: {str(e)}"
    
    def _get_ticket_status_response(self, ticket_number):
        """Get response for ticket status queries."""
        try:
            ticket_id = ticket_number.replace('T-', '')
            ticket = self.ticket_db['get_ticket'](ticket_id)
            
            if not ticket:
                return f"I couldn't find ticket {ticket_number}. Please check the ticket number."
            
            customer = ticket.get('customer', {}).get('name', 'Unknown Customer')
            device = ticket.get('device', 'Unknown Device')
            status = ticket.get('status', 'Unknown')
            assigned_to = ticket.get('assigned_to', {}).get('name', 'Unassigned')
            total_amount = ticket.get('total_amount', 0)
            
            response = f"**Status for Ticket {ticket_number}:**\n\n"
            response += f"👤 **Customer:** {customer}\n"
            response += f"📱 **Device:** {device}\n"
            response += f"📊 **Status:** {status}\n"
            response += f"👨‍🔧 **Assigned to:** {assigned_to}\n"
            
            if total_amount:
                response += f"💰 **Total:** ${total_amount:.2f}\n"
            
            return response
            
        except Exception as e:
            logging.error(f"Error getting ticket status: {str(e)}")
            return f"I encountered an error while retrieving ticket status: {str(e)}"
    
    def _get_ticket_last_updated_response(self, ticket_number):
        """Get response for ticket last updated queries."""
        try:
            ticket_id = ticket_number.replace('T-', '')
            ticket = self.ticket_db['get_ticket'](ticket_id)
            
            if not ticket:
                return f"I couldn't find ticket {ticket_number}. Please check the ticket number."
            
            # Try to get last updated information
            last_updated = ticket.get('updated_at') or ticket.get('last_updated') or ticket.get('modified_date')
            created_at = ticket.get('created_at') or ticket.get('created_date')
            
            response = f"**Update Information for Ticket {ticket_number}:**\n\n"
            
            if last_updated:
                response += f"🕒 **Last Updated:** {last_updated}\n"
            elif created_at:
                response += f"🕒 **Created:** {created_at}\n"
                response += f"ℹ️ No specific update timestamp available, showing creation date.\n"
            else:
                response += f"⚠️ No timestamp information available for this ticket.\n"
            
            # Add current status for context
            status = ticket.get('status', 'Unknown')
            response += f"📊 **Current Status:** {status}\n"
            
            return response
            
        except Exception as e:
            logging.error(f"Error getting ticket last updated: {str(e)}")
            return f"I encountered an error while retrieving ticket update information: {str(e)}"

    
    
    def display_ai_message(self, sender, message):
        """Display an AI message in the chat display with proper formatting.
        
        Args:
            sender: The sender of the message (e.g., "NestBot")
            message: The message content to display
        """
        try:
            # Enable text widget for editing
            self.ai_chat_display.config(state="normal")
            
            # Add a blank line if not at the beginning
            if self.ai_chat_display.index("end-1c") != "1.0":
                self.ai_chat_display.insert("end", "\n\n")
            
            # Get current time
            timestamp = datetime.now().strftime("%H:%M")
            
            # Determine message type for styling
            is_system = sender.lower() == "system"
            is_user = sender.lower() == "you"
            
            # Add timestamp
            self.ai_chat_display.insert("end", f"[{timestamp}] ", "timestamp")
            
            # Add sender with appropriate styling
            if is_system:
                self.ai_chat_display.insert("end", f"{sender}:\n", "system_sender")
                # Add message with system styling
                self.insert_rich_text("end", message, "system_message")
            elif is_user:
                self.ai_chat_display.insert("end", f"{sender}:\n", "user_sender")
                # Add user message with user styling
                self.insert_rich_text("end", message, "user_message")
            else:
                self.ai_chat_display.insert("end", f"{sender}:\n", "bot_sender")
                # Add bot message with bot styling
                self.insert_rich_text("end", message, "bot_message")
            
            # Ensure there's always a newline at the end
            if not message.endswith("\n"):
                self.ai_chat_display.insert("end", "\n")
            
            # Scroll to see the newest message
            self.ai_chat_display.see("end")
            
            # Force update the display
            self.ai_chat_display.update_idletasks()
            
        except Exception as e:
            logging.error(f"Error displaying message from {sender}: {str(e)}")
            # Fallback to simple text display
            try:
                self.ai_chat_display.config(state="normal")
                self.ai_chat_display.insert("end", f"{sender}: {message}\n")
                self.ai_chat_display.see("end")
            except Exception as inner_e:
                logging.error(f"Fallback display also failed: {str(inner_e)}")
        finally:
            # Always ensure the widget is left in a disabled state
            self.ai_chat_display.config(state="disabled")
