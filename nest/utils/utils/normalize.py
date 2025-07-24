import datetime
from utils.logger import log_message


def ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def format_date(timestamp: float) -> str:
    dt = datetime.datetime.fromtimestamp(timestamp)
    month = dt.strftime("%B")
    day = ordinal(dt.day)
    year = dt.strftime("%Y")
    return f"{month} {day}, {year}"


def format_timestamp(ts) -> str:
    if ts is None:
        return "N/A"
    try:
        return format_date(float(ts))
    except Exception:
        return "N/A"


def map_job_status(raw_status: str) -> str:
    mapping = {
        "Open": "Open",
        "In Progress": "In Progress",
        "Repaired": "Repaired",
        "Waiting For Parts": "Waiting For Parts",
        "Pending recycle": "Pending Recycle",
        "B2B Outsourced": "B2B Outsourced",
    }
    return mapping.get(raw_status, raw_status)


def normalize_ticket(ticket: dict) -> dict:
    summary = ticket.get("summary", {})
    devices = ticket.get("devices", [])

    order_id = summary.get("order_id", "N/A")
    if order_id != "N/A" and not str(order_id).startswith("T-"):
        order_id = f"T-{order_id}"

    created_ts_raw = summary.get("created_date")
    try:
        created_ts = float(created_ts_raw) if created_ts_raw else None
    except Exception as e:
        log_message(f"Error parsing created_date: {e}")
        created_ts = None

    raw_status = summary.get("status", "Open")
    for d in devices:
        d_status = d.get("status", {}).get("name", "")
        if d_status and d_status != "Open":
            raw_status = d_status
            break
    job_status = map_job_status(raw_status)
    booked_in = format_timestamp(created_ts)
    days_open = (
        (datetime.datetime.now() - datetime.datetime.fromtimestamp(created_ts)).days
        if created_ts
        else "N/A"
    )
    quoted_price = summary.get("total", "N/A")
    assigned_to = summary.get("assigned_to")
    if not assigned_to and devices:
        assigned_to = devices[0].get("assigned_to", {}).get("fullname", "N/A")
    customer = summary.get("customer", {})
    customer_name = customer.get("fullName", "N/A")
    customer_mobile = customer.get("mobile", "N/A")
    last_updated_raw = summary.get("last_updated")
    try:
        last_updated_ts = float(last_updated_raw) if last_updated_raw else None
    except Exception:
        last_updated_ts = None
    device_name = "N/A"
    if devices:
        device_name = devices[0].get("device", {}).get("name", "N/A")
    normalized = {
        "ticket_id": order_id,
        "customer_name": customer_name,
        "customer_mobile": customer_mobile,
        "job_status": job_status,
        "quoted_price": quoted_price,
        "booked_in": booked_in,
        "days_open": days_open,
        "assigned_to": assigned_to if assigned_to else "N/A",
        "last_updated_ts": last_updated_ts,
        "device": device_name,
    }
    return normalized
