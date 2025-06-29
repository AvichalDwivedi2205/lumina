from fastapi import FastAPI, HTTPException, Depends, Request, Response
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import logging
from typing import Optional, Dict, Any
from datetime import datetime

# Import our custom modules
from config import settings
from auth import auth_manager, get_current_user, get_current_user_optional
from routes.auth import auth_router
from routes.journal import journal_router
from routes.therapy import therapy_router
from routes.mental_exercises import exercises_router
from routes.nutrition import nutrition_router
from routes.ai_friend import ai_friend_router
from routes.scheduling import scheduling_router

# Configure logging
logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL))
logger = logging.getLogger(__name__)

# Validate required settings
settings.validate_required_settings()

# Initialize FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="FastAPI application with WorkOS AuthKit authentication and AI-powered mental health services"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all routers
app.include_router(auth_router)
app.include_router(journal_router)
app.include_router(therapy_router)
app.include_router(exercises_router)
app.include_router(nutrition_router)
app.include_router(ai_friend_router)
app.include_router(scheduling_router)

@app.get("/")
async def root():
    """Root endpoint with comprehensive API documentation"""
    return {
        "message": "Welcome to Lumina Mental Health AI Platform",
        "version": settings.APP_VERSION,
        "status": "operational",
        "services": {
            "authentication": {
                "provider": "WorkOS",
                "status": "configured" if settings.WORKOS_API_KEY else "not_configured",
                "endpoints": ["/auth/login", "/auth/callback", "/auth/status", "/auth/logout"]
            },
            "journaling": {
                "description": "AI-powered journaling with crisis detection",
                "status": "operational",
                "endpoints": ["/journal/analyze", "/journal/health", "/journal/crisis/resources"]
            },
            "therapy": {
                "description": "Voice and video therapy agents",
                "status": "configured" if settings.ELEVENLABS_THERAPY_API_KEY else "not_configured",
                "agents": {
                    "elevenlabs_voice": 2,  # Male and female therapists
                    "tavus_video": 2  # Male and female video personas
                },
                "endpoints": ["/therapy/session", "/therapy/agents/status", "/therapy/crisis/resources"]
            },
            "mental_exercises": {
                "description": "4 types of therapeutic exercises",
                "status": "configured" if settings.ELEVENLABS_EXERCISE_API_KEY else "not_configured",
                "exercise_types": ["mindfulness", "cbt_tools", "behavioral_activation", "self_compassion"],
                "endpoints": ["/exercises/available", "/exercises/start", "/exercises/analytics"]
            },
            "nutrition": {
                "description": "AI nutrition agent with Gemini Vision",
                "status": "configured" if settings.GOOGLE_API_KEY and settings.USDA_API_KEY else "not_configured",
                "features": ["food_image_analysis", "meal_planning", "calorie_tracking", "nutrition_consultation"],
                "endpoints": ["/nutrition/analyze-food-image", "/nutrition/generate-meal-plan", "/nutrition/consultation"]
            },
            "ai_friend": {
                "description": "5 AI friend personalities for emotional support",
                "status": "configured" if settings.ELEVENLABS_FRIEND_API_KEY else "not_configured",
                "personalities": ["supportive", "motivator", "mentor", "funny", "mindful"],
                "endpoints": ["/friend/start-conversation", "/friend/personalities", "/friend/analytics"]
            },
            "scheduling": {
                "description": "AI-powered schedule optimization",
                "status": "operational",
                "features": ["schedule_optimization", "conflict_detection", "analytics", "templates"],
                "endpoints": ["/scheduling/create", "/scheduling/optimize", "/scheduling/analytics"]
            }
        },
        "integrations": {
            "elevenlabs": {
                "therapy_account": "configured" if settings.ELEVENLABS_THERAPY_API_KEY else "not_configured",
                "exercise_account": "configured" if settings.ELEVENLABS_EXERCISE_API_KEY else "not_configured",
                "friend_account": "configured" if settings.ELEVENLABS_FRIEND_API_KEY else "not_configured"
            },
            "tavus": "configured" if settings.TAVUS_API_KEY else "not_configured",
            "gemini": "configured" if settings.GOOGLE_API_KEY else "not_configured",
            "usda": "configured" if settings.USDA_API_KEY else "not_configured",
            "supabase": "configured" if settings.SUPABASE_URL else "not_configured",
            "workos": "configured" if settings.WORKOS_API_KEY else "not_configured"
        },
        "security": {
            "encryption": "enabled" if settings.FERNET_KEY else "disabled",
            "row_level_security": "enabled",
            "authentication": "required"
        },
        "documentation": {
            "openapi": "/docs",
            "redoc": "/redoc",
            "openapi_json": "/openapi.json"
        },
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health_check():
    """Comprehensive health check for all services"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "api": "operational",
            "database": "connected" if settings.SUPABASE_URL else "not_configured",
            "authentication": "configured" if settings.WORKOS_API_KEY else "not_configured"
        },
        "integrations": {
            "elevenlabs": {
                "therapy": "configured" if settings.ELEVENLABS_THERAPY_API_KEY else "not_configured",
                "exercise": "configured" if settings.ELEVENLABS_EXERCISE_API_KEY else "not_configured", 
                "friend": "configured" if settings.ELEVENLABS_FRIEND_API_KEY else "not_configured"
            },
            "tavus": "configured" if settings.TAVUS_API_KEY else "not_configured",
            "gemini": "configured" if settings.GOOGLE_API_KEY else "not_configured",
            "usda": "configured" if settings.USDA_API_KEY else "not_configured"
        },
        "agents": {
            "therapy_agents": 2 if settings.ELEVENLABS_MALE_THERAPIST_AGENT_ID and settings.ELEVENLABS_FEMALE_THERAPIST_AGENT_ID else 0,
            "exercise_agents": 4 if all([
                settings.ELEVENLABS_MINDFULNESS_AGENT_ID,
                settings.ELEVENLABS_CBT_AGENT_ID, 
                settings.ELEVENLABS_BEHAVIORAL_AGENT_ID,
                settings.ELEVENLABS_COMPASSION_AGENT_ID
            ]) else 0,
            "friend_agents": 5 if all([
                settings.ELEVENLABS_FRIEND_SUPPORTIVE_AGENT_ID,
                settings.ELEVENLABS_FRIEND_MOTIVATOR_AGENT_ID,
                settings.ELEVENLABS_FRIEND_MENTOR_AGENT_ID,
                settings.ELEVENLABS_FRIEND_FUNNY_AGENT_ID,
                settings.ELEVENLABS_FRIEND_UNHINGED_AGENT_ID
            ]) else 0,
            "tavus_personas": 2 if settings.TAVUS_MALE_THERAPIST_PERSONA_ID and settings.TAVUS_FEMALE_THERAPIST_PERSONA_ID else 0
        },
        "security": {
            "encryption": "enabled" if settings.FERNET_KEY else "disabled",
            "crisis_detection": "enabled" if settings.CRISIS_DETECTION_ENABLED else "disabled"
        }
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