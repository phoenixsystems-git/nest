#!/usr/bin/env python
"""
Ticket utilities for NestBot AI Assistant

This module contains helper functions for loading and processing ticket data
for use with the NestBot AI assistant.
"""

import os
import json
import logging
import tkinter as tk
from tkinter import messagebox
from typing import Dict, List, Any, Callable, Optional


def load_ticket(ticket_number: str, display_callback: Optional[Callable] = None) -> bool:
    """
    Load a specific ticket's details for AI reference.
    
    Args:
        ticket_number: The ticket number to load
        display_callback: Optional callback function to display messages in the AI chat panel
        
    Returns:
        bool: True if ticket was loaded successfully, False otherwise
    """
    # Clean up the ticket number format
    # Remove any non-numeric characters if it's just a number
    if ticket_number.isdigit():
        ticket_number = ticket_number.strip()
    # If it has a T- prefix, make sure it's formatted correctly
    elif ticket_number.lower().startswith('t') and not ticket_number.startswith('T-'):
        # Add the dash if missing
        if ticket_number.lower().startswith('t-'):
            ticket_number = 'T-' + ticket_number[2:]
        else:
            ticket_number = 'T-' + ticket_number[1:]
    # If it doesn't have a T prefix, add it
    elif not ticket_number.startswith('T-'):
        ticket_number = f"T-{ticket_number}"
        
    try:
        # Load the ticket cache to find the internal API ID
        cached_tickets = load_ticket_data(include_specific_ticket=False)
        if not cached_tickets:
            messagebox.showerror(
                "Error", 
                "Could not load ticket cache. Please refresh tickets first and try again."
            )
            return False
            
        # Look for the ticket in the cache to get the internal API ID
        api_ticket_id = None
        numeric_id = ticket_number.replace('T-', '')
        
        # Add debug logging
        logging.debug(f"Looking for ticket {ticket_number} (numeric: {numeric_id}) in cache with {len(cached_tickets)} tickets")
        
        # Log a few sample tickets to help debug
        sample_size = min(5, len(cached_tickets))
        logging.debug(f"Sample of first {sample_size} tickets in cache:")
        for i in range(sample_size):
            ticket = cached_tickets[i]
            summary = ticket.get('summary', {})
            logging.debug(f"  - Cache ticket {i+1}: ID={summary.get('id')}, order_id={summary.get('order_id')}, status={ticket.get('status')}")
        
        # If we're looking for a specific ID, show more details
        search_results = [t for t in cached_tickets if t.get('summary', {}).get('order_id', '').replace('T-', '') == numeric_id 
                           or t.get('summary', {}).get('id') == numeric_id]
        for t in search_results:
            logging.debug(f"Found partial match: {t.get('summary', {})}")

        
        for ticket in cached_tickets:
            # Check if this is the ticket we're looking for - try different formats
            summary = ticket.get('summary', {})
            order_id = summary.get('order_id', '')
            
            # Try matching different formats (with or without T- prefix)
            if (order_id == ticket_number or  # Exact match
                (order_id and order_id.replace('T-', '') == numeric_id) or  # Match without prefix
                (summary.get('id') == numeric_id)):  # Match by API ID
                # Found the ticket, get the internal API ID
                api_ticket_id = summary.get('id')
                logging.info(f"Found API ID {api_ticket_id} for ticket {ticket_number}")
                break
                
        if not api_ticket_id:
            logging.debug(f"Ticket {ticket_number} not found in standard cache. Trying fallback methods...")
            
            # Fallback: Try to get the ticket info from the RepairDesk API directly
            try:
                from nest.api.api_client import RepairDeskClient
                client = RepairDeskClient()
                
                # Try to find the ticket by its number
                ticket_info = client.search_tickets(ticket_number)
                if ticket_info and isinstance(ticket_info, dict) and 'data' in ticket_info:
                    for ticket in ticket_info['data']:
                        if ticket.get('order_id') == ticket_number or ticket.get('id') == numeric_id:
                            api_ticket_id = ticket.get('id')
                            logging.info(f"Found API ID {api_ticket_id} for ticket {ticket_number} via direct API search")
                            break
            except Exception as e:
                logging.error(f"Error in API fallback ticket lookup: {str(e)}")
                
        # If we still don't have an API ID, give up            
        if not api_ticket_id:
            messagebox.showerror(
                "Error", 
                f"Ticket {ticket_number} not found in any available sources. Please refresh tickets first."
            )
            return False
            
        # Create API client
        from nest.api.api_client import RepairDeskClient
        api_client = RepairDeskClient()
        
        # Fetch ticket using the internal API ID
        detailed_ticket = api_client.get_ticket_by_id(ticket_number, actual_api_id=api_ticket_id)
        
        if not detailed_ticket or not isinstance(detailed_ticket, dict):
            error_msg = f"Ticket {ticket_number} could not be found on the RepairDesk server. "
            error_msg += "Please check the ticket number and try again."
            
            messagebox.showerror("Ticket Not Found", error_msg)
            
            # Also add an error message to the chat if callback provided
            if display_callback:
                display_callback(
                    "System", 
                    f"⚠️ **Error**: Could not find ticket **{ticket_number}** on the RepairDesk server."
                )
            return False
            
        # Show success message
        messagebox.showinfo(
            "Success", 
            f"Ticket {ticket_number} details loaded successfully and are now available for AI reference."
        )
        
        # Also add a message to the chat if callback provided
        if display_callback:
            display_callback(
                "System", 
                f"Loaded details for ticket **{ticket_number}**. You can now ask questions about this specific ticket."
            )
            
        return True
        
    except Exception as e:
        logging.error(f"Error loading ticket for AI: {str(e)}")
        messagebox.showerror(
            "Error", 
            f"Failed to load ticket: {str(e)[:100]}"
        )
        return False


def extract_ticket_numbers(message_text):
    """
    Extract ticket numbers from a message text.
    
    Args:
        message_text: The text message to analyze
            
    Returns:
        list: List of extracted ticket numbers
    """
    import re
    
    # Different patterns to match ticket numbers
    patterns = [
        r'T-\d+',                 # Match T-12345 format
        r'[Tt]\d+',               # Match T12345 or t12345 format
        r'ticket\s+(?:no\.?\s*)?\d+',  # Match "ticket 12345" or "ticket no. 12345" 
        r'ticket\s+(?:no\.?\s*)?[Tt]-?\d+'  # Match "ticket T-12345" or "ticket no. T12345"
    ]
    
    ticket_numbers = []
    
    for pattern in patterns:
        matches = re.findall(pattern, message_text, re.IGNORECASE)
        for match in matches:
            # Extract just the numeric part or the T-numeric part
            if match.upper().startswith('T') and not match.startswith('ticket'):
                # Handle T12345 or T-12345 format
                num = match.upper().replace(' ', '')
                if not '-' in num:
                    # Convert T12345 to T-12345 format
                    num = f"T-{num[1:]}"
                ticket_numbers.append(num)
            elif match.lower().startswith('ticket'):
                # Extract from formats like "ticket 12345" or "ticket no. 12345"
                num_match = re.search(r'(?:[Tt]-?)?\d+', match)
                if num_match:
                    num = num_match.group(0)
                    # Ensure proper T- format
                    if num.upper().startswith('T') and not '-' in num:
                        num = f"T-{num[1:]}"
                    elif not num.upper().startswith('T'):
                        num = f"T-{num}"
                    ticket_numbers.append(num.upper())
    
    # Deduplicate and clean up
    unique_tickets = []
    for ticket in ticket_numbers:
        # Standardize format to T-XXXXX
        if ticket.upper().startswith('T') and not '-' in ticket:
            ticket = f"T-{ticket[1:]}"
        ticket = ticket.upper()
        if ticket not in unique_tickets:
            unique_tickets.append(ticket)
    
    return unique_tickets

def load_ticket_data(include_specific_ticket=True):
    """
    Load tickets from the ticket_cache.json file and optionally include specific ticket data
    
    Args:
        include_specific_ticket: If True, also look for a specific ticket file to include
            
    Returns:
        list: List of ticket data dictionaries
    """
    try:
        # Get the directory of the current script (should be Nest 2.5 root)
        script_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        cache_path = os.path.join(script_dir, 'cache', 'ticket_cache.json')
        
        # Check if the cache file exists
        if not os.path.exists(cache_path):
            return []
            
        # Load the cache
        with open(cache_path, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
            
        # Extract the tickets from the cache structure
        if isinstance(cache_data, dict) and 'items' in cache_data:
            tickets = cache_data['items']
        elif isinstance(cache_data, list):
            tickets = cache_data
        else:
            logging.warning(f"Unexpected cache structure: {type(cache_data)}")
            return []
            
        # If we don't need to include a specific ticket, or if there's no specific ticket file,
        # just return the regular cache
        if not include_specific_ticket or not os.path.exists(os.path.join(script_dir, 'cache', 'specific_ticket.json')):
            return tickets
            
        # Load the specific ticket data
        specific_ticket_path = os.path.join(script_dir, 'cache', 'specific_ticket.json')
        with open(specific_ticket_path, 'r', encoding='utf-8') as f:
            specific_ticket = json.load(f)
            
        # Add the specific ticket to the beginning of the list if it's not already there
        if specific_ticket and specific_ticket.get('id'):
            # Remove the ticket if it already exists in the cache
            tickets = [t for t in tickets if t.get('id') != specific_ticket.get('id')]
            # Add the specific ticket to the beginning
            tickets.insert(0, specific_ticket)
            
        return tickets
        
    except Exception as e:
        logging.error(f"Error loading ticket data: {e}")
        return []


def get_user_tickets(user_id: str, status: str = 'open', limit: int = 50) -> List[Dict[str, Any]]:
    """
    Get tickets assigned to a specific user.
    
    Args:
        user_id: ID of the user
        status: Status filter ('open', 'closed', 'all')
        limit: Maximum number of tickets to return
        
    Returns:
        List of ticket dictionaries
    """
    try:
        # Load all tickets
        tickets = load_ticket_data(include_specific_ticket=False)
        
        if not tickets:
            return []
            
        # Filter by assigned user
        user_tickets = [t for t in tickets if str(t.get('assigned_to_id')) == str(user_id)]
        
        # Apply status filter
        if status.lower() == 'open':
            user_tickets = [t for t in user_tickets if t.get('status', '').lower() != 'closed']
        elif status.lower() == 'closed':
            user_tickets = [t for t in user_tickets if t.get('status', '').lower() == 'closed']
            
        # Apply limit
        return user_tickets[:limit]
        
    except Exception as e:
        logging.error(f"Error getting user tickets: {str(e)}")
        return []

def get_store_tickets(store_id: str, status: str = 'open', limit: int = 100) -> List[Dict[str, Any]]:
    """
    Get all tickets for a specific store.
    
    Args:
        store_id: ID of the store
        status: Status filter ('open', 'closed', 'all')
        limit: Maximum number of tickets to return
        
    Returns:
        List of ticket dictionaries
    """
    try:
        # Load all tickets
        tickets = load_ticket_data(include_specific_ticket=False)
        
        if not tickets:
            return []
            
        # Filter by store
        store_tickets = [t for t in tickets if str(t.get('store_id')) == str(store_id)]
        
        # Apply status filter
        if status.lower() == 'open':
            store_tickets = [t for t in store_tickets if t.get('status', '').lower() != 'closed']
        elif status.lower() == 'closed':
            store_tickets = [t for t in store_tickets if t.get('status', '').lower() == 'closed']
            
        # Apply limit
        return store_tickets[:limit]
        
    except Exception as e:
        logging.error(f"Error getting store tickets: {str(e)}")
        return []

def load_specific_ticket_for_ai(nestbot_panel):
    """
    Load a specific ticket for AI analysis.
    
    Args:
        nestbot_panel: An instance of NestBotPanel that this function will operate on
    """
    # Create a dialog to get the ticket number
    from tkinter import simpledialog
    
    ticket_number = simpledialog.askstring(
        "Load Ticket",
        "Enter ticket number:",
        parent=nestbot_panel.parent
    )
    
    if not ticket_number:
        return
        
    # Load the ticket using the existing load_ticket function
    from .ticket_utils import load_ticket
    
    try:
        # Try to load the ticket
        success = load_ticket(ticket_number, nestbot_panel.display_ai_message)
        
        if success:
            nestbot_panel.display_ai_message("System", f"Successfully loaded ticket {ticket_number} for analysis.")
            # Store the ticket number for context in future AI interactions
            nestbot_panel.detected_ticket_for_context = ticket_number
        else:
            nestbot_panel.display_ai_message("System", f"Failed to load ticket {ticket_number}. Please check the number and try again.")
    except Exception as e:
        logging.error(f"Error loading ticket for AI: {e}")
        nestbot_panel.display_ai_message("System", f"An error occurred while loading the ticket: {str(e)}")
