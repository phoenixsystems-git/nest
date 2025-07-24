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
- **Cross-Platform Support**: Native Windows, macOS, and WinPE compatibility

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

For additional assistance, please ensure you have the latest version installed.

---
