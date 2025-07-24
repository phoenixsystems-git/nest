import requests
from utils.logger import log_message


class RepairDeskClient:
    """Lightweight client for RepairDesk – tickets, notes, *single‑page* customers."""

    def __init__(self, api_key=None):
        self.base_url = "https://api.repairdesk.co/api/web/v1"
        self.api_key = api_key

    # ------------------------------------------------------------ #
    # Core GET helper
    # ------------------------------------------------------------ #
    def _get(self, path: str, params=None):
        params = params or {}
        params["api_key"] = self.api_key
        url = f"{self.base_url}{path}"
        log_message(f"GET {url} params={params}")
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        return r.json()

    # ------------------------------------------------------------ #
    # Tickets (existing)
    # ------------------------------------------------------------ #
    def get_tickets(self, page=1):
        try:
            data = self._get("/tickets", {"page": page})
            if "data" not in data:
                raise ValueError("Unexpected ticket payload")
            return data
        except Exception as e:
            log_message(f"Ticket fetch error: {e}")
            return {"error": str(e)}

    def get_all_tickets(self):
        page, out = 1, []
        while True:
            data = self.get_tickets(page)
            if "error" in data:
                break
            page_rows = data.get("data", {}).get("ticketData", [])
            if not page_rows:
                break
            out.extend(page_rows)
            pag = data.get("data", {}).get("pagination", {})
            if pag.get("next_page_exist"):
                page = pag.get("next_page", page + 1)
            else:
                break
        return out

    def add_note_to_ticket(self, ticket_id, note, note_type=1, is_flag=0):
        url = f"{self.base_url}/ticket/addnote?api_key={self.api_key}"
        payload = {"id": ticket_id, "note": note, "type": note_type, "is_flag": is_flag}
        try:
            r = requests.post(url, json=payload, timeout=15)
            r.raise_for_status()
            res = r.json()
            if not res.get("success"):
                raise ValueError(res)
            return res
        except Exception as e:
            log_message(f"Add note error: {e}")
            return {"success": False, "message": str(e)}

    # ------------------------------------------------------------ #
    # Customers – SINGLE PAGE ONLY (page 1) to prevent runaway loop
    # ------------------------------------------------------------ #
    def get_customers(self, page=1):
        try:
            return self._get("/customers", {"page": page})
        except Exception as e:
            log_message(f"Customer page error: {e}")
            return {"error": str(e)}

    def _unwrap_customer_page(self, payload):
        blk = payload.get("data", payload)
        if isinstance(blk, list):
            return blk
        if isinstance(blk, dict):
            return blk.get("customerData", [])
        return payload.get("customerData", [])

    def get_all_customers(self):
        """Intentionally returns **only page 1** to keep Nest quick and avoid endless pagination."""
        first = self.get_customers(page=1)
        if "error" in first:
            return []
        return self._unwrap_customer_page(first)
