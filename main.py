from fastapi import FastAPI, HTTPException, Depends, Request, Response
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import logging
from typing import Optional, Dict, Any

# Import our custom modules
from config import settings
from auth import auth_manager, get_current_user, get_current_user_optional
from routes import auth_router

# Configure logging
logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL))
logger = logging.getLogger(__name__)

# Validate required settings
settings.validate_required_settings()

# Initialize FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="FastAPI application with WorkOS AuthKit authentication (unified login for all methods)"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include authentication routes
app.include_router(auth_router)

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to Lumina Agent with WorkOS AuthKit Authentication",
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "auth_methods": "All methods handled by AuthKit (Google OAuth, Email/Password, etc.)",
        "endpoints": {
            "login": "/auth/login",  # Single unified login endpoint!
            "callback": "/auth/callback",
            "profile": "/auth/profile",
            "logout": "/auth/logout",
            "status": "/auth/status",
            "providers": "/auth/providers",
            "config": "/auth/config"
        },
        "note": "WorkOS AuthKit automatically handles all authentication providers in a single unified interface"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "workos_configured": settings.is_workos_configured,
        "auth_provider": "WorkOS AuthKit"
    }

# Run the application
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level=settings.LOG_LEVEL.lower()
    ) 