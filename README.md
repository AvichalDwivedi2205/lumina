# Lumina Agent - WorkOS AuthKit Authentication

FastAPI application with WorkOS AuthKit authentication providing unified login for all authentication methods.

## Overview

This application uses **WorkOS AuthKit** - a unified authentication interface that automatically handles all authentication providers you've enabled in your WorkOS dashboard:

- **Google OAuth**
- **Email/Password**
- **Any other providers** you enable in WorkOS

**Key Feature**: Single `/auth/login` endpoint that redirects to AuthKit, which presents users with all available authentication options in a unified interface.

## Setup Instructions

### 1. Environment Configuration

Copy the environment example and configure your settings:

```bash
cp env-example.txt .env
```

Configure your `.env` file with:

```env
# WorkOS Configuration
WORKOS_API_KEY=sk_test_your_api_key_here
WORKOS_CLIENT_ID=client_your_client_id_here
WORKOS_REDIRECT_URI=http://localhost:8000/auth/callback

# Application Settings
APP_NAME=Lumina Agent
APP_VERSION=1.0.0
LOG_LEVEL=INFO
```

### 2. Install Dependencies

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. WorkOS Dashboard Configuration

Configure the following in your WorkOS Dashboard:

#### Required Settings:
1. **Redirect URI**: `http://localhost:8000/auth/callback`
2. **Initiate Login URL**: `http://localhost:8000/auth/login`

#### Enable Authentication Methods:
- Go to **Authentication** section in WorkOS Dashboard
- Enable desired methods (Email/Password is enabled by default)
- For Google OAuth: Enable in **Social Login** section

### 4. Run the Application

```bash
python3 main.py
```

The application will start at: http://localhost:8000

## API Endpoints

### Authentication Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/auth/login` | GET | **Unified login endpoint** - redirects to AuthKit with all enabled auth methods |
| `/auth/callback` | GET | OAuth callback handler |
| `/auth/profile` | GET | Get user profile (requires authentication) |
| `/auth/logout` | POST | Logout user |
| `/auth/refresh` | POST | Refresh access token |
| `/auth/status` | GET | Check authentication status |
| `/auth/providers` | GET | Get available authentication providers |
| `/auth/config` | GET | Get public authentication configuration |

### Application Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Root endpoint with app info |
| `/health` | GET | Health check |

## Authentication Flow

### 1. Initiate Login
```bash
curl -X GET "http://localhost:8000/auth/login"
```
- Redirects to WorkOS AuthKit
- AuthKit shows all enabled authentication methods
- User chooses their preferred method (Google, email/password, etc.)

### 2. Handle Callback
After authentication, WorkOS redirects to `/auth/callback` with an authorization code.

### 3. Use Session
Use the returned `session_id` as a Bearer token:
```bash
curl -H "Authorization: Bearer <session_id>" http://localhost:8000/auth/profile
```

## Testing the Application

### 1. Test Public Endpoints
```bash
# Root endpoint
curl http://localhost:8000/

# Health check
curl http://localhost:8000/health

# Available providers
curl http://localhost:8000/auth/providers

# Public config
curl http://localhost:8000/auth/config

# Auth status (unauthenticated)
curl http://localhost:8000/auth/status
```

### 2. Test Authentication Flow
```bash
# Initiate login (will redirect to AuthKit)
curl -v http://localhost:8000/auth/login

# After completing login in browser, test protected endpoints
curl -H "Authorization: Bearer <your_session_id>" http://localhost:8000/auth/profile
```

## Key Features

### Unified Authentication
- **Single login endpoint** (`/auth/login`) handles all authentication methods
- **WorkOS AuthKit** automatically detects and shows available providers
- **No separate endpoints** needed for different authentication methods

### Supported Authentication Methods
- **Email/Password** (enabled by default)
- **Google OAuth** (configure in WorkOS dashboard)
- **Other OAuth providers** (enable in WorkOS dashboard as needed)

### Session Management
- **In-memory sessions** (suitable for development)
- **Bearer token authentication** using session IDs
- **Token refresh** capability

## Production Considerations

### Security
- Replace in-memory session storage with Redis or database
- Use HTTPS for all endpoints
- Configure CORS appropriately
- Use secure session management

### WorkOS Configuration
- Use production API keys
- Configure production redirect URIs
- Set up custom domains for AuthKit
- Enable appropriate authentication methods

## Troubleshooting

### Common Issues

1. **"module 'workos.user_management' has no attribute 'get_authorization_url'"**
   - Ensure you have the latest WorkOS SDK: `pip install --upgrade workos`
   - Check that User Management is activated in WorkOS Dashboard

2. **Authentication endpoints return errors**
   - Verify WorkOS API key and Client ID in `.env`
   - Check redirect URI configuration in WorkOS Dashboard
   - Ensure authentication methods are enabled in WorkOS Dashboard

3. **"Command 'python' not found"**
   - Use `python3` instead of `python` on Ubuntu/Linux systems

### Testing Commands

```bash
# Test all public endpoints
curl http://localhost:8000/ && \
curl http://localhost:8000/health && \
curl http://localhost:8000/auth/providers && \
curl http://localhost:8000/auth/config && \
curl http://localhost:8000/auth/status

# Test login redirect
curl -v http://localhost:8000/auth/login
```

## Architecture

```
User → /auth/login → WorkOS AuthKit → User chooses method → Authentication → /auth/callback → Session created
```

WorkOS AuthKit handles:
- User interface for authentication
- Multiple authentication providers
- Security and validation
- Redirect back to your application

Your application handles:
- Session management
- Protected routes
- Business logic

## Next Steps

1. **Complete WorkOS Dashboard setup**
2. **Test authentication flow**
3. **Implement frontend integration**
4. **Add business logic and protected routes**
5. **Configure production environment** 