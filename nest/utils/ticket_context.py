#!/usr/bin/env python3
"""
Ticket Context Manager for PC Tools

Handles ticket lookup, context management, and RepairDesk integration.
Provides functions to associate system snapshots with specific repair tickets.
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path

try:
    # Try to import Nest's RepairDesk API client
    from nest.utils.repairdesk_api import RepairDeskAPI
except ImportError:
    # Fallback to direct imports if not running within Nest
    try:
        from utils.repairdesk_api import RepairDeskAPI
    except ImportError:
        logging.error("Could not import RepairDeskAPI")
        
# Load config module for API key retrieval
try:
    from nest.utils.config_manager import ConfigManager
except ImportError:
    try:
        from utils.config_manager import ConfigManager
    except ImportError:
        logging.error("Could not import ConfigManager")


class TicketContext:
    """Manages ticket context for PC diagnostics and repair workflows."""
    
    def __init__(self, api_key=None, store_slug=None):
        self.api_key = api_key
        self.store_slug = store_slug
        self.ticket_info = None
        self.customer_info = None
        self.ticket_id = None
        self.client = None
        self.last_ticket_path = None
        
        # Set up the last ticket file path based on execution environment
        if hasattr(os, 'getcwd'):
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.last_ticket_path = os.path.join(base_dir, "data", "last_ticket.json")
            os.makedirs(os.path.dirname(self.last_ticket_path), exist_ok=True)
            
        # Initialize RepairDesk client if credentials are provided
        if api_key:
            self.init_client(api_key, store_slug)
    
    def init_client(self, api_key=None, store_slug=None):
        """Initialize the RepairDesk API client.
        
        Args:
            api_key: RepairDesk API key, if None will try to load from config
            store_slug: Store slug for RepairDesk
            
        Returns:
            True if client was initialized successfully, False otherwise
        """
        try:
            # If no API key provided, try to load from config
            if api_key is None:
                try:
                    config = ConfigManager()
                    api_key = config.get('api_key')
                    store_slug = config.get('store_slug')
                    logging.info("Loaded API key from config")
                except Exception as config_err:
                    logging.error(f"Failed to load API key from config: {config_err}")
            
            if not api_key:
                logging.error("No API key available for RepairDesk")
                return False
                
            self.api_key = api_key
            self.store_slug = store_slug
            
            # Initialize the RepairDeskAPI client
            self.client = RepairDeskAPI(api_key, store_slug)
            
            # Test that the connection works
            if self.client.validate_credentials():
                logging.info("RepairDesk API client initialized successfully")
                return True
            else:
                logging.error("RepairDesk API credentials are invalid")
                return False
                
        except Exception as e:
            logging.error(f"Failed to initialize RepairDesk API client: {e}")
            return False
    
    def lookup_ticket(self, ticket_id):
        """Look up a ticket by ID and retrieve details.
        
        Args:
            ticket_id: The ticket number, with or without T- prefix
            
        Returns:
            Ticket information dictionary or None if not found
        """
        if not self.client:
            logging.error("RepairDesk client not initialized")
            return None
            
        try:
            # Log the lookup attempt
            if isinstance(ticket_id, str) and ticket_id.startswith('T-'):
                display_id = ticket_id
            else:
                display_id = f"T-{ticket_id}"
                
            logging.info(f"Looking up RepairDesk ticket: {display_id}")
            
            # First try to get the internal numeric ID (more reliable)
            try:
                # Use the new get_numeric_ticket_id method to handle the conversion
                numeric_id = self.client.get_numeric_ticket_id(ticket_id)
                
                if not numeric_id:
                    logging.error(f"Could not find numeric ID for ticket {display_id}")
                    raise ValueError(f"Ticket {display_id} not found in RepairDesk system")
                    
                # Now get the full ticket details with the found numeric ID
                logging.info(f"Found numeric ID {numeric_id} for ticket {display_id}, fetching details")
                ticket_data = self.client.get_ticket(numeric_id)
            except Exception as e:
                logging.error(f"Error finding numeric ID, falling back to direct lookup: {e}")
                
                # Fallback to direct lookup if get_numeric_ticket_id fails
                # Remove any T- prefix for direct API call
                if isinstance(ticket_id, str) and ticket_id.startswith('T-'):
                    ticket_id = ticket_id[2:]
                    
                # Ensure it's a number for the API
                numeric_id = int(ticket_id)
                ticket_data = self.client.get_ticket(numeric_id)
            
            # Process the API response
            if ticket_data and isinstance(ticket_data, dict):
                # Check for API error messages
                if 'error' in ticket_data:
                    error_msg = ticket_data.get('error', 'Unknown API error')
                    logging.error(f"API error: {error_msg}")
                    raise ValueError(f"API error: {error_msg}")
                
                # Check for error messages and different response formats
                if 'success' in ticket_data and ticket_data['success'] is False:
                    error_msg = ticket_data.get('message', 'API error')
                    logging.error(f"API error response: {error_msg}")
                    raise ValueError(f"Ticket {display_id} not found or API returned error: {error_msg}")
                
                # Check if data exists and handle various response formats
                # RepairDesk API sometimes returns data directly, sometimes nested under 'data'
                if 'data' in ticket_data:
                    if not ticket_data['data']:
                        error_msg = ticket_data.get('message', 'No ticket data returned')
                        logging.error(f"Empty data for ticket: {error_msg}")
                        raise ValueError(f"Ticket {display_id} not found or API returned error: {error_msg}")
                    ticket_content = ticket_data['data']
                else:
                    # Some endpoints return data directly without 'data' wrapper
                    ticket_content = ticket_data
                
                # Look for expected structures in the response
                # The API documentation shows ticket data has 'summary' section
                if 'summary' in ticket_content:
                    logging.info(f"Found summary data for ticket {display_id}")
                elif isinstance(ticket_content, dict) and len(ticket_content) > 0:
                    # Data exists but not in expected format, try to use it anyway
                    logging.warning(f"Ticket data doesn't have expected structure but contains {len(ticket_content)} keys")
                else:
                    error_msg = 'Ticket data structure not recognized'
                    logging.error(error_msg)
                    raise ValueError(f"Ticket {display_id} not found or API returned unexpected format")
                
                # Success - store ticket info
                self.ticket_info = ticket_content  # Using our processed ticket_content from above
                self.ticket_id = numeric_id
                
                # Extract customer info if available
                if 'customer_details' in self.ticket_info:
                    self.customer_info = self.ticket_info['customer_details']
                    logging.info(f"Found customer: {self.get_customer_name()}")
                
                # Save as last ticket
                self._save_last_ticket()
                
                logging.info(f"Successfully retrieved ticket {display_id}")
                return self.ticket_info
            else:
                logging.error(f"Invalid response format for ticket {display_id}")
                return None
                
        except ValueError as ve:
            # Re-raise ValueError with more details for the UI
            raise ValueError(f"Ticket Error: {str(ve)}")
        except Exception as e:
            logging.error(f"Error looking up ticket {ticket_id}: {e}")
            return None
    
    def get_customer_reported_issues(self):
        """Extract customer-reported issues from the ticket."""
        if not self.ticket_info:
            return None
            
        issues = []
        
        # Look for problem description in various fields
        if 'problem' in self.ticket_info:
            issues.append(self.ticket_info['problem'])
            
        if 'description' in self.ticket_info:
            issues.append(self.ticket_info['description'])
        
        # Check for comments that might contain customer issues
        if 'comments' in self.ticket_info and isinstance(self.ticket_info['comments'], list):
            for comment in self.ticket_info['comments']:
                if comment.get('type') == 'customer' or 'customer reported' in comment.get('note', '').lower():
                    issues.append(comment.get('note', ''))
        
        return "\n\n".join([issue for issue in issues if issue])  
    
    def get_customer_name(self):
        """Get the customer name from the ticket."""
        if self.customer_info and 'name' in self.customer_info:
            return self.customer_info['name']
        elif self.ticket_info and 'customer_name' in self.ticket_info:
            return self.ticket_info['customer_name']
        return None
    
    def get_formatted_ticket_id(self):
        """Get the ticket ID in the format T-12345.
        
        Always returns the ticket ID with the T- prefix, regardless of how it was originally entered.
        """
        if self.ticket_id:
            return f"T-{self.ticket_id}"
        return None
    
    def _save_last_ticket(self):
        """Save the current ticket as the last accessed ticket."""
        if not self.last_ticket_path or not self.ticket_id:
            return False
            
        try:
            os.makedirs(os.path.dirname(self.last_ticket_path), exist_ok=True)
            
            # Prepare minimal data to save
            last_ticket_data = {
                "ticket_id": self.ticket_id,
                "formatted_id": self.get_formatted_ticket_id(),
                "timestamp": datetime.now().isoformat(),
            }
            
            # Add customer info if available
            if self.customer_info:
                last_ticket_data["customer_name"] = self.get_customer_name()
                
            # Add device info if available
            if self.ticket_info and 'item_name' in self.ticket_info:
                last_ticket_data["device"] = self.ticket_info['item_name']
            
            # Save to file
            with open(self.last_ticket_path, 'w') as f:
                json.dump(last_ticket_data, f, indent=2)
                
            return True
        except Exception as e:
            logging.error(f"Error saving last ticket: {e}")
            return False
    
    def load_last_ticket(self):
        """Load the last accessed ticket, if available."""
        if not self.last_ticket_path or not os.path.exists(self.last_ticket_path):
            return None
            
        try:
            with open(self.last_ticket_path, 'r') as f:
                last_ticket_data = json.load(f)
                
            if 'ticket_id' in last_ticket_data:
                # Just load the ticket ID and other basic info, don't fetch from API yet
                self.ticket_id = last_ticket_data['ticket_id']
                return last_ticket_data
            
            return None
        except Exception as e:
            logging.error(f"Error loading last ticket: {e}")
            return None
    
    def upload_diagnostic_note(self, note_text):
        """Upload a diagnostic note to the current ticket.
        
        Uses the new add_diagnostic_note method that properly handles T- prefixed ticket numbers.
        """
        if not self.client or not self.ticket_id:
            logging.error("RepairDesk client not initialized or no ticket selected")
            return False
            
        try:
            # Get formatted ticket ID with T- prefix for consistent reporting
            formatted_ticket_id = self.get_formatted_ticket_id()
            
            # Use the new add_diagnostic_note method that handles the ticket ID conversion
            result = self.client.add_diagnostic_note(
                ticket_id=self.ticket_id,  # Can be numeric or T-prefixed 
                note=note_text,
                is_flag=0  # Not flagged by default
            )
            
            # Check for success response formats
            if result and isinstance(result, dict) and (result.get('success') or result.get('status') == 'success'):
                logging.info(f"Diagnostic note uploaded successfully to ticket {formatted_ticket_id}")
                return True
            # Check if result is a list - RepairDesk API may return a list of all notes when successful
            elif result and isinstance(result, list):
                # This is actually a success case - the API returned all notes for the ticket including the new one
                logging.info(f"Diagnostic note uploaded successfully to ticket {formatted_ticket_id}. API returned {len(result)} notes.")
                return True
            else:
                error_msg = result.get('message', 'Unknown error') if result and isinstance(result, dict) else str(result)
                logging.error(f"Failed to upload diagnostic note: {error_msg}")
                return False
        except Exception as e:
            logging.error(f"Error uploading diagnostic note: {e}")
            return False
    
    def upload_to_ticket(self, ticket_number, title, content):
        """Upload content to a RepairDesk ticket.
        
        Args:
            ticket_number: RepairDesk ticket number (can be with or without T- prefix)
            title: Report title
            content: Report content
            
        Returns:
            Dict with success status and message
        """
        try:
            # Format ticket number consistently with T- prefix
            # First remove any existing T- prefix to avoid duplicates
            if isinstance(ticket_number, str) and ticket_number.startswith('T-'):
                numeric_part = ticket_number[2:]
            else:
                numeric_part = ticket_number
            
            # Create properly formatted ticket ID
            formatted_ticket_id = f"T-{numeric_part}"
            
            # Lookup the ticket to get its details
            ticket_info = self.lookup_ticket(numeric_part)
            
            if not ticket_info:
                return {
                    "success": False,
                    "message": f"Could not find ticket {formatted_ticket_id}"
                }
                
            # Format the content with title
            formatted_note = f"# {title}\n\n{content}"
            
            # Upload as diagnostic note
            result = self.upload_diagnostic_note(formatted_note)
            
            if result:
                return {
                    "success": True,
                    "message": f"Successfully uploaded to ticket {formatted_ticket_id}",
                    "ticket_id": self.ticket_id,
                    "ticket_url": self.ticket_info.get('ticket_url', ''),
                    "formatted_ticket_id": formatted_ticket_id
                }
            else:
                return {
                    "success": False,
                    "message": f"Failed to upload note to ticket {formatted_ticket_id}"
                }
                
        except Exception as e:
            logging.error(f"Error in upload_to_ticket: {e}")
            return {
                "success": False,
                "message": f"Error: {str(e)}"
            }

    def save_to_network_folder(self, snapshot_file, server_path=None):
        """Save the snapshot to a network folder using ticket/customer info."""
        if not snapshot_file or not os.path.exists(snapshot_file):
            logging.error(f"Snapshot file doesn't exist: {snapshot_file}")
            return False
            
        # Get customer and ticket info for folder naming
        customer_name = self.get_customer_name() or "Unknown_Customer"
        ticket_id = self.get_formatted_ticket_id() or "No_Ticket"
        
        # Clean up customer name for folder naming
        safe_customer_name = ''.join(c if c.isalnum() or c in '- ' else '_' for c in customer_name)
        folder_name = f"{safe_customer_name}_{ticket_id}"
        
        # Create the target path
        if not server_path:
            logging.error("No server path specified")
            return False
            
        target_dir = os.path.join(server_path, folder_name)
        
        try:
            # Create the target directory if it doesn't exist
            os.makedirs(target_dir, exist_ok=True)
            
            # Copy the file to the target directory
            import shutil
            target_file = os.path.join(target_dir, os.path.basename(snapshot_file))
            shutil.copy2(snapshot_file, target_file)
            
            logging.info(f"Saved snapshot to network folder: {target_file}")
            return target_file
        except Exception as e:
            logging.error(f"Error saving to network folder: {e}")
            return False


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Example API key (not a real key)
    API_KEY = "your-api-key-here"
    
    # Initialize ticket context
    tc = TicketContext(API_KEY)
    
    # Example ticket lookup
    ticket_info = tc.lookup_ticket("12345")
    
    if ticket_info:
        print(f"Found ticket for customer: {tc.get_customer_name()}")
        
        # Get customer-reported issues
        issues = tc.get_customer_reported_issues()
        if issues:
            print(f"\nCustomer-reported issues:\n{issues}")
            
        # Example diagnostic note upload
        print("\nUploading diagnostic note...")
        tc.upload_diagnostic_note("System diagnostic completed. CPU: Intel i7, RAM: 16GB, Disk: 500GB SSD.")
    else:
        print("No ticket found or API error occurred.")
