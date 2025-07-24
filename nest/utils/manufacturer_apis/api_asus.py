# asus_api.py

ASUS_API = {
    "PRIME-B760M-A-WIFI": {
        "series": "prime",
        "model": "PRIME B760M-A WIFI",
        "support_url": "https://www.asus.com/au/motherboards-components/motherboards/prime/prime-b760m-a-wifi/helpdesk_knowledge?model2Name=PRIME-B760M-A-WIFI",
        "downloads": [
            {
                "type": "LAN Driver",
                "description": "Realtek 8125 LAN Driver for Windows 11 64-bit",
                "file": "DRV_LAN_RTK_8125_SZ-TSD_W11_64_V1125219032024_20240914R.zip",
                "url": "https://dlcdnets.asus.com/pub/ASUS/mb/04LAN/DRV_LAN_RTK_8125_SZ-TSD_W11_64_V1125219032024_20240914R.zip",
            }
        ],
    },
    "ROG-STRIX-B850-I-GAMING-WIFI": {
        "series": "rog-strix",
        "model": "ROG STRIX B850-I GAMING WIFI",
        "support_url": "https://rog.asus.com/au/motherboards/rog-strix/rog-strix-b850-i-gaming-wifi/helpdesk/?model2Name=ROG-STRIX-B850-I-GAMING-WIFI",
        "downloads": [
            {
                "type": "LAN Driver",
                "description": "Intel LAN Driver for Windows 11",
                "file": "Intel_LAN_Driver_V2.1.4.3_Windows_11.zip",
                "url": "https://dlcdnets.asus.com/pub/ASUS/mb/SocketAM5/M6870/Intel_LAN_Driver_V2.1.4.3_Windows_11.zip",
            }
        ],
    },
    "TUF-GAMING-B650-PLUS-WIFI": {
        "series": "tuf-gaming",
        "model": "TUF GAMING B650-PLUS WIFI",
        "support_url": "https://www.asus.com/motherboards-components/motherboards/tuf-gaming/tuf-gaming-b650-plus-wifi/helpdesk_download/?model2Name=TUF-GAMING-B650-PLUS-WIFI",
        "downloads": [
            {
                "type": "Chipset Driver",
                "description": "AMD Chipset Driver for Windows 11/10",
                "file": "AMD_Chipset_Software.zip",
                "url": "https://dlcdnets.asus.com/pub/ASUS/mb/SocketAM5/B650-PLUS/AMD_Chipset_Software.zip",
            }
        ],
    },
    "PRIME-Z790-P": {
        "series": "prime",
        "model": "PRIME Z790-P",
        "support_url": "https://www.asus.com/motherboards-components/motherboards/prime/prime-z790-p/helpdesk_download/?model2Name=PRIME-Z790-P",
        "downloads": [
            {
                "type": "Audio Driver",
                "description": "Realtek Audio Driver for Windows 11/10 64-bit",
                "file": "Audio_Driver_WIN64_V6019373.zip",
                "url": "https://dlcdnets.asus.com/pub/ASUS/mb/LGA1700/PRIME_Z790_P/Audio_Driver_WIN64_V6019373.zip",
            }
        ],
    },
    "ROG-STRIX-B650E-E-GAMING-WIFI": {
        "series": "rog-strix",
        "model": "ROG STRIX B650E-E GAMING WIFI",
        "support_url": "https://rog.asus.com/motherboards/rog-strix/rog-strix-b650e-e-gaming-wifi-model/helpdesk_download/?model2Name=ROG-STRIX-B650E-E-GAMING-WIFI-MODEL",
        "downloads": [
            {
                "type": "BIOS",
                "description": "BIOS 2007 for ROG STRIX B650E-E GAMING WIFI",
                "file": "ROG-STRIX-B650E-E-GAMING-WIFI-ASUS-2007.CAP",
                "url": "https://dlcdnets.asus.com/pub/ASUS/mb/SocketAM5/B650E/ROG-STRIX-B650E-E-GAMING-WIFI-ASUS-2007.CAP",
            }
        ],
    },
}


def get_asus_info(model_key):
    model_key = model_key.replace(" ", "-").upper()
    return ASUS_API.get(model_key.upper())
