# Nest - RepairDesk Management System

![License](https://img.shields.io/badge/license-Private-red.svg)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20WinPE-lightgrey.svg)

**Nest** is a comprehensive computer repair shop management system designed as a standalone desktop application with all dependencies bundled. It integrates seamlessly with the RepairDesk API and provides repair shops with a complete solution for managing tickets, customers, inventory, diagnostics, and business operations across Windows, macOS, and WinPE environments.

## 🚀 Features

### Core Functionality
- **RepairDesk API Integration**: Full integration with RepairDesk for ticket management
- **Customer Management**: Complete customer database with purchase history
- **Inventory Control**: Parts tracking and inventory management
- **Ticket Management**: Create, update, and track repair tickets
- **Appointment Scheduling**: Google Calendar integration for appointments

### Advanced Tools
- **Hardware Diagnostics**: Comprehensive PC, Android, and iOS diagnostic tools
- **AI Integration**: Claude AI for intelligent ticket analysis and assistance
- **Reporting System**: Business reports and analytics
- **Cross-Platform Support**: Native Windows and Linux compatibility

### Security Features
- **Environment Variables**: Secure API key management
- **Data Protection**: Local data caching with security best practices
- **Access Control**: User authentication and role management
- **Portable Execution**: Self-contained with no external dependencies

## 📋 System Requirements

- **Windows**: Windows 10 or later (64-bit)
- **macOS**: macOS 10.14 (Mojave) or later
- **WinPE**: Compatible with Windows PE environments for diagnostic scenarios
- **Storage**: Minimum 100MB free disk space
- **Memory**: 4GB RAM recommended for optimal performance

## 🛠️ Installation

### Windows
1. **Download** the latest `Nest.exe` from the releases page
2. **Run** the executable directly - no installation required
3. **First Launch**: The application will create its configuration and cache directories automatically
4. **Optional**: Create a desktop shortcut for easy access

### macOS
1. **Download** the latest `Nest.app` from the releases page
2. **Install**: Drag `Nest.app` to your Applications folder
3. **First Launch**: Right-click and select "Open" to bypass Gatekeeper security
4. **Subsequent Launches**: Use Launchpad or Applications folder normally

### WinPE (Portable Environments)
1. **Copy** `Nest.exe` to any location on your WinPE system or USB drive
2. **Run** directly from any location - fully portable execution
3. **Data Storage**: Configuration and cache files are created relative to the executable location
4. **Network**: Ensure network connectivity for RepairDesk API access

## ⚙️ Configuration

### First-Time Setup
On first launch, Nest will guide you through the initial configuration:
1. **RepairDesk API Key**: Enter your RepairDesk API credentials
2. **Store Information**: Configure your store name and slug
3. **Optional AI Integration**: Configure Claude, OpenAI, or Gemini API keys for enhanced features

### Advanced Configuration (Optional)
For advanced users, you can create a `.env` file in the same directory as the executable:

```env
# RepairDesk API Configuration
REPAIRDESK_API_KEY=your_repairdesk_api_key_here

# AI API Keys (optional)
CLAUDE_API_KEY=your_claude_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here

# Store Configuration
STORE_NAME=Your Store Name
STORE_SLUG=your_store_slug
```

### Portable Data Storage
- **Configuration**: Stored in `config/` directory relative to executable
- **Cache**: Stored in `cache/` directory relative to executable  
- **Logs**: Stored in `logs/` directory relative to executable
- **Automatic Creation**: All directories are created automatically on first run

## 🏗️ Project Structure

```
nest/
├── launch_nest.py          # Application entry point
├── requirements.txt        # Python dependencies
├── .env.example           # Environment variables template
├── nest/                  # Main application package
│   ├── main.py           # Main application logic
│   ├── api/              # RepairDesk API client
│   ├── ui/               # Tkinter UI components
│   ├── utils/            # Utility functions
│   ├── config/           # Configuration management
│   └── assets/           # Images and resources
├── assets/               # Additional assets
└── docs/                 # Documentation
```

## 🎯 Usage

### Basic Workflow
1. **Launch Application**: Double-click `Nest.exe` (Windows) or `Nest.app` (macOS)
2. **First-Time Setup**: Complete the initial configuration wizard
3. **Login**: Enter your RepairDesk credentials
4. **Dashboard**: Access tickets, customers, and inventory
5. **Create Tickets**: Add new repair tickets with customer information
6. **Diagnostics**: Run hardware diagnostics on customer devices
7. **Reports**: Generate business reports and analytics

### Key Features
- **Ticket Search**: Find tickets by number, customer, or device
- **Batch Operations**: Process multiple tickets efficiently
- **Offline Mode**: Work with cached data when internet is unavailable
- **Export Data**: Export reports and ticket information

## 🔧 Development

### For Contributors Only
This section is for developers who want to modify the Nest source code. End users should use the standalone executable.

### Setting Up Development Environment
```bash
# Clone the repository
git clone https://github.com/phoenixsystems-git/nest.git
cd nest

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run from source
python launch_nest.py
```

### Building Executables
```bash
# Install PyInstaller
pip install pyinstaller

# Build for current platform
pyinstaller --onefile --windowed launch_nest.py

# Output will be in dist/ directory
```

### Contributing Guidelines
1. Create feature branches from `main`
2. Follow PEP 8 coding standards
3. Add tests for new functionality
4. Update documentation as needed
5. Submit pull requests for review

## 📚 Documentation

- **User Guide**: Complete usage instructions included with the application
- **API Documentation**: Check `docs/api.md` in the source repository
- **Troubleshooting**: See troubleshooting section below
- **Developer Documentation**: Available in the source repository for contributors

## 🐛 Troubleshooting

### Common Issues

#### Windows
- **Antivirus Blocking**: Some antivirus software may flag the executable. Add Nest.exe to your antivirus exclusions
- **Windows Defender SmartScreen**: Click "More info" then "Run anyway" on first launch
- **Permission Errors**: Run as administrator if you encounter file permission issues

#### macOS
- **Gatekeeper Warning**: Right-click the app and select "Open" to bypass security warnings
- **"App is damaged"**: If you see this error, run `xattr -cr /Applications/Nest.app` in Terminal
- **Permission Denied**: Ensure the app has necessary permissions in System Preferences > Security & Privacy

#### General
- **API Connection**: Verify RepairDesk API key and internet connection
- **Configuration Issues**: Delete the `config/` directory to reset to defaults
- **Performance Issues**: Ensure adequate system resources (4GB+ RAM recommended)
- **Network Connectivity**: Verify firewall settings allow outbound HTTPS connections

### Getting Help
1. Check log files in the `logs/` directory next to the executable
2. Verify API key configuration in the settings
3. Test network connectivity to RepairDesk servers
4. Try running from a different location if using portable mode

## 📄 License

This project is private and proprietary. All rights reserved.

## 🤝 Support

For support and questions:
- Check the documentation in the `docs/` folder
- Review the troubleshooting guide
- Contact the development team

---

**Nest** - Streamlining repair shop operations with powerful RepairDesk integration.

*Available as a standalone application for Windows, macOS, and WinPE environments - no installation or dependencies required.*
System Requirements
bash# Ubuntu/Debian
sudo apt update
sudo apt install -y python3.13 python3.13-venv python3-tk python3-dev libffi-dev libssl-dev \
  git build-essential pkg-config libjpeg-dev zlib1g-dev
  
# Fedora/RHEL
sudo dnf install -y python3.13 python3-tkinter python3-devel libffi-devel openssl-devel \
  git gcc gcc-c++ make libjpeg-devel zlib-devel

# Arch Linux
sudo pacman -S python tk python-pip gcc git make pkg-config libjpeg-turbo zlib
Virtual Environment Setup
bash# Clone repository or extract archive
git clone https://github.com/repairdesk/nest.git ~/nest_2.0
# OR
unzip nest_2.0.zip -d ~/nest_2.0
cd ~/nest_2.0

# Create and activate virtual environment 
python3.13 -m venv .venv
source .venv/bin/activate

# Upgrade pip and install dependencies
pip install --upgrade pip wheel setuptools
pip install -r requirements.txt

# If requirements.txt doesn't exist or contains Windows-specific packages, use:
pip install tkinter pillow==10.4.0 requests==2.32.3 psutil==5.9.8 beautifulsoup4==4.13.4 \
  tkcalendar==1.6.1 python-dateutil==2.9.0.post0 cryptography==42.0.5
Linux Launcher Script
Create a robust launcher script with error handling and logging:
bashcat > ~/nest_2.0/run_nest.sh << 'EOF'
#!/bin/bash
# Nest Linux Launcher
set -e

# Configuration
APP_DIR="$(dirname "$(realpath "$0")")"
VENV_DIR="${APP_DIR}/.venv"
LOG_FILE="${APP_DIR}/nest_linux.log"
PYTHON_VERSION="3.13"

# Function for logging
log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "${LOG_FILE}"
}

# Check Python installation
if ! command -v python${PYTHON_VERSION} &> /dev/null; then
  log "ERROR: Python ${PYTHON_VERSION} not found. Please install it first."
  log "On Ubuntu/Debian: sudo apt install python${PYTHON_VERSION}"
  log "On Fedora/RHEL: sudo dnf install python${PYTHON_VERSION}"
  log "On Arch Linux: sudo pacman -S python"
  exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "${VENV_DIR}" ]; then
  log "Creating virtual environment..."
  python${PYTHON_VERSION} -m venv "${VENV_DIR}"
  source "${VENV_DIR}/bin/activate"
  pip install --upgrade pip wheel setuptools
  
  # Install dependencies
  if [ -f "${APP_DIR}/requirements.txt" ]; then
    log "Installing dependencies from requirements.txt..."
    pip install -r "${APP_DIR}/requirements.txt"
  else
    log "requirements.txt not found, installing core dependencies..."
    pip install tkinter pillow==10.4.0 requests==2.32.3 psutil==5.9.8 \
      beautifulsoup4==4.13.4 tkcalendar==1.6.1 python-dateutil==2.9.0.post0 \
      cryptography==42.0.5
  fi
else
  source "${VENV_DIR}/bin/activate"
fi

# Change to app directory
cd "${APP_DIR}"

# Set Python path for module imports
export PYTHONPATH="${APP_DIR}"

# Run Nest
log "Starting Nest application..."
python -m nest.main
exit_code=$?

if [ $exit_code -ne 0 ]; then
  log "ERROR: Nest exited with code ${exit_code}"
  echo "Nest encountered an error. Check ${LOG_FILE} for details."
  exit $exit_code
fi
EOF

chmod +x ~/nest_2.0/run_nest.sh
Desktop Integration
Create a desktop entry for system integration:
bashcat > ~/.local/share/applications/nest.desktop << EOF
[Desktop Entry]
Name=RepairDesk Nest
Comment=RepairDesk repair shop management system
Exec=$(realpath ~/nest_2.0/run_nest.sh)
Icon=$(realpath ~/nest_2.0/assets/images/icon.png)
Terminal=false
Type=Application
Categories=Utility;Office;
StartupWMClass=nest
EOF
2. Codebase Modifications
Module Import Structure
First, fix any absolute imports to ensure Linux compatibility:
python# Before:
from nest.utils.config_util import load_config

# After:
try:
    from nest.utils.config_util import load_config
except ImportError:
    # Fallback for direct script execution
    import os
    import sys
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, parent_dir)
    from nest.utils.config_util import load_config
Fixing repairdesk_api.py for Ticket Lookups
Based on our earlier analysis, update the ticket lookup function to properly use the cache:
pythondef get_numeric_ticket_id(self, ticket_number):
    """
    Get the numeric RepairDesk ticket ID from a ticket number (e.g., T-12345).
    
    Args:
        ticket_number (str): The ticket number, with or without "T-" prefix
        
    Returns:
        str: The internal RepairDesk ticket ID, or None if not found
    """
    # Normalize ticket number format
    if ticket_number.startswith("T-"):
        display_number = ticket_number
        numeric_part = ticket_number[2:]
    else:
        display_number = f"T-{ticket_number}"
        numeric_part = ticket_number
        
    logging.info(f"Looking up numeric ID for ticket {display_number}")
    
    # STEP 1: Check ticket cache first
    try:
        cache_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
            'ticket_cache.json'
        )
        
        if os.path.exists(cache_path):
            with open(cache_path, 'r') as f:
                tickets = json.load(f)
                
            for ticket in tickets:
                if ticket.get('summary', {}).get('order_id') == display_number:
                    internal_id = ticket.get('summary', {}).get('id')
                    logging.info(f"Found ticket {display_number} in cache with internal ID: {internal_id}")
                    return internal_id
                    
            logging.info(f"Ticket {display_number} not found in cache")
    except Exception as e:
        logging.error(f"Error checking ticket cache: {e}")
    
    # STEP 2: Try direct API lookup using numeric part
    try:
        url = f"{self.base_url}/web/v1/tickets/{numeric_part}?api_key={self.api_key}"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, dict) and data.get('success') and data.get('data'):
                ticket_id = data['data'].get('id')
                logging.info(f"Direct API lookup successful. Ticket ID: {ticket_id}")
                return ticket_id
        
        logging.info(f"Direct lookup failed for {display_number}, trying all tickets search")
    except Exception as e:
        logging.error(f"Error in direct ticket lookup: {e}")
    
    # STEP 3: Fetch all tickets and search
    try:
        all_tickets = self.get_all_tickets()
        if all_tickets:
            for ticket in all_tickets:
                if ticket.get('summary', {}).get('order_id') == display_number:
                    internal_id = ticket.get('summary', {}).get('id')
                    logging.info(f"Found ticket {display_number} in API results with internal ID: {internal_id}")
                    return internal_id
    except Exception as e:
        logging.error(f"Error searching all tickets: {e}")
    
    logging.error(f"Could not find numeric ID for ticket {display_number}")
    return None
Ticket Cache Management
Improve the ticket cache management to work on Linux:
pythondef _update_ticket_cache(self, tickets):
    """Update the local ticket cache file with the latest tickets."""
    try:
        # Use platform-independent path
        cache_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
            'ticket_cache.json'
        )
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        
        # Safely write to temp file first, then rename
        temp_path = f"{cache_path}.tmp"
        with open(temp_path, 'w') as f:
            json.dump(tickets, f, indent=2)
            
        # Atomic rename operation
        os.replace(temp_path, cache_path)
        
        logging.info(f"Updated ticket cache with {len(tickets)} tickets")
        return True
    except Exception as e:
        logging.error(f"Failed to update ticket cache: {e}")
        return False
3. Hardware Detection Adaptations
CPU Information
pythondef get_cpu_info():
    """Get CPU information in a platform-independent way."""
    if platform.system() == "Windows":
        try:
            import wmi
            c = wmi.WMI()
            for processor in c.Win32_Processor():
                return {
                    "name": processor.Name.strip(),
                    "cores": processor.NumberOfCores,
                    "threads": processor.NumberOfLogicalProcessors,
                    "manufacturer": processor.Manufacturer,
                }
        except Exception as e:
            logging.error(f"Error getting Windows CPU info via WMI: {e}")
    
    # Linux implementation
    try:
        cpu_info = {}
        with open('/proc/cpuinfo', 'r') as f:
            content = f.read()
            
        # Parse CPU model name
        model_pattern = re.compile(r'model name\s+:\s+(.*)')
        model_match = model_pattern.search(content)
        if model_match:
            cpu_info["name"] = model_match.group(1).strip()
        
        # Parse CPU cores
        cpu_cores = len(re.findall(r'processor\s+:\s+\d+', content))
        cpu_info["threads"] = cpu_cores
        
        # Physical cores 
        physical_id_pattern = re.compile(r'physical id\s+:\s+(\d+)')
        core_id_pattern = re.compile(r'core id\s+:\s+(\d+)')
        
        physical_ids = set()
        core_ids = {}
        
        for line in content.splitlines():
            physical_match = physical_id_pattern.match(line)
            if physical_match:
                physical_ids.add(physical_match.group(1))
                
            core_match = core_id_pattern.match(line)
            if core_match and physical_match:
                if physical_match.group(1) not in core_ids:
                    core_ids[physical_match.group(1)] = set()
                core_ids[physical_match.group(1)].add(core_match.group(1))
        
        # Calculate physical cores
        physical_cores = sum(len(cores) for cores in core_ids.values()) if core_ids else 1
        cpu_info["cores"] = physical_cores if physical_cores > 0 else cpu_cores
        
        # Get manufacturer
        vendor_pattern = re.compile(r'vendor_id\s+:\s+(.*)')
        vendor_match = vendor_pattern.search(content)
        if vendor_match:
            cpu_info["manufacturer"] = vendor_match.group(1).strip()
            
        return cpu_info
    except Exception as e:
        logging.error(f"Error getting Linux CPU info: {e}")
    
    # Fallback using platform module
    return {
        "name": platform.processor() or "Unknown CPU",
        "cores": psutil.cpu_count(logical=False) or 1,
        "threads": psutil.cpu_count(logical=True) or 1,
        "manufacturer": "Unknown",
    }
Memory Information
pythondef get_memory_info():
    """Get memory information in a platform-independent way."""
    if platform.system() == "Windows":
        try:
            import wmi
            c = wmi.WMI()
            total_memory = 0
            for mem_module in c.Win32_PhysicalMemory():
                total_memory += int(mem_module.Capacity)
            
            memory_info = {
                "total": total_memory,
                "total_gb": round(total_memory / (1024**3), 2),
            }
            
            # Add information from psutil
            vm = psutil.virtual_memory()
            memory_info.update({
                "available": vm.available,
                "available_gb": round(vm.available / (1024**3), 2),
                "used": vm.used,
                "used_gb": round(vm.used / (1024**3), 2),
                "percent": vm.percent,
            })
            
            return memory_info
        except Exception as e:
            logging.error(f"Error getting Windows memory info via WMI: {e}")
    
    # Linux implementation
    try:
        # Get memory info from /proc/meminfo
        with open('/proc/meminfo', 'r') as f:
            meminfo = f.read()
        
        # Extract total memory
        total_pattern = re.compile(r'MemTotal:\s+(\d+)\s+kB')
        total_match = total_pattern.search(meminfo)
        
        total_memory = 0
        if total_match:
            total_kb = int(total_match.group(1))
            total_memory = total_kb * 1024  # Convert KB to bytes
        
        memory_info = {
            "total": total_memory,
            "total_gb": round(total_memory / (1024**3), 2),
        }
        
        # Add information from psutil
        vm = psutil.virtual_memory()
        memory_info.update({
            "available": vm.available,
            "available_gb": round(vm.available / (1024**3), 2),
            "used": vm.used,
            "used_gb": round(vm.used / (1024**3), 2),
            "percent": vm.percent,
        })
        
        return memory_info
    except Exception as e:
        logging.error(f"Error getting Linux memory info: {e}")
    
    # Fallback to psutil only
    try:
        vm = psutil.virtual_memory()
        return {
            "total": vm.total,
            "total_gb": round(vm.total / (1024**3), 2),
            "available": vm.available,
            "available_gb": round(vm.available / (1024**3), 2),
            "used": vm.used,
            "used_gb": round(vm.used / (1024**3), 2),
            "percent": vm.percent,
        }
    except Exception as e:
        logging.error(f"Error getting memory info via psutil: {e}")
        return {
            "total": 0,
            "total_gb": 0,
            "available": 0,
            "available_gb": 0,
            "used": 0,
            "used_gb": 0,
            "percent": 0,
        }
Disk Information
pythondef get_disk_info():
    """Get disk information in a platform-independent way."""
    if platform.system() == "Windows":
        try:
            import wmi
            c = wmi.WMI()
            disks = []
            
            # Physical disks
            for disk in c.Win32_DiskDrive():
                disk_info = {
                    "model": disk.Model.strip(),
                    "size": int(disk.Size),
                    "size_gb": round(int(disk.Size) / (1024**3), 2),
                    "interface": disk.InterfaceType,
                }
                disks.append(disk_info)
            
            # Add partition information
            partitions = []
            for partition in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    partition_info = {
                        "device": partition.device,
                        "mountpoint": partition.mountpoint,
                        "filesystem": partition.fstype,
                        "total": usage.total,
                        "total_gb": round(usage.total / (1024**3), 2),
                        "used": usage.used,
                        "used_gb": round(usage.used / (1024**3), 2),
                        "free": usage.free,
                        "free_gb": round(usage.free / (1024**3), 2),
                        "percent": usage.percent,
                    }
                    partitions.append(partition_info)
                except PermissionError:
                    # Skip partitions that can't be accessed
                    continue
            
            return {
                "disks": disks,
                "partitions": partitions,
            }
        except Exception as e:
            logging.error(f"Error getting Windows disk info via WMI: {e}")
    
    # Linux implementation
    try:
        disks = []
        
        # Get physical disk information from /proc/partitions
        with open('/proc/partitions', 'r') as f:
            # Skip header
            next(f)
            next(f)
            
            for line in f:
                parts = line.strip().split()
                if len(parts) == 4 and not parts[3][0].isdigit():  # Exclude partitions
                    # Check if it's a real disk (not a partition)
                    if not re.match(r'.*\d+$', parts[3]):
                        disk_path = f"/dev/{parts[3]}"
                        
                        # Try to get model info from /sys
                        model = "Unknown"
                        try:
                            model_path = f"/sys/block/{parts[3]}/device/model"
                            if os.path.exists(model_path):
                                with open(model_path, 'r') as model_file:
                                    model = model_file.read().strip()
                        except:
                            pass
                        
                        # Calculate size
                        size = int(parts[2]) * 1024  # blocks * 1024 = bytes
                        
                        disk_info = {
                            "model": model,
                            "size": size,
                            "size_gb": round(size / (1024**3), 2),
                            "interface": "Unknown",  # Could be determined with additional parsing
                        }
                        disks.append(disk_info)
        
        # Add partition information
        partitions = []
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                partition_info = {
                    "device": partition.device,
                    "mountpoint": partition.mountpoint,
                    "filesystem": partition.fstype,
                    "total": usage.total,
                    "total_gb": round(usage.total / (1024**3), 2),
                    "used": usage.used,
                    "used_gb": round(usage.used / (1024**3), 2),
                    "free": usage.free,
                    "free_gb": round(usage.free / (1024**3), 2),
                    "percent": usage.percent,
                }
                partitions.append(partition_info)
            except PermissionError:
                # Skip partitions that can't be accessed
                continue
        
        return {
            "disks": disks,
            "partitions": partitions,
        }
    except Exception as e:
        logging.error(f"Error getting Linux disk info: {e}")
    
    # Fallback to psutil only
    try:
        partitions = []
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                partition_info = {
                    "device": partition.device,
                    "mountpoint": partition.mountpoint,
                    "filesystem": partition.fstype,
                    "total": usage.total,
                    "total_gb": round(usage.total / (1024**3), 2),
                    "used": usage.used,
                    "used_gb": round(usage.used / (1024**3), 2),
                    "free": usage.free,
                    "free_gb": round(usage.free / (1024**3), 2),
                    "percent": usage.percent,
                }
                partitions.append(partition_info)
            except PermissionError:
                # Skip partitions that can't be accessed
                continue
        
        return {
            "disks": [],
            "partitions": partitions,
        }
    except Exception as e:
        logging.error(f"Error getting disk info via psutil: {e}")
        return {
            "disks": [],
            "partitions": [],
        }
System Information
pythondef get_system_info():
    """Get system information in a platform-independent way."""
    if platform.system() == "Windows":
        try:
            import wmi
            c = wmi.WMI()
            
            # Computer system info
            computer_system = c.Win32_ComputerSystem()[0]
            system_info = {
                "manufacturer": computer_system.Manufacturer.strip(),
                "model": computer_system.Model.strip(),
                "system_type": computer_system.SystemType,
            }
            
            # BIOS info
            bios = c.Win32_BIOS()[0]
            system_info.update({
                "bios_version": bios.SMBIOSBIOSVersion.strip(),
                "bios_manufacturer": bios.Manufacturer.strip(),
                "bios_release_date": bios.ReleaseDate,
            })
            
            # OS info
            os_info = c.Win32_OperatingSystem()[0]
            system_info.update({
                "os_name": os_info.Caption.strip(),
                "os_version": os_info.Version,
                "os_build": os_info.BuildNumber,
                "os_architecture": os_info.OSArchitecture,
            })
            
            return system_info
        except Exception as e:
            logging.error(f"Error getting Windows system info via WMI: {e}")
    
    # Linux implementation
    try:
        system_info = {}
        
        # OS information
        system_info.update({
            "os_name": platform.system(),
            "os_version": platform.release(),
            "os_build": platform.version(),
            "os_architecture": platform.machine(),
        })
        
        # Try to get more detailed distribution info
        try:
            # Some distributions include this file with distro info
            if os.path.exists('/etc/os-release'):
                with open('/etc/os-release', 'r') as f:
                    os_release = {}
                    for line in f:
                        if '=' in line:
                            key, value = line.strip().split('=', 1)
                            os_release[key] = value.strip('"\'')
                
                if 'NAME' in os_release:
                    system_info["os_name"] = os_release['NAME']
                if 'VERSION_ID' in os_release:
                    system_info["os_version"] = os_release['VERSION_ID']
                if 'PRETTY_NAME' in os_release:
                    system_info["os_full_name"] = os_release['PRETTY_NAME']
        except Exception as e:
            logging.warning(f"Error parsing os-release file: {e}")
        
        # System manufacturer and model
        # Check DMI info
        manufacturer = "Unknown"
        model = "Unknown"
        
        try:
            if os.path.exists('/sys/class/dmi/id/sys_vendor'):
                with open('/sys/class/dmi/id/sys_vendor', 'r') as f:
                    manufacturer = f.read().strip()
            
            if os.path.exists('/sys/class/dmi/id/product_name'):
                with open('/sys/class/dmi/id/product_name', 'r') as f:
                    model = f.read().strip()
        except Exception as e:
            logging.warning(f"Error reading DMI info: {e}")
        
        system_info.update({
            "manufacturer": manufacturer,
            "model": model,
        })
        
        # BIOS information
        try:
            bios_version = "Unknown"
            bios_manufacturer = "Unknown"
            bios_release_date = "Unknown"
            
            if os.path.exists('/sys/class/dmi/id/bios_version'):
                with open('/sys/class/dmi/id/bios_version', 'r') as f:
                    bios_version = f.read().strip()
            
            if os.path.exists('/sys/class/dmi/id/bios_vendor'):
                with open('/sys/class/dmi/id/bios_vendor', 'r') as f:
                    bios_manufacturer = f.read().strip()
            
            if os.path.exists('/sys/class/dmi/id/bios_date'):
                with open('/sys/class/dmi/id/bios_date', 'r') as f:
                    bios_release_date = f.read().strip()
            
            system_info.update({
                "bios_version": bios_version,
                "bios_manufacturer": bios_manufacturer,
                "bios_release_date": bios_release_date,
            })
        except Exception as e:
            logging.warning(f"Error reading BIOS info: {e}")
        
        return system_info
    except Exception as e:
        logging.error(f"Error getting Linux system info: {e}")
    
    # Fallback to platform module
    return {
        "os_name": platform.system(),
        "os_version": platform.release(),
        "os_build": platform.version(),
        "os_architecture": platform.machine(),
        "manufacturer": "Unknown",
        "model": "Unknown",
        "bios_version": "Unknown",
        "bios_manufacturer": "Unknown",
        "bios_release_date": "Unknown",
    }
4. Path Handling
Path utilities module (nest/utils/path_util.py)
Create a dedicated file for path handling:
python"""
Path handling utilities for Nest application.
Ensures cross-platform compatibility between Windows and Linux.
"""

import os
import platform
import sys
import logging

def get_app_root():
    """
    Get the application root directory in a platform-independent way.
    
    Returns:
        str: Absolute path to application root directory
    """
    # If running as module
    if __name__.startswith('nest.'):
        # Get directory containing "nest" package
        module_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        parent_dir = os.path.dirname(module_path)
        return parent_dir
    
    # If running as script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if os.path.basename(script_dir) == 'utils':
        # We're in nest/utils directory
        return os.path.dirname(os.path.dirname(script_dir))
    return script_dir

def get_config_dir():
    """
    Get the configuration directory.
    
    Returns:
        str: Absolute path to configuration directory
    """
    app_root = get_app_root()
    config_dir = os.path.join(app_root, 'config')
    
    # Create directory if it doesn't exist
    if not os.path.exists(config_dir):
        try:
            os.makedirs(config_dir)
        except Exception as e:
            logging.error(f"Failed to create config directory: {e}")
    
    return config_dir

def get_config_path(filename='config.json'):
    """
    Get the path to a configuration file.
    
    Args:
        filename (str): Name of configuration file
        
    Returns:
        str: Absolute path to configuration file
    """
    return os.path.join(get_config_dir(), filename)

def get_cache_dir():
    """
    Get the cache directory.
    
    Returns:
        str: Absolute path to cache directory
    """
    app_root = get_app_root()
    cache_dir = os.path.join(app_root, 'cache')
    
    # Create directory if it doesn't exist
    if not os.path.exists(cache_dir):
        try:
            os.makedirs(cache_dir)
        except Exception as e:
            logging.error(f"Failed to create cache directory: {e}")
    
    return cache_dir

def get_cache_path(filename):
    """
    Get the path to a cache file.
    
    Args:
        filename (str): Name of cache file
        
    Returns:
        str: Absolute path to cache file
    """
    return os.path.join(get_cache_dir(), filename)

def get_logs_dir():
    """
    Get the logs directory.
    
    Returns:
        str: Absolute path to logs directory
    """
    app_root = get_app_root()
    logs_dir = os.path.join(app_root, 'logs')
    
    # Create directory if it doesn't exist
    if not os.path.exists(logs_dir):
        try:
            os.makedirs(logs_dir)
        except Exception as e:
            logging.error(f"Failed to create logs directory: {e}")
    
    return logs_dir

def get_log_path(filename='nest.log'):
    """
    Get the path to a log file.
    
    Args:
        filename (str): Name of log file
        
    Returns:
        str: Absolute path to log file
    """
    return os.path.join(get_logs_dir(), filename)

def get_assets_dir():
    """
    Get the assets directory.
    
    Returns:
        str: Absolute path to assets directory
    """
    app_root = get_app_root()
    return os.path.join(app_root, 'assets')

def get_asset_path(filename):
    """
    Get the path to an asset file.
    
    Args:
        filename (str): Path to asset file relative to assets directory
        
    Returns:
        str: Absolute path to asset file
    """
    return os.path.join(get_assets_dir(), filename)

def get_image_path(filename):
    """
    Get the path to an image file.
    
    Args:
        filename (str): Name of image file
        
    Returns:
        str: Absolute path to image file
    """
    return os.path.join(get_assets_dir(), 'images', filename)

def get_icon_path():
    """
    Get the path to the application icon.
    
    Returns:
        str: Absolute path to application icon
    """
    if platform.system() == "Windows":
        return get_image_path('icon.ico')
    else:
        # Try PNG first, fall back to ICO
        png_path = get_image_path('icon.png')
        if os.path.exists(png_path):
            return png_path
        return get_image_path('icon.ico')
Update Config Manager
pythondef load_config():
    """Load configuration from the config file."""
    from nest.utils.path_util import get_config_path
    
    config_path = get_config_path('config.json')
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)
            logging.info(f"Configuration loaded from {config_path}")
            return config
        else:
            logging.warning(f"Configuration file {config_path} not found, creating default")
            config = create_default_config()
            save_config(config)
            return config
    except Exception as e:
        logging.error(f"Error loading configuration: {e}")
        return create_default_config()

def save_config(config):
    """Save configuration to the config file."""
    from nest.utils.path_util import get_config_path
    
    config_path = get_config_path('config.json')
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        # Write to temporary file first
        temp_path = f"{config_path}.tmp"
        with open(temp_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        # Atomic rename
        os.replace(temp_path, config_path)
        
        logging.info(f"Configuration saved to {config_path}")
        return True
    except Exception as e:
        logging.error(f"Error saving configuration: {e}")
        return False
5. API Integration
API Client Updates
Ensure the RepairDesk API client handles Linux differences:
pythonclass RepairDeskClient:
    """Client for interacting with the RepairDesk API."""
    
    def __init__(self, api_key=None, base_url=None):
        """Initialize the RepairDesk API client."""
        from nest.utils.config_util import get_repairdesk_api_key, get_repairdesk_base_url
        
        self.api_key = api_key or get_repairdesk_api_key()
        self.base_url = base_url or get_repairdesk_base_url() or "https://api.repairdesk.co/api"
        
        if not self.api_key:
            logging.error("No API key provided. RepairDesk integration will be limited.")
    
    def get_all_tickets(self, limit=50, status=None):
        """
        Get all tickets from RepairDesk.
        
        Args:
            limit (int): Number of tickets to retrieve per page
            status (str): Filter tickets by status
            
        Returns:
            list: List of tickets
        """
        logging.info("Fetching all tickets from RepairDesk (this may take some time)")
        
        all_tickets = []
        page = 1
        
        while True:
            try:
                tickets = self._get_tickets_page(page, limit, status)
                if not tickets:
                    break
                
                all_tickets.extend(tickets)
                page += 1
                
                # Check if we've reached the end
                if len(tickets) < limit:
                    break
            except Exception as e:
                logging.error(f"Error fetching tickets page {page}: {e}")
                break
        
        logging.info(f"Fetched {len(all_tickets)} tickets from RepairDesk")
        
        # Update the local cache
        from nest.utils.path_util import get_cache_path
        cache_path = get_cache_path('ticket_cache.json')
        
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(cache_path), exist_ok=True)
            
            # Write to a temporary file first
            temp_path = f"{cache_path}.tmp"
            with open(temp_path, 'w') as f:
                json.dump(all_tickets, f, indent=2)
            
            # Atomic rename
            os.replace(temp_path, cache_path)
            
            logging.info(f"Updated ticket cache with {len(all_tickets)} tickets")
        except Exception as e:
            logging.error(f"Failed to update ticket cache: {e}")
        
        return all_tickets
Improve Ticket Upload
Update the diagnostic note upload function:
pythondef upload_diagnostic_note(self, ticket_id, note, type=1, is_flag=0):
    """
    Upload a diagnostic note to a ticket.
    
    Args:
        ticket_id (str): The numeric ticket ID
        note (str): The note content
        type (int): Note type (1=public, 2=private)
        is_flag (int): Flag status (0=normal, 1=flagged)
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Format ticket ID for logging
        if str(ticket_id).startswith('T-'):
            formatted_ticket_id = ticket_id
        else:
            formatted_ticket_id = f"T-{ticket_id}"
            
        logging.info(f"Uploading diagnostic note to ticket {formatted_ticket_id}")
        
        url = f"{self.base_url}/web/v1/ticket/addnote?api_key={self.api_key}"
        payload = {
            "id": ticket_id,
            "note": note,
            "type": type,
            "is_flag": is_flag,
        }
        
        response = requests.post(url, json=payload)
        
        if response.status_code == 200:
            result = response.json()
            
            # Check for different success response formats
            if isinstance(result, dict) and result.get('success'):
                logging.info(f"Diagnostic note uploaded successfully to ticket {formatted_ticket_id}")
                return True
            elif isinstance(result, list):
                # This is also a success case - the API returned all notes
                logging.info(f"Diagnostic note uploaded successfully to ticket {formatted_ticket_id}. API returned {len(result)} notes.")
                return True
            else:
                error_message = result.get('message', 'Unknown error')
                logging.error(f"Failed to upload diagnostic note: {error_message}")
                return False
        else:
            logging.error(f"Upload failed: status {response.status_code}, response: {response.text}")
            return False
    except Exception as e:
        logging.error(f"Exception during diagnostic note upload: {e}")
        return False
6. UI and Theming
Theme System
Create a cross-platform theme system:
python"""
Nest theme system.
Provides consistent branding and UI appearance across platforms.
"""

import os
import platform
import logging
import tkinter as tk
from tkinter import ttk, font

class NestTheme:
    """Theme manager for Nest application."""
    
    # Brand colors - MUST be preserved exactly
    PRIMARY_COLOR = "#017E84"  # RepairDesk teal
    SECONDARY_COLOR = "#1A1A1A"  # Slightly lighter panels
    BACKGROUND_COLOR = "#111111"  # Dark charcoal
    TEXT_COLOR = "#F5EBD0"  # Eggshell text
    ERROR_COLOR = "#E63946"  # Error red
    SUCCESS_COLOR = "#2A9D8F"  # Success green
    INACTIVE_COLOR = "#6C757D"  # Inactive gray
    
    def __init__(self, root):
        """Initialize the theme manager."""
        self.root = root
        self.style = ttk.Style()
        
        # Detect platform
        self.platform = platform.system()
        
        # Apply appropriate theme based on platform
        self._setup_base_theme()
        self._configure_fonts()
        self._configure_colors()
        self._configure_styles()
    
    def _setup_base_theme(self):
        """Set up the base theme based on platform."""
        available_themes = self.style.theme_names()
        
        if self.platform == "Windows":
            # Windows: Use vista or winnative
            if "vista" in available_themes:
                self.style.theme_use("vista")
            elif "winnative" in available_themes:
                self.style.theme_use("winnative")
            else:
                self.style.theme_use("default")
        elif self.platform == "Darwin":  # macOS
            # macOS: Use aqua if available
            if "aqua" in available_themes:
                self.style.theme_use("aqua")
            else:
                self.style.theme_use("default")
        else:
            # Linux: Use clam or alt
            if "clam" in available_themes:
                self.style.theme_use("clam")
            elif "alt" in available_themes:
                self.style.theme_use("alt")
            else:
                self.style.theme_use("default")
        
        logging.info(f"Using '{self.style.theme_use()}' UI theme")
    
    def _configure_fonts(self):
        """Configure application fonts."""
        # Default fonts
        default_font = font.nametofont("TkDefaultFont")
        text_font = font.nametofont("TkTextFont")
        fixed_font = font.nametofont("TkFixedFont")
        
        # Set font properties
        default_font.configure(size=10)
        text_font.configure(size=10)
        fixed_font.configure(size=10)
        
        # Create custom fonts
        self.heading_font = font.Font(family=default_font.cget("family"), size=14, weight="bold")
        self.subheading_font = font.Font(family=default_font.cget("family"), size=12, weight="bold")
        self.button_font = font.Font(family=default_font.cget("family"), size=10)
        self.small_font = font.Font(family=default_font.cget("family"), size=9)
    
    def _configure_colors(self):
        """Configure application colors."""
        # Configure root background
        self.root.configure(background=self.BACKGROUND_COLOR)
        
        # Store colors in a dictionary for easy access
        self.colors = {
            "primary": self.PRIMARY_COLOR,
            "secondary": self.SECONDARY_COLOR,
            "background": self.BACKGROUND_COLOR,
            "text": self.TEXT_COLOR,
            "error": self.ERROR_COLOR,
            "success": self.SUCCESS_COLOR,
            "inactive": self.INACTIVE_COLOR,
        }
    
    def _configure_styles(self):
        """Configure TTK styles."""
        # Frames
        self.style.configure("TFrame", background=self.BACKGROUND_COLOR)
        self.style.configure("Card.TFrame", background=self.SECONDARY_COLOR)
        
        # Labels
        self.style.configure("TLabel", background=self.BACKGROUND_COLOR, foreground=self.TEXT_COLOR)
        self.style.configure("Card.TLabel", background=self.SECONDARY_COLOR, foreground=self.TEXT_COLOR)
        self.style.configure("Heading.TLabel", font=self.heading_font)
        self.style.configure("Subheading.TLabel", font=self.subheading_font)
        
        # Buttons
        self.style.configure("TButton", 
                             background=self.PRIMARY_COLOR, 
                             foreground=self.TEXT_COLOR,
                             font=self.button_font)
        
        self.style.map("TButton",
                       background=[("active", self._adjust_color(self.PRIMARY_COLOR, 1.1))],
                       foreground=[("active", self.TEXT_COLOR)])
        
        # Error button
        self.style.configure("Error.TButton", 
                             background=self.ERROR_COLOR, 
                             foreground=self.TEXT_COLOR)
        
        self.style.map("Error.TButton",
                       background=[("active", self._adjust_color(self.ERROR_COLOR, 1.1))],
                       foreground=[("active", self.TEXT_COLOR)])
        
        # Success button
        self.style.configure("Success.TButton", 
                             background=self.SUCCESS_COLOR, 
                             foreground=self.TEXT_COLOR)
        
        self.style.map("Success.TButton",
                       background=[("active", self._adjust_color(self.SUCCESS_COLOR, 1.1))],
                       foreground=[("active", self.TEXT_COLOR)])
        
        # Entry
        self.style.configure("TEntry", 
                             fieldbackground=self._adjust_color(self.SECONDARY_COLOR, 1.2),
                             foreground=self.TEXT_COLOR)
        
        # Combobox
        self.style.configure("TCombobox", 
                             fieldbackground=self._adjust_color(self.SECONDARY_COLOR, 1.2),
                             foreground=self.TEXT_COLOR)
        
        # Notebook (tabs)
        self.style.configure("TNotebook", background=self.BACKGROUND_COLOR)
        self.style.configure("TNotebook.Tab", 
                             background=self.BACKGROUND_COLOR,
                             foreground=self.TEXT_COLOR,
                             padding=[10, 2])
        
        self.style.map("TNotebook.Tab",
                       background=[("selected", self.PRIMARY_COLOR),
                                   ("active", self._adjust_color(self.PRIMARY_COLOR, 0.9))],
                       foreground=[("selected", self.TEXT_COLOR),
                                   ("active", self.TEXT_COLOR)])
        
        # Progressbar
        self.style.configure("TProgressbar", 
                             background=self.PRIMARY_COLOR,
                             troughcolor=self._adjust_color(self.BACKGROUND_COLOR, 1.2))
    
    def _adjust_color(self, hex_color, factor):
        """
        Adjust color brightness by a factor.
        
        Args:
            hex_color (str): Hex color code (e.g., #RRGGBB)
            factor (float): Factor to multiply RGB values by (>1 for lighter, <1 for darker)
            
        Returns:
            str: Adjusted hex color code
        """
        # Convert hex to RGB
        hex_color = hex_color.lstrip('#')
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        
        # Adjust brightness
        r = min(255, max(0, int(r * factor)))
        g = min(255, max(0, int(g * factor)))
        b = min(255, max(0, int(b * factor)))
        
        # Convert back to hex
        return f"#{r:02x}{g:02x}{b:02x}"
    
    def get_color(self, name):
        """
        Get a theme color by name.
        
        Args:
            name (str): Color name
            
        Returns:
            str: Hex color code
        """
        return self.colors.get(name, self.BACKGROUND_COLOR)
Update main.py to use proper theme initialization
pythondef initialize_app():
    """Initialize the Nest application."""
    # Create root window
    root = tk.Tk()
    root.title("RepairDesk Nest")
    root.geometry("1024x768")
    
    # Set window icon
    try:
        from nest.utils.path_util import get_icon_path
        icon_path = get_icon_path()
        
        if icon_path and os.path.exists(icon_path):
            if platform.system() == "Windows":
                root.iconbitmap(icon_path)
            else:
                # Linux/macOS - use PhotoImage
                icon_img = tk.PhotoImage(file=icon_path)
                root.iconphoto(True, icon_img)
        else:
            logging.debug("App icon not found. Using default.")
    except Exception as e:
        logging.debug(f"Error setting app icon: {e}")
    
    # Apply theme
    from nest.ui.theme.theme import NestTheme
    theme = NestTheme(root)
    
    # Set theme as attribute of root for access by other modules
    root.theme = theme
    
    return root
7. Testing and Validation
Test Script
Create a comprehensive test script to validate Linux port:
python#!/usr/bin/env python3
"""
Nest Linux Port Validation Script
This script tests all critical functionality of the Nest application on Linux.
"""

import os
import sys
import platform
import logging
import json
import tkinter as tk
from tkinter import ttk

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def check_python_version():
    """Check Python version compatibility."""
    version = sys.version_info
    logging.info(f"Python version: {platform.python_version()}")
    
    if version.major == 3 and version.minor >= 10:
        logging.info("✅ Python version check passed")
        return True
    else:
        logging.error(f"❌ Python version incompatible - requires 3.10 or higher")
        return False

def check_platform():
    """Check platform compatibility."""
    system = platform.system()
    logging.info(f"Platform: {system} {platform.release()}")
    
    if system == "Linux":
        logging.info("✅ Platform check passed")
        return True
    else:
        logging.warning(f"⚠️ Platform check - expected Linux, got {system}")
        return False

def check_dependencies():
    """Check if required dependencies are installed."""
    required_modules = [
        "tkinter",
        "PIL",
        "requests",
        "psutil",
        "cryptography",
    ]
    
    missing_modules = []
    
    for module in required_modules:
        try:
            if module == "PIL":
                __import__("PIL.Image")
            else:
                __import__(module)
            logging.info(f"✅ Module {module} is available")
        except ImportError:
            missing_modules.append(module)
            logging.error(f"❌ Module {module} is missing")
    
    if missing_modules:
        logging.error(f"Missing dependencies: {', '.join(missing_modules)}")
        logging.error("Install missing dependencies with: pip install " + " ".join(missing_modules))
        return False
    
    return True

def check_path_structure():
    """Check if the application path structure is correct."""
    # Check if we're in the right directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Look for nest module
    nest_dir = os.path.join(current_dir, "nest")
    if not os.path.isdir(nest_dir):
        logging.error(f"❌ Could not find 'nest' directory at {nest_dir}")
        return False
    
    # Check for critical subdirectories
    critical_dirs = ["ui", "utils", "managers", "config"]
    missing_dirs = []
    
    for dir_name in critical_dirs:
        dir_path = os.path.join(nest_dir, dir_name)
        if not os.path.isdir(dir_path):
            missing_dirs.append(dir_name)
    
    if missing_dirs:
        logging.error(f"❌ Missing critical directories: {', '.join(missing_dirs)}")
        return False
    
    # Check for main.py
    main_path = os.path.join(nest_dir, "main.py")
    if not os.path.isfile(main_path):
        logging.error(f"❌ Could not find 'main.py' at {main_path}")
        return False
    
    logging.info("✅ Application path structure check passed")
    return True

def check_config():
    """Check if configuration can be loaded."""
    try:
        # Add parent directory to path for module imports
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        
        # Try to import and load config
        from nest.utils.config_util import load_config
        
        config = load_config()
        if config:
            logging.info(f"✅ Configuration loaded successfully")
            
            # Check for API key
            api_key = config.get("api_key")
            if api_key:
                logging.info(f"✅ RepairDesk API key found in configuration")
            else:
                logging.warning(f"⚠️ No RepairDesk API key found in configuration")
            
            return True
        else:
            logging.error(f"❌ Failed to load configuration")
            return False
    except Exception as e:
        logging.error(f"❌ Error checking configuration: {e}")
        return False

def test_ui_initialization():
    """Test if Tkinter UI can be initialized."""
    try:
        # Create root window
        root = tk.Tk()
        root.title("Nest Test")
        
        # Check if we can create UI components
        frame = ttk.Frame(root)
        label = ttk.Label(frame, text="Test Label")
        button = ttk.Button(frame, text="Test Button")
        
        # Clean up
        root.destroy()
        
        logging.info("✅ UI initialization test passed")
        return True
    except Exception as e:
        logging.error(f"❌ UI initialization test failed: {e}")
        return False

def test_repairdesk_api():
    """Test RepairDesk API connection."""
    try:
        # Add parent directory to path for module imports
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        
        # Try to import and initialize API client
        from nest.utils.config_util import get_repairdesk_api_key
        from nest.utils.repairdesk_api import RepairDeskClient
        
        api_key = get_repairdesk_api_key()
        if not api_key:
            logging.warning("⚠️ No API key found, skipping API test")
            return None
        
        client = RepairDeskClient(api_key=api_key)
        
        # Test employees endpoint
        logging.info("Testing RepairDesk API employees endpoint...")
        employees = client.get_employees()
        
        if employees and isinstance(employees, list):
            logging.info(f"✅ RepairDesk API employees endpoint working: {len(employees)} employees retrieved")
        else:
            logging.error(f"❌ RepairDesk API employees endpoint failed")
            return False
        
        # Test ticket endpoint
        logging.info("Testing RepairDesk API ticket endpoint...")
        ticket_id = "12353"  # Use a known ticket ID for testing
        logging.info(f"Testing RepairDesk integration with ticket T-{ticket_id}")
        
        numeric_id = client.get_numeric_ticket_id(f"T-{ticket_id}")
        if numeric_id:
            logging.info(f"✅ RepairDesk API ticket lookup successful: T-{ticket_id} -> {numeric_id}")
        else:
            logging.error(f"❌ Failed to look up ticket T-{ticket_id}")
            
            # Try fallback using cache
            logging.info("Checking ticket cache for fallback...")
            try:
                from nest.utils.path_util import get_cache_path
                cache_path = get_cache_path('ticket_cache.json')
                
                if os.path.exists(cache_path):
                    with open(cache_path, 'r') as f:
                        tickets = json.load(f)
                    
                    for ticket in tickets:
                        if ticket.get('summary', {}).get('order_id') == f"T-{ticket_id}":
                            numeric_id = ticket.get('summary', {}).get('id')
                            logging.info(f"✅ Found ticket T-{ticket_id} in cache with internal ID: {numeric_id}")
                            break
            except Exception as e:
                logging.error(f"❌ Error checking ticket cache: {e}")
            
            if not numeric_id:
                return False
        
        return True
    except Exception as e:
        logging.error(f"❌ RepairDesk API test failed: {e}")
        return False

def run_all_tests():
    """Run all validation tests."""
    logging.info("Starting Nest Linux port validation tests")
    logging.info(f"Date/Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logging.info("-" * 50)
    
    # Track test results
    results = {
        "python_version": check_python_version(),
        "platform": check_platform(),
        "dependencies": check_dependencies(),
        "path_structure": check_path_structure(),
        "config": check_config(),
        "ui_initialization": test_ui_initialization(),
        "repairdesk_api": test_repairdesk_api(),
    }
    
    # Print summary
    logging.info("\nTest Results Summary:")
    logging.info("-" * 50)
    
    all_passed = True
    for test_name, result in results.items():
        if result is True:
            status = "✅ PASSED"
        elif result is False:
            status = "❌ FAILED"
            all_passed = False
        else:
            status = "⚠️ SKIPPED"
        
        logging.info(f"{test_name.ljust(20)}: {status}")
    
    logging.info("-" * 50)
    
    if all_passed:
        logging.info("🎉 All tests passed! The Nest Linux port is working correctly.")
        return 0
    else:
        logging.error("❌ Some tests failed. Please fix the issues and run the tests again.")
        return 1

if __name__ == "__main__":
    import datetime
    sys.exit(run_all_tests())
8. Distribution and Deployment
Create a build script
python#!/usr/bin/env python3
"""
Nest Linux Build Script
Creates distribution packages for easy installation on Linux.
"""

import os
import sys
import subprocess
import shutil
import argparse
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Nest Linux Build Script")
    
    parser.add_argument("--dist-dir", type=str, default="dist",
                        help="Directory for distribution files")
    
    parser.add_argument("--version", type=str, default="1.0.0",
                        help="Version number for package")
    
    parser.add_argument("--deb", action="store_true", 
                        help="Build Debian package")
    
    parser.add_argument("--rpm", action="store_true",
                        help="Build RPM package")
    
    parser.add_argument("--tar", action="store_true",
                        help="Build tar.gz archive")
    
    parser.add_argument("--clean", action="store_true",
                        help="Clean build directory before building")
    
    args = parser.parse_args()
    
    # If no package type specified, build tar.gz by default
    if not (args.deb or args.rpm or args.tar):
        args.tar = True
    
    return args

def check_requirements():
    """Check if build requirements are installed."""
    required_tools = []
    
    if args.deb:
        required_tools.append("dpkg-deb")
    
    if args.rpm:
        required_tools.append("rpmbuild")
    
    for tool in required_tools:
        if shutil.which(tool) is None:
            logging.error(f"Required tool '{tool}' not found. Please install it.")
            return False
    
    return True

def clean_build_dir(dist_dir):
    """Clean build directory."""
    logging.info(f"Cleaning build directory: {dist_dir}")
    
    if os.path.exists(dist_dir):
        shutil.rmtree(dist_dir)
    
    os.makedirs(dist_dir)

def create_tarball(args):
    """Create tar.gz archive."""
    logging.info("Creating tar.gz archive...")
    
    archive_name = f"nest-{args.version}.tar.gz"
    archive_path = os.path.join(args.dist_dir, archive_name)
    
    # Create archive
    cmd = [
        "tar",
        "-czf",
        archive_path,
        "--exclude=__pycache__",
        "--exclude=*.pyc",
        "--exclude=.git",
        "--exclude=dist",
        "--exclude=build",
        "."
    ]
    
    subprocess.run(cmd, check=True)
    
    logging.info(f"Created tar.gz archive: {archive_path}")
    return archive_path

def create_deb_package(args):
    """Create Debian package."""
    logging.info("Creating Debian package...")
    
    package_name = f"nest-{args.version}"
    package_dir = os.path.join(args.dist_dir, package_name)
    
    # Create package directory structure
    os.makedirs(os.path.join(package_dir, "DEBIAN"), exist_ok=True)
    os.makedirs(os.path.join(package_dir, "usr/share/nest"), exist_ok=True)
    os.makedirs(os.path.join(package_dir, "usr/bin"), exist_ok=True)
    os.makedirs(os.path.join(package_dir, "usr/share/applications"), exist_ok=True)
    os.makedirs(os.path.join(package_dir, "usr/share/pixmaps"), exist_ok=True)
    
    # Create control file
    control_content = f"""Package: nest
Version: {args.version}
Section: utils
Priority: optional
Architecture: all
Depends: python3 (>= 3.10), python3-tk, python3-pip, python3-venv
Maintainer: RepairDesk <support@repairdesk.co>
Description: RepairDesk Nest
 Desktop companion application for RepairDesk repair shop management system.
"""
    
    with open(os.path.join(package_dir, "DEBIAN/control"), "w") as f:
        f.write(control_content)
    
    # Create postinst script
    postinst_content = """#!/bin/bash
set -e

# Create virtual environment and install dependencies
cd /usr/share/nest
python3 -m venv .venv
.venv/bin/pip install --upgrade pip wheel setuptools
.venv/bin/pip install -r requirements.txt

# Set permissions
chmod +x /usr/bin/nest
chmod +x /usr/share/nest/run_nest.sh

exit 0
"""
    
    with open(os.path.join(package_dir, "DEBIAN/postinst"), "w") as f:
        f.write(postinst_content)
    
    os.chmod(os.path.join(package_dir, "DEBIAN/postinst"), 0o755)
    
    # Copy application files
    cmd = [
        "rsync",
        "-a",
        "--exclude=__pycache__",
        "--exclude=*.pyc",
        "--exclude=.git",
        "--exclude=dist",
        "--exclude=build",
        ".",
        os.path.join(package_dir, "usr/share/nest/")
    ]
    
    subprocess.run(cmd, check=True)
    
    # Create launcher script
    launcher_content = """#!/bin/bash
/usr/share/nest/run_nest.sh "$@"
"""
    
    with open(os.path.join(package_dir, "usr/bin/nest"), "w") as f:
        f.write(launcher_content)
    
    os.chmod(os.path.join(package_dir, "usr/bin/nest"), 0o755)
    
    # Copy desktop file
    desktop_content = """[Desktop Entry]
Name=RepairDesk Nest
Comment=RepairDesk repair shop management system
Exec=nest
Icon=nest
Terminal=false
Type=Application
Categories=Utility;Office;
"""
    
    with open(os.path.join(package_dir, "usr/share/applications/nest.desktop"), "w") as f:
        f.write(desktop_content)
    
    # Copy icon
    icon_path = os.path.join("assets", "images", "icon.png")
    if os.path.exists(icon_path):
        shutil.copy2(icon_path, os.path.join(package_dir, "usr/share/pixmaps/nest.png"))
    
    # Build package
    cmd = [
        "dpkg-deb",
        "--build",
        package_dir,
        os.path.join(args.dist_dir, f"nest_{args.version}_all.deb")
    ]
    
    subprocess.run(cmd, check=True)
    
    logging.info(f"Created Debian package: {os.path.join(args.dist_dir, f'nest_{args.version}_all.deb')}")
    return os.path.join(args.dist_dir, f"nest_{args.version}_all.deb")

def create_rpm_package(args):
    """Create RPM package."""
    logging.info("Creating RPM package...")
    
    # Create RPM build directories
    rpm_build_dir = os.path.join(args.dist_dir, "rpm-build")
    os.makedirs(os.path.join(rpm_build_dir, "BUILD"), exist_ok=True)
    os.makedirs(os.path.join(rpm_build_dir, "RPMS"), exist_ok=True)
    os.makedirs(os.path.join(rpm_build_dir, "SOURCES"), exist_ok=True)
    os.makedirs(os.path.join(rpm_build_dir, "SPECS"), exist_ok=True)
    os.makedirs(os.path.join(rpm_build_dir, "SRPMS"), exist_ok=True)
    
    # Create tar.gz source
    tarball_path = create_tarball(args)
    shutil.copy2(tarball_path, os.path.join(rpm_build_dir, "SOURCES"))
    
    # Create spec file
    spec_content = f"""Name:           nest
Version:        {args.version}
Release:        1%{{?dist}}
Summary:        RepairDesk Nest

License:        Proprietary
URL:            https://repairdesk.co
Source0:        nest-{args.version}.tar.gz

BuildArch:      noarch
Requires:       python3 >= 3.10
Requires:       python3-tkinter
Requires:       python3-pip

%description
Desktop companion application for RepairDesk repair shop management system.

%prep
%setup -q

%install
mkdir -p %{{buildroot}}/usr/share/nest
mkdir -p %{{buildroot}}/usr/bin
mkdir -p %{{buildroot}}/usr/share/applications
mkdir -p %{{buildroot}}/usr/share/pixmaps

cp -r * %{{buildroot}}/usr/share/nest/

# Create launcher script
cat > %{{buildroot}}/usr/bin/nest << 'EOF'
#!/bin/bash
/usr/share/nest/run_nest.sh "$@"
EOF
chmod +x %{{buildroot}}/usr/bin/nest

# Create desktop file
cat > %{{buildroot}}/usr/share/applications/nest.desktop << 'EOF'
[Desktop Entry]
Name=RepairDesk Nest
Comment=RepairDesk repair shop management system
Exec=nest
Icon=nest
Terminal=false
Type=Application
Categories=Utility;Office;
EOF

# Copy icon
if [ -f assets/images/icon.png ]; then
    cp assets/images/icon.png %{{buildroot}}/usr/share/pixmaps/nest.png
fi

%post
cd /usr/share/nest
python3 -m venv .venv
.venv/bin/pip install --upgrade pip wheel setuptools
.venv/bin/pip install -r requirements.txt

%files
%attr(755, root, root) /usr/bin/nest
/usr/share/nest
/usr/share/applications/nest.desktop
/usr/share/pixmaps/nest.png

%changelog
* {datetime.datetime.now().strftime('%a %b %d %Y')} RepairDesk <support@repairdesk.co> - {args.version}-1
- Initial package
"""
    
    with open(os.path.join(rpm_build_dir, "SPECS/nest.spec"), "w") as f:
        f.write(spec_content)
    
    # Build RPM
    cmd = [
        "rpmbuild",
        "-bb",
        "--define", f"_topdir {os.path.abspath(rpm_build_dir)}",
        os.path.join(rpm_build_dir, "SPECS/nest.spec")
    ]
    
    subprocess.run(cmd, check=True)
    
    # Copy RPM to dist directory
    rpm_path = None
    for root, _, files in os.walk(os.path.join(rpm_build_dir, "RPMS")):
        for file in files:
            if file.endswith(".rpm"):
                rpm_path = os.path.join(root, file)
                shutil.copy2(rpm_path, args.dist_dir)
                logging.info(f"Created RPM package: {os.path.join(args.dist_dir, file)}")
                return os.path.join(args.dist_dir, file)
    
    logging.error("No RPM package found after build")
    return None

def main(args):
    """Main build function."""
    # Check requirements
    if not check_requirements():
        return 1
    
    # Clean build directory if requested
    if args.clean:
        clean_build_dir(args.dist_dir)
    else:
        os.makedirs(args.dist_dir, exist_ok=True)
    
    # Build packages
    results = {}
    
    if args.tar:
        try:
            results["tar"] = create_tarball(args)
        except Exception as e:
            logging.error(f"Error creating tar.gz archive: {e}")
            results["tar"] = None
    
    if args.deb:
        try:
            results["deb"] = create_deb_package(args)
        except Exception as e:
            logging.error(f"Error creating Debian package: {e}")
            results["deb"] = None
    
    if args.rpm:
        try:
            results["rpm"] = create_rpm_package(args)
        except Exception as e:
            logging.error(f"Error creating RPM package: {e}")
            results["rpm"] = None
    
    # Print summary
    logging.info("\nBuild Results:")
    logging.info("-" * 50)
    
    for package_type, path in results.items():
        if path:
            status = f"✅ Created: {path}"
        else:
            status = "❌ Failed"
        
        logging.info(f"{package_type.upper().ljust(10)}: {status}")
    
    logging.info("-" * 50)
    
    # Check if any build failed
    if any(path is None for path in results.values()):
        return 1
    
    return 0

if __name__ == "__main__":
    import datetime
    args = parse_args()
    sys.exit(main(args))
9. Troubleshooting
Create a troubleshooting guide for common Linux port issues:
markdown# Nest Linux Port Troubleshooting Guide

## Common Issues and Solutions

### 1. Missing Dependencies

**Symptoms**: Application crashes on startup with ImportError.

**Solution**:
```bash
# Ubuntu/Debian
sudo apt install python3-tk python3-dev libffi-dev libssl-dev

# Activate virtual environment
source .venv/bin/activate

# Install Python dependencies
pip install --upgrade pip 
pip install -r requirements.txt
2. UI Rendering Issues
Symptoms: UI elements look wrong or theme doesn't apply correctly.
Solution:

Check that Tkinter is properly installed with Tk 8.6 or higher:
bashpython3 -c "import tkinter; print(tkinter.TkVersion)"
The version should be at least 8.6.
Try a different theme in the theme manager:
python# In nest/ui/theme/theme.py, modify _setup_base_theme method
# Try a different theme like:
self.style.theme_use("clam")  # or "alt" or "default"


3. Path Issues
Symptoms: Application can't find configuration files or modules.
Solution:

Make sure to use the provided launcher script which sets PYTHONPATH
Check that all paths are constructed using os.path.join() for platform independence
Verify that path_util.py is being used for all path operations
Run app with logging enabled to see the paths being used:
bashPYTHONPATH=$(pwd) python -m nest.main --verbose


4. RepairDesk API Connection Issues
Symptoms: Can't authenticate with RepairDesk or retrieve data.
Solution:

Verify your API key is correctly saved in config.json
Check your network connection and firewall settings
Make sure API endpoints include the required /web/v1/ prefix
Check response status codes and error messages in the logs
Test API connection independently:
bashcurl -X GET "https://api.repairdesk.co/api/web/v1/employees?api_key=YOUR_API_KEY"


5. Hardware Detection Problems
Symptoms: System information is empty or incorrect.
Solution:

The Linux implementation uses /proc filesystem to get hardware info
Make sure your user has permission to read these files:
bashsudo chmod +r /proc/cpuinfo /proc/meminfo

Check if information is available directly:
bashcat /proc/cpuinfo
cat /proc/meminfo
cat /sys/class/dmi/id/sys_vendor


6. Font Issues
Symptoms: Text appears too small, too large, or with wrong font.
Solution:

The theme system should handle fonts, but Linux distributions might have different defaults
Modify font configuration in nest/ui/theme/theme.py to use platform-specific font sizes:
pythonif platform.system() == "Linux":
    default_font.configure(size=11)  # Slightly larger for Linux


7. Ticket Cache Problems
Symptoms: Can't find tickets or get "Ticket not found" errors.
Solution:

Verify ticket_cache.json exists and has valid content
Make sure file paths are correct for Linux:
pythoncache_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'ticket_cache.json')

Refresh the cache manually:
bashrm ticket_cache.json  # Then restart the application


8. Virtual Environment Issues
Symptoms: Application can't find installed packages even after pip install.
Solution:

Make sure virtual environment is activated:
bashsource .venv/bin/activate

Check that environment is working correctly:
bashwhich python  # Should point to .venv/bin/python
pip list  # Should show installed packages

If necessary, recreate the virtual environment:
bashrm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt


9. Permission Issues
Symptoms: Application can't write to configuration or log files.
Solution:

Check file permissions:
bashls -la config/
ls -la logs/

Fix permissions if needed:
bashchmod -R 755 config/
chmod -R 755 logs/

Make sure directories exist and are writable:
pythonos.makedirs("config", exist_ok=True)
os.makedirs("logs", exist_ok=True)



## 10. Performance Optimization

```python
"""
Performance optimization tips for Nest on Linux.
"""

# 1. Optimize module imports
# --------------------------
# Lazy loading of heavy modules saves memory and startup time

# Instead of this at the top level:
import wmi  # Windows-only module

# Do this:
def get_system_info():
    if platform.system() == "Windows":
        try:
            import wmi  # Only import when needed on Windows
            # Windows-specific code
        except ImportError:
            # Fallback
            pass
    else:
        # Linux-specific code
        pass

# 2. Use threading for I/O operations
# ----------------------------------
# Network and disk operations should be threaded to keep UI responsive

def fetch_data_in_background():
    # Don't do this in UI thread:
    # data = api_client.get_all_tickets()  # Blocks UI
    
    # Do this instead:
    import threading
    
    def background_fetch():
        try:
            data = api_client.get_all_tickets()
            # Use after() to update UI from background thread
            self.after(0, lambda: self.update_ui_with_data(data))
        except Exception as e:
            self.after(0, lambda: self.show_error(str(e)))
    
    threading.Thread(target=background_fetch, daemon=True).start()

# 3. Cache heavy computations
# --------------------------
# Use functools.lru_cache for expensive operations

from functools import lru_cache

@lru_cache(maxsize=32)
def get_cpu_info():
    """
    Expensive operation to get CPU info.
    Results are cached to avoid repeated parsing of /proc/cpuinfo.
    """
    # ... implementation ...
    return cpu_info

# 4. Image handling optimization
# ----------------------------
# Only load images when needed and at appropriate sizes

def optimize_image_loading(image_path, target_width=None, target_height=None):
    """Load and optionally resize an image efficiently."""
    from PIL import Image, ImageTk
    
    # Open image without loading it fully into memory
    with Image.open(image_path) as img:
        # Only resize if needed
        if target_width and target_height:
            img = img.resize((target_width, target_height), Image.LANCZOS)
        
        # Convert to Tkinter PhotoImage
        photo = ImageTk.PhotoImage(img)
    
    return photo

# 5. Avoid blocking UI during application startup
# ---------------------------------------------
# Load non-essential components after UI is shown

def deferred_loading():
    """Load non-critical components after UI is shown."""
    # Show a loading indicator in UI first
    loading_label = ttk.Label(root, text="Loading additional components...")
    loading_label.pack()
    root.update()
    
    def load_in_background():
        try:
            # Load non-critical components
            load_plugins()
            fetch_initial_data()
            
            # Update UI from main thread
            root.after(0, lambda: [
                loading_label.destroy(),
                show_complete_ui()
            ])
        except Exception as e:
            root.after(0, lambda: show_error_message(str(e)))
    
    # Start background loading
    import threading
    threading.Thread(target=load_in_background, daemon=True).start()

# 6. Reduce memory consumption
# --------------------------
# Clean up large objects when no longer needed

def cleanup_large_data():
    """Release memory from large objects when finished."""
    import gc
    
    # Delete large data
    del self.large_dataset
    
    # Suggest garbage collection
    gc.collect()

# 7. Linux-specific optimizations
# -----------------------------

def optimize_for_linux():
    """Linux-specific performance optimizations."""
    if platform.system() == "Linux":
        # Reduce Tkinter idle tasks frequency
        root.tk.eval('set ::tk::MouseWheelFactor 2')  # More efficient scrolling
        
        # Use native theme for better performance
        style = ttk.Style()
        if "clam" in style.theme_names():
            style.theme_use("clam")
This comprehensive guide should give you everything you need for a successful Linux port of Nest 2.0, with special attention to the RepairDesk API integration that we fixed. The guide covers all aspects from environment setup to distribution, with detailed code examples for each section.
By following these instructions, your Linux port will maintain all the functionality of the Windows version while properly handling platform-specific differences. The RepairDesk API integration will work correctly, including the ticket lookup and comment posting that you highlighted as critical features.
