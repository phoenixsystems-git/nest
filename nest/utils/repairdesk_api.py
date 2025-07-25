import requests
import json
import logging
import os
import time
from typing import Dict, List, Optional, Any, Union, Tuple, BinaryIO
from datetime import datetime, date


class RepairDeskAPI:
    """Comprehensive client for interacting with RepairDesk's official API."""
    
    def __init__(self, api_key: Optional[str] = None, store_slug: Optional[str] = None, cache_ttl: int = 3600):
        """Initialize API client with authentication details.
        
        Args:
            api_key: The RepairDesk API key for authentication
            store_slug: The RepairDesk store slug (for reference, not used in API calls)
            cache_ttl: Time to live for cached data in seconds (default: 1 hour)
        """
        # Initialize logger first so it can be used in load_from_config
        self.logger = logging.getLogger(__name__)
        
        self.api_key = api_key
        self.store_slug = store_slug
        self.base_url = "https://api.repairdesk.co/api/web/v1"
        self.cache_ttl = cache_ttl
        self._cache = {}
        
        if not api_key:
            # Try to load from config
            self.load_from_config()
    
    def load_from_config(self) -> bool:
        """Load API key and store slug from config file.
        
        Returns:
            True if successfully loaded config, False otherwise
        """
        config_path = self._find_config_file()
        if not config_path or not os.path.exists(config_path):
            return False
            
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                
            self.api_key = config.get('repairdesk_api_key') or config.get('api_key')
            self.store_slug = config.get('store_slug')
            
            if self.api_key:
                self.logger.info(f"Loaded API key from config for store: {self.store_slug}")
                return True
            return False
        except Exception as e:
            self.logger.warning(f"Failed to load API config: {str(e)}")
            return False
    
    def _find_config_file(self) -> Optional[str]:
        """Find the configuration file path using platform-appropriate location."""
        try:
            from .platform_paths import PlatformPaths
            platform_paths = PlatformPaths()
            config_dir = platform_paths.get_config_dir()
            config_path = config_dir / 'config.json'
            if config_path.exists():
                return str(config_path)
            platform_paths.ensure_dir_exists(config_dir)
            return str(config_path)
        except ImportError:
            pass
        
        # Fallback to common locations
        possible_paths = [
            os.path.join(os.path.dirname(__file__), '..', 'config', 'config.json'),
            os.path.join(os.path.dirname(__file__), 'config', 'config.json')
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
                
        return None
    
    def save_to_config(self, remember_api_key: bool = True) -> bool:
        """Save API key and store slug to config file.
        
        Args:
            remember_api_key: Whether to save the API key
            
        Returns:
            True if successfully saved, False otherwise
        """
        config_path = self._find_config_file()
        if not config_path:
            # Create config directory using platform-appropriate location
            try:
                from .platform_paths import PlatformPaths
                platform_paths = PlatformPaths()
                config_dir = platform_paths.ensure_dir_exists(platform_paths.get_config_dir())
                config_path = str(config_dir / 'config.json')
            except ImportError:
                # Fallback to current working directory
                config_dir = os.path.join(os.getcwd(), 'config')
                os.makedirs(config_dir, exist_ok=True)
                config_path = os.path.join(config_dir, 'config.json')
        
        try:
            # Load existing config
            config = {}
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = json.load(f)
            
            # Update config
            config['store_slug'] = self.store_slug
            if remember_api_key:
                config['repairdesk_api_key'] = self.api_key
            
            # Save config
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
                
            self.logger.info(f"Saved API config for store: {self.store_slug}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to save API config: {str(e)}")
            return False
    
    def _get_from_cache(self, cache_key: str) -> Tuple[bool, Any]:
        """Get data from cache if available and not expired.
        
        Args:
            cache_key: Unique key for cached data
            
        Returns:
            Tuple of (found, data)
        """
        if cache_key in self._cache:
            entry = self._cache[cache_key]
            if time.time() - entry["timestamp"] < self.cache_ttl:
                return True, entry["data"]
        return False, None
    
    def _set_cache(self, cache_key: str, data: Any) -> None:
        """Store data in cache with current timestamp.
        
        Args:
            cache_key: Unique key for cached data
            data: Data to cache
        """
        self._cache[cache_key] = {
            "timestamp": time.time(),
            "data": data
        }
    
    def _clear_cache(self, prefix: Optional[str] = None) -> None:
        """Clear all cached data or items with specific prefix.
        
        Args:
            prefix: Optional prefix to clear only matching cache entries
        """
        if prefix:
            keys_to_remove = [k for k in self._cache.keys() if k.startswith(prefix)]
            for key in keys_to_remove:
                del self._cache[key]
        else:
            self._cache.clear()
    
    def request(self, endpoint: str, method: str = "GET", params: Dict = None, 
               data: Dict = None, files: Dict = None, use_cache: bool = False,
               raw_response: bool = False) -> Dict:
        """Make a request to the RepairDesk API.
        
        Args:
            endpoint: API endpoint (without leading slash)
            method: HTTP method (GET, POST, PUT, DELETE)
            params: Optional query parameters
            data: Optional JSON data for request body
            files: Optional files to upload
            use_cache: Whether to use cached data for GET requests
            raw_response: Return raw response without extracting data field
            
        Returns:
            Response data as dictionary
            
        Raises:
            ValueError: If API key is not set
            Exception: If API request fails
        """
        if not self.api_key:
            raise ValueError("API key not set")
        
        url = f"{self.base_url}/{endpoint}"
        
        # Ensure params includes API key
        if params is None:
            params = {}
        params['api_key'] = self.api_key
        
        # For GET requests with caching, check cache first
        cache_key = None
        if use_cache and method.upper() == "GET":
            cache_key = f"{method}:{endpoint}:{json.dumps(params, sort_keys=True)}"
            cache_hit, cached_data = self._get_from_cache(cache_key)
            if cache_hit:
                self.logger.debug(f"Cache hit for {url}")
                return cached_data
        
        self.logger.debug(f"Making {method} request to {url}")
        
        try:
            # Prepare request arguments
            request_args = {
                "method": method,
                "url": url,
                "params": params,
                "timeout": 30
            }
            
            # Handle files upload or JSON body
            if files:
                request_args["files"] = files
                if data:
                    request_args["data"] = data  # For multipart/form-data
            elif data:
                request_args["json"] = data
            
            # Make the request
            response = requests.request(**request_args)
            
            # Log response status
            self.logger.debug(f"API response: {response.status_code}")
            
            # Raise exception for bad responses
            response.raise_for_status()
            
            # Parse response
            try:
                response_data = response.json()
            except json.JSONDecodeError:
                if response.content:
                    response_data = {"content": response.content.decode('utf-8', errors='replace')}
                else:
                    response_data = {}
            
            # Extract data or return full response based on parameter
            result = response_data
            if isinstance(response_data, dict) and 'success' in response_data:
                # Check for API success flag
                if not response_data['success']:
                    error_msg = response_data.get('message', 'API request failed')
                    self.logger.error(f"API error: {error_msg}")
                    raise Exception(f"API error: {error_msg}")
                    
                # Return actual data or full response
                if not raw_response and 'data' in response_data:
                    result = response_data['data']
            
            # Cache result for GET requests
            if cache_key:
                self._set_cache(cache_key, result)
                
            return result
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request error: {e}")
            raise Exception(f"API request failed: {e}")
    
    def validate_credentials(self) -> bool:
        """Validate API key by checking if we can fetch employees list.
        
        Returns:
            True if credentials are valid, False otherwise
        """
        try:
            employees = self.get_employees()
            return len(employees) > 0
        except Exception as e:
            self.logger.error(f"Failed to validate API credentials: {str(e)}")
            return False
    
    def set_credentials(self, api_key: str, store_slug: str = None, 
                       remember: bool = True) -> bool:
        """Update API credentials and optionally store in config.
        
        Args:
            api_key: The RepairDesk API key
            store_slug: The RepairDesk store slug (optional)
            remember: Whether to save to config file
            
        Returns:
            True if credentials are valid and saved, False otherwise
        """
        # Store old values in case validation fails
        old_api_key = self.api_key
        old_store_slug = self.store_slug
        
        # Set new values
        self.api_key = api_key
        if store_slug:
            self.store_slug = store_slug
        
        # Validate credentials
        if self.validate_credentials():
            # Save to config if requested
            if remember:
                self.save_to_config(remember_api_key=True)
            return True
        else:
            # Restore old values if validation fails
            self.api_key = old_api_key
            self.store_slug = old_store_slug
            return False
    
    # =====================
    # Store Information
    # =====================
    
    def get_store_info(self) -> Dict:
        """Get information about the current store.
        
        Returns:
            Store information dictionary
        """
        return self.request("store/info", use_cache=True)
    
    def get_store_settings(self) -> Dict:
        """Get settings for the current store.
        
        Returns:
            Store settings dictionary
        """
        return self.request("store/settings", use_cache=True)
    
    def get_tax_rates(self) -> List[Dict]:
        """Get all tax rates configured for the store.
        
        Returns:
            List of tax rate dictionaries
        """
        response = self.request("taxes", use_cache=True)
        return response if isinstance(response, list) else []
    
    # =====================
    # Employee Methods
    # =====================
    
    def get_employees(self, include_inactive: bool = False) -> List[Dict]:
        """Fetch all employees for the store.
        
        Args:
            include_inactive: Whether to include inactive employees
            
        Returns:
            List of employee dictionaries
        """
        params = {}
        if include_inactive:
            params["include_inactive"] = 1
            
        response = self.request("employees", params=params, use_cache=True)
        return response if isinstance(response, list) else []
    
    def get_employee(self, employee_id: Union[str, int]) -> Optional[Dict]:
        """Get a specific employee by ID.
        
        Args:
            employee_id: The employee ID
            
        Returns:
            Employee data dictionary or None if not found
        """
        try:
            return self.request(f"employees/{employee_id}", use_cache=True)
        except Exception as e:
            self.logger.error(f"Error fetching employee {employee_id}: {e}")
            
            # Fallback to the employees list if direct lookup fails
            employees = self.get_employees()
            for employee in employees:
                if str(employee.get("id")) == str(employee_id):
                    return employee
            return None
    
    def create_employee(self, employee_data: Dict) -> Dict:
        """Create a new employee.
        
        Args:
            employee_data: Dictionary with employee details including:
                - name: Employee full name
                - email: Employee email
                - phone: Employee phone number
                - role_id: Role ID for the employee
                - access_pin: Optional PIN for login
                - status: 1 for active, 0 for inactive
            
        Returns:
            Created employee data
        """
        response = self.request("employees", method="POST", data=employee_data)
        self._clear_cache("GET:employees")
        return response
    
    def update_employee(self, employee_id: Union[str, int], employee_data: Dict) -> Dict:
        """Update an existing employee.
        
        Args:
            employee_id: The employee ID to update
            employee_data: Dictionary with updated employee details
            
        Returns:
            Updated employee data
        """
        response = self.request(f"employees/{employee_id}", method="PUT", data=employee_data)
        self._clear_cache("GET:employees")
        return response
    
    def delete_employee(self, employee_id: Union[str, int]) -> Dict:
        """Delete an employee (or mark as inactive).
        
        Args:
            employee_id: The employee ID to delete
            
        Returns:
            Response dictionary
        """
        response = self.request(f"employees/{employee_id}", method="DELETE")
        self._clear_cache("GET:employees")
        return response
    
    def verify_employee_pin(self, employee_id: Union[str, int], pin: str) -> Tuple[bool, Optional[Dict]]:
        """Verify employee PIN locally against employees data.
        
        Args:
            employee_id: The employee ID to verify
            pin: The PIN to verify
            
        Returns:
            Tuple of (is_valid, employee_data or None)
        """
        employees = self.get_employees()
        
        for employee in employees:
            if str(employee.get("id")) == str(employee_id) and employee.get("accesspin") == pin:
                return True, employee
        
        return False, None
    
    def get_employee_roles(self) -> List[Dict]:
        """Get all employee roles for the store.
        
        Returns:
            List of role dictionaries
        """
        response = self.request("roles", use_cache=True)
        return response if isinstance(response, list) else []
    
    # =====================
    # Customer Methods
    # =====================
    
    def get_customers(self, page: int = 1, limit: int = 1000, search: str = None) -> Dict:
        """Fetch customers with optional search and pagination.
        
        Args:
            page: Page number for pagination
            limit: Number of customers per page
            search: Optional search term
            
        Returns:
            Dictionary with customer data and pagination info
        """
        params = {
            "page": page,
            "limit": limit
        }
        
        if search:
            params["search"] = search
            
        return self.request("customers", params=params)
    
    def search_customers(self, query: str, field: str = None, exact: bool = False) -> List[Dict]:
        """Search for customers by name, email, or phone.
        
        Args:
            query: Search query string
            field: Specific field to search (name, email, phone)
            exact: Whether to perform exact match
            
        Returns:
            List of matching customer dictionaries
        """
        params = {"search": query}
        if field:
            params["field"] = field
        if exact:
            params["exact"] = 1
            
        response = self.request("customers/search", params=params)
        return response if isinstance(response, list) else []
    
    def get_all_customers(self) -> List[Dict]:
        """Fetch all customers using pagination.
        
        NOTE: Customer data caching is handled in the UI layer.
        This method does NOT handle caching directly.
        
        Returns:
            List of customer dictionaries
        """
        # Customer caching is handled by the customers module, not here
        
        self.logger.info("Fetching all customers from RepairDesk (this may take some time)")
        page = 1
        customers = []
        
        while True:
            response = self.get_customers(page)
            
            if not response or not isinstance(response, dict):
                break
                
            current_page = response.get("customerData", [])
            if not current_page:
                break
                
            customers.extend(current_page)
            
            # Check pagination
            pagination = response.get("pagination", {})
            if pagination.get("next_page_exist"):
                page = pagination.get("next_page")
                self.logger.debug(f"Fetching customer page {page}")
            else:
                break
        
        # We still save a sanitized version with only IDs for debugging purposes
        # (The actual customer data with encryption is handled in the UI layer)
        if customers:
            self.save_customer_cache(customers)
                
        self.logger.info(f"Fetched {len(customers)} customers from RepairDesk")
        return customers
    
    def get_customer(self, customer_id: Union[str, int]) -> Dict:
        """Fetch a specific customer by ID.
        
        Args:
            customer_id: The customer ID
            
        Returns:
            Customer data dictionary
        """
        return self.request(f"customers/{customer_id}")
    
    def get_customer_by_email(self, email: str) -> Optional[Dict]:
        """Find a customer by email address.
        
        Args:
            email: Customer email address
            
        Returns:
            Customer data dictionary or None if not found
        """
        customers = self.search_customers(email, field="email", exact=True)
        return customers[0] if customers else None
    
    def get_customer_by_phone(self, phone: str) -> Optional[Dict]:
        """Find a customer by phone number.
        
        Args:
            phone: Customer phone number
            
        Returns:
            Customer data dictionary or None if not found
        """
        customers = self.search_customers(phone, field="phone", exact=True)
        return customers[0] if customers else None
    
    def create_customer(self, customer_data: Dict) -> Dict:
        """Create a new customer.
        
        Args:
            customer_data: Dictionary with customer details including:
                - firstname: Customer first name
                - lastname: Customer last name
                - email: Customer email
                - mobile: Customer mobile number
                - address: Optional address
                - city: Optional city
                - state: Optional state
                - zip: Optional ZIP code
                - company: Optional company name
            
        Returns:
            Created customer data
        """
        response = self.request("customers", method="POST", data=customer_data)
        self._clear_cache("GET:customers")
        return response
    
    def update_customer(self, customer_id: Union[str, int], customer_data: Dict) -> Dict:
        """Update an existing customer.
        
        Args:
            customer_id: The customer ID to update
            customer_data: Dictionary with updated customer details
            
        Returns:
            Updated customer data
        """
        response = self.request(f"customers/{customer_id}", method="PUT", data=customer_data)
        self._clear_cache("GET:customers")
        return response
    
    def delete_customer(self, customer_id: Union[str, int]) -> Dict:
        """Delete a customer.
        
        Args:
            customer_id: The customer ID to delete
            
        Returns:
            Response dictionary
        """
        response = self.request(f"customers/{customer_id}", method="DELETE")
        self._clear_cache("GET:customers")
        return response
    
    def get_customer_tickets(self, customer_id: Union[str, int]) -> List[Dict]:
        """Get all tickets for a specific customer.
        
        Args:
            customer_id: The customer ID
            
        Returns:
            List of ticket dictionaries
        """
        response = self.request(f"customers/{customer_id}/tickets")
        return response if isinstance(response, list) else []
    
    def get_customer_purchases(self, customer_id: Union[str, int]) -> List[Dict]:
        """Get all purchases for a specific customer.
        
        Args:
            customer_id: The customer ID
            
        Returns:
            List of purchase dictionaries
        """
        response = self.request(f"customers/{customer_id}/purchases")
        return response if isinstance(response, list) else []
    
    # =====================
    # Ticket Methods
    # =====================
    
    def get_tickets(self, page: int = 1, limit: int = 1000, status: str = None, 
                   technician_id: Union[str, int] = None, 
                   date_from: Union[str, datetime, date] = None,
                   date_to: Union[str, datetime, date] = None) -> Dict:
        """Fetch tickets with optional filtering and pagination.
        
        Args:
            page: Page number for pagination
            limit: Number of tickets per page
            status: Optional status filter (e.g., 'open', 'closed')
            technician_id: Optional technician ID to filter by
            date_from: Optional start date (format: YYYY-MM-DD)
            date_to: Optional end date (format: YYYY-MM-DD)
            
        Returns:
            Dictionary with ticket data and pagination info
        """
        params = {
            "page": page,
            "limit": limit
        }
        
        if status:
            params["status"] = status
            
        if technician_id:
            params["technician_id"] = technician_id
            
        if date_from:
            if isinstance(date_from, (datetime, date)):
                params["date_from"] = date_from.strftime("%Y-%m-%d")
            else:
                params["date_from"] = date_from
                
        if date_to:
            if isinstance(date_to, (datetime, date)):
                params["date_to"] = date_to.strftime("%Y-%m-%d")
            else:
                params["date_to"] = date_to
            
        return self.request("tickets", params=params)
    
    def get_all_tickets(self, status: str = None, 
                      technician_id: Union[str, int] = None,
                      date_from: Union[str, datetime, date] = None,
                      date_to: Union[str, datetime, date] = None,
                      use_cache=True, max_cache_age_minutes=15) -> List[Dict]:
        """Fetch all tickets using pagination with optional filtering.
        
        Args:
            status: Optional status filter (e.g., 'open', 'closed')
            technician_id: Optional technician ID to filter by
            date_from: Optional start date filter
            date_to: Optional end date filter
            use_cache (bool): Whether to use cached ticket data if available
            max_cache_age_minutes (int): Maximum age of cache in minutes before refreshing
            
        Returns:
            List of ticket dictionaries
        """
        # Skip cache if filters are applied, as the cache contains all tickets
        skip_cache = bool(status or technician_id or date_from or date_to)
        
        # Try to load from cache file if we should use cache and no filters are applied
        if use_cache and not skip_cache:
            cached_items = self.load_ticket_cache(max_cache_age_minutes)
            if cached_items is not None:
                return cached_items
        else:
            if skip_cache:
                self.logger.info("Filters applied, bypassing ticket cache")
            else:
                self.logger.info("Cache usage disabled, fetching fresh ticket data from API")
        
        # If no valid cache or cache disabled, fetch from API
        self.logger.info("Fetching all tickets from RepairDesk (this may take some time)")
        page = 1
        tickets = []
        
        # Format dates if provided
        from_date_str = None
        to_date_str = None
        
        if date_from:
            if isinstance(date_from, (datetime, date)):
                from_date_str = date_from.strftime("%Y-%m-%d")
            else:
                from_date_str = date_from
                
        if date_to:
            if isinstance(date_to, (datetime, date)):
                to_date_str = date_to.strftime("%Y-%m-%d")
            else:
                to_date_str = date_to
        
        # Fetch tickets with pagination
        while True:
            response = self.get_tickets(
                page=page, 
                status=status,
                technician_id=technician_id,
                date_from=from_date_str,
                date_to=to_date_str
            )
            
            if response and isinstance(response, dict):
                # RepairDesk API returns 'ticketData' not 'data.tickets'
                current_page = response.get("ticketData", [])
                
                if current_page:
                    tickets.extend(current_page)
                else:
                    break
                    
                # Pagination is at root level, not nested
                pagination = response.get("pagination", {})
                
                # Check if there are more pages
                if pagination.get("next_page_exist"):
                    page = pagination.get("next_page")
                    self.logger.debug(f"Fetching ticket page {page}")
                else:
                    break
            else:
                break
        
        # Save results to cache file if no filters were applied
        if tickets and not skip_cache:
            self.save_ticket_cache(tickets)
                
        self.logger.info(f"Fetched {len(tickets)} tickets from RepairDesk")
        return tickets
    
    def get_numeric_ticket_id(self, ticket_number: Union[str, int]) -> Optional[int]:
        """Get the internal RepairDesk numeric ID from a ticket number.
        
        The RepairDesk API uses internal numeric IDs that are different from the
        visible ticket numbers (like T-12353). This method looks up the correct
        internal ID by checking the local cache first, then falling back to API calls.
        
        Args:
            ticket_number: Ticket number, with or without T- prefix (e.g. T-12353 or 12353)
            
        Returns:
            The internal RepairDesk numeric ID if found, None otherwise
        """
        # Normalize the ticket number format
        if isinstance(ticket_number, str):
            ticket_str = ticket_number.strip()
            if ticket_str.startswith('T-'):
                display_number = ticket_str
                numeric_part = ticket_str[2:]  # Remove 'T-' prefix
            else:
                numeric_part = ticket_str
                display_number = f"T-{numeric_part}"
        else:
            numeric_part = str(ticket_number)
            display_number = f"T-{numeric_part}"
        
        self.logger.info(f"Looking up internal ID for ticket {display_number}")
        
        # STEP 1: First try to find the ticket in the local cache
        try:
            # Try to find cache file in common locations
            # Use the centralized cache directory
            cache_path = self.get_ticket_cache_path()
            cache_paths = [cache_path]  # Only use our centralized cache path now
            
            for cache_path in cache_paths:
                if os.path.exists(cache_path):
                    self.logger.info(f"Found ticket cache at {cache_path}")
                    with open(cache_path, 'r') as f:
                        tickets = json.load(f)
                    
                    # Look for matching ticket by order_id
                    for ticket in tickets:
                        if ticket.get('summary', {}).get('order_id') == display_number:
                            internal_id = ticket.get('summary', {}).get('id')
                            if internal_id:
                                self.logger.info(f"Found internal ID {internal_id} for {display_number} in cache")
                                return internal_id
                    
                    self.logger.info(f"Ticket {display_number} not found in cache")
                    break  # Only check one cache file if found
        except Exception as e:
            self.logger.warning(f"Error checking ticket cache: {e}")
        
        # STEP 2: If not in cache, try direct API lookup first
        try:
            tickets_response = self.get_tickets(page=1)
            
            if 'data' in tickets_response and 'ticketData' in tickets_response['data']:
                tickets = tickets_response['data']['ticketData']
                
                for ticket in tickets:
                    if ticket.get('summary', {}).get('order_id') == display_number:
                        internal_id = ticket.get('summary', {}).get('id')
                        if internal_id:
                            self.logger.info(f"Found internal ID {internal_id} for {display_number} via API")
                            return internal_id
        except Exception as e:
            self.logger.warning(f"Error in API lookup: {e}")
        
        # STEP 3: Try getting all tickets as a last resort
        try:
            all_tickets = self.get_all_tickets()
            if all_tickets:
                for ticket in all_tickets:
                    if ticket.get('summary', {}).get('order_id') == display_number:
                        internal_id = ticket.get('summary', {}).get('id')
                        if internal_id:
                            self.logger.info(f"Found internal ID {internal_id} for {display_number} via get_all_tickets")
                            
                            # Save to cache for future use
                            self._update_ticket_cache(all_tickets)
                            
                            return internal_id
        except Exception as e:
            self.logger.error(f"Error in get_all_tickets: {e}")
        
        self.logger.error(f"Could not find internal ID for ticket {display_number}")
        return None
    
    def get_cache_directory(self):
        """Returns the path to the centralized cache directory.
        
        Creates the directory if it doesn't exist.
        """
        # Use platform-appropriate cache directory
        from .platform_paths import PlatformPaths
        platform_paths = PlatformPaths()
        cache_dir = str(platform_paths.ensure_dir_exists(platform_paths.get_cache_dir()))
        
        # Create cache directory if it doesn't exist
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
            self.logger.info(f"Created cache directory at {cache_dir}")
            
        return cache_dir
    
    def get_inventory_cache_path(self):
        """Returns the path to the inventory cache file."""
        return os.path.join(self.get_cache_directory(), 'inventory_cache.json')
    
    def get_ticket_cache_path(self):
        """Returns the path to the ticket cache file."""
        return os.path.join(self.get_cache_directory(), 'ticket_cache.json')
    
    def get_customer_cache_path(self):
        """Returns the path to the customer cache file."""
        return os.path.join(self.get_cache_directory(), 'customer_cache.json')
    
    def get_ticket(self, ticket_id: Union[str, int]) -> Dict:
        """Fetch a specific ticket by ID.
        
        Args:
            ticket_id: The ticket ID (either internal ID or T-number)
            
        Returns:
            Ticket data dictionary
        """
        # If ticket_id is a T-number, convert to internal ID
        if isinstance(ticket_id, str) and ticket_id.startswith('T-'):
            internal_id = self.get_numeric_ticket_id(ticket_id)
            if not internal_id:
                raise ValueError(f"Could not find internal ID for ticket {ticket_id}")
            ticket_id = internal_id
            
        return self.request(f"tickets/{ticket_id}")
    
    def get_ticket_by_number(self, ticket_number: str) -> Optional[Dict]:
        """Get ticket details by ticket number (e.g., 'T-12345').
        
        Args:
            ticket_number: The ticket number to look up
            
        Returns:
            Ticket data dictionary or None if not found
        """
        # Clean up ticket number format
        if ticket_number.startswith("T-"):
            order_id = ticket_number
        else:
            order_id = f"T-{ticket_number.strip()}"
            
        self.logger.info(f"Searching for ticket with order ID: {order_id}")
        
        # Get first page of tickets
        response = self.request("tickets", params={"page": 1, "limit": 100})
        
        # Search for matching ticket
        tickets = response.get("ticketData", [])
        for ticket in tickets:
            if ticket.get("summary", {}).get("order_id") == order_id:
                ticket_id = ticket.get("summary", {}).get("id")
                self.logger.info(f"Found ticket ID {ticket_id} for order ID {order_id}")
                return self.get_ticket(ticket_id)
        
        self.logger.warning(f"No ticket found with order ID: {order_id}")
        return None
    
    def create_ticket(self, ticket_data: Dict) -> Dict:
        """Create a new ticket.
        
        Args:
            ticket_data: Dictionary with ticket details including:
                - customer_id: Customer ID
                - device_id: Device ID
                - issue: Issue description
                - status_id: Ticket status ID
                - technician_id: Assigned technician ID (optional)
                - due_date: Due date (format: YYYY-MM-DD)
                - estimated_cost: Estimated repair cost
                
        Returns:
            Created ticket data
        """
        response = self.request("tickets", method="POST", data=ticket_data)
        self._clear_cache("GET:tickets")
        return response
    
    def quick_create_ticket(self, customer_name: str, customer_email: str, 
                          customer_phone: str, device_type: str, 
                          issue: str, technician_id: Union[str, int] = None) -> Dict:
        """Create a ticket quickly with minimal required information.
        
        This helper method simplifies ticket creation by handling customer creation 
        if needed and formatting the ticket data correctly.
        
        Args:
            customer_name: Customer full name
            customer_email: Customer email
            customer_phone: Customer phone number
            device_type: Device type or model
            issue: Description of the issue
            technician_id: Optional technician ID to assign to the ticket
            
        Returns:
            Created ticket data
        """
        # First check if customer exists by email
        customer = self.get_customer_by_email(customer_email)
        
        # If customer doesn't exist, create a new one
        if not customer:
            # Split name into first and last name
            name_parts = customer_name.strip().split(' ', 1)
            first_name = name_parts[0]
            last_name = name_parts[1] if len(name_parts) > 1 else ""
            
            customer_data = {
                "firstname": first_name,
                "lastname": last_name,
                "email": customer_email,
                "mobile": customer_phone
            }
            
            customer = self.create_customer(customer_data)
        
        customer_id = customer.get("id")
        if not customer_id:
            raise ValueError("Failed to get or create customer")
            
        # Prepare ticket data
        ticket_data = {
            "customer_id": customer_id,
            "device_brand": device_type,
            "issue": issue
        }
        
        if technician_id:
            ticket_data["technician_id"] = technician_id
            
        # Create the ticket
        return self.create_ticket(ticket_data)
    
    def update_ticket(self, ticket_id: Union[str, int], ticket_data: Dict) -> Dict:
        """Update an existing ticket.
        
        Args:
            ticket_id: The ticket ID to update
            ticket_data: Dictionary with updated ticket details
            
        Returns:
            Updated ticket data
        """
        # If ticket_id is a T-number, convert to internal ID
        if isinstance(ticket_id, str) and ticket_id.startswith('T-'):
            internal_id = self.get_numeric_ticket_id(ticket_id)
            if not internal_id:
                raise ValueError(f"Could not find internal ID for ticket {ticket_id}")
            ticket_id = internal_id
            
        response = self.request(f"tickets/{ticket_id}", method="PUT", data=ticket_data)
        self._clear_cache("GET:tickets")
        return response
    
    def change_ticket_status(self, ticket_id: Union[str, int], status_id: Union[str, int]) -> Dict:
        """Change the status of a ticket.
        
        Args:
            ticket_id: The ticket ID
            status_id: New status ID
            
        Returns:
            Updated ticket data
        """
        # If ticket_id is a T-number, convert to internal ID
        if isinstance(ticket_id, str) and ticket_id.startswith('T-'):
            internal_id = self.get_numeric_ticket_id(ticket_id)
            if not internal_id:
                raise ValueError(f"Could not find internal ID for ticket {ticket_id}")
            ticket_id = internal_id
            
        data = {"status_id": status_id}
        return self.update_ticket(ticket_id, data)
    
    def assign_technician(self, ticket_id: Union[str, int], technician_id: Union[str, int]) -> Dict:
        """Assign a technician to a ticket.
        
        Args:
            ticket_id: The ticket ID
            technician_id: Technician ID to assign
            
        Returns:
            Updated ticket data
        """
        # If ticket_id is a T-number, convert to internal ID
        if isinstance(ticket_id, str) and ticket_id.startswith('T-'):
            internal_id = self.get_numeric_ticket_id(ticket_id)
            if not internal_id:
                raise ValueError(f"Could not find internal ID for ticket {ticket_id}")
            ticket_id = internal_id
            
        data = {"technician_id": technician_id}
        return self.update_ticket(ticket_id, data)
    
    def add_ticket_note(self, ticket_id: Union[str, int], note: str, is_private: bool = False) -> Dict:
        """Add a note to a ticket using the older endpoint (legacy support).
        
        Args:
            ticket_id: The ticket ID
            note: The note text
            is_private: Whether this is a private note
            
        Returns:
            Response data
        """
        # If ticket_id is a T-number, convert to internal ID
        if isinstance(ticket_id, str) and ticket_id.startswith('T-'):
            internal_id = self.get_numeric_ticket_id(ticket_id)
            if not internal_id:
                raise ValueError(f"Could not find internal ID for ticket {ticket_id}")
            ticket_id = internal_id
            
        data = {
            "note": note,
            "is_private": is_private
        }
        return self.request(f"tickets/{ticket_id}/notes", method="POST", data=data)
    
    def add_diagnostic_note(self, ticket_id: Union[str, int], note: str, is_flag: int = 0) -> Dict:
        """Add a diagnostic note to a ticket using the new official API endpoint.
        
        Uses the POST https://api.repairdesk.co/api/web/v1/ticket/addnote endpoint.
        
        Args:
            ticket_id: The ticket ID (can be numeric ID or T-prefixed format like T-12345)
            note: The diagnostic note text
            is_flag: Whether the note is flagged (0 or 1)
            
        Returns:
            Response data with success status and message
        """
        # Convert ticket ID from T-prefixed format if needed
        numeric_id = None
        
        if isinstance(ticket_id, str):
            if ticket_id.startswith('T-'):
                # Try to look up the internal ID
                numeric_id = self.get_numeric_ticket_id(ticket_id)
                if not numeric_id:
                    raise ValueError(f"Could not find internal ID for ticket {ticket_id}")
            elif ticket_id.isdigit():
                numeric_id = int(ticket_id)
            else:
                # Try to look up the ticket by number to get its ID
                ticket_data = self.get_ticket_by_number(ticket_id)
                if ticket_data and 'data' in ticket_data:
                    numeric_id = ticket_data['data'].get('id')
                if not numeric_id:
                    raise ValueError(f"Could not find ticket with number: {ticket_id}")
        else:
            # Assume numeric ID was provided directly
            numeric_id = int(ticket_id)
            
        # Prepare the data according to API documentation
        data = {
            "id": numeric_id,
            "note": note,
            "type": 1,  # 1 = diagnostic note, 0 = internal note
            "is_flag": is_flag
        }
        
        self.logger.info(f"Adding diagnostic note to RepairDesk ticket ID: {numeric_id}")
        return self.request("ticket/addnote", method="POST", data=data)
    
    def add_attachment(self, ticket_id: Union[str, int], 
                     file_path: str = None, 
                     file_content: BinaryIO = None,
                     file_name: str = None,
                     file_type: str = None) -> Dict:
        """Add an attachment to a ticket.
        
        Args:
            ticket_id: The ticket ID
            file_path: Path to the file to attach (optional)
            file_content: File content as bytes or file-like object (optional)
            file_name: Name of the file (required if file_content is provided)
            file_type: MIME type of the file (optional)
            
        Returns:
            Response data
        """
        # If ticket_id is a T-number, convert to internal ID
        if isinstance(ticket_id, str) and ticket_id.startswith('T-'):
            internal_id = self.get_numeric_ticket_id(ticket_id)
            if not internal_id:
                raise ValueError(f"Could not find internal ID for ticket {ticket_id}")
            ticket_id = internal_id
            
        files = {}
        
        if file_path:
            # Use file path to open and read file
            with open(file_path, 'rb') as f:
                file_data = f.read()
                file_name = os.path.basename(file_path)
                files = {'file': (file_name, file_data)}
        elif file_content:
            # Use provided file content
            if not file_name:
                raise ValueError("file_name is required when providing file_content")
                
            files = {'file': (file_name, file_content, file_type)}
        else:
            raise ValueError("Either file_path or file_content must be provided")
            
        return self.request(f"tickets/{ticket_id}/attachments", method="POST", files=files)
    
    def get_ticket_attachments(self, ticket_id: Union[str, int]) -> List[Dict]:
        """Get all attachments for a ticket.
        
        Args:
            ticket_id: The ticket ID
            
        Returns:
            List of attachment dictionaries
        """
        # If ticket_id is a T-number, convert to internal ID
        if isinstance(ticket_id, str) and ticket_id.startswith('T-'):
            internal_id = self.get_numeric_ticket_id(ticket_id)
            if not internal_id:
                raise ValueError(f"Could not find internal ID for ticket {ticket_id}")
            ticket_id = internal_id
            
        response = self.request(f"tickets/{ticket_id}/attachments")
        return response if isinstance(response, list) else []
    
    def get_ticket_notes(self, ticket_id: Union[str, int]) -> List[Dict]:
        """Get all notes for a ticket.
        
        Args:
            ticket_id: The ticket ID
            
        Returns:
            List of note dictionaries
        """
        # If ticket_id is a T-number, convert to internal ID
        if isinstance(ticket_id, str) and ticket_id.startswith('T-'):
            internal_id = self.get_numeric_ticket_id(ticket_id)
            if not internal_id:
                raise ValueError(f"Could not find internal ID for ticket {ticket_id}")
            ticket_id = internal_id
            
        response = self.request(f"tickets/{ticket_id}/notes")
        return response if isinstance(response, list) else []
    
    def get_repair_statuses(self) -> List[Dict]:
        """Get all available repair status options.
        
        Returns:
            List of status dictionaries
        """
        response = self.request("repair/statuses", use_cache=True)
        return response if isinstance(response, list) else []
    
    def get_repair_types(self) -> List[Dict]:
        """Get all available repair types.
        
        Returns:
            List of repair type dictionaries
        """
        response = self.request("repair/types", use_cache=True)
        return response if isinstance(response, list) else []
    
    def get_device_types(self) -> List[Dict]:
        """Get all available device types.
        
        Returns:
            List of device type dictionaries
        """
        response = self.request("devices", use_cache=True)
        return response if isinstance(response, list) else []
    
    # =====================
    # Inventory Methods
    # =====================
    
    def get_inventory(self, page: int = 1, limit: int = 1000, search: str = None,
                 type_id: Union[str, int] = None, category_id: Union[str, int] = None) -> Dict:
        """Fetch inventory items with optional filtering and pagination.
        
        Args:
            page: Page number for pagination
            limit: Number of items per page
            search: Optional search term
            type_id: Optional inventory type ID filter
            category_id: Optional category ID filter
            
        Returns:
            Dictionary with inventory data and pagination info
        """
        params = {
            "page": page,
            "limit": limit
        }
        
        if search:
            params["search"] = search
            
        if type_id:
            params["type_id"] = type_id
            
        if category_id:
            params["category_id"] = category_id
        
        response = self.request("inventory", params=params)
        # Log the structure of the response to help debug
        if isinstance(response, dict):
            self.logger.debug(f"Inventory API response keys: {list(response.keys())}")
            if "data" in response:
                self.logger.debug(f"Data field keys: {list(response['data'].keys())}")
            if "inventoryData" in response:
                self.logger.debug(f"InventoryData length: {len(response['inventoryData'])}")
        return response
    
    def get_cache_directory(self) -> str:
        """Get the directory path for cache files.
        Creates the directory if it doesn't exist.
        
        Returns:
            str: Path to cache directory
        """
        # Use platform-appropriate cache directory
        from .platform_paths import PlatformPaths
        platform_paths = PlatformPaths()
        cache_dir = str(platform_paths.ensure_dir_exists(platform_paths.get_cache_dir()))
        
        # Create cache directory if it doesn't exist
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
            self.logger.info(f"Created cache directory at {cache_dir}")
        
        return cache_dir
        
    def get_inventory_cache_file(self) -> str:
        """Get the full path to the inventory cache file.
        
        Returns:
            str: Path to inventory cache file
        """
        return os.path.join(self.get_cache_directory(), 'inventory_cache.json')
        
    def get_customer_cache_file(self) -> str:
        """Get the full path to the customer cache file.
        NOTE: This method is NOT used for actual customer data caching!
        Customer data caching is handled in the customers module.
        
        Returns:
            str: Path to customer cache file for NON-SENSITIVE data only
        """
        return os.path.join(self.get_cache_directory(), 'customer_cache.json')
        
    def get_ticket_cache_file(self) -> str:
        """Get the full path to the ticket cache file.
        
        Returns:
            str: Path to ticket cache file
        """
        return os.path.join(self.get_cache_directory(), 'ticket_cache.json')
    
    def save_inventory_cache(self, items: List[Dict]) -> None:
        """Save inventory items to cache file.
        
        Args:
            items: List of inventory items to cache
        """
        cache_file = self.get_inventory_cache_file()
        
        # Prepare cache data with metadata
        cache_data = {
            'timestamp': datetime.now().isoformat(),
            'items': items,
            'count': len(items)
        }
        
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2)
            
            self.logger.info(f"Saved {len(items)} inventory items to cache file: {cache_file}")
        except Exception as e:
            self.logger.error(f"Failed to save inventory cache: {e}")
            
    def save_customer_cache(self, items: List[Dict]) -> None:
        """IMPORTANT: This method should NOT be used for actual customer data!
        Customer data caching is handled in the customers module.
        
        This is a placeholder that avoids writing sensitive customer data to disk.
        
        Args:
            items: List of customer items to cache
        """
        # We don't save actual customer data without encryption
        self.logger.warning(
            "Customer data caching is handled in the customers module! " + 
            "Not saving to regular cache file. " +
            "Use the customers module for customer data caching."
        )
        
        # Only save non-sensitive fields as a fallback
        try:
            # Create a sanitized version with only non-sensitive fields
            sanitized_items = []
            for item in items:
                sanitized = {
                    'id': item.get('id', ''),
                    'count': len(items),
                    'timestamp': datetime.now().isoformat(),
                    'note': 'Only ID is stored - sensitive data handled by customers module'
                }
                sanitized_items.append(sanitized)
                
            cache_file = self.get_customer_cache_file()
            cache_data = {
                'timestamp': datetime.now().isoformat(),
                'note': 'CONTAINS ONLY NON-SENSITIVE FIELDS - See note in items',
                'items': sanitized_items,
                'count': len(items)
            }
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2)
                
            self.logger.info(f"Saved {len(items)} customer IDs (sanitized) to cache file")
        except Exception as e:
            self.logger.error(f"Failed to save sanitized customer cache: {e}")
            
    def save_ticket_cache(self, items: List[Dict]) -> None:
        """Save ticket data to cache file.
        
        Args:
            items: List of ticket items to cache
        """
        cache_file = self.get_ticket_cache_file()
        
        # Prepare cache data with metadata
        cache_data = {
            'timestamp': datetime.now().isoformat(),
            'items': items,
            'count': len(items)
        }
        
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2)
            
            self.logger.info(f"Saved {len(items)} tickets to cache file: {cache_file}")
            
            # After successfully saving the cache, create individual ticket detail files
            self._create_ticket_detail_files(items)
        except Exception as e:
            self.logger.error(f"Failed to save ticket cache: {e}")
            
    def _create_ticket_detail_files(self, tickets: List[Dict]) -> None:
        """Create individual ticket detail JSON files for each ticket.
        
        This function fetches detailed ticket information from the API for each ticket
        and saves it to individual files named ticket_detail_T-XXXXX.json in the cache directory.
        It uses the ticket ID instead of order_id for the API call.
        
        Args:
            tickets: List of tickets to create detail files for
        """
        if not tickets:
            self.logger.warning("No tickets provided to create detail files")
            return
            
        if not self.api_key:
            self.logger.error("API key is missing, cannot create ticket detail files")
            return
        
        # Create ticket data directory if it doesn't exist
        from nest.utils.cache_utils import get_ticket_detail_directory
        cache_dir = get_ticket_detail_directory()
        
        # Sort tickets by created_date (newest first) and limit to 50 most recent
        try:
            sorted_tickets = sorted(tickets, key=lambda x: int(x.get('summary', {}).get('created_date', 0) or 0), reverse=True)[:50]
            self.logger.info(f"Creating ticket detail files for {len(sorted_tickets)} recent tickets")
        except Exception as e:
            self.logger.error(f"Error sorting tickets: {e}")
            sorted_tickets = tickets[:50]  # Fallback to first 50 tickets without sorting
        
        success_count = 0
        error_count = 0
        
        # Process each ticket and create its detail file
        for ticket in sorted_tickets:
            try:
                # Extract the ticket ID and order ID
                ticket_summary = ticket.get('summary', {})
                ticket_id = ticket_summary.get('id')
                order_id = ticket_summary.get('order_id')
                
                if not ticket_id or not order_id:
                    self.logger.warning(f"Skipping ticket with missing ID or order_id: ID={ticket_id}, order_id={order_id}")
                    error_count += 1
                    continue
                    
                # Check if the detail file was updated in the last 24 hours
                file_path = os.path.join(cache_dir, f"ticket_detail_{order_id}.json")
                if os.path.exists(file_path):
                    file_stat = os.stat(file_path)
                    file_age_hours = (time.time() - file_stat.st_mtime) / 3600
                    
                    if file_age_hours < 24:
                        self.logger.debug(f"Skipping recent ticket detail file: {order_id} (age: {file_age_hours:.1f} hours)")
                        continue
                
                # Directly construct URL and make request rather than using self.request
                # to ensure we have visibility into any errors
                url = f"{self.base_url}/tickets/{ticket_id}?api_key={self.api_key}"
                self.logger.debug(f"Fetching ticket details from URL: {url}")
                
                response = requests.get(url)
                response.raise_for_status()  # Raise exception for non-200 responses
                data = response.json()
                
                # Verify we got a valid response
                if not data or not isinstance(data, dict) or data.get('success') is False:
                    error_msg = data.get('message', 'Unknown error') if isinstance(data, dict) else 'Invalid response format'
                    self.logger.warning(f"Failed to get details for ticket {order_id}: {error_msg}")
                    error_count += 1
                    continue
                
                # ENHANCEMENT: Also fetch ticket notes/comments for richer AI analysis
                try:
                    notes_data = self.get_ticket_notes(ticket_id)
                    if notes_data:
                        # Add the notes/comments to the ticket data
                        data['notes'] = notes_data
                        self.logger.debug(f"Added {len(notes_data)} notes/comments to ticket {order_id}")
                    else:
                        data['notes'] = []
                except Exception as e:
                    self.logger.warning(f"Could not fetch notes for ticket {order_id}: {e}")
                    data['notes'] = []
                
                # Save the detailed information with notes to a file
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2)
                
                success_count += 1
                self.logger.debug(f"Successfully saved ticket detail file: {file_path}")
                
            except requests.exceptions.RequestException as e:
                self.logger.error(f"API request error for ticket ID {ticket_id}: {e}")
                error_count += 1
            except Exception as e:
                self.logger.error(f"Unexpected error creating ticket detail file for {ticket_id}: {e}")
                error_count += 1
        
        self.logger.info(f"Finished creating ticket detail files: {success_count} successes, {error_count} failures")

    
    def load_inventory_cache(self, max_cache_age_minutes: int = 15) -> Optional[List[Dict]]:
        """Load inventory items from cache file if available and not expired.
        
        Args:
            max_cache_age_minutes: Maximum age of cache in minutes before considered expired
            
        Returns:
            List of inventory items if valid cache exists, None otherwise
        """
        cache_file = self.get_inventory_cache_file()
        
        if not os.path.exists(cache_file):
            self.logger.info(f"No inventory cache file found at {cache_file}")
            return None
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            # Parse timestamp and check cache age
            timestamp = datetime.fromisoformat(cache_data['timestamp'])
            cache_age = (datetime.now() - timestamp).total_seconds() / 60
            
            if cache_age < max_cache_age_minutes:
                items = cache_data['items']
                self.logger.info(f"Loaded {len(items)} inventory items from cache ({cache_age:.1f} minutes old)")
                return items
            else:
                self.logger.info(f"Cache file expired ({cache_age:.1f} minutes old), will fetch fresh data")
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to load inventory cache: {e}")
            return None
            
    def load_customer_cache(self, max_cache_age_minutes: int = 15) -> Optional[List[Dict]]:
        """IMPORTANT: This method does NOT load actual customer data!
        The application uses PinSecureCache for customer data with encryption.
        
        This method will always return None to ensure the application fetches
        actual customer data properly with encryption.
        
        Args:
            max_cache_age_minutes: Maximum age of cache in minutes before considered expired
            
        Returns:
            None - Always forces a fresh API fetch for customer data
        """
        self.logger.warning(
            "Customer data requires PIN-based encryption! " + 
            "Cannot load from regular cache file. " +
            "Use PinSecureCache for customer data instead."
        )
        
        # Check if our sanitized cache file exists (just for logging)
        cache_file = self.get_customer_cache_file()
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                self.logger.info(f"Found sanitized customer cache with {cache_data.get('count', 0)} IDs")
            except Exception as e:
                self.logger.error(f"Error checking sanitized customer cache: {e}")
                
        # Always return None to force API fetch for actual customer data
        return None
            
    def load_ticket_cache(self, max_cache_age_minutes: int = 15) -> Optional[List[Dict]]:
        """Load ticket data from cache file if available and not expired.
        
        Args:
            max_cache_age_minutes: Maximum age of cache in minutes before considered expired
            
        Returns:
            List of tickets if valid cache exists, None otherwise
        """
        cache_file = self.get_ticket_cache_file()
        
        if not os.path.exists(cache_file):
            self.logger.info(f"No ticket cache file found at {cache_file}")
            return None
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            # Parse timestamp and check cache age
            timestamp = datetime.fromisoformat(cache_data['timestamp'])
            cache_age = (datetime.now() - timestamp).total_seconds() / 60
            
            if cache_age < max_cache_age_minutes:
                items = cache_data['items']
                self.logger.info(f"Loaded {len(items)} tickets from cache ({cache_age:.1f} minutes old)")
                return items
            else:
                self.logger.info(f"Ticket cache file expired ({cache_age:.1f} minutes old), will fetch fresh data")
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to load ticket cache: {e}")
            return None
    
    def get_all_inventory(self, use_cache=True, max_cache_age_minutes=15, page_callback=None) -> List[Dict]:
        """Fetch all inventory items using pagination.
        
        Args:
            use_cache (bool): Whether to use cached inventory data if available
            max_cache_age_minutes (int): Maximum age of cache in minutes before refreshing
            page_callback (callable): Optional callback function that will be called with each page of data as it's loaded
                The callback receives (current_page_items, is_complete, total_items_so_far, pagination_info)
        
        Returns:
            List of inventory item dictionaries
        """
        # Try to load from cache file if we should use cache
        if use_cache:
            cached_items = self.load_inventory_cache(max_cache_age_minutes)
            if cached_items is not None:
                # If using cache and there's a callback, call it with all items at once
                if page_callback:
                    page_callback(cached_items, True, len(cached_items), {"current_page": 1, "total_pages": 1})
                return cached_items
        else:
            self.logger.info("Cache usage disabled, fetching fresh data from API")
        
        # If no valid cache or cache disabled, fetch from API
        self.logger.info("Fetching all inventory items from RepairDesk (this may take some time)")
        page = 1
        items = []
        
        while True:
            response = self.get_inventory(page)
            
            if not response or not isinstance(response, dict):
                break
            
            # The API response key is 'inventoryListData' not 'inventoryData'    
            current_page = response.get("inventoryListData", [])
            if not current_page:
                break
                
            items.extend(current_page)
            
            # Get pagination info
            pagination = response.get("pagination", {})
            is_complete = not pagination.get("next_page_exist", False)
            
            # Call the callback with the current page data if provided
            if page_callback:
                pagination_info = {
                    "current_page": page,
                    "total_pages": pagination.get("total_pages", 1) if pagination else 1
                }
                page_callback(current_page, is_complete, len(items), pagination_info)
            
            # Check if there are more pages
            if is_complete:
                break
            else:
                page = pagination.get("next_page")
                self.logger.debug(f"Fetching inventory page {page}")
        
        # Save results to cache file
        if items:
            self.save_inventory_cache(items)
        
        self.logger.info(f"Fetched {len(items)} inventory items from RepairDesk")
        return items
    
    def get_inventory_item(self, item_id: Union[str, int]) -> Dict:
        """Fetch a specific inventory item by ID.
        
        Args:
            item_id: The inventory item ID
            
        Returns:
            Inventory item data dictionary
        """
        return self.request(f"inventory/{item_id}")
    
    def create_inventory_item(self, item_data: Dict) -> Dict:
        """Create a new inventory item.
        
        Args:
            item_data: Dictionary with item details including:
                - name: Item name
                - sku: SKU code
                - price: Selling price
                - cost: Cost price
                - quantity: Stock quantity
                - category_id: Category ID
                - type_id: Type ID (1 for product, 2 for service)
                
        Returns:
            Created inventory item data
        """
        response = self.request("inventory", method="POST", data=item_data)
        self._clear_cache("GET:inventory")
        return response
    
    def update_inventory_item(self, item_id: Union[str, int], item_data: Dict) -> Dict:
        """Update an inventory item.
        
        Args:
            item_id: The inventory item ID
            item_data: Dictionary with updated item details
            
        Returns:
            Updated inventory item data
        """
        response = self.request(f"inventory/{item_id}", method="PUT", data=item_data)
        self._clear_cache("GET:inventory")
        return response
    
    def adjust_inventory(self, item_id: Union[str, int], quantity: int, reason: str = None) -> Dict:
        """Adjust inventory quantity for an item.
        
        Args:
            item_id: The inventory item ID
            quantity: Quantity to add (positive) or subtract (negative)
            reason: Optional reason for adjustment
            
        Returns:
            Response data
        """
        data = {
            "quantity": quantity
        }
        
        if reason:
            data["reason"] = reason
            
        return self.request(f"inventory/{item_id}/adjust", method="POST", data=data)
    
    def delete_inventory_item(self, item_id: Union[str, int]) -> Dict:
        """Delete an inventory item.
        
        Args:
            item_id: The inventory item ID to delete
            
        Returns:
            Response dictionary
        """
        response = self.request(f"inventory/{item_id}", method="DELETE")
        self._clear_cache("GET:inventory")
        return response
    
    def get_inventory_categories(self) -> List[Dict]:
        """Get all inventory categories.
        
        Returns:
            List of category dictionaries
        """
        response = self.request("inventory/categories", use_cache=True)
        return response if isinstance(response, list) else []
    
    def create_inventory_category(self, name: str, description: str = None) -> Dict:
        """Create a new inventory category.
        
        Args:
            name: Category name
            description: Optional category description
            
        Returns:
            Created category data
        """
        data = {"name": name}
        if description:
            data["description"] = description
            
        response = self.request("inventory/categories", method="POST", data=data)
        self._clear_cache("GET:inventory/categories")
        return response
    
    def get_inventory_types(self) -> List[Dict]:
        """Get all inventory types (product, service, etc.).
        
        Returns:
            List of inventory type dictionaries
        """
        response = self.request("inventory/types", use_cache=True)
        return response if isinstance(response, list) else []
    
    # =====================
    # Supplier Methods
    # =====================
    
    def get_suppliers(self, page: int = 1, limit: int = 50, search: str = None) -> Dict:
        """Fetch suppliers with optional search and pagination.
        
        Args:
            page: Page number for pagination
            limit: Number of suppliers per page
            search: Optional search term
            
        Returns:
            Dictionary with supplier data and pagination info
        """
        params = {
            "page": page,
            "limit": limit
        }
        
        if search:
            params["search"] = search
            
        return self.request("suppliers", params=params)
    
    def get_all_suppliers(self) -> List[Dict]:
        """Fetch all suppliers using pagination.
        
        Returns:
            List of supplier dictionaries
        """
        self.logger.info("Fetching all suppliers from RepairDesk")
        page = 1
        suppliers = []
        
        while True:
            response = self.get_suppliers(page)
            
            if not response or not isinstance(response, dict):
                break
                
            current_page = response.get("supplierData", [])
            if not current_page:
                break
                
            suppliers.extend(current_page)
            
            # Check pagination
            pagination = response.get("pagination", {})
            if pagination.get("next_page_exist"):
                page = pagination.get("next_page")
                self.logger.debug(f"Fetching supplier page {page}")
            else:
                break
                
        self.logger.info(f"Fetched {len(suppliers)} suppliers from RepairDesk")
        return suppliers
    
    def get_supplier(self, supplier_id: Union[str, int]) -> Dict:
        """Fetch a specific supplier by ID.
        
        Args:
            supplier_id: The supplier ID
            
        Returns:
            Supplier data dictionary
        """
        return self.request(f"suppliers/{supplier_id}")
    
    def create_supplier(self, supplier_data: Dict) -> Dict:
        """Create a new supplier.
        
        Args:
            supplier_data: Dictionary with supplier details including:
                - name: Supplier name
                - contact_name: Contact person name
                - email: Supplier email
                - phone: Supplier phone
                - address: Optional supplier address
                
        Returns:
            Created supplier data
        """
        response = self.request("suppliers", method="POST", data=supplier_data)
        self._clear_cache("GET:suppliers")
        return response
    
    def update_supplier(self, supplier_id: Union[str, int], supplier_data: Dict) -> Dict:
        """Update an existing supplier.
        
        Args:
            supplier_id: The supplier ID to update
            supplier_data: Dictionary with updated supplier details
            
        Returns:
            Updated supplier data
        """
        response = self.request(f"suppliers/{supplier_id}", method="PUT", data=supplier_data)
        self._clear_cache("GET:suppliers")
        return response
    
    def delete_supplier(self, supplier_id: Union[str, int]) -> Dict:
        """Delete a supplier.
        
        Args:
            supplier_id: The supplier ID to delete
            
        Returns:
            Response dictionary
        """
        response = self.request(f"suppliers/{supplier_id}", method="DELETE")
        self._clear_cache("GET:suppliers")
        return response
    
    # =====================
    # Purchase Order Methods
    # =====================
    
    def get_purchase_orders(self, page: int = 1, limit: int = 50, 
                          status: str = None, supplier_id: Union[str, int] = None) -> Dict:
        """Fetch purchase orders with optional filtering and pagination.
        
        Args:
            page: Page number for pagination
            limit: Number of purchase orders per page
            status: Optional status filter (e.g., 'open', 'received')
            supplier_id: Optional supplier ID filter
            
        Returns:
            Dictionary with purchase order data and pagination info
        """
        params = {
            "page": page,
            "limit": limit
        }
        
        if status:
            params["status"] = status
            
        if supplier_id:
            params["supplier_id"] = supplier_id
            
        return self.request("purchase-orders", params=params)
    
    def get_purchase_order(self, po_id: Union[str, int]) -> Dict:
        """Fetch a specific purchase order by ID.
        
        Args:
            po_id: The purchase order ID
            
        Returns:
            Purchase order data dictionary
        """
        return self.request(f"purchase-orders/{po_id}")
    
    def create_purchase_order(self, po_data: Dict) -> Dict:
        """Create a new purchase order.
        
        Args:
            po_data: Dictionary with purchase order details including:
                - supplier_id: Supplier ID
                - items: List of items with item_id and quantity
                - expected_on: Expected delivery date
                
        Returns:
            Created purchase order data
        """
        response = self.request("purchase-orders", method="POST", data=po_data)
        self._clear_cache("GET:purchase-orders")
        return response
    
    def update_purchase_order(self, po_id: Union[str, int], po_data: Dict) -> Dict:
        """Update an existing purchase order.
        
        Args:
            po_id: The purchase order ID to update
            po_data: Dictionary with updated purchase order details
            
        Returns:
            Updated purchase order data
        """
        response = self.request(f"purchase-orders/{po_id}", method="PUT", data=po_data)
        self._clear_cache("GET:purchase-orders")
        return response
    
    def receive_purchase_order(self, po_id: Union[str, int], 
                             items: List[Dict] = None, 
                             receive_all: bool = False) -> Dict:
        """Mark a purchase order as received (partially or fully).
        
        Args:
            po_id: The purchase order ID
            items: List of received items with item_id and quantity
            receive_all: Whether to receive all items on the PO
            
        Returns:
            Updated purchase order data
        """
        data = {}
        
        if receive_all:
            data["receive_all"] = True
        elif items:
            data["items"] = items
        else:
            raise ValueError("Either items or receive_all must be provided")
            
        return self.request(f"purchase-orders/{po_id}/receive", method="POST", data=data)
    
    # =====================
    # Invoice Methods
    # =====================
    
    def get_invoices(self, page: int = 1, limit: int = 50, 
                   status: str = None, customer_id: Union[str, int] = None,
                   date_from: Union[str, datetime, date] = None,
                   date_to: Union[str, datetime, date] = None) -> Dict:
        """Fetch invoices with optional filtering and pagination.
        
        Args:
            page: Page number for pagination
            limit: Number of invoices per page
            status: Optional status filter (e.g., 'paid', 'unpaid')
            customer_id: Optional customer ID filter
            date_from: Optional start date (format: YYYY-MM-DD)
            date_to: Optional end date (format: YYYY-MM-DD)
            
        Returns:
            Dictionary with invoice data and pagination info
        """
        params = {
            "page": page,
            "limit": limit
        }
        
        if status:
            params["status"] = status
            
        if customer_id:
            params["customer_id"] = customer_id
            
        if date_from:
            if isinstance(date_from, (datetime, date)):
                params["date_from"] = date_from.strftime("%Y-%m-%d")
            else:
                params["date_from"] = date_from
                
        if date_to:
            if isinstance(date_to, (datetime, date)):
                params["date_to"] = date_to.strftime("%Y-%m-%d")
            else:
                params["date_to"] = date_to
            
        return self.request("invoices", params=params)
    
    def get_invoice(self, invoice_id: Union[str, int]) -> Dict:
        """Fetch a specific invoice by ID.
        
        Args:
            invoice_id: The invoice ID
            
        Returns:
            Invoice data dictionary
        """
        return self.request(f"invoices/{invoice_id}")
    
    def create_invoice(self, invoice_data: Dict) -> Dict:
        """Create a new invoice.
        
        Args:
            invoice_data: Dictionary with invoice details including:
                - customer_id: Customer ID
                - items: List of items with item_id, quantity, and price
                - payment_method: Payment method (optional)
                - paid_amount: Amount paid (optional)
                - note: Optional invoice note
                
        Returns:
            Created invoice data
        """
        response = self.request("invoices", method="POST", data=invoice_data)
        self._clear_cache("GET:invoices")
        return response
    
    def add_payment(self, invoice_id: Union[str, int], payment_data: Dict) -> Dict:
        """Add a payment to an invoice.
        
        Args:
            invoice_id: The invoice ID
            payment_data: Dictionary with payment details including:
                - amount: Payment amount
                - method: Payment method
                - reference: Payment reference (optional)
                
        Returns:
            Updated invoice data
        """
        return self.request(f"invoices/{invoice_id}/payments", method="POST", data=payment_data)
    
    def void_invoice(self, invoice_id: Union[str, int], reason: str = None) -> Dict:
        """Void an invoice.
        
        Args:
            invoice_id: The invoice ID to void
            reason: Optional reason for voiding
            
        Returns:
            Response data
        """
        data = {}
        if reason:
            data["reason"] = reason
            
        return self.request(f"invoices/{invoice_id}/void", method="POST", data=data)
    
    def get_payment_methods(self) -> List[Dict]:
        """Get all available payment methods.
        
        Returns:
            List of payment method dictionaries
        """
        response = self.request("payment-methods", use_cache=True)
        return response if isinstance(response, list) else []
    
    # =====================
    # Reporting Methods
    # =====================
    
    def get_sales_report(self, date_from: Union[str, datetime, date],
                       date_to: Union[str, datetime, date] = None,
                       group_by: str = "daily") -> Dict:
        """Get sales report for a date range.
        
        Args:
            date_from: Start date (format: YYYY-MM-DD)
            date_to: End date (format: YYYY-MM-DD), defaults to today
            group_by: Grouping option - daily, weekly, monthly, yearly
            
        Returns:
            Sales report data
        """
        # Convert dates to string format
        if isinstance(date_from, (datetime, date)):
            date_from = date_from.strftime("%Y-%m-%d")
            
        if date_to:
            if isinstance(date_to, (datetime, date)):
                date_to = date_to.strftime("%Y-%m-%d")
        else:
            date_to = datetime.now().strftime("%Y-%m-%d")
            
        params = {
            "date_from": date_from,
            "date_to": date_to,
            "group_by": group_by
        }
        
        return self.request("reports/sales", params=params)
    
    def get_technician_report(self, date_from: Union[str, datetime, date],
                            date_to: Union[str, datetime, date] = None,
                            technician_id: Union[str, int] = None) -> Dict:
        """Get technician performance report.
        
        Args:
            date_from: Start date (format: YYYY-MM-DD)
            date_to: End date (format: YYYY-MM-DD), defaults to today
            technician_id: Optional technician ID to filter by
            
        Returns:
            Technician report data
        """
        # Convert dates to string format
        if isinstance(date_from, (datetime, date)):
            date_from = date_from.strftime("%Y-%m-%d")
            
        if date_to:
            if isinstance(date_to, (datetime, date)):
                date_to = date_to.strftime("%Y-%m-%d")
        else:
            date_to = datetime.now().strftime("%Y-%m-%d")
            
        params = {
            "date_from": date_from,
            "date_to": date_to
        }
        
        if technician_id:
            params["technician_id"] = technician_id
            
        return self.request("reports/technicians", params=params)
    
    def get_inventory_report(self, low_stock_only: bool = False,
                           category_id: Union[str, int] = None) -> Dict:
        """Get inventory report.
        
        Args:
            low_stock_only: Whether to only include items with low stock
            category_id: Optional category ID to filter by
            
        Returns:
            Inventory report data
        """
        params = {}
        
        if low_stock_only:
            params["low_stock"] = 1
            
        if category_id:
            params["category_id"] = category_id
            
        return self.request("reports/inventory", params=params)
    
    # =====================
    # Webhook Methods
    # =====================
    
    def get_webhooks(self) -> List[Dict]:
        """Get all registered webhooks.
        
        Returns:
            List of webhook dictionaries
        """
        response = self.request("webhooks")
        return response if isinstance(response, list) else []
    
    def create_webhook(self, url: str, events: List[str], secret: str = None) -> Dict:
        """Register a new webhook.
        
        Args:
            url: Webhook endpoint URL
            events: List of events to trigger webhook (e.g., 'ticket.created')
            secret: Optional secret for webhook signature verification
            
        Returns:
            Created webhook data
        """
        data = {
            "url": url,
            "events": events
        }
        
        if secret:
            data["secret"] = secret
            
        return self.request("webhooks", method="POST", data=data)
    
    def delete_webhook(self, webhook_id: Union[str, int]) -> Dict:
        """Delete a webhook.
        
        Args:
            webhook_id: The webhook ID to delete
            
        Returns:
            Response dictionary
        """
        return self.request(f"webhooks/{webhook_id}", method="DELETE")
    
    # =====================
    # Appointment Methods
    # =====================
    
    def get_appointments(self, date_from: Union[str, datetime, date],
                       date_to: Union[str, datetime, date] = None,
                       technician_id: Union[str, int] = None,
                       status: str = None) -> List[Dict]:
        """Get appointments within a date range.
        
        Args:
            date_from: Start date (format: YYYY-MM-DD)
            date_to: End date (format: YYYY-MM-DD), defaults to same as date_from
            technician_id: Optional technician ID to filter by
            status: Optional status filter (confirmed, cancelled, completed)
            
        Returns:
            List of appointment dictionaries
        """
        # Convert dates to string format
        if isinstance(date_from, (datetime, date)):
            date_from = date_from.strftime("%Y-%m-%d")
            
        if date_to:
            if isinstance(date_to, (datetime, date)):
                date_to = date_to.strftime("%Y-%m-%d")
        else:
            date_to = date_from
            
        params = {
            "date_from": date_from,
            "date_to": date_to
        }
        
        if technician_id:
            params["technician_id"] = technician_id
            
        if status:
            params["status"] = status
            
        response = self.request("appointments", params=params)
        return response if isinstance(response, list) else []
    
    def get_appointment(self, appointment_id: Union[str, int]) -> Dict:
        """Get details for a specific appointment.
        
        Args:
            appointment_id: The appointment ID
            
        Returns:
            Appointment data dictionary
        """
        return self.request(f"appointments/{appointment_id}")
    
    def create_appointment(self, appointment_data: Dict) -> Dict:
        """Create a new appointment.
        
        Args:
            appointment_data: Dictionary with appointment details including:
                - customer_id: Customer ID
                - title: Appointment title
                - start_time: Start time (format: YYYY-MM-DD HH:MM:SS)
                - end_time: End time (format: YYYY-MM-DD HH:MM:SS)
                - technician_id: Assigned technician ID
                - notes: Optional appointment notes
                
        Returns:
            Created appointment data
        """
        return self.request("appointments", method="POST", data=appointment_data)
    
    def update_appointment(self, appointment_id: Union[str, int], 
                         appointment_data: Dict) -> Dict:
        """Update an existing appointment.
        
        Args:
            appointment_id: The appointment ID to update
            appointment_data: Dictionary with updated appointment details
            
        Returns:
            Updated appointment data
        """
        return self.request(f"appointments/{appointment_id}", method="PUT", data=appointment_data)
    
    def cancel_appointment(self, appointment_id: Union[str, int], 
                         reason: str = None) -> Dict:
        """Cancel an appointment.
        
        Args:
            appointment_id: The appointment ID to cancel
            reason: Optional cancellation reason
            
        Returns:
            Response dictionary
        """
        data = {}
        if reason:
            data["reason"] = reason
            
        return self.request(f"appointments/{appointment_id}/cancel", method="POST", data=data)
