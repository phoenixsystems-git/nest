import requests
import logging
import time
import os
import json
from datetime import datetime, timedelta
from functools import wraps
from nest.utils.config_util import load_config, ConfigManager

# Unified cache system with consistent expiry times
RESPONSE_CACHE = {}
DEFAULT_CACHE_EXPIRY = 180  # 3 minutes - balanced between freshness and performance
EMPLOYEE_CACHE_EXPIRY = 1800  # 30 minutes for employees (reduced from 1 hour)
TICKET_CACHE_EXPIRY = 90  # 1.5 minutes for tickets (reduced from 2 minutes)

# Retry configuration - optimized for better performance
MAX_RETRIES = 2  # Reduced from 3 to 2 for faster failures
RETRY_DELAY = 0.5  # Reduced from 1 second to 0.5 seconds

# Helper function for retrying API calls with optimized backoff
def retry_with_backoff(max_retries=MAX_RETRIES, initial_delay=RETRY_DELAY):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            delay = initial_delay
            last_exception = None
            
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except requests.RequestException as e:
                    last_exception = e
                    logging.warning(f"API call failed (attempt {retries+1}/{max_retries}): {str(e)}")
                    
                    if retries < max_retries - 1:
                        if isinstance(e, (requests.exceptions.Timeout, requests.exceptions.ConnectionError)):
                            time.sleep(delay)
                            retries += 1
                            delay *= 1.2  # Further reduced multiplier for faster retries
                        else:
                            break
                    else:
                        break
            
            # If we get here, all retries failed
            logging.error(f"All {max_retries} API call attempts failed. Last error: {str(last_exception)}")
            if last_exception:
                raise last_exception
            else:
                raise requests.RequestException("API call failed with unknown error")
        return wrapper
    return decorator


class RepairDeskClient:
    def __init__(self, api_key: str, base_url=None):
        self.api_key = api_key
        # Always use the official API endpoint - do not allow overrides to prevent connection issues
        self.base_url = "https://api.repairdesk.co/api/web/v1" # Hardcode the working web API endpoint
        
        # Standardize headers
        self.headers = {"Content-Type": "application/json"}
        
        # For monitoring API health and usage
        self.last_successful_call = None
        self.failed_calls = 0
        self.total_calls = 0
        
        # Load API key from config if not provided
        if not self.api_key:
            self._load_api_key_from_config()
            
        # To avoid startup delay, don't validate the API key on init
        # It will be validated when first used instead
        self._api_key_validated = False
        
    def _load_api_key_from_config(self):
        """Load API key from config file."""
        try:
            config = load_config()
            # Check both possible locations of API key in config
            self.api_key = config.get("repairdesk_api_key") or config.get("api_key") or \
                          config.get("repairdesk", {}).get("api_key", "")
            if self.api_key:
                logging.info(f"[RepairDeskClient] Loaded API key from config: {self.api_key[:5]}...")
            return bool(self.api_key)
        except Exception as e:
            logging.error(f"[RepairDeskClient] Error loading API key from config: {e}")
            return False

    def _validate_api_key(self):
        """Validate the API key by making a test call to fetch a single ticket"""
        # Only validate if we have a key to test
        if not self.api_key:
            # Try to load API key from config as fallback
            try:
                config = load_config()
                # Check both possible locations of API key in config
                self.api_key = config.get("repairdesk_api_key") or config.get("api_key") or \
                              config.get("repairdesk", {}).get("api_key", "")
                logging.info(f"[RepairDeskClient] Loaded API key from config: {self.api_key[:5]}...")
            except Exception as e:
                logging.error(f"[RepairDeskClient] Error loading API key from config: {e}")
                
        if not self.api_key:
            logging.warning("[RepairDeskClient] No API key provided, skipping validation")
            return False
        
        try:
            # Make a lightweight call to validate the API key
            url = f"{self.base_url}/web/v1/tickets"
            params = {"api_key": self.api_key, "limit": 1}  # Just get one ticket
            
            logging.info("[RepairDeskClient] Validating API key...")
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                logging.info("[RepairDeskClient] API key validation successful")
                self.last_successful_call = datetime.now()
                return True
            else:
                logging.error(f"[RepairDeskClient] API key validation failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logging.error(f"[RepairDeskClient] API key validation error: {e}")
            return False
    
    @classmethod
    def from_config(cls):
        """Create a client instance from configuration file"""
        config = load_config()
        api_key = config.get("repairdesk", {}).get("api_key", "")
        base_url = config.get("repairdesk", {}).get("base_url", "https://api.repairdesk.co/api")
        
        if not api_key:
            logging.error("[RepairDeskClient] API key missing from config")
        else:
            logging.info("[RepairDeskClient] API key loaded successfully")
            
        return cls(api_key=api_key, base_url=base_url)

    def get_employees(self):
        """Get all employees from RepairDesk"""
        # Create a cache key based on the method name
        cache_key = 'employees'
        
        # Use a cache time of 1 hour for employees since they rarely change
        EMPLOYEE_CACHE_EXPIRY = 3600  # 1 hour
        
        # Check if we have a valid cached response
        if cache_key in RESPONSE_CACHE:
            cache_time, cache_data = RESPONSE_CACHE[cache_key]
            if datetime.now() - cache_time < timedelta(seconds=EMPLOYEE_CACHE_EXPIRY):
                logging.info("[RepairDeskClient] Returning cached employees list")
                return cache_data
        
        # Attempt to fetch fresh data - avoid excessive retries that could hang the app
        return self._fetch_employees_with_timeout()
    
    def _fetch_employees_with_timeout(self):
        """Fetch employees from the API with a timeout to prevent hanging."""
        self.total_calls += 1
        
        # Use only the working API endpoint
        try:
            url = f"{self.base_url}/employees"
            params = {"api_key": self.api_key}
            
            logging.info(f"[RepairDeskClient] Fetching employees from: {url}")
            response = requests.get(url, params=params, timeout=8)  # 8-second timeout
            
            if response.status_code == 200:
                self.last_successful_call = datetime.now()
                employees_data = response.json()
                
                # Cache the successful response
                RESPONSE_CACHE['employees'] = (datetime.now(), employees_data)
                return employees_data
            else:
                self.failed_calls += 1
                error_msg = f"[RepairDeskClient] Error fetching employees: {response.status_code}"
                try:
                    error_details = response.json()
                    error_msg += f" - {error_details}"
                except:
                    error_msg += f" - {response.text[:100]}"  # Limit text length
                    
                logging.error(error_msg)
                
                # Return empty list instead of None so the app can proceed
                return []
        except requests.exceptions.Timeout:
            self.failed_calls += 1
            logging.error("[RepairDeskClient] Timeout while fetching employees - API may be slow")
            return []
        except Exception as e:
            self.failed_calls += 1
            logging.error(f"[RepairDeskClient] Error fetching employees: {e}")
            return []

    @retry_with_backoff()
    def get_tickets(self, status=None, page=1, limit=50, force_refresh=False):
        """
        Get tickets from RepairDesk.
        
        Args:
            status (str, optional): Filter by ticket status. Defaults to None.
            page (int, optional): Page number for pagination. Defaults to 1.
            limit (int, optional): Number of tickets per page. Defaults to 50.
            
        Returns:
            dict: The API response containing tickets data
        """
        # Create a cache key based on the parameters
        cache_key = f'tickets_status={status}_page={page}_limit={limit}'
        
        # Check if we have a valid cached response with ticket-specific expiry time
        # Skip cache if force_refresh is True
        if not force_refresh and cache_key in RESPONSE_CACHE:
            cache_time, cache_data = RESPONSE_CACHE[cache_key]
            if datetime.now() - cache_time < timedelta(seconds=TICKET_CACHE_EXPIRY):
                logging.debug(f"[RepairDeskClient] Using cached tickets data for {cache_key}")
                return cache_data
                
        if force_refresh:
            logging.info(f"[RepairDeskClient] Force refreshing tickets data for {cache_key}")
        
        # Validate API key if not already done
        if not getattr(self, '_api_key_validated', False):
            if not self._validate_api_key():
                return None
            self._api_key_validated = True
            
        # We need to make a fresh API call
        self.total_calls += 1
        
        # Use the base_url for consistent API access
        url = f"{self.base_url}/tickets"
        params = {"api_key": self.api_key, "page": page, "limit": limit}
        
        # Add status filter if provided
        if status:
            params["status"] = status
        
        try:
            logging.info(f"[RepairDeskClient] GET {url}")
            response = requests.get(url, params=params, timeout=15)
            
            if response.status_code == 200:
                self.last_successful_call = datetime.now()
                tickets_data = response.json()
                
                # Cache the successful response
                RESPONSE_CACHE[cache_key] = (datetime.now(), tickets_data)
                return tickets_data
            else:
                self.failed_calls += 1
                logging.error(f"[RepairDeskClient] Error fetching tickets: {response.status_code} - {response.text}")
                return {"data": [], "error": f"HTTP {response.status_code}"}
        except Exception as e:
            self.failed_calls += 1
            logging.error(f"[RepairDeskClient] Error fetching tickets: {e}")
            return {"data": [], "error": str(e)}

    @retry_with_backoff()
    def get_all_tickets(self, force_refresh=False):
        """
        Get all tickets from RepairDesk by handling pagination automatically.
        
        Returns:
            list: A list of all tickets across all pages
        """
        all_tickets = []
        page = 1
        limit = 100  # Maximum allowed by the API for efficiency
        
        while True:
            # Get a page of tickets
            tickets_response = self.get_tickets(page=page, limit=limit, force_refresh=force_refresh)
            
            # Check if the response is valid
            if not tickets_response or 'data' not in tickets_response:
                logging.error(f"[RepairDeskClient] Invalid response when fetching page {page} of tickets")
                break
                
            # Get the tickets from the response - handle different API response structures
            tickets = []
            
            # Check if this is using the newer API format with ticketData
            if 'data' in tickets_response and 'ticketData' in tickets_response['data']:
                ticket_data = tickets_response['data'].get('ticketData', {})
                # ticketData can be a dict with numeric keys or a list
                if isinstance(ticket_data, dict):
                    tickets = list(ticket_data.values())
                elif isinstance(ticket_data, list):
                    tickets = ticket_data
            # Check if using the older API format with 'data' array directly
            elif 'data' in tickets_response and isinstance(tickets_response['data'], list):
                tickets = tickets_response['data']
            # Fallback to direct data access
            else:
                tickets = tickets_response.get('data', [])
            
            # Process tickets - ensure each one is a dictionary, not a string
            processed_tickets = []
            for ticket in tickets:
                try:
                    # Skip metadata fields
                    if isinstance(ticket, str) and (ticket.startswith('ticketData') or ticket.startswith('pagination')):
                        logging.warning(f"[RepairDeskClient] Skipping metadata: {ticket[:20]}...")
                        continue
                        
                    # If ticket is a string, try to parse it as JSON
                    if isinstance(ticket, str):
                        try:
                            ticket = json.loads(ticket)
                        except json.JSONDecodeError:
                            logging.error(f"[RepairDeskClient] Failed to parse ticket string as JSON: {ticket[:100]}...")
                            continue
                    
                    # If ticket is not a dictionary after processing, skip it
                    if not isinstance(ticket, dict):
                        logging.error(f"[RepairDeskClient] Ticket is not a dictionary: {type(ticket)}")
                        continue
                        
                    processed_tickets.append(ticket)
                except Exception as e:
                    logging.error(f"[RepairDeskClient] Error processing ticket: {e}")
            
            # Add the processed tickets to our list
            all_tickets.extend(processed_tickets)
            
            # Check if we've reached the end of the pages
            total_pages = tickets_response.get('meta', {}).get('pagination', {}).get('total_pages', 1)
            if page >= total_pages or not tickets:
                break
                
            # Move to the next page
            page += 1
            
        return all_tickets

    def add_note_to_ticket(self, ticket_id, note, note_type=1, is_flag=0):
        """
        Add a note to a RepairDesk ticket.
        
        Args:
            ticket_id (int): The ticket ID (numeric ID, not the T-number)
            note (str): The text content of the note
            note_type (int, optional): Type of note: 0=Internal, 1=Diagnostic. Defaults to 1.
            is_flag (int, optional): Whether the note is flagged. Defaults to 0.
            
        Returns:
            dict: The API response
        """
        self.total_calls += 1
        
        # Ensure we're using the official web API endpoint
        # Don't try to modify the base URL, just use the official endpoint directly
        url = "https://api.repairdesk.co/api/web/v1/ticket/addnote"
        
        # Ensure note_type is 0 or 1
        if note_type not in [0, 1]:
            note_type = 1  # Default to diagnostic note
            
        payload = {
            "id": ticket_id,
            "note": note,
            "type": note_type,
            "is_flag": is_flag
        }
        
        logging.info(f"[RepairDeskClient] Adding note to ticket {ticket_id}")
        
        # API key is passed as a query parameter
        params = {"api_key": self.api_key}
        response = requests.post(url, json=payload, params=params, timeout=15)
        
        try:
            response_json = response.json()
        except ValueError:
            # Handle case where response isn't valid JSON
            self.failed_calls += 1
            logging.error(f"[RepairDeskClient] Invalid JSON response: {response.text}")
            return {"success": False, "message": "Invalid response from server"}
            
        if response.status_code == 200 and response_json.get("success", False):
            self.last_successful_call = datetime.now()
            logging.info(f"[RepairDeskClient] Note added successfully to ticket {ticket_id}")
            return response_json
        else:
            self.failed_calls += 1
            error_message = response_json.get('message', 'Unknown error')
            logging.error(f"[RepairDeskClient] Error adding note: {error_message}")
            return response_json
    
    def get_ticket_details(self, ticket_id):
        """
        Get detailed information for a specific ticket.
        
        Args:
            ticket_id (int): The ticket ID (numeric ID, not the T-number)
            
        Returns:
            dict: The ticket details
        """
        # Create a cache key based on ticket ID
        cache_key = f'ticket_details_{ticket_id}'
        
        # Check if we have a valid cached response
        if cache_key in RESPONSE_CACHE:
            cache_time, cache_data = RESPONSE_CACHE[cache_key]
            if datetime.now() - cache_time < timedelta(seconds=DEFAULT_CACHE_EXPIRY):
                logging.info(f"[RepairDeskClient] Returning cached ticket details for {ticket_id}")
                return cache_data
                
        self.total_calls += 1
        url = f"{self.base_url}/tickets/{ticket_id}"
        params = {"api_key": self.api_key}
        
        logging.info(f"[RepairDeskClient] GET {url}")
        
        try:
            response = requests.get(url, params=params, timeout=15)
            
            if response.status_code == 200:
                self.last_successful_call = datetime.now()
                ticket_data = response.json()
                
                # Cache the successful response
                RESPONSE_CACHE[cache_key] = (datetime.now(), ticket_data)
                return ticket_data
            else:
                self.failed_calls += 1
                logging.error(f"[RepairDeskClient] Error fetching ticket details: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            self.failed_calls += 1
            logging.error(f"[RepairDeskClient] Error fetching ticket details: {e}")
            return None
    
    def update_ticket_status(self, ticket_id, status):
        """
        Update the status of a ticket.
        
        Args:
            ticket_id (str): The ticket ID (T-number or numeric ID)
            status (str): The new status to set
            
        Returns:
            dict: The API response
        """
        # Handle T-number format by extracting numeric part
        if isinstance(ticket_id, str) and ticket_id.startswith('T-'):
            try:
                ticket_id = ticket_id[2:]  # Remove 'T-' prefix
            except:
                pass
                
        self.total_calls += 1
        url = f"{self.base_url}/tickets/{ticket_id}"
        params = {"api_key": self.api_key}
        
        # Map status names to RepairDesk status IDs
        status_map = {
            "Pending": 1,
            "In Progress": 2,
            "Waiting For Parts": 3,
            "Completed": 4,
            "Ready For Pickup": 5,
            "Waiting For Customer": 6,
            "Waiting For Quote": 7,
            "Waiting For Deposit": 8,
            "Cancelled": 9,
            "On Hold": 10,
        }
        
        # Try to get status ID from the map
        status_id = None
        for name, id in status_map.items():
            if name.lower() == status.lower() or name.lower() in status.lower() or status.lower() in name.lower():
                status_id = id
                break
                
        # Prepare the payload with either status ID or name
        data = {}
        if status_id:
            # Use status_id which is more reliable
            data["status_id"] = status_id
            logging.info(f"[RepairDeskClient] Mapped status '{status}' to ID {status_id}")
        else:
            # Fallback to status string if no mapping found
            data["status"] = status
            logging.warning(f"[RepairDeskClient] Could not map status '{status}' to an ID, using string value")
        
        logging.info(f"[RepairDeskClient] Updating ticket {ticket_id} status to {status}")
        
        try:
            # First make the status update request
            response = requests.put(url, json=data, params=params, timeout=15)
            
            if response.status_code in [200, 201, 202]:
                self.last_successful_call = datetime.now()
                result = response.json()
                logging.info(f"[RepairDeskClient] Successfully updated ticket {ticket_id} status")
                
                # Force update the ticket cache to reflect the new status
                try:
                    # Delete the ticket cache to force a refresh on next fetch
                    # Look for the cache file in current directory first (working directory)
                    cache_path = "ticket_cache.json"
                    if os.path.exists(cache_path):
                        os.remove(cache_path)
                        logging.info("[RepairDeskClient] Cleared ticket cache to reflect status update")
                    else:
                        # Try alternative locations
                        alternative_paths = [
                            os.path.join(os.path.dirname(__file__), "..", "ticket_cache.json"),
                            os.path.join(os.getcwd(), "ticket_cache.json")
                        ]
                        for alt_path in alternative_paths:
                            if os.path.exists(alt_path):
                                os.remove(alt_path)
                                logging.info(f"[RepairDeskClient] Cleared ticket cache at {alt_path}")
                                break
                except Exception as cache_err:
                    logging.warning(f"[RepairDeskClient] Could not clear ticket cache: {cache_err}")
                    
                return result
            else:
                self.failed_calls += 1
                logging.error(f"[RepairDeskClient] Error updating ticket status: {response.status_code} - {response.text}")
                return {"error": f"API Error: {response.status_code} - {response.text}"}
        except Exception as e:
            self.failed_calls += 1
            error_msg = str(e)
            logging.error(f"[RepairDeskClient] Error updating ticket status: {error_msg}")
            return {"error": error_msg}

@retry_with_backoff()
def add_note_to_ticket(self, ticket_id, note, note_type=1, is_flag=0):
    """
    Add a note to a RepairDesk ticket.
    
    Args:
        ticket_id (int): The ticket ID (numeric ID, not the T-number)
        note (str): The text content of the note
        note_type (int, optional): Type of note: 0=Internal, 1=Diagnostic. Defaults to 1.
        is_flag (int, optional): Whether the note is flagged. Defaults to 0.
        
    Returns:
        dict: The API response
    """
    self.total_calls += 1
    
    # Ensure we're using the official web API endpoint
    # Don't try to modify the base URL, just use the official endpoint directly
    url = "https://api.repairdesk.co/api/web/v1/ticket/addnote"
    
    # Ensure note_type is 0 or 1
    if note_type not in [0, 1]:
        note_type = 1  # Default to diagnostic note
        
    payload = {
        "id": ticket_id,
        "note": note,
        "type": note_type,
        "is_flag": is_flag
    }
    
    logging.info(f"[RepairDeskClient] Adding note to ticket {ticket_id}")
    
    # API key is passed as a query parameter
    params = {"api_key": self.api_key}
    response = requests.post(url, json=payload, params=params, timeout=15)
    
    try:
        response_json = response.json()
    except ValueError:
        # Handle case where response isn't valid JSON
        self.failed_calls += 1
        logging.error(f"[RepairDeskClient] Invalid JSON response: {response.text}")
        return {"success": False, "message": "Invalid response from server"}
        
    if response.status_code == 200 and response_json.get("success", False):
        self.last_successful_call = datetime.now()
        logging.info(f"[RepairDeskClient] Note added successfully to ticket {ticket_id}")
        return response_json
    else:
        self.failed_calls += 1
        error_message = response_json.get('message', 'Unknown error')
        logging.error(f"[RepairDeskClient] Error adding note: {error_message}")
        return response_json

    def get_all_tickets(self):
        """
        Get all available tickets from RepairDesk API using a more direct approach.
        
        This method attempts to fetch all tickets through pagination in a way that's more
        consistent with the dashboard module's approach, which is proven to work reliably.
        
        Returns:
            list: List of ticket dictionaries
        """
        logging.info("[RepairDeskClient] Fetching all tickets using direct approach")
        
        # Force refresh if requested
        if hasattr(self, '_force_refresh') and self._force_refresh:
            logging.info("[RepairDeskClient] Forcing ticket refresh - bypassing cache")
            delattr(self, '_force_refresh')
        else:
            # Check for cached tickets
            cached_data = self._load_from_cache()
            if cached_data:
                logging.info(f"[RepairDeskClient] Returning {len(cached_data)} tickets from cache")
                return cached_data
        
        # Start with empty list and first page
        all_tickets = []
        page = 1
        
        # Match the dashboard module's direct URL approach
        while True:
            url = f"{self.base_url}/tickets?api_key={self.api_key}&page={page}&limit=50"
            logging.info(f"[RepairDeskClient] Fetching: {url}")
            
            try:
                # Direct request like dashboard uses
                response = requests.get(url, headers={"Content-Type": "application/json"}, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                # Check for success
                if not data.get("success"):
                    logging.error(f"[RepairDeskClient] API error: {data.get('message')}")
                    break
                    
                # Process this batch of tickets
                batch = data.get("data", {}).get("ticketData", [])
                if isinstance(batch, dict):
                    batch = list(batch.values())
                    
                if batch:
                    all_tickets.extend(batch)
                    logging.info(f"[RepairDeskClient] Found {len(batch)} tickets on page {page}")
                
                # Check pagination for next page
                pagination = data.get("data", {}).get("pagination", {})
                if pagination.get("next_page_exist") == 1:
                    page = pagination.get("next_page")
                else:
                    logging.info("[RepairDeskClient] No more pages available")
                    break
                    
            except Exception as e:
                logging.error(f"[RepairDeskClient] Error fetching tickets: {str(e)}")
                break
        
        # Save to cache if we got any tickets
        if all_tickets:
            logging.info(f"[RepairDeskClient] Successfully fetched {len(all_tickets)} tickets")
            self._save_to_cache(all_tickets)
        else:
            logging.warning("[RepairDeskClient] No tickets found from API")
        
        return all_tickets

    def get_ticket_details(self, ticket_id):
        """
        Get detailed information for a specific ticket.
        
        Args:
            ticket_id (int): The ticket ID (numeric ID, not the T-number)
            
        Returns:
            dict: The ticket details
        """
        # Validate and clean the ticket_id
        if not ticket_id:
            logging.error("[RepairDeskClient] Invalid ticket ID: None or empty")
            return {}
            
        # Remove the T- prefix if present
        numeric_id = str(ticket_id)
        if numeric_id.startswith("T-"):
            numeric_id = numeric_id[2:]
            
        try:
            # Endpoint for ticket details
            url = f"{self.base_url}/ticket/details/{numeric_id}?api_key={self.api_key}"
            logging.info(f"[RepairDeskClient] Fetching ticket details for ID: {ticket_id}")
            
            # Make the API call
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Check for API-level errors
            if not data.get("success"):
                logging.error(f"[RepairDeskClient] API error: {data.get('message')}")
                return {}
                
            # Extract the ticket details
            ticket_details = data.get("data", {})
            logging.info(f"[RepairDeskClient] Successfully fetched details for ticket {ticket_id}")
            return ticket_details
            
        except requests.RequestException as e:
            logging.error(f"[RepairDeskClient] Network error fetching ticket details: {str(e)}")
        except Exception as e:
            logging.error(f"[RepairDeskClient] Unexpected error fetching ticket details: {str(e)}")
            
        return {}

    # Helper methods for caching, similar to dashboard module
    def _save_to_cache(self, data):
        """Save ticket data to the cache file."""
        try:
            cache_path = os.path.join(os.path.dirname(__file__), "..", "ticket_cache.json")
            with open(cache_path, "w") as file:
                json.dump(data, file)
            logging.info("[RepairDeskClient] Tickets data cached successfully.")
        except Exception as e:
            logging.error(f"[RepairDeskClient] Failed to cache tickets: {e}")

    def _load_from_cache(self):
        """Load ticket data from the cache file."""
        try:
            cache_path = os.path.join(os.path.dirname(__file__), "..", "ticket_cache.json")
            if os.path.exists(cache_path):
                with open(cache_path, "r") as file:
                    logging.info("[RepairDeskClient] Loading tickets from cache.")
                    return json.load(file)
        except Exception as e:
            logging.error(f"[RepairDeskClient] Failed to load cached tickets: {e}")
        return None
