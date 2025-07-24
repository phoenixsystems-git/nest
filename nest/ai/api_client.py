#!/usr/bin/env python
"""
AI API client for NestBot - FIXED VERSION

Handles interactions with various AI APIs (Claude, OpenAI/GPT, Gemini)
and formats requests and responses appropriately with proper fallback handling.
"""

import os
import json
import logging
import requests
from datetime import datetime
from typing import Dict, List, Any, Optional

# Import the ticket utilities
from nest.ai.ticket_utils import load_ticket_data


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


def get_ai_response(user_message, selected_model=None, ticket_access=True, specific_ticket=None, custom_knowledge_path=None, current_user=None, conversation_context=None):
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
    
    # IMMEDIATE FIX: Check for valid API keys first
    try:
        from nest.utils.platform_paths import PlatformPaths
        platform_paths = PlatformPaths()
        config_path = platform_paths.get_config_dir() / 'config.json'
        with open(str(config_path), 'r') as file:
            config = json.load(file)
        
        # Check if we have valid API keys (not placeholder values)
        valid_apis = []
        for api_name in ['claude', 'openai', 'gemini']:
            api_config = config.get(api_name, {})
            api_key = api_config.get('api_key', '')
            if api_key and api_key != f'YOUR_{api_name.upper()}_API_KEY_HERE':
                valid_apis.append(api_name)
        
        if not valid_apis:
            # Return intelligent fallback response based on user input
            message_lower = user_message.lower()
            if any(word in message_lower for word in ['hi', 'hello', 'hey', 'greetings']):
                return "Hello! I'm NestBot, your AI assistant for the repair shop. While my AI services are currently unavailable, I can still help you navigate the system. What would you like to do?"
            elif any(word in message_lower for word in ['ticket', 'repair', 'status']):
                return "I'd love to help you with ticket information! While my AI analysis is temporarily unavailable, you can view detailed ticket information in the main dashboard. Is there a specific ticket number you're looking for?"
            elif any(word in message_lower for word in ['help', 'support', 'how']):
                return "I'm here to help! Although my AI capabilities are currently limited, you can:\n\n• View tickets in the Dashboard\n• Check customer information\n• Access PC and Mobile tools\n• Generate reports\n\nWhat specific task would you like assistance with?"
            else:
                return "I apologize, but my AI services are currently unavailable due to missing API configuration. However, I'm still here to help guide you through the Nest application. Please check with your administrator about setting up AI API keys!"
    
    except Exception as e:
        logging.error(f"Error checking API configuration: {str(e)}")
        return "Hello! I'm NestBot. My AI services are temporarily unavailable, but I can still help you navigate the repair shop system. What would you like to do?"
    
    try:
        # Load config first to check API keys
        try:
            from nest.utils.platform_paths import PlatformPaths
            platform_paths = PlatformPaths()
            config_path = platform_paths.get_config_dir() / 'config.json'
            with open(str(config_path), 'r') as file:
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


def _call_claude_api(user_message: str, model_name: str, config: Dict, 
                     ticket_data: Optional[List] = None, processed_tickets: Optional[List] = None,
                     specific_ticket: Optional[str] = None, custom_knowledge_path: Optional[str] = None,
                     current_user: Optional[Dict] = None) -> str:
    """
    Call the Claude API with the user message and any additional context.
    """
    # Get API key from config
    api_key = config.get("claude", {}).get("api_key")
    if not api_key:
        raise ValueError("Claude API key not found in config file")
    
    # Use the model from config
    model = config.get("claude", {}).get("model", "claude-3-haiku-20240307")
    
    # Log the model we're using
    logging.info(f"Using Claude model: {model}")
    
    # Claude API endpoint
    api_url = "https://api.anthropic.com/v1/messages"
    
    # Start building the system message
    system_text = "You are NestBot, an AI assistant for a computer repair shop."
    
    # Add user's first name for personalization if available
    if current_user:
        full_name = current_user.get("name", "")
        # Extract first name (everything before the first space)
        first_name = full_name.split()[0] if full_name and " " in full_name else full_name
        if first_name:
            system_text += f" The user's first name is {first_name}. DO NOT use their last name."
    
    # Add ticket data if available
    if ticket_data and processed_tickets:
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
    
    # Set up the API request data
    data = {
        "model": model,
        "max_tokens": 1024,
        "temperature": 0.7,
        "system": system_text,
        "messages": [
            {
                "role": "user",
                "content": user_message
            }
        ]
    }
    
    # Set up headers
    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01"
    }
    
    # Log request summary
    logging.debug(f"Making Claude API request with model: {model}")
    
    # Make the API request
    response = requests.post(
        api_url,
        json=data,
        headers=headers
    )
    
    # Process the response
    if response.status_code == 200:
        response_json = response.json()
        logging.info(f"Claude API response successful. Model: {model}")
        try:
            # Extract the response text from the Claude API structure
            return response_json["content"][0]["text"]
        except (KeyError, IndexError) as e:
            logging.error(f"Error parsing Claude API response: {e}")
            return "I encountered an error while processing the API response."
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
    """
    # Get API key from config
    api_key = config.get("openai", {}).get("api_key")
    if not api_key:
        raise ValueError("OpenAI API key not found in config file")
    
    # Use the model from config
    model = config.get("openai", {}).get("model", "gpt-3.5-turbo")
    
    # Log the model we're using
    logging.info(f"Using OpenAI model: {model}")
    
    # OpenAI API endpoint
    api_url = "https://api.openai.com/v1/chat/completions"
    
    # Start building the system message
    system_text = "You are NestBot, an AI assistant for a computer repair shop."
    
    # Add user's first name for personalization if available
    if current_user:
        full_name = current_user.get("name", "")
        # Extract first name (everything before the first space)
        first_name = full_name.split()[0] if full_name and " " in full_name else full_name
        if first_name:
            system_text += f" The user's first name is {first_name}. DO NOT use their last name."
    
    # Add ticket data if available
    if ticket_data and processed_tickets:
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
    
    # Set up the API request data
    data = {
        "model": model,
        "max_tokens": 1024,
        "temperature": 0.7,
        "messages": [
            {
                "role": "system",
                "content": system_text
            },
            {
                "role": "user",
                "content": user_message
            }
        ]
    }
    
    # Set up headers
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    # Log request summary
    logging.debug(f"Making OpenAI API request with model: {model}")
    
    # Make the API request
    response = requests.post(
        api_url,
        json=data,
        headers=headers
    )
    
    # Process the response
    if response.status_code == 200:
        response_json = response.json()
        logging.info(f"OpenAI API response successful. Model: {model}")
        try:
            # Extract the response text from the OpenAI API structure
            return response_json["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as e:
            logging.error(f"Error parsing OpenAI API response: {e}")
            return "I encountered an error while processing the API response."
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
    """
    # Get API key from config
    api_key = config.get("gemini", {}).get("api_key")
    if not api_key:
        raise ValueError("Gemini API key not found in config file")
    
    # Use the model from config
    model = config.get("gemini", {}).get("model", "gemini-1.5-pro")
    
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
        full_name = current_user.get("name", "")
        # Extract first name (everything before the first space)
        first_name = full_name.split()[0] if full_name and " " in full_name else full_name
        if first_name:
            system_text += f" The user's first name is {first_name}. DO NOT use their last name."
    
    # Add ticket data if available
    if ticket_data and processed_tickets:
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
