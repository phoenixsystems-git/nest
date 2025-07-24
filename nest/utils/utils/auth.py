import requests
import os
import json
from utils.config_util import load_config
import logging


# Load configuration
def load_config():
    config_path = os.path.join(os.path.dirname(__file__), "config", "config.json")
    with open(config_path, "r") as config_file:
        return json.load(config_file)


CONFIG = load_config()
EMPLOYEES_API_URL = "https://api.repairdesk.co/api/web/v1/employees"


def authenticate():
    api_key = CONFIG.get("repairdesk_api_key") or CONFIG.get("repairdesk", {}).get("api_key")
    if not api_key:
        logging.error("No RepairDesk API key found in configuration")
        return None
    response = requests.get(f"{EMPLOYEES_API_URL}?api_key={api_key}", timeout=10)
    return response.json()
