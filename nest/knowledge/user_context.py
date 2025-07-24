# Module to generate and update user context knowledge file
import json
import os
import logging
import datetime

# Auto-generate the file when this module is imported
_AUTO_GENERATE = True

def generate_user_knowledge_files():
    """Generate or update both user knowledge JSON files based on current login info:
    1. user_context.json - with ticket instructions
    2. user_context_general.json - without ticket instructions for general queries
    """
    try:
        # Get the main config file path
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'config.json')
        knowledge_path = os.path.join(os.path.dirname(__file__), 'user_context.json')
        knowledge_path_general = os.path.join(os.path.dirname(__file__), 'user_context_general.json')
        
        # Load current config
        with open(config_path, 'r') as file:
            config = json.load(file)
        
        # Extract relevant information
        store_slug = config.get("store_slug", "eliterepairs")
        current_user = config.get("current_user", {"name": "Unknown", "role": "User"})
        
        # Extract business information from config
        # Try to get from several possible config locations without hardcoding
        store_info = {}
        
        # Look for business details in various possible config locations
        if "business" in config:
            store_info = config.get("business", {})
        elif "business_info" in config:
            store_info = config.get("business_info", {})
        elif "store_info" in config:
            store_info = config.get("store_info", {})
        elif "company" in config:
            store_info = config.get("company", {})
            
        # Get business name directly from config
        business_name = config.get("store_name", "")
        # Fallback if store_name is not available
        if not business_name:
            business_name = store_info.get("name", "")
            if not business_name:
                # Try to create a reasonable business name from the slug
                words = store_slug.replace("_", " ").replace("-", " ").split()
                business_name = " ".join(word.capitalize() for word in words)
        
        # Get any additional business details from config
        business_type = store_info.get("type", "")
        business_specialty = store_info.get("specialty", "")
        
        # If no explicit type provided, guess based on slug
        if not business_type:
            # Try to detect business type from slug
            if any(tech_term in store_slug.lower() for tech_term in ["tech", "computer", "electronics", "repair", "phone", "cell"]):
                business_type = "Technology Services"
            elif any(bike_term in store_slug.lower() for bike_term in ["bike", "cycle", "wheel"]):
                business_type = "Bicycle Services"
            elif any(jewelry_term in store_slug.lower() for jewelry_term in ["jewel", "watch", "craft"]):
                business_type = "Jewelry Services"
            else:
                business_type = "Service Provider"
        
        # Build common user knowledge object with the base information
        user_knowledge_base = {
            "business": {
                "name": business_name,
                "slug": store_slug,
                "type": business_type,
                "specialty": business_specialty or "Customer service and repair"
            },
            "user": {
                "name": current_user.get("name", "Unknown"),
                "role": current_user.get("role", "Staff"),
                "id": current_user.get("id", "0"),
                "last_login": current_user.get("last_login", "")
            },
            "personalization": {
                "business_reference": "our shop",
                "tone": "friendly and helpful",
                "response_style": "direct and conversational",
                "ai_instructions": "IMPORTANT INSTRUCTIONS: DO NOT use last name in responses. DO NOT begin every response with greetings like 'Hello' or 'Hi' followed by name, only the first response. Respond directly to questions without these formalities after that."
            }
        }
        
        # Create a copy for the full version with ticket details
        user_knowledge_full = user_knowledge_base.copy()
        user_knowledge_full["ticket_details"] = {
            "instructions": "VERY IMPORTANT INSTRUCTIONS: When asked about notes, comments, updates, or information about a specific ticket, you MUST refer to and summarize any notes found in the ticket data. Even if the notes are diagnostic reports or system information, they ARE still notes/comments on the ticket and should be mentioned. Any content in the 'msg_text' field IS a note/comment. Do NOT say there are no notes or comments if there are any present in the data. Pay special attention to the 'notes' arrays in both the processed data AND raw data sections."
        }
        
        # Create a copy for the general version with capabilities info instead of ticket details
        user_knowledge_general = user_knowledge_base.copy()
        #user_knowledge_general["capabilities"] = {
            #"general": "I'm NestBot, your AI assistant. I can answer questions about your repair shop, provide information about Eliterepairs, and help with general inquiries. When ticket access is enabled, I can also look up information about specific repair tickets including customer details, notes, and status updates."
        #}
        
        # Save both knowledge files
        with open(knowledge_path, 'w') as file:
            json.dump(user_knowledge_full, file, indent=2)
            
        with open(knowledge_path_general, 'w') as file:
            json.dump(user_knowledge_general, file, indent=2)
            
        logging.info(f"Updated user context knowledge files for {current_user.get('name', 'Unknown')}")
        return knowledge_path
        
    except Exception as e:
        logging.error(f"Error generating user knowledge file: {str(e)}")
        return None
        
# Backward compatibility function
def generate_user_knowledge_file():
    """Legacy function for backward compatibility.
    
    Returns:
        str: Path to the generated knowledge file
    """
    try:
        knowledge_path = generate_user_knowledge_files()
        return knowledge_path[0] if isinstance(knowledge_path, (list, tuple)) else knowledge_path
    except Exception as e:
        logging.error(f"Error generating user knowledge file: {str(e)}")
        return None

# Auto-generate the knowledge files when this module is imported
if _AUTO_GENERATE:
    try:
        knowledge_path = generate_user_knowledge_files()
        if knowledge_path:
            logging.info(f"Auto-generated user context knowledge file at {knowledge_path}")
    except Exception as e:
        logging.error(f"Failed to auto-generate user context knowledge file: {str(e)}")
