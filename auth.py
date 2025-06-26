import os
import uuid
import secrets
from typing import Optional, Dict, Any, List
from workos import WorkOSClient
from fastapi import HTTPException, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from config import settings
import logging

logger = logging.getLogger(__name__)

# Configure WorkOS Client
workos_client = WorkOSClient(
    api_key=settings.WORKOS_API_KEY,
    client_id=settings.WORKOS_CLIENT_ID
)

# Security scheme
security = HTTPBearer()

# In-memory session store (replace with Redis/database in production)
sessions: Dict[str, Dict[str, Any]] = {}

class AuthManager:
    """Authentication manager for WorkOS integration"""
    
    def __init__(self):
        self.client_id = settings.WORKOS_CLIENT_ID
        self.redirect_uri = settings.WORKOS_REDIRECT_URI
        
    def get_authorization_url(self, 
                            provider: Optional[str] = None,
                            connection_id: Optional[str] = None,
                            organization_id: Optional[str] = None,
                            domain_hint: Optional[str] = None,
                            login_hint: Optional[str] = None,
                            state: Optional[str] = None) -> str:
        """
        Generate authorization URL for WorkOS AuthKit
        
        Args:
            provider: Should be 'authkit' for unified authentication
            connection_id: WorkOS connection ID for SSO
            organization_id: Organization ID for SSO
            domain_hint: Domain hint for SSO
            login_hint: Login hint (email) for authentication
            state: State parameter for CSRF protection
            
        Returns:
            Authorization URL for WorkOS AuthKit
        """
        
        # Generate state if not provided
        if not state:
            state = secrets.token_urlsafe(32)
        
        # Build authorization URL using the correct method signature
        auth_url = workos_client.user_management.get_authorization_url(
            provider=provider,
            redirect_uri=self.redirect_uri,
            connection_id=connection_id,
            organization_id=organization_id,
            domain_hint=domain_hint,
            login_hint=login_hint,
            state=state
        )
        
        logger.info(f"Generated authorization URL for provider: {provider}")
        return auth_url
    
    def get_authkit_url(self, state: Optional[str] = None) -> str:
        """
        Get AuthKit authorization URL - handles ALL authentication methods
        
        AuthKit automatically shows all enabled authentication methods:
        - Google OAuth
        - Email/Password  
        - Any other providers enabled in WorkOS dashboard
        """
        return self.get_authorization_url(provider="authkit", state=state)
    
    async def handle_callback(self, code: str, state: Optional[str] = None) -> Dict[str, Any]:
        """
        Handle OAuth callback and exchange code for user info
        
        Args:
            code: Authorization code from WorkOS
            state: State parameter for CSRF protection
            
        Returns:
            User information and session data
        """
        try:
            # Exchange code for access token and user info
            profile_and_token = workos_client.user_management.authenticate_with_code(
                code=code
            )
            
            # Extract user and access token
            user = profile_and_token.user
            access_token = profile_and_token.access_token
            refresh_token = profile_and_token.refresh_token
            
            # Create session
            session_id = str(uuid.uuid4())
            session_data = {
                "session_id": session_id,
                "user_id": user.id,
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "email_verified": user.email_verified,
                    "profile_picture_url": user.profile_picture_url,
                    "created_at": user.created_at,
                    "updated_at": user.updated_at
                },
                "access_token": access_token,
                "refresh_token": refresh_token,
                "state": state
            }
            
            # Store session (in production, use Redis or database)
            sessions[session_id] = session_data
            
            logger.info(f"Successfully authenticated user: {user.email}")
            return session_data
            
        except Exception as e:
            logger.error(f"Authentication failed: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Authentication failed: {str(e)}")
    
    async def get_current_user(self, credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
        """
        Get current authenticated user from session
        
        Args:
            credentials: HTTP Bearer token (session ID)
            
        Returns:
            Current user information
        """
        session_id = credentials.credentials
        
        if session_id not in sessions:
            raise HTTPException(status_code=401, detail="Invalid session")
        
        session_data = sessions[session_id]
        
        # Optionally refresh token here if needed
        # For now, just return the user data
        return session_data["user"]
    
    async def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh access token using refresh token
        
        Args:
            refresh_token: Refresh token from WorkOS
            
        Returns:
            New access token information
        """
        try:
            refreshed_token = workos_client.user_management.authenticate_with_refresh_token(
                refresh_token=refresh_token
            )
            
            return {
                "access_token": refreshed_token.access_token,
                "refresh_token": refreshed_token.refresh_token
            }
            
        except Exception as e:
            logger.error(f"Token refresh failed: {str(e)}")
            raise HTTPException(status_code=401, detail="Token refresh failed")
    
    def logout(self, session_id: str) -> bool:
        """
        Logout user and remove session
        
        Args:
            session_id: Session ID to remove
            
        Returns:
            True if logout successful
        """
        if session_id in sessions:
            del sessions[session_id]
            logger.info(f"User logged out: {session_id}")
            return True
        return False
    
    def get_logout_url(self, session_id: str) -> str:
        """
        Get WorkOS logout URL
        
        Args:
            session_id: Current session ID
            
        Returns:
            WorkOS logout URL
        """
        return workos_client.user_management.get_logout_url(session_id)

# Global auth manager instance
auth_manager = AuthManager()

# Dependency for getting current user
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """Dependency to get current authenticated user"""
    return await auth_manager.get_current_user(credentials)

# Optional dependency for getting current user (returns None if not authenticated)
async def get_current_user_optional(request: Request) -> Optional[Dict[str, Any]]:
    """Optional dependency to get current authenticated user"""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    
    try:
        session_id = auth_header.split(" ")[1]
        if session_id in sessions:
            return sessions[session_id]["user"]
    except:
        pass
    
    return None 