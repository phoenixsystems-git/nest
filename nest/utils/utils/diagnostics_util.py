import json
import logging
import platform
import requests
import psutil
import math
import os
import webbrowser

try:
    import wmi
except ImportError:
    wmi = None

def load_config():
    """
    Load configuration settings from the config.json file located in the project root.
    """
    # Get the directory of this file (utils folder)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # Assuming project root is one level up:
config_path = os.path.join(os.path.dirname(__file__), 'config', 'config.json')
    with open(config_path, "r") as f:
        return json.load(f)

# Load configuration and extract the API key for RepairDesk.
config = load_config()
API_KEY = config.get("repairdesk", {}).get("api_key", "")

# Import your custom RepairDesk client (ensure this file exists at nest/utils/api_client.py)
from nest.utils.api_client import RepairDeskClient


def get_all_tickets():
    """
    Retrieve all tickets from the RepairDesk API using pagination.
    
    Returns:
        list: A list of ticket dictionaries.
    """
    client = RepairDeskClient(api_key=API_KEY)
    all_tickets = []
    page = 1

    while True:
        try:
            response = client.get_tickets(page=page)
        except Exception as e:
            logging.exception("Failed to retrieve tickets on page %d: %s", page, e)
            break

        page_tickets = []
        if isinstance(response, dict) and "data" in response:
            data = response["data"]
            if "ticketData" in data and isinstance(data["ticketData"], list):
                page_tickets = data["ticketData"]
            else:
                logging.warning("Expected 'ticketData' key missing or not a list in response data: %s", data)
        elif isinstance(response, list):
            page_tickets = response
        else:
            logging.warning("Unexpected response structure: %s", response)

        parsed_tickets = []
        for t in page_tickets:
            if isinstance(t, dict):
                parsed_tickets.append(t)
            elif isinstance(t, str):
                try:
                    t_dict = json.loads(t)
                    parsed_tickets.append(t_dict)
                except Exception as parse_err:
                    logging.warning("Failed to parse ticket string '%s': %s", t, parse_err)
            else:
                logging.warning("Unexpected ticket type: %s", type(t))
        all_tickets.extend(parsed_tickets)

        total_pages = 1
        if isinstance(response, dict) and "data" in response:
            pagination = response["data"].get("pagination", {})
            try:
                total_pages = int(pagination.get("total_pages", 1))
            except (ValueError, TypeError):
                logging.warning("Invalid total_pages in pagination: %s", pagination.get("total_pages"))
        if page >= total_pages:
            break
        page += 1

    logging.debug("Total tickets retrieved (all pages): %d", len(all_tickets))
    return all_tickets


def get_numeric_ticket_id(ticket_number):
    """
    Retrieve the numeric RepairDesk ticket ID corresponding to your internal ticket.
    
    Parameters:
        ticket_number (str): Your internal ticket number (e.g., "T-12353" or "12353").
    
    Returns:
        The numeric RepairDesk ticket ID if found; otherwise, None.
    """
    internal_str = ticket_number.strip()
    if internal_str.startswith("T-"):
        internal_str = internal_str[2:]
    try:
        internal_num = int(internal_str)
    except ValueError:
        internal_num = None
    logging.debug("Normalized internal ticket: '%s' (as number: %s)", internal_str, internal_num)

    tickets = get_all_tickets()
    if not tickets:
        logging.error("No tickets retrieved from API.")
        return None

    for ticket in tickets:
        if not isinstance(ticket, dict):
            try:
                ticket = json.loads(ticket)
            except Exception as e:
                logging.warning("Unable to parse ticket: %s", ticket)
                continue

        summary = ticket.get("summary", {})
        raw_order_id = str(summary.get("order_id", "")).strip()
        if raw_order_id.startswith("T-"):
            order_id_str = raw_order_id[2:]
        else:
            order_id_str = raw_order_id
        try:
            order_id_num = int(order_id_str)
        except ValueError:
            order_id_num = None

        logging.debug("Comparing internal '%s' (num: %s) with ticket order '%s' (num: %s, ticket id: %s)",
                      internal_str, internal_num, raw_order_id, order_id_num, summary.get("id"))
        if internal_num is not None and order_id_num is not None:
            if internal_num == order_id_num:
                logging.info("Numeric match found: internal %s matches ticket order %s", internal_num, order_id_num)
                return summary.get("id")
        else:
            if internal_str == order_id_str:
                logging.info("String match found: '%s' equals '%s'", internal_str, order_id_str)
                return summary.get("id")
    logging.error("No matching RepairDesk ticket found for internal ticket: %s", ticket_number)
    return None


def gather_system_diagnostics(technician_name):
    """
    Gather PC hardware specifications and build a diagnostic report.
    
    Parameters:
        technician_name (str): Name of the technician.
    
    Returns:
        str: A formatted diagnostic report.
    """
    try:
        if wmi is None:
            logging.error("WMI module is not available.")
            return "WMI module not available. Diagnostics not collected."
        wmi_obj = wmi.WMI()

        # OS Info
        os_info = f"{platform.system()} {platform.release()} ({platform.version()})"

        # CPU Info
        cpu_info = wmi_obj.Win32_Processor()[0].Name.strip()

        # RAM (in GB)
        total_ram_gb = int(round(psutil.virtual_memory().total / (1024 ** 3)))

        # System Manufacturer and Model
        computer_system = wmi_obj.Win32_ComputerSystem()[0]
        system_manufacturer = computer_system.Manufacturer.strip()
        system_model = computer_system.Model.strip()

        # Manufacturer & Product Info (moved to top)
        manufacturer_info = f"Manufacturer: {system_manufacturer}\n"
        product_info = f"Product: {system_model}\n"

        # BIOS Information
        bios = wmi_obj.Win32_BIOS()[0]
        bios_version = bios.SMBIOSBIOSVersion.strip()
        bios_release_date = bios.ReleaseDate[:8]  # YYYYMMDD...
        bios_release_date_formatted = f"{bios_release_date[:4]}-{bios_release_date[4:6]}-{bios_release_date[6:8]}"

        # BIOS Mode via Secure Boot, defaulting to UEFI:
        bios_mode = "UEFI"
        try:
            hw = wmi.WMI(namespace="root\\Microsoft\\Windows\\HardwareManagement")
            secure_boot = hw.query("SELECT * FROM MS_SecureBoot")
            if secure_boot and hasattr(secure_boot[0], 'SecureBootState'):
                secure_state = secure_boot[0].SecureBootState
                if secure_state != 1:
                    bios_mode = "Legacy"
                else:
                    bios_mode = "UEFI"
            else:
                logging.warning("MS_SecureBoot query returned no data; defaulting to UEFI.")
        except Exception as e:
            logging.warning("Could not determine Secure Boot state: %s", e)
            bios_mode = "UEFI"

        bios_info = (
            f"BIOS Version/Date: {bios_version}, {bios_release_date_formatted}\n"
            f"BIOS Mode: {bios_mode}\n"
        )

        # BaseBoard Information (Motherboard)
        baseboard = wmi_obj.Win32_BaseBoard()[0]
        baseboard_manufacturer = baseboard.Manufacturer.strip()
        baseboard_product = baseboard.Product.strip()
        baseboard_version = getattr(baseboard, "Version", "").strip()
        motherboard_info = ""
        if baseboard_version and ("rev" in baseboard_version.lower() or "revision" in baseboard_version.lower()):
            motherboard_info = f"Motherboard Revision: {baseboard_version}\n"

        # GPU Information
        gpus = ", ".join([gpu.Name.strip() for gpu in wmi_obj.Win32_VideoController()])

        # Drives Information with improved detection:
        drives = []
        for disk in wmi_obj.Win32_DiskDrive():
            try:
                size_gb = round(int(disk.Size) / (1024 ** 3), 2)
            except Exception:
                size_gb = "Unknown"
            disk_model = disk.Model.strip() if disk.Model else "Unknown Model"
            drive_type = ""
            # Check MediaType property first.
            if hasattr(disk, "MediaType") and disk.MediaType:
                media_type = disk.MediaType.strip().upper()
                if media_type in ["SSD", "HDD"]:
                    drive_type = media_type
            # Fallback: if MediaType isn't informative, use heuristics.
            if not drive_type:
                model_upper = disk_model.upper()
                if "SSD" in model_upper:
                    drive_type = "SSD"
                else:
                    drive_type = "HDD"
            # Final override: if drive_type is HDD but model shows both "SATA" and "SSD", mark as SSD.
            if drive_type == "HDD" and "SATA" in disk_model.upper() and "SSD" in disk_model.upper():
                drive_type = "SSD"
            drives.append(f"{disk_model} [{size_gb} GB] ({drive_type})")

        diagnostics = ""
        diagnostics += "Elite Repairs - System Diagnostic Report\n\n"
        diagnostics += f"Manufacturer: {system_manufacturer}\n"
        diagnostics += f"Product: {system_model}\n"
        diagnostics += f"BaseBoard Manufacturer: {baseboard_manufacturer}\n"
        diagnostics += f"BaseBoard Product: {baseboard_product}\n"
        diagnostics += f"BIOS Version/Date: {bios_version}, {bios_release_date_formatted}\n"
        diagnostics += f"BIOS Mode: {bios_mode}\n"
        diagnostics += f"OS: {os_info}\n"
        diagnostics += f"CPU: {cpu_info}\n"
        diagnostics += f"RAM: {total_ram_gb} GB\n"
        diagnostics += f"GPU: {gpus}\n\n"
        diagnostics += "Drives:\n" + "\n".join(drives) + "\n"
        diagnostics += motherboard_info
        return diagnostics

    except Exception as e:
        logging.exception("Failed gathering system diagnostics: %s", e)
        return "Failed gathering system diagnostics."


def upload_diagnostics(ticket_number, technician_name):
    """
    Upload a diagnostic report for a given ticket.
    
    Parameters:
        ticket_number (str): The internal ticket number.
        technician_name (str): Name of the technician.
        
    Returns:
        bool: True if the diagnostic report was successfully uploaded, False otherwise.
    """
    numeric_ticket_id = get_numeric_ticket_id(ticket_number)
    if not numeric_ticket_id:
        logging.error("Could not find numeric ticket ID for %s.", ticket_number)
        return False

    diagnostic_note = gather_system_diagnostics(technician_name)
    url = f"https://api.repairdesk.co/api/web/v1/ticket/addnote?api_key={API_KEY}"
    payload = {
        "id": numeric_ticket_id,
        "note": diagnostic_note,
        "type": 1,
        "is_flag": 0
    }
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            logging.info("Diagnostic report uploaded successfully for ticket %s", ticket_number)
            return True
        else:
            logging.error("Upload failed for ticket %s: status %s, response: %s", 
                          ticket_number, response.status_code, response.text)
            return False
    except Exception as e:
        logging.exception("Exception during diagnostics upload: %s", e)
        return False


def open_product_page(system_manufacturer, system_model):
    """
    Automatically open the first result from a Google search for drivers and BIOS updates
    for the given product. If the extraction of the first result fails, open the general search page.
    
    Parameters:
        system_manufacturer (str): The manufacturer of the system.
        system_model (str): The model of the system.
    """
    query = f"{system_manufacturer} {system_model} drivers bios updates"
    query_formatted = query.replace(" ", "+")
    search_url = f"https://www.google.com/search?q={query_formatted}"
    
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/90.0.4430.93 Safari/537.36"
        )
    }
    
    try:
        response = requests.get(search_url, headers=headers, timeout=5)
        if response.status_code == 200:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, "html.parser")
            # Attempt selector "div.yuRUbf > a"
            result_links = soup.select("div.yuRUbf > a")
            if not result_links:
                # Fallback: try alternative selector "div.g a"
                logging.debug("Primary selector failed, trying 'div.g a'")
                result_links = soup.select("div.g a")
            if result_links:
                first_result = result_links[0].get("href")
                if first_result:
                    webbrowser.open(first_result)
                    logging.info("Automatically opened the first search result: %s", first_result)
                    return
                else:
                    logging.warning("Found a result container but no href attribute.")
            else:
                logging.warning("No search results found with available selectors.")
        else:
            logging.error("Google search failed with status code: %s", response.status_code)
    except Exception as e:
        logging.error("Exception during Google search: %s", e)
    
    # Fallback: open the general search page if automatic extraction fails.
    webbrowser.open(search_url)
    logging.info("Opened the general search page instead: %s", search_url)


def get_numeric_ticket_id(ticket_number):
    """
    Retrieve the numeric RepairDesk ticket ID corresponding to your internal ticket.
    
    Parameters:
        ticket_number (str): Your internal ticket number (e.g., "T-12353" or "12353").
    
    Returns:
        The numeric RepairDesk ticket ID if found; otherwise, None.
    """
    internal_str = ticket_number.strip()
    if internal_str.startswith("T-"):
        internal_str = internal_str[2:]
    try:
        internal_num = int(internal_str)
    except ValueError:
        internal_num = None
    logging.debug("Normalized internal ticket: '%s' (as number: %s)", internal_str, internal_num)

    tickets = get_all_tickets()
    if not tickets:
        logging.error("No tickets retrieved from API.")
        return None

    for ticket in tickets:
        if not isinstance(ticket, dict):
            try:
                ticket = json.loads(ticket)
            except Exception as e:
                logging.warning("Unable to parse ticket: %s", ticket)
                continue

        summary = ticket.get("summary", {})
        raw_order_id = str(summary.get("order_id", "")).strip()
        if raw_order_id.startswith("T-"):
            order_id_str = raw_order_id[2:]
        else:
            order_id_str = raw_order_id
        try:
            order_id_num = int(order_id_str)
        except ValueError:
            order_id_num = None

        logging.debug("Comparing internal '%s' (num: %s) with ticket order '%s' (num: %s, ticket id: %s)",
                      internal_str, internal_num, raw_order_id, order_id_num, summary.get("id"))
        if internal_num is not None and order_id_num is not None:
            if internal_num == order_id_num:
                logging.info("Numeric match found: internal %s matches ticket order %s", internal_num, order_id_num)
                return summary.get("id")
        else:
            if internal_str == order_id_str:
                logging.info("String match found: '%s' equals '%s'", internal_str, order_id_str)
                return summary.get("id")
    logging.error("No matching RepairDesk ticket found for internal ticket: %s", ticket_number)
    return None
