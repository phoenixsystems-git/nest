import webbrowser
import logging
import re


class MSI_API:
    model_lookup = {
        "MS-7883": "X99A GODLIKE GAMING",
        "X99A GODLIKE GAMING CARBON (MS-7883)": "X99A GODLIKE GAMING",
    }

    @staticmethod
    def normalize_model(model: str) -> str:
        logging.info(f"[DEBUG] Raw model input: {model}")
        print(f"[DEBUG] Raw model input: {model}")
        if model in MSI_API.model_lookup:
            resolved = MSI_API.model_lookup[model]
            logging.info(f"[DEBUG] Direct match found: {model} -> {resolved}")
            return resolved.upper().replace(" ", "-")

        match = re.search(r"(MS-\d{4})", model.upper())
        if match:
            code = match.group(1)
            logging.info(f"[DEBUG] Extracted model code: {code}")
            if code in MSI_API.model_lookup:
                resolved = MSI_API.model_lookup[code]
                logging.info(f"[DEBUG] Lookup match: {code} -> {resolved}")
                return resolved.upper().replace(" ", "-")

        logging.warning(f"[DEBUG] No match found, using raw: {model}")
        return model.upper().replace(" ", "-")

    @staticmethod
    def get_driver_url(model: str) -> str:
        model_url = MSI_API.normalize_model(model)
        url = f"https://www.msi.com/Motherboard/{model_url}/support"
        logging.info(f"[DEBUG] Final driver URL: {url}")
        print(f"[DEBUG] Final driver URL: {url}")
        return url

    @staticmethod
    def get_product_info_url(model: str) -> str:
        model_url = MSI_API.normalize_model(model)
        url = f"https://www.msi.com/Motherboard/{model_url}/Specification"
        logging.info(f"[DEBUG] Final product info URL: {url}")
        print(f"[DEBUG] Final product info URL: {url}")
        return url

    @staticmethod
    def open_driver_page(model: str) -> None:
        url = MSI_API.get_driver_url(model)
        logging.info(f"Opening MSI driver page: {url}")
        webbrowser.open(url)

    @staticmethod
    def open_product_info_page(model: str) -> None:
        url = MSI_API.get_product_info_url(model)
        logging.info(f"Opening MSI product info page: {url}")
        webbrowser.open(url)
