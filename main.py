from fastapi import FastAPI, HTTPException, Depends, Request, Response
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import logging
from typing import Optional, Dict, Any

# Import our custom modules
from config import settings
from auth import auth_manager, get_current_user, get_current_user_optional
from routes.auth import auth_router
from routes.journal import journal_router

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

# Include routers
app.include_router(auth_router)
app.include_router(journal_router)

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to Lumina - Mental Health AI Platform",
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "features": {
            "authentication": "WorkOS AuthKit (Google OAuth, Email/Password, etc.)",
            "journaling": "AI-powered therapeutic journaling with clinical insights",
            "security": "AES-256 encryption for all sensitive data",
            "analysis": "Evidence-based therapeutic analysis (CBT, DBT, ACT)"
        },
        "endpoints": {
            "auth": {
                "login": "/auth/login",
                "callback": "/auth/callback",
                "profile": "/auth/profile",
                "logout": "/auth/logout",
                "status": "/auth/status"
            },
            "journal": {
                "create_entry": "/journal/entry",
                "get_history": "/journal/entries",
                "insights_summary": "/journal/insights/summary",
                "crisis_resources": "/journal/crisis/resources",
                "health_check": "/journal/health"
            }
        }
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