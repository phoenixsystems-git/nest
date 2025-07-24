import requests
import os
import json
from utils.config_util import load_config
import logging


# Load configuration using centralized system
def load_config():
    from nest.utils.config import load_config as main_load_config
    return main_load_config()


CONFIG = load_config()
EMPLOYEES_API_URL = "https://api.repairdesk.co/api/web/v1/employees"


def authenticate():
    api_key = CONFIG.get("repairdesk_api_key") or CONFIG.get("repairdesk", {}).get("api_key")
    if not api_key:
        logging.error("No RepairDesk API key found in configuration")
        return None
    response = requests.get(f"{EMPLOYEES_API_URL}?api_key={api_key}", timeout=10)
    return response.json()
