import os
import json
import pickle
import datetime
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

class GoogleCalendarClient:
    """
    Client for interacting with Google Calendar API.
    Handles authentication, event fetching, creation, updating, and deletion.
    """
    
    # Define OAuth2 scopes needed
    SCOPES = ['https://www.googleapis.com/auth/calendar']
    
    def __init__(self):
        self.creds = None
        self.service = None
        self.token_path = None
        self.credentials_path = None
        self._setup_paths()
        self._authenticate()
    
    def _setup_paths(self):
        """Setup paths for token and credentials files"""
        from nest.utils.platform_paths import PlatformPaths
        platform_paths = PlatformPaths()
        
        # Create data/google directory if it doesn't exist
        google_dir = platform_paths.get_user_data_dir() / 'data' / 'google'
        platform_paths.ensure_dir_exists(google_dir)
        
        self.token_path = google_dir / 'token.pickle'
        self.credentials_path = google_dir / 'credentials.json'
    
    def _authenticate(self):
        """Authenticate with Google Calendar API"""
        # First check if we have valid saved credentials
        if os.path.exists(self.token_path):
            with open(self.token_path, 'rb') as token:
                try:
                    self.creds = pickle.load(token)
                except Exception as e:
                    logging.error(f"Error loading token file: {e}")
                    self.creds = None
        
        # If credentials don't exist or are invalid, get new ones
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                try:
                    self.creds.refresh(Request())
                except Exception as e:
                    logging.error(f"Error refreshing credentials: {e}")
                    self.creds = None
            else:
                # If credentials.json doesn't exist, we can't proceed
                if not os.path.exists(self.credentials_path):
                    logging.error("Google API credentials file not found.")
                    logging.info("Please place credentials.json in data/google directory.")
                    return False
                
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_path, self.SCOPES)
                    self.creds = flow.run_local_server(port=0)
                except Exception as e:
                    logging.error(f"Error during authentication flow: {e}")
                    return False
                
                # Save credentials for next run
                with open(self.token_path, 'wb') as token:
                    pickle.dump(self.creds, token)
        
        try:
            # Build the Google Calendar API service
            self.service = build('calendar', 'v3', credentials=self.creds)
            return True
        except Exception as e:
            logging.error(f"Error building Google Calendar service: {e}")
            return False
    
    def is_authenticated(self) -> bool:
        """Check if client is authenticated and service is available"""
        return self.creds is not None and self.service is not None
    
    def get_calendar_list(self) -> List[Dict[str, Any]]:
        """Get list of available calendars"""
        if not self.is_authenticated():
            logging.error("Not authenticated. Cannot get calendars.")
            return []
        
        try:
            calendars = []
            page_token = None
            
            # Handle pagination
            while True:
                calendar_list = self.service.calendarList().list(pageToken=page_token).execute()
                for calendar_entry in calendar_list['items']:
                    calendars.append({
                        'id': calendar_entry['id'],
                        'summary': calendar_entry['summary'],
                        'primary': calendar_entry.get('primary', False),
                        'backgroundColor': calendar_entry.get('backgroundColor', '#4285F4'),
                        'accessRole': calendar_entry.get('accessRole', ''),
                    })
                
                page_token = calendar_list.get('nextPageToken')
                if not page_token:
                    break
            
            return calendars
        except HttpError as e:
            logging.error(f"Error fetching calendar list: {e}")
            return []
    
    def get_primary_calendar(self) -> Optional[Dict[str, Any]]:
        """Get the user's primary calendar"""
        calendars = self.get_calendar_list()
        for calendar in calendars:
            if calendar.get('primary', False):
                return calendar
        
        # If no primary calendar found, return first calendar or None
        return calendars[0] if calendars else None
    
    def get_events(self, 
                  calendar_id: str = 'primary',
                  time_min: Optional[datetime.datetime] = None,
                  time_max: Optional[datetime.datetime] = None,
                  max_results: int = 100) -> List[Dict[str, Any]]:
        """Get events from the specified calendar within the given time range"""
        if not self.is_authenticated():
            logging.error("Not authenticated. Cannot get events.")
            return []
        
        # Default time_min to start of current month if not provided
        if time_min is None:
            now = datetime.datetime.now()
            time_min = datetime.datetime(now.year, now.month, 1)
        
        # Default time_max to end of current month if not provided
        if time_max is None:
            now = datetime.datetime.now()
            if now.month == 12:
                time_max = datetime.datetime(now.year + 1, 1, 1)
            else:
                time_max = datetime.datetime(now.year, now.month + 1, 1)
        
        # Convert datetime objects to RFC3339 format
        time_min_str = time_min.isoformat() + 'Z'  # 'Z' indicates UTC time
        time_max_str = time_max.isoformat() + 'Z'
        
        try:
            events = []
            page_token = None
            
            # Handle pagination
            while True:
                events_result = self.service.events().list(
                    calendarId=calendar_id,
                    timeMin=time_min_str,
                    timeMax=time_max_str,
                    maxResults=max_results,
                    singleEvents=True,
                    orderBy='startTime',
                    pageToken=page_token
                ).execute()
                
                for event in events_result.get('items', []):
                    processed_event = self._process_event(event)
                    if processed_event:
                        events.append(processed_event)
                
                page_token = events_result.get('nextPageToken')
                if not page_token or len(events) >= max_results:
                    break
            
            return events
        except HttpError as e:
            logging.error(f"Error fetching events: {e}")
            return []
    
    def _process_event(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process a Google Calendar event into a standardized format"""
        try:
            # Extract start and end times
            start = event['start'].get('dateTime', event['start'].get('date'))
            end = event['end'].get('dateTime', event['end'].get('date'))
            
            # Some basic event details
            processed = {
                'id': event['id'],
                'summary': event.get('summary', 'No Title'),
                'description': event.get('description', ''),
                'location': event.get('location', ''),
                'start': start,
                'end': end,
                'status': event.get('status', 'confirmed'),
                'creator': event.get('creator', {}),
                'organizer': event.get('organizer', {}),
                'attendees': event.get('attendees', []),
                'color': self._get_event_color(event),
                'all_day': 'date' in event['start'] and 'dateTime' not in event['start'],
                'raw': event  # Include the raw event for access to all fields
            }
            
            return processed
        except KeyError as e:
            logging.warning(f"Error processing event: {e}")
            return None
    
    def _get_event_color(self, event: Dict[str, Any]) -> str:
        """Get the color for an event based on its colorId or default"""
        if 'colorId' not in event:
            return '#4285F4'  # Default Google blue
            
        # Google Calendar color IDs map to these colors
        color_map = {
            '1': '#7986CB',  # Lavender
            '2': '#33B679',  # Sage
            '3': '#8E24AA',  # Grape
            '4': '#E67C73',  # Flamingo
            '5': '#F6BF26',  # Banana
            '6': '#F4511E',  # Tangerine
            '7': '#039BE5',  # Peacock
            '8': '#616161',  # Graphite
            '9': '#3F51B5',  # Blueberry
            '10': '#0B8043', # Basil
            '11': '#D50000', # Tomato
        }
        
        return color_map.get(event['colorId'], '#4285F4')
    
    def create_event(self, 
                     summary: str,
                     start_time: datetime.datetime,
                     end_time: datetime.datetime,
                     description: str = '',
                     location: str = '',
                     calendar_id: str = 'primary',
                     attendees: List[Dict[str, str]] = None) -> Optional[Dict[str, Any]]:
        """Create a new event in the specified calendar"""
        if not self.is_authenticated():
            logging.error("Not authenticated. Cannot create event.")
            return None
        
        # Default empty list for attendees
        if attendees is None:
            attendees = []
            
        # Prepare event data
        event = {
            'summary': summary,
            'location': location,
            'description': description,
            'start': {
                'dateTime': start_time.isoformat(),
                'timeZone': 'Australia/Sydney',  # Use system timezone
            },
            'end': {
                'dateTime': end_time.isoformat(),
                'timeZone': 'Australia/Sydney',  # Use system timezone
            },
        }
        
        # Add attendees if provided
        if attendees:
            event['attendees'] = attendees
            
        try:
            created_event = self.service.events().insert(
                calendarId=calendar_id, body=event).execute()
            return self._process_event(created_event)
        except HttpError as e:
            logging.error(f"Error creating event: {e}")
            return None
            
    def update_event(self, 
                     event_id: str,
                     summary: Optional[str] = None,
                     start_time: Optional[datetime.datetime] = None,
                     end_time: Optional[datetime.datetime] = None,
                     description: Optional[str] = None,
                     location: Optional[str] = None,
                     calendar_id: str = 'primary') -> Optional[Dict[str, Any]]:
        """Update an existing event in the specified calendar"""
        if not self.is_authenticated():
            logging.error("Not authenticated. Cannot update event.")
            return None
            
        try:
            # First get the current event
            event = self.service.events().get(calendarId=calendar_id, eventId=event_id).execute()
            
            # Update fields that were provided
            if summary is not None:
                event['summary'] = summary
            if description is not None:
                event['description'] = description
            if location is not None:
                event['location'] = location
            if start_time is not None:
                event['start']['dateTime'] = start_time.isoformat()
            if end_time is not None:
                event['end']['dateTime'] = end_time.isoformat()
            
            # Send update request
            updated_event = self.service.events().update(
                calendarId=calendar_id, eventId=event_id, body=event).execute()
            return self._process_event(updated_event)
        except HttpError as e:
            logging.error(f"Error updating event: {e}")
            return None
    
    def delete_event(self, event_id: str, calendar_id: str = 'primary') -> bool:
        """Delete an event from the specified calendar"""
        if not self.is_authenticated():
            logging.error("Not authenticated. Cannot delete event.")
            return False
            
        try:
            self.service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
            return True
        except HttpError as e:
            logging.error(f"Error deleting event: {e}")
            return False
            
    def get_free_busy(self, 
                     time_min: datetime.datetime,
                     time_max: datetime.datetime,
                     calendar_ids: List[str] = None) -> Dict[str, List[Dict[str, str]]]:
        """Get free/busy information for specified calendars and time range"""
        if not self.is_authenticated():
            logging.error("Not authenticated. Cannot get free/busy info.")
            return {}
            
        # Default to primary calendar if none specified
        if calendar_ids is None:
            calendar_ids = ['primary']
            
        try:
            # Prepare the free/busy request
            body = {
                "timeMin": time_min.isoformat() + 'Z',
                "timeMax": time_max.isoformat() + 'Z',
                "timeZone": 'Australia/Sydney',  # Use system timezone
                "items": [{'id': calendar_id} for calendar_id in calendar_ids]
            }
            
            # Make the request
            free_busy_response = self.service.freebusy().query(body=body).execute()
            
            # Process the response
            result = {}
            for calendar_id, busy in free_busy_response.get('calendars', {}).items():
                result[calendar_id] = busy.get('busy', [])
                
            return result
        except HttpError as e:
            logging.error(f"Error getting free/busy info: {e}")
            return {}
            
    def suggest_meeting_times(self,
                            duration_minutes: int = 60,
                            work_day_start: int = 9,  # 9 AM
                            work_day_end: int = 17,   # 5 PM
                            days_to_check: int = 5) -> List[Dict[str, datetime.datetime]]:
        """Suggest available meeting times based on primary calendar availability"""
        if not self.is_authenticated():
            logging.error("Not authenticated. Cannot suggest meeting times.")
            return []
            
        # Set up time window to check
        now = datetime.datetime.now()
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0) + datetime.timedelta(days=1)
        end_date = start_date + datetime.timedelta(days=days_to_check)
        
        # Get busy times
        free_busy = self.get_free_busy(start_date, end_date)
        busy_times = free_busy.get('primary', [])
        
        # Generate all possible meeting slots
        available_slots = []
        current_date = start_date
        
        while current_date < end_date:
            # Skip weekends (0 = Monday, 6 = Sunday in Python's datetime)
            if current_date.weekday() < 5:  # Weekdays only
                day_start = current_date.replace(hour=work_day_start, minute=0)
                day_end = current_date.replace(hour=work_day_end, minute=0)
                
                # Check each potential slot in 30-min increments
                slot_start = day_start
                while slot_start + datetime.timedelta(minutes=duration_minutes) <= day_end:
                    slot_end = slot_start + datetime.timedelta(minutes=duration_minutes)
                    
                    # Check if slot overlaps with any busy time
                    is_available = True
                    for busy in busy_times:
                        busy_start = datetime.datetime.fromisoformat(busy['start'].replace('Z', '+00:00'))
                        busy_end = datetime.datetime.fromisoformat(busy['end'].replace('Z', '+00:00'))
                        
                        # Convert to local timezone for comparison
                        busy_start = busy_start.astimezone(datetime.timezone.utc).replace(tzinfo=None)
                        busy_end = busy_end.astimezone(datetime.timezone.utc).replace(tzinfo=None)
                        
                        # Check for overlap
                        if (slot_start < busy_end and slot_end > busy_start):
                            is_available = False
                            break
                    
                    if is_available:
                        available_slots.append({
                            'start': slot_start,
                            'end': slot_end
                        })
                    
                    # Move to next potential slot (30-min increments)
                    slot_start += datetime.timedelta(minutes=30)
            
            # Move to next day
            current_date += datetime.timedelta(days=1)
        
        return available_slots
