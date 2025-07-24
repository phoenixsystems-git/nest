import wmi
import logging
import pythoncom


def get_full_system_info():
    try:
        pythoncom.CoInitialize()
        c = wmi.WMI()
        info = {}
        os = c.Win32_OperatingSystem()[0]
        cpu = c.Win32_Processor()[0]
        mem = c.Win32_ComputerSystem()[0]
        gpu_list = c.Win32_VideoController()
        disks = c.Win32_DiskDrive()

        def safe(val):
            return str(val).strip() if val else "Unknown"

        info["OS"] = safe(os.Caption)
        info["OS Version"] = safe(os.Version)
        info["CPU"] = safe(cpu.Name)
        info["RAM"] = f"{round(float(mem.TotalPhysicalMemory)/1024**3, 2)} GB"
        info["GPU"] = ", ".join(safe(g.Name) for g in gpu_list)
        info["Disk Count"] = len(disks)

        return info
    except Exception as e:
        logging.exception("Error getting system info via WMI")
        return {"Error": "Failed to retrieve system information"}
