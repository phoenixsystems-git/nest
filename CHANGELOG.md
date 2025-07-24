# Nest Changelog

## [v1.2.0] - 2025-05-12

### Major Changes - Authentication System

- **Authentication Pivot**: Completely rebuilt authentication system using official RepairDesk API endpoints
- **Compatibility Handling**: Added fallback mechanism to handle both new and legacy API endpoints
- **Two-Pane Login**: New streamlined login UI with store selection and employee authentication
- **API Key Management**: Secure storage of API keys with encryption via the ConfigManager
- **Typed API Models**: Added proper typing for all API requests and responses
- **Session Management**: New SessionManager to properly track user sessions

### Features

- Store name normalization ensures consistent handling of store slugs in all formats
- PIN entry now auto-submits on 4th digit for smoother login experience
- Error rate limiting and retry logic for API requests
- Caching layer for frequently accessed API data
- Clear error messages for connection issues

### Security Improvements

- API keys are now encrypted using Fernet encryption
- Restricted permissions on key storage files
- Auto logout on session expiration
- Proper handling of lockouts after failed PIN attempts

### Technical Debt

- Removed deprecated authentication code paths
- Consolidated API request handling
- Standardized error handling across all API interactions
- Improved logging for better debugging

### Known Issues

- The new v1 API endpoint (`{store_slug}.repairdesk.co/api/v1`) currently returns 404, fallback mechanism handles this automatically
- Will need to update once RepairDesk fully activates their new endpoints
