import requests
from nest.utils.logger import log_message
from nest.utils.config import get_repairdesk_key


class RepairDeskClient:
    def __init__(self, api_key=None):
        self.base_url = "https://api.repairdesk.co/api/web/v1"
        # Use provided API key or fall back to config
        self.api_key = api_key or get_repairdesk_key()
        if not self.api_key:
            log_message("Warning: No API key available for RepairDesk client", level="warning")

    def get_tickets(self, page=1, force_refresh=False):
        if not self.api_key:
            log_message("Error: Cannot fetch tickets without API key", level="error")
            return {}

        url = f"{self.base_url}/tickets?api_key={self.api_key}&page={page}"
        log_message(f"Fetching tickets from URL: {url}")
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            log_message(f"API response received successfully (data not shown)")
            return data
        except Exception as e:
            log_message(f"Error fetching tickets: {e}")
            return {}

    def get_all_tickets(self, force_refresh=False):
        page = 1
        tickets = []
        while True:
            data = self.get_tickets(page, force_refresh=force_refresh)
            if data:
                tickets_page = data.get("data", {}).get("ticketData", [])
                tickets.extend(tickets_page)
                pagination = data.get("data", {}).get("pagination", {})
                if pagination.get("next_page_exist"):
                    page = pagination.get("next_page")
                else:
                    break
            else:
                break
            
        # After getting all tickets, create ticket detail files
        if tickets:
            log_message(f"Successfully retrieved {len(tickets)} tickets from API")
            log_message("Creating ticket detail files...")
            self._create_ticket_detail_files(tickets)
        
        return tickets
    
    def _create_ticket_detail_files(self, tickets):
        """Create individual ticket detail JSON files using efficient batch processing.
        
        This function uses the main tickets API with batch fetching (1000 at a time) to get
        detailed ticket information and saves it to individual files named ticket_detail_T-XXXXX.json.
        This is much more efficient than making individual API calls for each ticket.
        
        Args:
            tickets: List of tickets to create detail files for
        """
        # Import necessary modules at the beginning of the function
        import os
        import json
        import time
        from datetime import datetime
        
        if not tickets:
            log_message("No tickets provided to create detail files")
            return
        
        if not self.api_key:
            log_message("ERROR: API key is missing, cannot create ticket detail files")
            return
        
        # Create cache directory if it doesn't exist
        from nest.utils.cache_utils import get_cache_directory
        cache_dir = get_cache_directory()
        
        log_message(f"🚀 BATCH PROCESSING: Creating ticket detail files for {len(tickets)} tickets using efficient batch method")
        
        success_count = 0
        error_count = 0
        
        # Process tickets in batches - the tickets already contain detailed information from batch API calls
        # We just need to save them to individual files for compatibility
        for ticket in tickets:
            try:
                # Extract the ticket ID and order ID
                ticket_summary = ticket.get('summary', {})
                ticket_id = ticket_summary.get('id')
                order_id = ticket_summary.get('order_id')
                
                if not ticket_id or not order_id:
                    log_message(f"WARNING: Skipping ticket with missing ID or order_id: ID={ticket_id}, order_id={order_id}")
                    error_count += 1
                    continue
                    
                # Format the ticket ID for file name (ensure it starts with T-)
                formatted_id = f"T-{order_id}" if not str(order_id).startswith("T-") else str(order_id)
                
                # Check if the detail file was updated in the last 1 hour (reduced from 24 hours for better freshness)
                file_path = os.path.join(cache_dir, f"ticket_detail_{formatted_id}.json")
                if os.path.exists(file_path):
                    file_stat = os.stat(file_path)
                    file_age_hours = (time.time() - file_stat.st_mtime) / 3600
                    
                    if file_age_hours < 1:
                        log_message(f"DEBUG: Skipping recent ticket detail file: {order_id} (age: {file_age_hours:.1f} hours)")
                        continue
                
                # ✅ NO INDIVIDUAL API CALL - Use the detailed data already fetched in batch
                # The ticket data from batch API already contains all the details we need
                detailed_data = {
                    'success': True,
                    'data': ticket,  # Use the complete ticket data from batch fetch
                    'batch_processed': True,
                    'processed_at': datetime.now().isoformat()
                }
                
                # Save the detailed information to a file
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(detailed_data, f, indent=2)
                
                success_count += 1
                log_message(f"DEBUG: Successfully saved ticket detail file: {file_path}")
                
            except Exception as e:
                log_message(f"ERROR: Unexpected error creating ticket detail file for {ticket_id}: {e}")
                error_count += 1
        
        log_message(f"✅ BATCH COMPLETE: Created {success_count} ticket detail files, {error_count} failures - NO individual API calls made!")

    def add_note_to_ticket(self, ticket_id, note, note_type=1, is_flag=0):
        url = f"{self.base_url}/ticket/addnote?api_key={self.api_key}"
        payload = {"id": ticket_id, "note": note, "type": note_type, "is_flag": is_flag}
        log_message(f"Sending note to URL: {url} with payload: {payload}")
        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            log_message(f"Note added response: {data}")
            return data
        except Exception as e:
            log_message(f"Error adding note to ticket: {e}")
            return {"success": False, "message": str(e)}
            
    def get_ticket_by_id(self, ticket_id, actual_api_id=None):
        """Fetch a single ticket by its ID using the /tickets/{Ticket-Id} endpoint.
        
        Args:
            ticket_id: The display ID of the ticket (for logging purposes)
            actual_api_id: The actual API ID to use for the request (if different from ticket_id)
            
        Returns:
            dict: Complete ticket details or empty dict if error
        """
        if not self.api_key:
            log_message("Error: Cannot fetch ticket without API key", level="error")
            return {}
        
        # Use the actual API ID if provided, otherwise use the ticket_id    
        api_id = actual_api_id if actual_api_id else ticket_id
            
        # Remove T- prefix if present since the API expects only the numeric part
        if isinstance(api_id, str) and api_id.startswith("T-"):
            api_id = api_id[2:]
            
        url = f"{self.base_url}/tickets/{api_id}?api_key={self.api_key}"
        log_message(f"DEBUG: API request - Ticket ID: {ticket_id}, API ID: {api_id}, Using actual_api_id: {True if actual_api_id else False}")
        log_message(f"Fetching ticket details from URL: {url}")
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            
            # Check if the API response indicates the ticket was found
            if data.get("success") == False or data.get("statusCode") == 404:
                log_message(f"Ticket not found for ID: {ticket_id} - {data.get('message', 'No details provided')}")
                return {}
                
            log_message(f"Ticket details fetched successfully for ID: {ticket_id}")
            
            # Save the raw API response to a JSON file in the cache directory
            try:
                import os
                import json
                from datetime import datetime
                
                # Create cache directory if it doesn't exist
                from nest.utils.cache_utils import get_cache_directory
                cache_dir = get_cache_directory()
                
                # Create filename using only the ticket_id (without timestamp)
                display_id = ticket_id
                if isinstance(display_id, str) and not display_id.startswith("T-"):
                    display_id = f"T-{display_id}"
                    
                # Use consistent filename without timestamp so it gets overwritten
                filename = f"ticket_detail_{display_id}.json"
                filepath = os.path.join(cache_dir, filename)
                
                # Save the data to a file with pretty formatting
                with open(filepath, "w") as f:
                    json.dump(data, f, indent=2)
                    
                log_message(f"Saved raw API response to {filepath}")
            except Exception as e:
                log_message(f"Error saving API response to file: {e}", level="error")
            
            return data
        except Exception as e:
            log_message(f"Error fetching ticket details for ID {ticket_id}: {e}")
            return {}
