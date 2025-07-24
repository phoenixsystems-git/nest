"""
Simulated Gigabyte API Module

This module simulates integration with Gigabyte by constructing standard URLs for a given
motherboard model. It assumes that for any motherboard model:

- The product information page (showing key features) is at:
    https://www.gigabyte.com/Motherboard/{formatted_model}#kf

- The driver download page is at:
    https://www.gigabyte.com/Motherboard/{formatted_model}/support#support-dl-driver

Replace or adjust these URLs if your research shows differences.
"""

import logging

# Base URLs for Gigabyte pages.
BASE_PRODUCT_URL = "https://www.gigabyte.com/Motherboard"
SUPPORT_SUFFIX = "support-dl-driver"


def format_model_for_url(model):
    """
    Format the motherboard model to match Gigabyte's URL pattern.
    For example, convert "Z370M D3H" to "Z370M-D3H-rev-10".
    Here we assume that if the model string doesn't include a revision (e.g., "rev"),
    we append "-rev-10" by default.
    """
    formatted = model.replace(" ", "-")
    if "rev" not in formatted.lower():
        formatted += "-rev-10"
    return formatted


def get_gigabyte_product_info(model):
    """
    Simulate retrieval of product information for a Gigabyte motherboard.
    Constructs URLs for the product info page and the driver download page.

    Parameters:
        model (str): The motherboard model (e.g., "Z370M D3H").

    Returns:
        dict: A dictionary with the following keys:
            - product_url: URL for the product page (#kf page).
            - driver_url: URL for the driver download page.
            - bios_url: For this simulation, we assume BIOS updates are on the same page as drivers.
            - logo_url: (Optional) None for now; could be updated later.
    """
    formatted_model = format_model_for_url(model)

    product_url = f"{BASE_PRODUCT_URL}/{formatted_model}#kf"
    driver_url = f"{BASE_PRODUCT_URL}/{formatted_model}/support#{SUPPORT_SUFFIX}"
    bios_url = driver_url  # For this simulation, we use the same URL.
    logo_url = None  # You could add logic later to fetch a logo if available.

    info = {
        "product_url": product_url,
        "driver_url": driver_url,
        "bios_url": bios_url,
        "logo_url": logo_url,
    }

    logging.info("Simulated Gigabyte product info constructed for model %s", model)
    return info
