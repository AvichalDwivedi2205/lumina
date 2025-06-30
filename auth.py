import os
import uuid
import secrets
import json
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from workos import WorkOSClient
from fastapi import HTTPException, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from config import settings
from database.supabase_client import supabase_client
import logging

logger = logging.getLogger(__name__)

# Configure WorkOS Client
workos_client = WorkOSClient(
    api_key=settings.WORKOS_API_KEY,
    client_id=settings.WORKOS_CLIENT_ID
)

# Security scheme
security = HTTPBearer()

class SessionManager:
    """Database-backed session management"""
    
    async def create_session(self, session_data: Dict[str, Any]) -> str:
        """Create a new session in database"""
        try:
            session_id = str(uuid.uuid4())
            expires_at = datetime.now() + timedelta(days=7)  # 7 day expiry
            
            insert_data = {
                "id": session_id,
                "user_id": session_data["user_id"],
                "session_data": json.dumps(session_data),
                "expires_at": expires_at.isoformat(),
                "created_at": datetime.now().isoformat()
            }
            
            # Create sessions table if it doesn't exist
            await self._ensure_sessions_table()
            
            response = supabase_client.table("user_sessions").insert(insert_data).execute()
            
            if response.data:
                logger.info(f"Session created: {session_id}")
                return session_id
            else:
                raise Exception("Failed to create session")
                
        except Exception as e:
            logger.error(f"Session creation failed: {e}")
            raise HTTPException(status_code=500, detail="Session creation failed")
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session from database"""
        try:
            response = supabase_client.table("user_sessions") \
                .select("*") \
                .eq("id", session_id) \
                .gt("expires_at", datetime.now().isoformat()) \
                .execute()
            
            if response.data and len(response.data) > 0:
                session_record = response.data[0]
                return json.loads(session_record["session_data"])
            
            return None
            
        except Exception as e:
            logger.error(f"Session retrieval failed: {e}")
            return None
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete session from database"""
        try:
            response = supabase_client.table("user_sessions") \
                .delete() \
                .eq("id", session_id) \
                .execute()
            
            return True
            
        except Exception as e:
            logger.error(f"Session deletion failed: {e}")
            return False
    
    async def _ensure_sessions_table(self):
        """Ensure sessions table exists"""
        try:
            # This will be handled by the database schema
            pass
        except Exception as e:
            logger.error(f"Sessions table creation failed: {e}")

# Global session manager
session_manager = SessionManager()

class AuthManager:
    """Authentication manager for WorkOS integration"""
    
    def __init__(self):
        self.client_id = settings.WORKOS_CLIENT_ID
        self.redirect_uri = settings.WORKOS_REDIRECT_URI
    
    def get_authorization_url(self, provider: str = "authkit", state: Optional[str] = None) -> str:
        """
        Get authorization URL for WorkOS authentication
        
        Args:
            provider: Authentication provider (default: "authkit" for AuthKit)
            state: Optional state parameter for CSRF protection
            
        Returns:
            Authorization URL
        """
        if not state:
            state = secrets.token_urlsafe(32)
        
        return workos_client.user_management.get_authorization_url(
            provider=provider,
            redirect_uri=self.redirect_uri,
            state=state
        )
    
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
            
            # Create session data
            session_data = {
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
            
            # Store session in database
            session_id = await session_manager.create_session(session_data)
            
            # Add session_id to response
            session_data["session_id"] = session_id
            
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
        
        session_data = await session_manager.get_session(session_id)
        
        if not session_data:
            raise HTTPException(status_code=401, detail="Invalid session")
        
        # Return the user data
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
    
    async def logout(self, session_id: str) -> bool:
        """
        Logout user and remove session
        
        Args:
            session_id: Session ID to remove
            
        Returns:
            True if logout successful
        """
        success = await session_manager.delete_session(session_id)
        if success:
            logger.info(f"User logged out: {session_id}")
        return success
    
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
        session_data = await session_manager.get_session(session_id)
        if session_data:
            return session_data["user"]
    except:
        pass
    
    return None 