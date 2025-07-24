import psutil

try:
    import wmi
except ImportError:
    wmi = None


def gather_system_diagnostics(technician_name):
    import pythoncom

    pythoncom.CoInitialize()
    try:
        import datetime

        diagnostics_output = f"Technician: {technician_name}\n"
        diagnostics_output += f"Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        if wmi is None:
            diagnostics_output += "WMI module not available.\n"
            return diagnostics_output
        w = wmi.WMI()
        try:
            cs = w.Win32_ComputerSystem()[0]
            os_info = w.Win32_OperatingSystem()[0]
            proc = w.Win32_Processor()[0]
            bios = w.Win32_BIOS()[0]
            base = w.Win32_BaseBoard()[0]
            gpus = [gpu.Name.strip() for gpu in w.Win32_VideoController()]
            drives = [
                f"{d.Model} - {round(int(d.Size)/(1024**3), 2)} GB" for d in w.Win32_DiskDrive()
            ]
            diagnostics_output += f"Manufacturer: {cs.Manufacturer}\n"
            diagnostics_output += f"Model: {cs.Model}\n"
            diagnostics_output += f"OS: {os_info.Caption}\n"
            diagnostics_output += f"CPU: {proc.Name}\n"
            diagnostics_output += (
                f"RAM: {round(psutil.virtual_memory().total / (1024 ** 3), 2)} GB\n"
            )
            diagnostics_output += f"BIOS Version: {bios.SMBIOSBIOSVersion}\n"
            diagnostics_output += f"Baseboard: {base.Product} ({base.Manufacturer})\n"
            diagnostics_output += "GPU(s):\n" + "\n".join(gpus) + "\n"
            diagnostics_output += "Drives:\n" + "\n".join(drives) + "\n"
        except Exception as wmi_inner:
            diagnostics_output += f"Error reading WMI data: {wmi_inner}\n"
        return diagnostics_output
    finally:
        pythoncom.CoUninitialize()
