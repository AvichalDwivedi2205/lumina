from fastapi import APIRouter, HTTPException, Depends, Query, Request
from fastapi.responses import RedirectResponse
from typing import Optional, Dict, Any
import logging

from auth import auth_manager, get_current_user, get_current_user_optional
from config import settings

logger = logging.getLogger(__name__)

# Create authentication router
auth_router = APIRouter(prefix="/auth", tags=["authentication"])

@auth_router.get("/login")
async def login(redirect_uri: Optional[str] = Query(None), state: Optional[str] = None):
    """
    Initiate login via WorkOS AuthKit
    
    AuthKit will automatically show all enabled authentication methods:
    - Google OAuth
    - Email/Password  
    - Any other providers you've enabled in WorkOS dashboard
    
    This is the single unified login endpoint for all authentication methods.
    """
    try:
        # Store redirect_uri in state if provided
        if redirect_uri:
            import json
            import base64
            state_data = {"redirect_uri": redirect_uri}
            if state:
                state_data["original_state"] = state
            state = base64.urlsafe_b64encode(json.dumps(state_data).encode()).decode()
        
        # Generate AuthKit URL - this handles ALL auth methods
        auth_url = auth_manager.get_authkit_url(state=state)
        
        logger.info("Redirecting to WorkOS AuthKit")
        return RedirectResponse(url=auth_url, status_code=302)
        
    except Exception as e:
        logger.error(f"AuthKit login failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")

@auth_router.get("/callback")
async def auth_callback(
    code: str = Query(..., description="Authorization code from WorkOS"),
    state: Optional[str] = Query(None, description="State parameter for CSRF protection")
):
    """
    Handle OAuth callback from WorkOS AuthKit
    
    This endpoint processes the authorization code returned by WorkOS
    and creates a user session, then redirects to the frontend.
    """
    try:
        # Handle the callback and create session
        session_data = await auth_manager.handle_callback(code=code, state=state)
        
        # Parse redirect_uri from state if provided
        redirect_uri = "http://localhost:3001/auth/callback"  # Default frontend callback
        
        if state:
            try:
                import json
                import base64
                decoded_state = json.loads(base64.urlsafe_b64decode(state.encode()).decode())
                if "redirect_uri" in decoded_state:
                    redirect_uri = decoded_state["redirect_uri"]
            except Exception as e:
                logger.warning(f"Failed to parse state: {e}")
        
        # Log successful authentication
        logger.info(f"Authentication successful for user: {session_data['user']['email']}")
        logger.info(f"Session ID: {session_data['session_id']}")
        logger.info(f"Redirecting to: {redirect_uri}")
        
        # Redirect to frontend with success parameter
        return RedirectResponse(url=f"{redirect_uri}?success=true", status_code=302)
        
    except Exception as e:
        logger.error(f"Callback handling failed: {str(e)}")
        # Redirect to frontend with error
        error_uri = "http://localhost:3001/auth/callback?error=auth_failed"
        return RedirectResponse(url=error_uri, status_code=302)

@auth_router.get("/profile")
async def get_profile(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Get current user profile"""
    return {
        "message": "Profile retrieved successfully",
        "user": current_user
    }

@auth_router.post("/logout")
async def logout(
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Logout current user"""
    try:
        # Get session ID from authorization header
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Invalid authorization header")
        
        session_id = auth_header.split(" ")[1]
        
        # Logout user
        success = await auth_manager.logout(session_id)
        
        if success:
            return {"message": "Logout successful"}
        else:
            raise HTTPException(status_code=400, detail="Logout failed")
            
    except Exception as e:
        logger.error(f"Logout failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Logout failed")

@auth_router.post("/refresh")
async def refresh_token(
    refresh_token: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Refresh access token"""
    try:
        refreshed_data = await auth_manager.refresh_access_token(refresh_token)
        return {
            "message": "Token refreshed successfully",
            "access_token": refreshed_data["access_token"],
            "refresh_token": refreshed_data["refresh_token"]
        }
        
    except Exception as e:
        logger.error(f"Token refresh failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@auth_router.get("/status")
async def auth_status(current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)):
    """Check authentication status"""
    if current_user:
        return {
            "authenticated": True,
            "user": {
                "id": current_user["id"],
                "email": current_user["email"],
                "firstName": current_user.get("first_name", ""),
                "lastName": current_user.get("last_name", ""),
                "profilePicture": current_user.get("profile_picture_url", ""),
                "joinDate": current_user.get("created_at", ""),
                "emailVerified": current_user.get("email_verified", False)
            }
        }
    else:
        return {
            "authenticated": False,
            "message": "User not authenticated"
        }

@auth_router.get("/providers")
async def get_auth_providers():
    """Get available authentication providers - NEW AUTHKIT VERSION"""
    return {
        "providers": {
            "authkit": {
                "name": "AuthKit",
                "display_name": "WorkOS AuthKit",
                "description": "Unified authentication with all enabled methods",
                "endpoint": "/auth/login",
                "methods": [
                    "Google OAuth",
                    "Email & Password",
                    "Any other providers enabled in WorkOS dashboard"
                ]
            }
        },
        "callback_uri": settings.WORKOS_REDIRECT_URI,
        "note": "All authentication methods are handled through a single login endpoint via WorkOS AuthKit"
    }

@auth_router.get("/config")
async def get_auth_config():
    """Get authentication configuration (public information only)"""
    return {
        "client_id": settings.WORKOS_CLIENT_ID,
        "redirect_uri": settings.WORKOS_REDIRECT_URI,
        "provider": "authkit",
        "description": "WorkOS AuthKit handles all authentication methods",
        "workos_configured": settings.is_workos_configured,
        "login_endpoint": "/auth/login"
    }

@auth_router.get("/debug/sessions")
async def debug_sessions():
    """Debug endpoint to show current sessions (development only)"""
    try:
        from database.supabase_client import supabase_client
        response = supabase_client.table("user_sessions").select("id, user_id, created_at, expires_at").execute()
        sessions = response.data if response.data else []
        
        return {
            "active_sessions": len(sessions),
            "sessions": sessions,
            "note": "This endpoint should be removed in production"
        }
    except Exception as e:
        return {
            "active_sessions": 0,
            "sessions": [],
            "error": str(e),
            "note": "This endpoint should be removed in production"
        } 