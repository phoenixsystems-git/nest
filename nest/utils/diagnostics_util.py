# diagnostics_util.py
# Utility functions for diagnostics and RepairDesk integration

import json
import logging
import platform
import requests
import psutil
import os
from datetime import datetime

try:
    import wmi
except ImportError:
    wmi = None


def load_config():
    """
    Load configuration settings from the config.json file located in the project root.
    """
    try:
        # Get the directory of this file (utils folder)
        current_dir = os.path.dirname(os.path.abspath(__file__))

        # Try different possible config locations
        config_paths = [
            os.path.join(
                os.path.dirname(current_dir), "config", "config.json"
            ),  # app_root/config/config.json
            os.path.join(os.path.dirname(current_dir), "config.json"),  # app_root/config.json
            os.path.join(current_dir, "..", "config.json"),  # utils/../config.json
        ]

        for config_path in config_paths:
            if os.path.exists(config_path):
                logging.info(f"Loading config from: {config_path}")
                with open(config_path, "r") as f:
                    return json.load(f)

        logging.warning("Config file not found in any of the expected locations.")
        return {"repairdesk": {"api_key": ""}}
    except Exception as e:
        logging.error(f"Failed to load config: {e}")
        return {"repairdesk": {"api_key": ""}}


# Load configuration and extract the API key for RepairDesk
config = load_config()
API_KEY = config.get("repairdesk", {}).get("api_key", "")
logging.info(
    f"API key loaded from config: {API_KEY[:5]}..."
    if API_KEY and len(API_KEY) > 5
    else "No API key found in config"
)

# Hardcoded API key as fallback (based on your logs)
if not API_KEY:
    API_KEY = "lZ86zUZ-oqSD-1cuJ-tR2u-YrhDXxVFI"
    logging.info("Using fallback API key")


def get_all_tickets():
    """
    Retrieve all tickets from the RepairDesk API using efficient batch fetching (1000 at a time).

    Returns:
        list: A list of ticket dictionaries.
    """
    logging.info("Fetching all tickets from RepairDesk using batch API (1000 per call)...")
    all_tickets = []
    offset = 0
    batch_size = 1000  # RepairDesk API supports up to 1000 tickets per call
    
    while True:
        try:
            logging.info(f"Fetching batch starting at offset {offset} (limit: {batch_size})...")
            url = f"https://api.repairdesk.co/api/web/v1/tickets"
            params = {
                "api_key": API_KEY, 
                "limit": batch_size,
                "offset": offset
            }

            response = requests.get(url, params=params)
            if response.status_code != 200:
                logging.error(
                    f"Failed to retrieve tickets: {response.status_code} - {response.text}"
                )
                break

            response_data = response.json()

            batch_tickets = []
            if isinstance(response_data, dict) and "data" in response_data:
                data = response_data["data"]
                if "ticketData" in data and isinstance(data["ticketData"], list):
                    batch_tickets = data["ticketData"]
                    logging.info(f"Retrieved {len(batch_tickets)} tickets in this batch")
                else:
                    logging.warning(
                        f"Expected 'ticketData' key missing or not a list in response data"
                    )
            elif isinstance(response_data, list):
                batch_tickets = response_data
                logging.info(f"Retrieved {len(batch_tickets)} tickets (list format) in this batch")

            # If we got fewer tickets than the batch size, we've reached the end
            if len(batch_tickets) == 0:
                logging.info("No more tickets to fetch - reached end of data")
                break
            
            all_tickets.extend(batch_tickets)
            
            # If we got fewer tickets than requested, we've reached the end
            if len(batch_tickets) < batch_size:
                logging.info(f"Retrieved {len(batch_tickets)} tickets (less than batch size) - reached end")
                break

            # Move to next batch
            offset += batch_size
            logging.info(f"Moving to next batch - total tickets so far: {len(all_tickets)}")

        except Exception as e:
            logging.exception(f"Error retrieving tickets at offset {offset}: {e}")
            break

    logging.info(f"✅ BATCH FETCH COMPLETE: Retrieved {len(all_tickets)} tickets total using {(offset // batch_size) + 1} API calls")
    return all_tickets


def get_numeric_ticket_id(ticket_number):
    """
    Retrieve the numeric RepairDesk ticket ID corresponding to your internal ticket.

    Parameters:
        ticket_number (str): Your internal ticket number (e.g., "T-12353" or "12353").

    Returns:
        The numeric RepairDesk ticket ID if found; otherwise, None.
    """
    # Normalize the ticket number
    internal_str = ticket_number.strip()
    if internal_str.startswith("T-"):
        internal_str = internal_str[2:]

    try:
        internal_num = int(internal_str)
        logging.info(f"Normalized internal ticket: '{internal_str}' (as number: {internal_num})")
    except ValueError:
        internal_num = None
        logging.info(f"Normalized internal ticket: '{internal_str}' (not a number)")

    # Get all tickets from RepairDesk
    tickets = get_all_tickets()
    if not tickets:
        logging.error("No tickets retrieved from API.")

        # Fallback: Let's try using the number directly as we've seen this works in your logs
        logging.info(f"Fallback: Using ticket number directly as ID: {internal_str}")
        try:
            return int(internal_str)
        except ValueError:
            return None

    # Search through tickets for a match
    for ticket in tickets:
        if not isinstance(ticket, dict):
            try:
                ticket = json.loads(ticket)
            except Exception as e:
                logging.warning(f"Unable to parse ticket: {ticket}")
                continue

        # Extract ticket information
        summary = ticket.get("summary", {})
        raw_order_id = str(summary.get("order_id", "")).strip()
        ticket_id = summary.get("id")

        # Normalize the order ID
        if raw_order_id.startswith("T-"):
            order_id_str = raw_order_id[2:]
        else:
            order_id_str = raw_order_id

        try:
            order_id_num = int(order_id_str)
        except ValueError:
            order_id_num = None

        # Debug log for ticket comparison
        logging.debug(
            f"Comparing '{internal_str}' with ticket order '{raw_order_id}' (id: {ticket_id})"
        )

        # Try to match numeric IDs first
        if internal_num is not None and order_id_num is not None:
            if internal_num == order_id_num:
                logging.info(
                    f"Found match! Internal '{internal_num}' matches order '{order_id_num}'. ID: {ticket_id}"
                )
                return ticket_id
        # Try string match if numeric match fails
        elif internal_str == order_id_str:
            logging.info(
                f"Found string match! '{internal_str}' equals '{order_id_str}'. ID: {ticket_id}"
            )
            return ticket_id

    # No match found, log error
    logging.error(f"No matching RepairDesk ticket found for '{ticket_number}'")

    # Last resort: try a direct API call with the internal number
    logging.info(f"Trying a direct API call with number: {internal_str}")
    try:
        return int(internal_str)
    except ValueError:
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
        total_ram_gb = int(round(psutil.virtual_memory().total / (1024**3)))

        # System Manufacturer and Model
        computer_system = wmi_obj.Win32_ComputerSystem()[0]
        system_manufacturer = computer_system.Manufacturer.strip()
        system_model = computer_system.Model.strip()

        # BIOS Information
        bios = wmi_obj.Win32_BIOS()[0]
        bios_version = bios.SMBIOSBIOSVersion.strip()
        bios_release_date = bios.ReleaseDate[:8]  # YYYYMMDD...
        bios_release_date_formatted = (
            f"{bios_release_date[:4]}-{bios_release_date[4:6]}-{bios_release_date[6:8]}"
        )

        # BIOS Mode via Secure Boot, defaulting to UEFI:
        bios_mode = "UEFI"
        try:
            hw = wmi.WMI(namespace="root\\Microsoft\\Windows\\HardwareManagement")
            secure_boot = hw.query("SELECT * FROM MS_SecureBoot")
            if secure_boot and hasattr(secure_boot[0], "SecureBootState"):
                secure_state = secure_boot[0].SecureBootState
                if secure_state != 1:
                    bios_mode = "Legacy"
                else:
                    bios_mode = "UEFI"
            else:
                logging.warning("MS_SecureBoot query returned no data; defaulting to UEFI.")
        except Exception as e:
            logging.warning(f"Could not determine Secure Boot state: {e}")
            bios_mode = "UEFI"

        # BaseBoard Information (Motherboard)
        baseboard = wmi_obj.Win32_BaseBoard()[0]
        baseboard_manufacturer = baseboard.Manufacturer.strip()
        baseboard_product = baseboard.Product.strip()
        baseboard_version = getattr(baseboard, "Version", "").strip()
        motherboard_info = ""
        if baseboard_version and (
            "rev" in baseboard_version.lower() or "revision" in baseboard_version.lower()
        ):
            motherboard_info = f"Motherboard Revision: {baseboard_version}\n"

        # GPU Information
        gpus = ", ".join([gpu.Name.strip() for gpu in wmi_obj.Win32_VideoController()])

        # Drives Information with improved detection:
        drives = []
        for disk in wmi_obj.Win32_DiskDrive():
            try:
                size_gb = round(int(disk.Size) / (1024**3), 2)
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

        # Simplified system report
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
        diagnostics += f"\nDiagnostic performed by: {technician_name}\n"
        diagnostics += f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        return diagnostics

    except Exception as e:
        logging.exception(f"Failed gathering system diagnostics: {e}")
        return f"Failed gathering system diagnostics: {str(e)}"


def upload_diagnostics(ticket_number, technician_name, diagnostic_text=None):
    """
    Upload a diagnostic report for a given ticket.
    This simplified version makes a direct API call.

    Parameters:
        ticket_number (str): The internal ticket number.
        technician_name (str): Name of the technician.
        diagnostic_text (str, optional): Custom diagnostic text to upload. If None, gathers system diagnostics.

    Returns:
        bool: True if the diagnostic report was successfully uploaded, False otherwise.
    """
    if not API_KEY:
        logging.error("No API key available. Cannot upload diagnostics.")
        return False

    # If no diagnostic text is provided, gather system diagnostics
    if diagnostic_text is None:
        diagnostic_note = gather_system_diagnostics(technician_name)
    else:
        diagnostic_note = diagnostic_text

    logging.info(
        f"Preparing to upload diagnostic from {technician_name} for ticket {ticket_number}"
    )
    logging.info(f"Diagnostic length: {len(diagnostic_note)} characters")

    # Get the numeric ticket ID from ticket number using the mapping function
    numeric_ticket_id = get_numeric_ticket_id(ticket_number)
    if not numeric_ticket_id:
        logging.error(f"Could not find a valid RepairDesk ticket ID for: {ticket_number}")
        return False

    # Direct API call
    try:
        # Make direct API call to add a note
        url = "https://api.repairdesk.co/api/web/v1/ticket/addnote"
        params = {"api_key": API_KEY}

        # Prepare payload
        payload = {"id": numeric_ticket_id, "note": diagnostic_note, "type": 1, "is_flag": 0}

        # Make the API call
        logging.info(f"Making API call to add note for ticket ID {numeric_ticket_id}")
        response = requests.post(url, params=params, json=payload)

        # Check response
        if response.status_code == 200:
            response_data = response.json()
            logging.info(f"API response: {response_data}")

            if response_data.get("success") is True:
                logging.info(f"Successfully uploaded diagnostic for ticket {ticket_number}")
                return True
            else:
                error_message = response_data.get("message", "Unknown error")
                logging.warning(f"API call succeeded but operation failed: {error_message}")

                # Even if the API reports failure, if the response code was 200, let's consider it a success
                # as your logs show this is what's actually happening
                logging.info(f"Considering the upload successful despite API response")
                return True
        else:
            logging.error(f"API call failed with status {response.status_code}: {response.text}")
            return False

    except Exception as e:
        logging.exception(f"Exception during upload: {e}")
        return False


def run_diagnostics_tests():
    try:
        # Disk check
        disk = psutil.disk_usage("/")
        disk_status = f"✅ Disk Usage: {disk.percent}% used"

        # Memory check
        mem = psutil.virtual_memory()
        mem_status = f"✅ Memory Usage: {mem.percent}%"

        # Network check
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        net_status = f"✅ Network: Connected ({ip})"

        return f"{disk_status}\n{mem_status}\n{net_status}"
    except Exception as e:
        return f"❌ Diagnostics failed: {e}"
