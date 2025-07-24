#!/usr/bin/env python
"""
AI API client for NestBot

Handles interactions with various AI APIs (Claude, OpenAI/GPT, Gemini)
and formats requests and responses appropriately.
"""

import os
import json
import logging
import requests
from datetime import datetime
from typing import Dict, List, Any, Optional

# Import the ticket utilities
from nest.ai.ticket_utils import load_ticket_data


def get_ai_response(user_message, selected_model=None, ticket_access=False, specific_ticket=None, custom_knowledge_path=None, current_user=None, conversation_context=None):
    """
    Get AI response from the appropriate API (Claude, GPT, etc.)
    
    Args:
        user_message: The user's message to respond to
        selected_model: The selected AI model configuration
        ticket_access: Whether the user has access to ticket data
        specific_ticket: Specific ticket number to include in context
        custom_knowledge_path: Path to custom knowledge base
        current_user: Current user information
        conversation_context: The full conversation context
        
    Returns:
        str: The AI's response or an error message if something went wrong
    """
    
    # Fallback responses for when AI APIs are not available
    def get_fallback_response(message):
        """Generate intelligent fallback responses based on user input"""
        message_lower = message.lower()
        
        if any(word in message_lower for word in ['hi', 'hello', 'hey', 'greetings']):
            return "Hello! I'm NestBot, your AI assistant for the repair shop. While my AI services are currently unavailable, I can still help you navigate the system. What would you like to do?"
        
        elif any(word in message_lower for word in ['ticket', 'repair', 'status']):
            return "I'd love to help you with ticket information! While my AI analysis is temporarily unavailable, you can view detailed ticket information in the main dashboard. Is there a specific ticket number you're looking for?"
        
        elif any(word in message_lower for word in ['help', 'support', 'how']):
            return "I'm here to help! Although my AI capabilities are currently limited, you can:\n\n• View tickets in the Dashboard\n• Check customer information\n• Access PC and Mobile tools\n• Generate reports\n\nWhat specific task would you like assistance with?"
        
        elif any(word in message_lower for word in ['customer', 'client']):
            return "For customer information, please check the Customers section in the main application. I can help guide you there once my AI services are restored."
        
        else:
            return "I apologize, but my AI services are currently unavailable due to missing API configuration. However, I'm still here to help guide you through the Nest application. Please check with your administrator about setting up AI API keys, or let me know what specific task you need help with!"
    
    # Load config first to check API keys
    try:
        from nest.utils.platform_paths import PlatformPaths
        platform_paths = PlatformPaths()
        config_path = str(platform_paths.get_config_dir() / 'config.json')
        with open(config_path, 'r') as file:
            config = json.load(file)
    except Exception as e:
        logging.error(f"Error loading configuration: {str(e)}")
        return get_fallback_response(user_message)
    
    # Check if we have valid API keys (not placeholder values)
    valid_apis = []
    for api_name in ['claude', 'openai', 'gemini']:
        api_config = config.get(api_name, {})
        api_key = api_config.get('api_key', '')
        if api_key and api_key != f'YOUR_{api_name.upper()}_API_KEY_HERE':
            valid_apis.append(api_name)
    
    if not valid_apis:
        logging.warning("No valid AI API keys found in configuration")
        return get_fallback_response(user_message)
    
    try:
        
        # Initialize variables
    ticket_data = None
    oldest_ticket_id = None
    newest_ticket_id = None
    processed_tickets = []
    
    # Process specific ticket if one is provided
    specific_ticket_number = specific_ticket
    if specific_ticket_number:
        logging.info(f"Will include specific ticket {specific_ticket_number} in AI context")
    
        # Get tickets from database if ticket access is enabled or if there's a specific ticket requested
        if ticket_access or specific_ticket_number:
            try:
                # Use the imported load_ticket_data function
                ticket_data = load_ticket_data(include_specific_ticket=True)
                if ticket_data:
                    # Process ticket data into a more digestible format for all API implementations
                    oldest_created_date = float('inf')  # Initialize with infinity
                    newest_created_date = 0
                    
                    # Extract key information and find oldest/newest tickets
                    for ticket in ticket_data:
                        # Get basic ticket info
                        ticket_id = ticket.get('summary', {}).get('order_id', '')
                        created_date = ticket.get('summary', {}).get('created_date', 0)
                        customer_name = ticket.get('summary', {}).get('customer', {}).get('fullName', '')
                        total = ticket.get('summary', {}).get('total', '')
                        
                        # Find oldest and newest
                        if created_date and created_date < oldest_created_date:
                            oldest_created_date = created_date
                            oldest_ticket_id = ticket_id
                        if created_date and created_date > newest_created_date:
                            newest_created_date = created_date
                            newest_ticket_id = ticket_id
                        
                        # Extract device and status info
                        devices = []
                        for device in ticket.get('devices', []):
                            device_info = {
                                'name': device.get('device', {}).get('name', ''),
                                'status': device.get('status', {}).get('name', ''),
                                'assigned_to': device.get('assigned_to', {}).get('fullname', ''),
                                'repair_items': [item.get('name', '') for item in device.get('repairProdItems', [])]
                            }
                            devices.append(device_info)
                        
                        # Add processed ticket info
                        processed_tickets.append({
                            'id': ticket_id,
                            'customer': customer_name,
                            'total': total,
                            'devices': devices
                        })
                    logging.info(f"Processed {len(ticket_data)} tickets for AI context")
                else:
                    logging.warning("Could not load ticket data, continuing without it")
                    
            except Exception as e:
                logging.warning(f"Error loading ticket data: {str(e)}, continuing without it")
        
        # Check if we have a valid model selected
        if not selected_model or not isinstance(selected_model, (dict, str)):
            logging.warning("No valid AI model selected, using first available API")
            # Use the first valid API found
            if valid_apis:
                selected_model = {
                    'name': f'{valid_apis[0].title()} Default',
                    'api': valid_apis[0],
                    'model': config.get(valid_apis[0], {}).get('model', 'default')
                }
            else:
                return get_fallback_response(user_message)
            
        # Call the appropriate API based on the selected model
        if isinstance(selected_model, str):
            # If we just have a string, use it as the model name with first available API
            model_name = selected_model
            api_type = valid_apis[0] if valid_apis else 'claude'
        else:
            model_name = selected_model.get('model', '')
            api_type = selected_model.get('api', valid_apis[0] if valid_apis else 'claude').lower()
        
        # Ensure the selected API is actually available
        if api_type not in valid_apis:
            if valid_apis:
                api_type = valid_apis[0]
                logging.warning(f"Selected API not available, using {api_type} instead")
            else:
                return get_fallback_response(user_message)
        
        # Call the appropriate API
        try:
            if api_type == 'claude':
                return _call_claude_api(
                    user_message, model_name, config, 
                    ticket_data, processed_tickets, specific_ticket, 
                    custom_knowledge_path, current_user
                )
            elif api_type == 'openai':
                return _call_openai_api(
                    user_message, model_name, config, 
                    ticket_data, processed_tickets, specific_ticket, 
                    custom_knowledge_path, current_user
                )
            elif api_type == 'gemini':
                return _call_gemini_api(
                    user_message, model_name, config, 
                    ticket_data, processed_tickets, specific_ticket, 
                    custom_knowledge_path, current_user
                )
            else:
                logging.error(f"Unsupported API type: {api_type}")
                return get_fallback_response(user_message)
                
        except Exception as e:
            error_msg = f"Error calling {api_type} API: {str(e)}"
            logging.exception(error_msg)
            return get_fallback_response(user_message)
    
    except Exception as e:
        error_msg = f"Unexpected error in get_ai_response: {str(e)}"
        logging.exception(error_msg)
        return get_fallback_response(user_message)
            
            # Look for model in config if available
            if 'ai_models' in config:
                for model in config['ai_models']:
                    if model.get('name') == selected_model_name:
                        use_api = model.get('api', 'claude')
                        model_name = model.get('model', model_name)
                        break
            
            # Initialize model_config to None
            model_config = None
            
            # Look for model in ai_models list
            for model in ai_models:
                if model.get('name') == selected_model:
                    model_config = model
                    break
            
            if model_config:
                # Use the exact configuration from config.json
                use_api = model_config.get('api', 'claude')
                model_name = model_config.get('model', '')
                logging.info(f"Using model configuration from config.json: {selected_model_name} (API: {use_api}, ID: {model_name})")
            else:
                # Fallback to default Claude if not found
                use_api = 'claude'
                model_name = config.get('claude', {}).get('model', 'claude-3-opus-20240229')
                logging.warning(f"Model {selected_model} not found in config, defaulting to {model_name}")
        
        # Log which AI model is being used
        logging.info(f"Using AI model: {selected_model_name} (API: {use_api}, Model ID: {model_name})")
        
        response_text = "Sorry, I couldn't process your request."
        
        try:
            if use_api == "claude":
                # Claude API
                api_key = config.get("claude", {}).get("api_key")
                if not api_key:
                    raise ValueError("Claude API key not found in config file")
                
                # Use the selected model or default to the one from config
                model = model_name or config.get("claude", {}).get("model", "claude-3-opus-20240229")
                
                headers = {
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                }
                
                # Prepare the system message and payload based on available knowledge sources
                # Start by getting user's first name for personalization if available
                first_name = ""
                if current_user:
                    full_name = current_user.get("fullname", "")
                    # Extract first name (everything before the first space)
                    first_name = full_name.split()[0] if full_name and " " in full_name else full_name
                    if first_name:
                        system_message = f" You're talking to {first_name}."
                
                # Add company context if available
                company_name = ""
                if current_user and "company" in current_user:
                    company_name = current_user.get("company", "")
                
                # Create the base system message
                if first_name:
                    system_message = f"IMPORTANT INSTRUCTIONS: The user's first name is {first_name}. DO NOT use their last name. DO NOT begin your responses with greetings like 'Hello {first_name}' or 'Hi {first_name}'. Just respond directly to questions and requests without these formalities."
                
                # Determine which knowledge sources to include
                if custom_knowledge_path and os.path.exists(custom_knowledge_path):
                    # Load the custom knowledge
                    with open(custom_knowledge_path, "r") as file:
                        custom_data = json.load(file)
                    knowledge_blob = json.dumps(custom_data, indent=2)
                    
                    # Add the custom knowledge to system message
                    knowledge_prefix = "\n\nUse the following knowledge when responding:"
                    if system_message:
                        system_message += knowledge_prefix
                    else:
                        system_message = "You are NestBot, an AI assistant"
                        if company_name:
                            system_message += f" for {company_name}"
                        system_message += "." + knowledge_prefix
                    
                    system_message += f"\n{knowledge_blob}"
                    logging.info(f"Using custom knowledge from {custom_knowledge_path}")
                    
                # Add ticket data if available
                # This will run if either the checkbox is enabled OR a specific ticket was loaded
                if ticket_data:
                    # First check if there's a specific ticket requested
                    raw_specific_ticket_data = None
                    specific_ticket_id = None
                    
                    if specific_ticket_number:
                        # Format the specific ticket number
                        if specific_ticket_number.startswith('T-'):
                            specific_ticket_id = specific_ticket_number
                        else:
                            specific_ticket_id = f"T-{specific_ticket_number}"
                            
                        # Try to load the raw specific ticket data file directly
                        from nest.utils.cache_utils import get_ticket_detail_directory
                        cache_dir = get_ticket_detail_directory()
                        
                        potential_paths = [
                            os.path.join(cache_dir, f"ticket_detail_{specific_ticket_id}.json"),
                        ]
                        
                        # Try adding T- prefix if missing
                        if not specific_ticket_id.startswith('T-'):
                            potential_paths.append(os.path.join(cache_dir, f"ticket_detail_T-{specific_ticket_id}.json"))
                        
                        # Log all the paths we're checking
                        logging.info(f"Looking for ticket detail file in these locations: {potential_paths}")
                        
                        # Try each path
                        found_path = None
                        for path in potential_paths:
                            if os.path.exists(path):
                                found_path = path
                                logging.info(f"Found ticket detail file at: {path}")
                                break
                            else:
                                logging.debug(f"Ticket detail file not found at: {path}")
                                
                        specific_ticket_cache_path = found_path
                        if specific_ticket_cache_path and os.path.exists(specific_ticket_cache_path):
                            try:
                                with open(specific_ticket_cache_path, 'r') as f:
                                    raw_specific_ticket_data = json.load(f)
                                logging.info(f"Loaded raw specific ticket data for {specific_ticket_id} directly from cache file")
                                
                                # Debug what's in the raw data
                                if 'data' in raw_specific_ticket_data and 'notes' in raw_specific_ticket_data['data']:
                                    notes = raw_specific_ticket_data['data']['notes']
                                    logging.info(f"Found {len(notes)} notes in raw ticket data")
                                    if len(notes) > 0:
                                        sample_note = notes[0]
                                        msg_text = sample_note.get('msg_text', 'No message text')
                                        logging.info(f"Sample note content: {msg_text[:50]}...")
                                else:
                                    logging.warning(f"No notes found in raw ticket data structure")
                                    logging.debug(f"Raw ticket data keys: {list(raw_specific_ticket_data.keys())}")
                                    if 'data' in raw_specific_ticket_data:
                                        logging.debug(f"Raw ticket data['data'] keys: {list(raw_specific_ticket_data['data'].keys())}")
                                    
                            except Exception as e:
                                logging.error(f"Error loading specific ticket data file: {str(e)}")
                    
                    # Also look for any specific ticket data in the processed data as a fallback
                    specific_ticket = None
                    for ticket in ticket_data:
                        if ticket.get('specific_ticket', False):
                            specific_ticket = ticket
                            logging.info(f"Found specific ticket in processed data: {ticket.get('ticket_id')}")
                            break
                    
                    # If we have a specific ticket, extract all its detailed information
                    specific_ticket_data = {}
                    
                    # CRITICAL FIX: Check if we have the raw specific ticket data first as it's more reliable
                    if raw_specific_ticket_data and 'data' in raw_specific_ticket_data:
                        # We have the raw file, use it directly instead of relying on the processed data
                        data = raw_specific_ticket_data.get('data', {})
                        ticket_id = specific_ticket_id  # Use the ID we already determined
                        
                        # Extract all relevant parts from the raw data
                        logging.info(f"Using raw specific ticket data file for {ticket_id}")
                        specific_ticket_data = {
                            'ticket_id': ticket_id,
                            'summary': data.get('summary', {}),
                            'customer': data.get('summary', {}).get('customer', {}),
                            'notes': data.get('notes', []),
                            'activities': data.get('activities', []),
                            'devices': data.get('devices', [])
                        }
                        
                        # Add a special field to highlight note/comment count for the AI
                        note_count = len(data.get('notes', []))
                        activity_count = len(data.get('activities', []))
                        
                        specific_ticket_data['comment_summary'] = {
                            'total_comments': note_count + activity_count,
                            'notes_count': note_count,
                            'activities_count': activity_count,
                            'has_comments': note_count > 0 or activity_count > 0
                        }
                    # Fallback to using the processed specific ticket if the raw file isn't available
                    elif specific_ticket:
                        raw_data = specific_ticket.get('raw_data', {})
                        ticket_id = specific_ticket.get('ticket_id', 'Unknown')
                        
                        # Check raw data structure and extract all relevant parts
                        if 'data' in raw_data:
                            data = raw_data.get('data', {})
                            
                            # Create an enhanced structure that better highlights notes and comments
                            specific_ticket_data = {
                                'ticket_id': ticket_id,
                                'summary': data.get('summary', {}),
                                'customer': data.get('summary', {}).get('customer', {}),
                                'ticket_details': processed_tickets,
                                'notes': data.get('notes', []),
                                'activities': data.get('activities', []),
                                'devices': data.get('devices', [])
                            }
                            
                            # Add a special field to highlight note/comment count for the AI
                            note_count = len(data.get('notes', []))
                            activity_count = len(data.get('activities', []))
                            specific_ticket_data['comment_summary'] = {
                                'total_comments': note_count + activity_count,
                                'notes_count': note_count,
                                'activities_count': activity_count,
                                'has_comments': (note_count + activity_count) > 0
                            }
                            
                            # Initialize raw_notes and raw_activities lists
                            raw_notes = []
                            raw_activities = []
                            
                            # Handle file_content if available
                            file_content = None
                            if specific_ticket_cache_path and os.path.exists(specific_ticket_cache_path):
                                try:
                                    with open(specific_ticket_cache_path, 'r') as f:
                                        file_content = json.load(f)
                                        
                                    if file_content and 'data' in file_content and 'notes' in file_content['data']:
                                        raw_notes = file_content['data'].get('notes', [])
                                        raw_activities = file_content['data'].get('activities', [])
                                        note_count = len(raw_notes)
                                        activity_count = len(raw_activities)
                                        
                                        logging.info(f"Ticket file contains {note_count} notes and {activity_count} activities that will be sent to AI")
                                        
                                        # Log the first note content for debugging
                                        if note_count > 0:
                                            first_note = raw_notes[0]
                                            note_title = first_note.get('tittle', '')  # API spells it 'tittle'
                                            note_text = first_note.get('msg_text', '')
                                            note_preview = note_text[:50] + '...' if len(note_text) > 50 else note_text
                                            logging.info(f"First note: {note_title} - {note_preview}")
                                        
                                        logging.info(f"Including {note_count} raw notes and {activity_count} activities directly in AI context")
                                        
                                except Exception as e:
                                    logging.error(f"Error loading ticket cache file: {str(e)}")
                        else:
                            # If no data key, include the whole raw response
                            ticket_summary['raw_specific_ticket'] = raw_specific_ticket_data
                    
                    # Convert to JSON with indentation for readability
                    ticket_blob = json.dumps(ticket_summary, indent=2)
                    
                    # Create a detailed prefix with specific emphasis on notes if we have a specific ticket
                    ticket_prefix = "\n\n"
                    
                    # Create a special section for ticket notes if we have raw data
                    if raw_specific_ticket_data and 'data' in raw_specific_ticket_data and 'notes' in raw_specific_ticket_data['data']:
                        notes = raw_specific_ticket_data['data']['notes']
                        if notes and len(notes) > 0:
                            # Extract the notes content directly into the prompt
                            ticket_prefix += f"==== DIRECT QUOTE OF NOTES/COMMENTS FOR TICKET {specific_ticket_id} ====\n"
                            for i, note in enumerate(notes):
                                title = note.get('tittle', 'Note') # Yes, the API spells it 'tittle'
                                author = note.get('user', 'Unknown user')
                                date = note.get('created_on', '')
                                if date:
                                    try:
                                        date_obj = datetime.fromtimestamp(date)
                                        date_str = date_obj.strftime('%Y-%m-%d %H:%M')
                                    except:
                                        date_str = str(date)
                                else:
                                    date_str = 'Unknown date'
                                    
                                msg = note.get('msg_text', '')
                                if msg:
                                    # Add direct note content to the prompt
                                    ticket_prefix += f"NOTE {i+1}: {title} (by {author} on {date_str})\n"
                                    # Limit the message length to avoid extremely long prompts
                                    if len(msg) > 500:
                                        msg = msg[:497] + '...'
                                    ticket_prefix += f"{msg}\n\n"
                                    
                                    # Log for debugging
                                    logging.info(f"Added note: {title} with content length {len(msg)}")
                            
                            ticket_prefix += f"==== END OF NOTES/COMMENTS FOR TICKET {specific_ticket_id} ====\n\n"
                            
                            # Get ticket instructions from user_context.json if they exist
                            if custom_knowledge_path:
                                try:
                                    with open(custom_knowledge_path, 'r') as f:
                                        context_data = json.load(f)
                                        if 'ticket_details' in context_data and 'instructions' in context_data['ticket_details']:
                                            # Only include ticket instructions if ticket_access is enabled or specific_ticket is provided
                                            if ticket_access or specific_ticket:
                                                ticket_instructions = context_data['ticket_details']['instructions']
                                                ticket_prefix += ticket_instructions + "\n\n"
                                                logging.info("Using ticket instructions from user_context.json")
                                        else:
                                            # Only include basic instructions if ticket_access is enabled or specific_ticket is provided
                                            if ticket_access or specific_ticket:
                                                ticket_prefix += "Remember to check for notes and diagnostic reports when asked about ticket comments.\n\n"
                                except Exception as e:
                                    logging.error(f"Error loading ticket instructions from user_context.json: {str(e)}")
                                    # Only include ticket instructions in error case if ticket_access is enabled or specific_ticket is provided
                                    if ticket_access or specific_ticket:
                                        ticket_prefix += "Remember to check for notes and diagnostic reports when asked about ticket comments.\n\n"
                    
                    # Only include ticket-related instructions if ticket_access is enabled or a specific ticket is provided
                    if ticket_access or specific_ticket:
                        ticket_prefix += "You have access to the following repair shop ticket data. "
                    
                    if specific_ticket_data or raw_specific_ticket_data:
                        # Strong emphasis on specific ticket being available
                        ticket_id = specific_ticket_data['ticket_id'] if specific_ticket_data else specific_ticket_id
                        
                        # Count notes from both processed and raw data sources
                        notes_count = 0
                        activities_count = 0
                        
                        if specific_ticket_data:
                            notes_count += len(specific_ticket_data.get('notes', []))
                            activities_count += len(specific_ticket_data.get('activities', []))
                            
                        # Also check raw data which may have more complete information
                        if raw_specific_ticket_data:
                            data = raw_specific_ticket_data.get('data', {})
                            if data.get('notes'):
                                notes_count += len(data.get('notes', []))
                            if data.get('activities'):
                                activities_count += len(data.get('activities', []))
                        
                        ticket_prefix += f"IMPORTANT: You have DETAILED information about ticket {ticket_id} with "
                        
                        # Explicitly mention notes/comments to make them more prominent
                        if notes_count > 0 or activities_count > 0:
                            if notes_count > 0:
                                ticket_prefix += f"{notes_count} notes/comments"
                                if activities_count > 0:
                                    ticket_prefix += f" and {activities_count} activity records"
                            else:
                                ticket_prefix += f"{activities_count} activity records"
                            ticket_prefix += ". "
                        
                        ticket_prefix += "You also have customer details and status information. "
                    
                    ticket_prefix += "Use this to answer questions about tickets, customers, repairs, comments, and statuses. "
                    
                    # Add special emphasis if we have raw data
                    if raw_specific_ticket_data:
                        ticket_prefix += "IMPORTANT: For ticket " + ticket_id + ", look in BOTH the processed 'specific_ticket' and the complete 'raw_specific_ticket' JSON data. "
                        
                        # Add extremely direct instructions for finding diagnostic reports
                        if 'data' in raw_specific_ticket_data and 'notes' in raw_specific_ticket_data['data']:
                            notes = raw_specific_ticket_data['data']['notes']
                            diag_count = sum(1 for note in notes if 'diagnostic' in note.get('msg_text', '').lower() or 'system information' in note.get('msg_text', '').lower())
                            
                            if diag_count > 0:
                                ticket_prefix += f"CRITICAL: This ticket contains {diag_count} diagnostic reports in the notes/comments. "
                                ticket_prefix += "These diagnostic reports ARE comments on the ticket. "
                                ticket_prefix += "When asked about comments or notes, you MUST include information about these diagnostic reports. "
                        
                    ticket_prefix += "If asked about notes or comments for a specific ticket, check the 'notes' arrays in both the processed data AND raw data sections. "
                    ticket_prefix += "Notes/comments may appear in: 'specific_ticket.notes', 'specific_ticket.activities', 'raw_specific_ticket.data.notes', or 'raw_specific_ticket.data.activities'. "
                    ticket_prefix += "PAY SPECIAL ATTENTION to the 'msg_text' field in the notes arrays to find the actual comment content. "
                    ticket_prefix += "Remember that diagnostic reports, system information reports, and any other content in the 'msg_text' field ARE ticket comments."
                    
                    # Add to existing system message or create new one
                    if system_message:
                        system_message += ticket_prefix
                    else:
                        system_message = "You are NestBot, an AI assistant"
                        if company_name:
                            system_message += f" for {company_name}"
                        system_message += "." + ticket_prefix
                    
                    system_message += f"\n{ticket_blob}"
                    logging.info(f"Including ticket data in AI prompt context ({len(ticket_data)} tickets)")
                    
                    # Create a payload with system instructions and the user message
                    payload = {
                        "system": system_message, 
                        "messages": [{"role": "user", "content": user_message}]
                    }
                else:
                    # Handle case with just custom knowledge (no ticket data)
                    system_message = ""
                    
                    # Add custom knowledge if available
                    if custom_knowledge_path and os.path.exists(custom_knowledge_path):
                        # Load the custom knowledge
                        with open(custom_knowledge_path, "r") as file:
                            custom_data = json.load(file)
                            
                        # Convert the data to a string for the system message
                        knowledge_blob = json.dumps(custom_data, indent=2)
                        system_message = f"Use this knowledge when responding: {knowledge_blob}"
                        logging.info(f"Using custom knowledge from {custom_knowledge_path}")
                    
                    # Create payload with the knowledge as system message and user message
                    payload = {
                        "system": system_message,
                        "messages": [{"role": "user", "content": user_message}]
                    }
                
                # Create the request data - Claude API expects system at top level
                data = {
                    "model": model,
                    "max_tokens": 1000,
                    "system": payload.get("system", ""),
                    "messages": payload.get("messages", [{"role": "user", "content": user_message}])
                }
                
                # Log request details for debugging
                logging.debug(f"Making Claude API request with model: {model}")
                if system_message:
                    # Truncate for logging to prevent overwhelming logs
                    system_preview = system_message[:100] + "..." if len(system_message) > 100 else system_message
                    logging.debug(f"System message preview: {system_preview}")
                
                # Make a single API request to Claude
                response = requests.post(
                    "https://api.anthropic.com/v1/messages",
                    headers=headers,
                    json=data
                )
                
                # Process the response
                if response.status_code == 200:
                    response_json = response.json()
                    logging.info(f"Claude API response successful. Model: {model}")
                    response_text = response_json["content"][0]["text"]
                    # Log the first part of the response for debugging
                    response_preview = response_text[:100] + "..." if len(response_text) > 100 else response_text
                    logging.debug(f"AI response preview: {response_preview}")
                else:
                    error_msg = f"Error from Claude API: {response.status_code} - {response.text}"
                    logging.error(error_msg)
                    response_text = error_msg
                    
            elif use_api == "openai" or use_api == "gpt":
                # OpenAI API
                api_key = config.get("gpt", {}).get("api_key")
                if not api_key:
                    raise ValueError("OpenAI/GPT API key not found in config file")
                
                # Use the selected model or default to the one from config
                model = model_name or config.get("gpt", {}).get("model", "gpt-4")
                
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
                
                # If custom knowledge path is provided, inject the knowledge as context
                if custom_knowledge_path and os.path.exists(custom_knowledge_path):
                    if ticket_data:
                        # Load user context
                        with open(custom_knowledge_path, "r") as file:
                            custom_data = json.load(file)
                        
                        # Get the ticket summary we created earlier
                        ticket_summary = {
                            'total_tickets': len(ticket_data),
                            'oldest_ticket_id': oldest_ticket_id,
                            'newest_ticket_id': newest_ticket_id,
                            'ticket_details': processed_tickets
                        }
                        
                        # Format contexts as strings
                        context_blob = json.dumps(custom_data, indent=2)
                        ticket_blob = json.dumps(ticket_summary, indent=2)
                        
                        # Extract user's first name if available for personalization
                        first_name = ""
                        if current_user:
                            full_name = current_user.get("fullname", "")
                            # Extract first name (everything before the first space)
                            first_name = full_name.split()[0] if full_name and " " in full_name else full_name
                        
                        # Create system message with combined knowledge
                        system_message = ""
                        if first_name:
                            system_message = f"IMPORTANT INSTRUCTIONS: The user's first name is {first_name}. DO NOT use their last name. DO NOT begin your responses with greetings like 'Hello {first_name}' or 'Hi {first_name}'. "
                        
                        # Get company name if available
                        company_name = ""
                        if current_user and "company" in current_user:
                            company_name = current_user.get("company", "")
                        # No company_info in this context since this is not a class method
                            
                        # Add branding if company name is available
                        if not system_message:
                            system_message = "You are NestBot, an AI assistant"
                            if company_name:
                                system_message += f" for {company_name}"
                            system_message += "."
                        
                        # Add the knowledge sources
                        system_message += f"\n\nUse the following knowledge when responding:\n{context_blob}\n\nYou also have access to the following ticket data. Use this to answer questions about tickets, customers, repairs, etc.:\n{ticket_blob}"
                        
                        # Check if we have a specific ticket ID to include
                        specific_ticket_raw_file = None
                        if specific_ticket:
                            specific_id = specific_ticket
                            if not specific_id.startswith('T-'):
                                specific_id = f"T-{specific_id}"
                                
                            # Try to load the raw file directly
                            specific_path = f"/home/outbackelectronics/Nest_2.4/cache/ticket_detail_{specific_id}.json"
                            if os.path.exists(specific_path):
                                try:
                                    with open(specific_path, 'r') as f:
                                        specific_ticket_raw_file = json.load(f)
                                        logging.error(f"LOADED RAW TICKET FILE: {specific_path}")
                                except Exception as e:
                                    logging.error(f"ERROR loading ticket file: {str(e)}")
                        
                        # ADD DIRECT TICKET INFO TO USER MESSAGE INSTEAD OF SYSTEM PROMPT
                        # This bypasses any filtering that might happen in system message processing
                        enhanced_user_message = user_message
                        
                        if specific_ticket_raw_file:
                            # Add the raw ticket file directly to the user message
                            ticket_prompt = "\n\nHere is the raw ticket detail data for your reference:\n```json\n"
                            ticket_json = json.dumps(specific_ticket_raw_file, indent=2)
                            ticket_prompt += ticket_json + "\n```\n"
                            enhanced_user_message = enhanced_user_message + ticket_prompt
                            logging.error(f"ADDED RAW TICKET FILE DIRECTLY TO USER MESSAGE: {len(ticket_json)} bytes")
                        
                        # Create API request with messages
                        messages = [
                            {"role": "system", "content": system_message},
                            {"role": "user", "content": enhanced_user_message}
                        ]
                        logging.info(f"Using combined custom knowledge and ticket data for GPT")
                        
                        # Debug what notes are being sent in the prompt
                        if ticket_summary and 'raw_specific_ticket' in ticket_summary:
                            # Extract just the raw notes from the specific ticket for debugging
                            raw_ticket_data = ticket_summary['raw_specific_ticket']
                            if 'data' in raw_ticket_data and 'notes' in raw_ticket_data['data']:
                                notes_data = []
                                for note in raw_ticket_data['data']['notes']:
                                    note_copy = {
                                        'id': note.get('id', ''),
                                        'tittle': note.get('tittle', ''),  # Yes, API spells it as 'tittle'
                                        'msg_text': note.get('msg_text', ''),
                                        'user': note.get('user', ''),
                                        'created_on': note.get('created_on', '')
                                    }
                                    notes_data.append(note_copy)
                                
                                logging.info(f"Found {len(notes_data)} notes to send to AI")
                                if notes_data:
                                    first_note = notes_data[0]
                                    logging.info(f"First note: {first_note['tittle']} - {first_note['msg_text'][:50]}")
                    else:
                        # Just use the original custom knowledge without ticket data
                        # Define messages list before using it
                        messages = []
                        # Direct implementation to replace self.inject_custom_knowledge call
                        if custom_knowledge_path and os.path.exists(custom_knowledge_path):
                            with open(custom_knowledge_path, 'r') as f:
                                custom_knowledge = json.load(f)
                            knowledge_str = json.dumps(custom_knowledge)
                            messages.append({"role": "system", "content": f"Use this knowledge when responding: {knowledge_str}"})
                            # Add the user message to the messages array
                            messages.append({"role": "user", "content": user_message})
                            logging.info(f"Using custom knowledge from {custom_knowledge_path}")
                else:
                    # Extract user's first name if available
                    first_name = ""
                    if current_user:
                        full_name = current_user.get("fullname", "")
                        # Extract first name (everything before the first space)
                        first_name = full_name.split()[0] if full_name and " " in full_name else full_name
                    
                    # Create system message with strict instructions about addressing the user
                    system_message = ""
                    if first_name:
                        system_message = f"IMPORTANT INSTRUCTIONS: The user's first name is {first_name}. DO NOT use their last name. DO NOT begin your responses with greetings like 'Hello {first_name}' or 'Hi {first_name}'. Just respond directly to questions and requests without these formalities."
                    
                    # Add ticket data if available
                    if ticket_data:
                        # Get the ticket summary we created earlier
                        ticket_summary = {
                            'total_tickets': len(ticket_data),
                            'oldest_ticket_id': oldest_ticket_id,
                            'newest_ticket_id': newest_ticket_id,
                            'ticket_details': processed_tickets
                        }
                        
                        # DIRECT FIX: Load and include the specific ticket file
                        if specific_ticket:
                            specific_id = specific_ticket
                            # Format with T- prefix if needed
                            if not specific_id.startswith('T-') and not specific_id.lower().startswith('t'):
                                specific_id = f"T-{specific_id}"
                            elif specific_id.lower().startswith('t') and not specific_id.startswith('T-'):
                                specific_id = f"T-{specific_id[1:]}"
                                
                            # Try multiple locations with both T- prefix and without
                            from nest.utils.cache_utils import get_ticket_detail_directory
                            cache_dir = get_ticket_detail_directory()
                            
                            paths = [
                                os.path.join(cache_dir, f"ticket_detail_{specific_id}.json"),
                            ]
                            
                            logging.info(f"DEBUGGING: Looking for ticket file for ID {specific_id}")
                            logging.info(f"DEBUGGING: Path search list: {paths}")
                            
                            # Add version without T- prefix if it has one
                            if specific_id.startswith('T-'):
                                num_id = specific_id[2:]
                                paths.append(f"/home/outbackelectronics/Nest_2.4/cache/ticket_detail_{num_id}.json")
                            
                            # Check each path
                            for path in paths:
                                if os.path.exists(path):
                                    try:
                                        with open(path, 'r') as f:
                                            ticket_file_content = json.load(f)
                                            
                                            # ADD THE RAW TICKET FILE DIRECTLY to the ticket_summary
                                            ticket_summary['specific_ticket_file'] = ticket_file_content
                                            
                                            # CRITICAL DEBUGGING: Log the actual ticket data that's being added
                                            logging.info(f"SUCCESS: Added COMPLETE ticket file {path} to AI context")
                                            logging.error(f"CRITICAL DEBUG: Ticket data keys: {ticket_file_content.keys()}")
                                            
                                            # Dump the full ticket data to a debug file to confirm content
                                            debug_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'cache', 'ticket_debug_dump.json')
                                            try:
                                                with open(debug_path, 'w') as f:
                                                    json.dump(ticket_summary, f, indent=2)
                                                logging.error(f"FULL TICKET DATA DUMPED to {debug_path} for debugging")
                                            except Exception as e:
                                                logging.error(f"Error writing debug file: {str(e)}")

                                            
                                            # Print info about what we found for debugging
                                            if 'data' in ticket_file_content:
                                                data = ticket_file_content['data']
                                                if 'notes' in data:
                                                    notes = data['notes']
                                                    logging.info(f"Ticket file contains {len(notes)} notes that will be seen by the AI")
                                                    
                                                    # Show preview of first note for verification
                                                    if len(notes) > 0:
                                                        note = notes[0]
                                                        title = note.get('tittle', 'Note')  # API spells it 'tittle'
                                                        msg = note.get('msg_text', '')[:50] + '...' if len(note.get('msg_text', '')) > 50 else note.get('msg_text', '')
                                                        logging.info(f"First note preview: {title} - {msg}")
                                        break
                                    except Exception as e:
                                        logging.error(f"Error loading ticket file {path}: {str(e)}")
                        
                        ticket_blob = json.dumps(ticket_summary, indent=2)
                        ticket_prefix = "\n\nYou have access to the following repair shop ticket data. Use this to answer questions about tickets, customers, repairs, etc.:"
                        
                        # Get company name if available
                        company_name = ""
                        if current_user and "company" in current_user:
                            company_name = current_user.get("company", "")
                        # No company_info in this context since this is not a class method
                            
                        # Add to existing system message or create new one
                        if system_message:
                            system_message += ticket_prefix + f"\n{ticket_blob}"
                        else:
                            system_message = "You are NestBot, an AI assistant"
                            if company_name:
                                system_message += f" for {company_name}"
                            system_message += "." + ticket_prefix + f"\n{ticket_blob}"
                        logging.info(f"Including ticket data in GPT prompt context ({len(ticket_data)} tickets)")
                        
                    messages = [
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": user_message}
                    ]
                
                data = {
                    "model": model,
                    "messages": messages,
                    "max_tokens": 1000
                }
                
                # CRITICAL DEBUGGING: Check if the specific ticket data is actually in the API call
                # We need to see what is ACTUALLY being sent to the API
                has_ticket_file = False
                for message in messages:
                    if message.get('role') == 'system':
                        system_content = message.get('content', '')
                        # Check if our ticket file is in the system message
                        if 'specific_ticket_file' in system_content:
                            logging.error("FOUND specific_ticket_file IN SYSTEM CONTENT! Data is being sent!")
                            has_ticket_file = True
                            # Log excerpt with the specific_ticket_file
                            start_idx = system_content.find('specific_ticket_file')
                            excerpt = system_content[start_idx:start_idx+200] + '...'
                            logging.error(f"EXCERPT of specific_ticket_file in system content: {excerpt}")
                            
                            # Check for notes specifically
                            if "notes" in system_content:
                                logging.error("The word 'notes' IS present in the system message!")
                                
                                # Find the specific notes section
                                notes_idx = system_content.find('"notes"')
                                if notes_idx > 0:
                                    notes_excerpt = system_content[notes_idx:notes_idx+200] + '...'
                                    logging.error(f"EXCERPT of notes in system content: {notes_excerpt}")
                
                if not has_ticket_file and specific_ticket:
                    # Only log this as an error if the user specifically requested a ticket
                    logging.warning("Specific ticket file not found in API request, but was requested. The AI will still respond with general information.")
                    
                    # Try to find ticket_summary for debugging purposes
                    for message in messages:
                        if message.get('role') == 'system':
                            if "ticket_summary" in message.get('content', ''):
                                logging.debug("Found ticket_summary in system message, but specific ticket file is missing.")
                            
                            # Also check if ticket_blob has the right content
                            msg_content = message.get('content', '')
                            if "total_tickets" in msg_content and "ticket_details" in msg_content:
                                logging.error("Found ticket_blob content in system message, but specific_ticket_file is missing!")
                                
                logging.info(f"API Request Payload: {json.dumps(data, indent=2)}")
                
                response = requests.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=headers,
                    json=data
                )
                
                if response.status_code == 200:
                    response_json = response.json()
                    logging.info(f"OpenAI API response successful. Model: {model}")
                    response_text = response_json["choices"][0]["message"]["content"]
                elif response.status_code == 404 and "model_not_found" in response.text.lower():
                    # Specific error handling for model not found (404)
                    error_msg = f"The selected model '{model}' is not available or you do not have access to it."
                    logging.error(f"Model not found error: {response.text}")
                    response_text = f"⚠️ Model Unavailable: {error_msg}\nPlease try selecting a different model."
                else:
                    error_msg = f"Error from OpenAI API: {response.status_code} - {response.text}"
                    logging.error(error_msg)
                    response_text = error_msg
                
            elif use_api == "gemini":
                # Gemini API
                api_key = config.get("gemini", {}).get("api_key")
                if not api_key:
                    raise ValueError("Gemini API key not found in config file")
                
                # Use the selected model or default to the one from config
                model = model_name or config.get("gemini", {}).get("model", "gemini-2.5-pro-preview-05-06")
                
                # Construct the API URL with model and API key
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
                
                headers = {
                    "Content-Type": "application/json"
                }
                
                # Prepare the message content
                if custom_knowledge_path and os.path.exists(custom_knowledge_path):
                    # Load custom knowledge
                    with open(custom_knowledge_path, "r") as file:
                        custom_data = json.load(file)
                    
                    # Format as string
                    context_blob = json.dumps(custom_data, indent=2)
                    
                    # For Gemini, we need to format differently than OpenAI/Claude
                    system_prompt = f"Use the following knowledge when responding:\n{context_blob}"
                    full_message = f"{system_prompt}\n\nUser query: {user_message}"
                    logging.info(f"Using custom knowledge from {custom_knowledge_path}")
                else:
                    full_message = user_message
                
                data = {
                    "contents": [
                        {
                            "parts": [
                                {
                                    "text": full_message
                                }
                            ]
                        }
                    ],
                    "generationConfig": {
                        "temperature": 0.7,
                        "maxOutputTokens": 1000
                    }
                }
                
                response = requests.post(
                    url,
                    headers=headers,
                    json=data
                )
                
                if response.status_code == 200:
                    response_json = response.json()
                    logging.info(f"Gemini API response successful. Model: {model}")
                    # Extract text from the Gemini response format
                    if response_json.get("candidates") and len(response_json["candidates"]) > 0:
                        candidate = response_json["candidates"][0]
                        if (candidate.get("content") and
                            candidate["content"].get("parts") and
                            len(candidate["content"]["parts"]) > 0):
                            response_text = candidate["content"]["parts"][0].get("text", "")
                        else:
                            response_text = "Received empty response from Gemini API"
                    else:
                        response_text = "No valid response from Gemini API"
                elif response.status_code == 404:
                    # Specific error handling for model not found (404)
                    error_msg = f"The selected Gemini model '{model}' is not available or you do not have access to it."
                    logging.error(f"Model not found error: {response.text}")
                    response_text = f"⚠️ Model Unavailable: {error_msg}\nPlease try selecting a different model."
                else:
                    error_msg = f"Error from Gemini API: {response.status_code} - {response.text}"
                    logging.error(error_msg)
                    response_text = error_msg
            else:
                response_text = "No valid API selected. Please configure either Claude, OpenAI, or Gemini."
                
        except Exception as e:
            error_msg = f"Error when contacting AI service: {str(e)}"
            logging.error(error_msg)
            import traceback
            logging.error(traceback.format_exc())
            response_text = f"⚠️ Error: {str(e)}\nPlease check the config or try again later."
        
        # Simply return the response text - UI updates are handled by the caller
        return response_text


def _call_claude_api(user_message: str, model_name: str, config: Dict, 
                    ticket_data: Optional[List] = None, processed_tickets: Optional[List] = None,
                    specific_ticket: Optional[str] = None, custom_knowledge_path: Optional[str] = None,
                    current_user: Optional[Dict] = None) -> str:
    """
    Call the Claude API with the user message and any additional context.
    
    Args:
        user_message: The user's message
        model_name: The Claude model to use
        config: Application configuration dict containing API keys
        ticket_data: Raw ticket data to include in context
        processed_tickets: Processed ticket data for context
        specific_ticket: Specific ticket number to include
        custom_knowledge_path: Path to custom knowledge file
        current_user: Current user information
        
    Returns:
        str: The AI's response text
    """
    # Get API key from config
    api_key = config.get("claude", {}).get("api_key")
    if not api_key:
        raise ValueError("Claude API key not found in config file")
    
    # Use the selected model or default to the one from config
    model = model_name or config.get("claude", {}).get("model", "claude-3-opus-20240229")
    
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    
    # Prepare the system message and payload based on available knowledge sources
    # Start by getting user's first name for personalization if available
    first_name = ""
    if current_user:
        full_name = current_user.get("fullname", "")
        # Extract first name (everything before the first space)
        first_name = full_name.split()[0] if full_name and " " in full_name else full_name
    
    # Get company name if available for branding
    company_name = ""
    if current_user and "company" in current_user:
        company_name = current_user.get("company", "")
    
    # Create the base system message
    system_message = ""
    if first_name:
        system_message = f"IMPORTANT INSTRUCTIONS: The user's first name is {first_name}. DO NOT use their last name. DO NOT begin your responses with greetings like 'Hello {first_name}' or 'Hi {first_name}'. Just respond directly to questions and requests without these formalities."
    
    # Determine which knowledge sources to include
    if custom_knowledge_path and os.path.exists(custom_knowledge_path):
        # Load the custom knowledge
        with open(custom_knowledge_path, "r") as file:
            custom_data = json.load(file)
            
        # Filter out ticket_details if ticket access is not enabled and no specific ticket
        if not (ticket_access or specific_ticket) and "ticket_details" in custom_data:
            # Create a copy of the data without ticket_details to avoid modifying the original
            filtered_data = {k: v for k, v in custom_data.items() if k != "ticket_details"}
            knowledge_blob = json.dumps(filtered_data, indent=2)
            logging.info("Filtered out ticket_details from knowledge as ticket access is not enabled")
        else:
            # Use the full data including ticket_details
            knowledge_blob = json.dumps(custom_data, indent=2)
        
        # Add the custom knowledge to system message
        knowledge_prefix = "\n\nUse this knowledge when responding:"
        if system_message:
            system_message += knowledge_prefix
        else:
            system_message = "You are NestBot, an AI assistant"
            if company_name:
                system_message += f" for {company_name}"
            system_message += "." + knowledge_prefix
        
        system_message += f" {knowledge_blob}"
        logging.info(f"Using custom knowledge from {custom_knowledge_path}")
    
    # Add ticket data if available
    if ticket_data:
        # Prepare ticket summary for the prompt
        ticket_summary = {
            "summary": {
                "total_tickets": len(processed_tickets),
                "oldest_ticket": oldest_ticket_id,
                "newest_ticket": newest_ticket_id
            },
            "ticket_details": processed_tickets
        }
        
        # Look for specific ticket information if requested
        if specific_ticket:
            # First format the specific ticket number consistently
            if not specific_ticket.startswith('T-'):
                specific_ticket = f"T-{specific_ticket}"
            
            # Try to find detailed information about this specific ticket
            specific_ticket_data = None
            raw_specific_ticket_data = None
            
            # Try to load the specific ticket detail file directly
            from nest.utils.cache_utils import get_ticket_detail_directory
            cache_dir = get_ticket_detail_directory()
            
            potential_paths = [
                os.path.join(cache_dir, f"ticket_detail_{specific_ticket}.json"),
            ]
            
            # Also look for variations without the T- prefix
            if specific_ticket.startswith('T-'):
                numeric_id = specific_ticket[2:]
                potential_paths.extend([
                    os.path.join(cache_dir, f"ticket_detail_{numeric_id}.json"),
                ])
            
            # Try each path
            file_content = None
            for path in potential_paths:
                if os.path.exists(path):
                    try:
                        with open(path, 'r') as f:
                            file_content = json.load(f)
                            logging.info(f"Loaded specific ticket file from {path}")
                            break
                    except Exception as e:
                        logging.error(f"Error loading specific ticket file {path}: {str(e)}")
            
            # Include specific ticket data if found
            if file_content:
                ticket_summary["specific_ticket_file"] = file_content
                
                # Extract notes for easier access
                if 'data' in file_content and 'notes' in file_content['data']:
                    raw_notes = file_content['data']['notes']
                    raw_activities = file_content['data']['activities'] if 'activities' in file_content['data'] else []
                    
                    # Log notes for debugging
                    logging.info(f"Found {len(raw_notes)} notes and {len(raw_activities)} activities in specific ticket")
        
        # Convert to JSON with indentation for readability
        ticket_blob = json.dumps(ticket_summary, indent=2)
        
        # Create detailed prefix for system message
        ticket_prefix = "\n\nYou have access to the following repair shop ticket data. "
        
        # Add specific ticket info if available
        if specific_ticket:
            ticket_prefix += f"IMPORTANT: You have DETAILED information about ticket {specific_ticket}. "
            ticket_prefix += "This includes detailed customer information, device information, and any notes or comments. "
        
        ticket_prefix += "Use this to answer questions about tickets, customers, repairs, and statuses."
        
        # Add to existing system message or create new one
        if system_message:
            system_message += ticket_prefix
        else:
            system_message = "You are NestBot, an AI assistant"
            if company_name:
                system_message += f" for {company_name}"
            system_message += "." + ticket_prefix
        
        system_message += f"\n{ticket_blob}"
        logging.info(f"Including ticket data in AI prompt context ({len(ticket_data)} tickets)")
    
    # Set up the payload with system message and user message
    data = {
        "model": model,
        "max_tokens": 1000,
        "system": system_message,
        "messages": [{"role": "user", "content": user_message}]
    }
    
    # Log request summary
    logging.debug(f"Making Claude API request with model: {model}")
    if system_message:
        system_preview = system_message[:100] + "..." if len(system_message) > 100 else system_message
        logging.debug(f"System message preview: {system_preview}")
    
    # Make the API request
    response = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers=headers,
        json=data
    )
    
    # Process the response
    if response.status_code == 200:
        response_json = response.json()
        logging.info(f"Claude API response successful. Model: {model}")
        return response_json["content"][0]["text"]
    else:
        # Handle error response
        error_message = f"Claude API error: {response.status_code} - {response.text}"
        logging.error(error_message)
        return f"I encountered an error while processing your request: {response.status_code} error."


def _call_openai_api(user_message: str, model_name: str, config: Dict, 
                    ticket_data: Optional[List] = None, processed_tickets: Optional[List] = None,
                    specific_ticket: Optional[str] = None, custom_knowledge_path: Optional[str] = None,
                    current_user: Optional[Dict] = None) -> str:
    """
    Call the OpenAI API with the user message and any additional context.
    
    Args:
        user_message: The user's message
        model_name: The OpenAI model to use
        config: Application configuration dict containing API keys
        ticket_data: Raw ticket data to include in context
        processed_tickets: Processed ticket data for context
        specific_ticket: Specific ticket number to include
        custom_knowledge_path: Path to custom knowledge file
        current_user: Current user information
        
    Returns:
        str: The AI's response text
    """
    # Get API key from config
    # Try both direct 'gpt' section and 'openai' section for backward compatibility
    api_key = config.get("gpt", {}).get("api_key") or config.get("openai", {}).get("api_key")
    if not api_key:
        raise ValueError("OpenAI API key not found in config file")
    
    # Use the selected model or default to the one from config
    model = model_name or config.get("gpt", {}).get("model", "gpt-4")
    
    # Log the model we're using
    logging.info(f"Using OpenAI model: {model}")
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Start building the messages list
    messages = []
    
    # Create system message with appropriate instructions
    system_content = "You are NestBot, an AI assistant for a computer repair shop."
    
    # Add user's first name for personalization if available
    if current_user:
        full_name = current_user.get("fullname", "")
        # Extract first name (everything before the first space)
        first_name = full_name.split()[0] if full_name and " " in full_name else full_name
        if first_name:
            system_content += f" The user's first name is {first_name}. DO NOT use their last name."
    
    # Add custom knowledge if available
    if custom_knowledge_path and os.path.exists(custom_knowledge_path):
        # Load the custom knowledge
        with open(custom_knowledge_path, "r") as file:
            custom_data = json.load(file)
            
        # Filter out ticket_details if ticket access is not enabled and no specific ticket
        if not (ticket_access or specific_ticket) and "ticket_details" in custom_data:
            # Create a copy of the data without ticket_details to avoid modifying the original
            filtered_data = {k: v for k, v in custom_data.items() if k != "ticket_details"}
            knowledge_blob = json.dumps(filtered_data, indent=2)
            logging.info("Filtered out ticket_details from knowledge as ticket access is not enabled")
        else:
            # Use the full data including ticket_details
            knowledge_blob = json.dumps(custom_data, indent=2)
        
        # Add the custom knowledge to system message
        system_content += f"\n\nUse this knowledge when responding: {knowledge_blob}"
        logging.info(f"Using custom knowledge from {custom_knowledge_path}")
    
    # Add ticket data if available
    if ticket_data:
        # Prepare ticket summary for the prompt
        ticket_summary = {
            "summary": {
                "total_tickets": len(processed_tickets),
            },
            "ticket_details": processed_tickets
        }
        
        # Look for specific ticket information if requested
        if specific_ticket:
            specific_ticket_data = [t for t in processed_tickets if t.get("id") == specific_ticket]
            if specific_ticket_data:
                ticket_summary["specific_ticket"] = specific_ticket_data[0]
        
        # Add ticket access information to system message
        system_content += f"\n\nYou have access to repair shop ticket data for {len(processed_tickets)} tickets."
        if specific_ticket and specific_ticket_data:
            system_content += f" This includes detailed information about ticket {specific_ticket}."
        
        # Add the ticket data as an attachment to the system message
        system_content += f"\n\nTicket Data:\n{json.dumps(ticket_summary, indent=2)}"
    
    # Add the complete system message
    messages.append({"role": "system", "content": system_content})
    
    # Add the user message
    messages.append({"role": "user", "content": user_message})
    
    # Log the user message to verify it's being included
    logging.info(f"USER QUESTION INCLUDED IN API REQUEST: '{user_message}'")
    
    # Set up the API request data
    data = {
        "model": model,
        "messages": messages,
        "max_tokens": 1000,
        "temperature": 0.7
    }
    
    # Log request summary
    logging.debug(f"Making OpenAI API request with model: {model}")
    
    # Make the API request
    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers=headers,
        json=data
    )
    
    # Process the response
    if response.status_code == 200:
        response_json = response.json()
        logging.info(f"OpenAI API response successful. Model: {model}")
        return response_json["choices"][0]["message"]["content"]
    else:
        # Handle error response
        error_message = f"OpenAI API error: {response.status_code} - {response.text}"
        logging.error(error_message)
        return f"I encountered an error while processing your request: {response.status_code} error."


def _call_gemini_api(user_message: str, model_name: str, config: Dict, 
                     ticket_data: Optional[List] = None, processed_tickets: Optional[List] = None,
                     specific_ticket: Optional[str] = None, custom_knowledge_path: Optional[str] = None,
                     current_user: Optional[Dict] = None) -> str:
    """
    Call the Google Gemini API with the user message and any additional context.
    
    Args:
        user_message: The user's message
        model_name: The Gemini model to use
        config: Application configuration dict containing API keys
        ticket_data: Raw ticket data to include in context
        processed_tickets: Processed ticket data for context
        specific_ticket: Specific ticket number to include
        custom_knowledge_path: Path to custom knowledge file
        current_user: Current user information
        
    Returns:
        str: The AI's response text
    """
    # Get API key from config
    api_key = config.get("gemini", {}).get("api_key")
    if not api_key:
        raise ValueError("Gemini API key not found in config file")
    
    # Use the model from config
    model = config.get("gemini", {}).get("model")
    
    # Log the model we're using
    logging.info(f"Using Gemini model: {model}")
    
    # Gemini API has a different endpoint structure based on the model
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    
    # Start building the content parts
    content_parts = []
    
    # Create system part with appropriate instructions
    system_text = "You are NestBot, an AI assistant for a computer repair shop."
    
    # Add user's first name for personalization if available
    if current_user:
        full_name = current_user.get("fullname", "")
        # Extract first name (everything before the first space)
        first_name = full_name.split()[0] if full_name and " " in full_name else full_name
        if first_name:
            system_text += f" The user's first name is {first_name}. DO NOT use their last name."
    
    # Add custom knowledge if available
    if custom_knowledge_path and os.path.exists(custom_knowledge_path):
        # Load the custom knowledge
        with open(custom_knowledge_path, "r") as file:
            custom_data = json.load(file)
        
        # Filter out ticket_details if ticket access is not enabled and no specific ticket
        if not (ticket_access or specific_ticket) and "ticket_details" in custom_data:
            # Create a copy of the data without ticket_details to avoid modifying the original
            filtered_data = {k: v for k, v in custom_data.items() if k != "ticket_details"}
            knowledge_blob = json.dumps(filtered_data, indent=2)
            logging.info("Filtered out ticket_details from knowledge as ticket access is not enabled")
        else:
            # Use the full data including ticket_details
            knowledge_blob = json.dumps(custom_data, indent=2)
        
        # Add the custom knowledge to system message
        system_text += f"\n\nUse this knowledge when responding: {knowledge_blob}"
        logging.info(f"Using custom knowledge from {custom_knowledge_path}")
    
    # Add ticket data if available
    if ticket_data:
        # Prepare ticket summary for the prompt
        ticket_summary = {
            "summary": {
                "total_tickets": len(processed_tickets),
            },
            "ticket_details": processed_tickets
        }
        
        # Look for specific ticket information if requested
        if specific_ticket:
            specific_ticket_data = [t for t in processed_tickets if t.get("id") == specific_ticket]
            if specific_ticket_data:
                ticket_summary["specific_ticket"] = specific_ticket_data[0]
        
        # Add ticket access information to system message
        system_text += f"\n\nYou have access to repair shop ticket data for {len(processed_tickets)} tickets."
        if specific_ticket and specific_ticket_data:
            system_text += f" This includes detailed information about ticket {specific_ticket}."
        
        # Add the ticket data as an attachment to the system message
        system_text += f"\n\nTicket Data:\n{json.dumps(ticket_summary, indent=2)}"
    
    # Add the system message as the first part
    content_parts.append({"text": system_text, "role": "system"})
    
    # Add the user message as the second part
    content_parts.append({"text": user_message, "role": "user"})
    
    # Set up the API request data
    data = {
        "contents": [
            {
                "parts": [{'text': part['text']} for part in content_parts]
            }
        ],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 1024,
        }
    }
    
    # Log request summary
    logging.debug(f"Making Gemini API request with model: {model}")
    
    # Make the API request
    response = requests.post(
        api_url,
        json=data
    )
    
    # Process the response
    if response.status_code == 200:
        response_json = response.json()
        logging.info(f"Gemini API response successful. Model: {model}")
        try:
            # Extract the response text from the Gemini API structure
            return response_json["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as e:
            logging.error(f"Error parsing Gemini API response: {e}")
            return "I encountered an error while processing the API response."
    else:
        # Handle error response
        error_message = f"Gemini API error: {response.status_code} - {response.text}"
        logging.error(error_message)
        return f"I encountered an error while processing your request: {response.status_code} error."
