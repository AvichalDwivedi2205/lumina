from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime

from models.ai_friend_models import *
from agents.ai_friend_agent import ai_friend_agent
from auth import get_current_user

logger = logging.getLogger(__name__)

ai_friend_router = APIRouter(prefix="/friend", tags=["ai_friend"])

# Start Conversation
@ai_friend_router.post("/start-conversation")
async def start_friend_conversation(
    conversation_request: FriendConversationRequest,
    user=Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Start a conversation with an AI friend personality.
    Requires WorkOS authentication.
    """
    try:
        result = await ai_friend_agent.start_conversation(
            user_id=user["id"],
            personality_type=conversation_request.personality_type,
            user_message=conversation_request.user_message or ""
        )
        
        if result.get('success'):
            logger.info(f"AI friend conversation started for user {user["id"]} with personality {conversation_request.personality_type}")
            return result
        else:
            logger.error(f"AI friend conversation failed: {result.get('error')}")
            raise HTTPException(status_code=500, detail=result.get('error', 'Conversation start failed'))
            
    except Exception as e:
        logger.error(f"Start friend conversation endpoint failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Get Available Personalities
@ai_friend_router.get("/personalities")
async def get_available_personalities(
    user=Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get list of available AI friend personalities.
    Requires WorkOS authentication.
    """
    try:
        personalities = ai_friend_agent.get_available_personalities()
        
        return {
            "success": True,
            "personalities": personalities
        }
        
    except Exception as e:
        logger.error(f"Get personalities endpoint failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Get Personality Recommendation
@ai_friend_router.post("/recommend-personality")
async def recommend_personality(
    context_request: PersonalityRecommendationRequest,
    user=Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get AI recommendation for best personality based on user context.
    Requires WorkOS authentication.
    """
    try:
        result = await ai_friend_agent.get_personality_recommendation(
            user_context=context_request.dict()
        )
        
        return {
            "success": True,
            "recommendation": result
        }
        
    except Exception as e:
        logger.error(f"Personality recommendation endpoint failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Session Management
@ai_friend_router.post("/session/{session_id}/end")
async def end_friend_session(
    session_id: str,
    session_feedback: SessionFeedback,
    user=Depends(get_current_user)
) -> Dict[str, Any]:
    """
    End a friend session and provide feedback.
    Requires WorkOS authentication.
    """
    try:
        result = await ai_friend_agent.end_session(
            user_id=user["id"],
            session_id=session_id,
            feedback=session_feedback.dict()
        )
        
        if result.get('success'):
            logger.info(f"AI friend session ended: {session_id}")
            return result
        else:
            logger.error(f"Session end failed: {result.get('error')}")
            raise HTTPException(status_code=500, detail=result.get('error', 'Session end failed'))
            
    except Exception as e:
        logger.error(f"End friend session endpoint failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@ai_friend_router.get("/sessions")
async def get_friend_sessions(
    limit: int = 20,
    personality_type: Optional[str] = None,
    user=Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get user's AI friend session history (minimal data).
    Requires WorkOS authentication.
    """
    try:
        result = await ai_friend_agent.get_session_history(
            user_id=user["id"],
            limit=limit,
            personality_type=personality_type
        )
        
        return {
            "success": True,
            "sessions": result
        }
        
    except Exception as e:
        logger.error(f"Get friend sessions endpoint failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# User Preferences
@ai_friend_router.get("/preferences")
async def get_friend_preferences(
    user=Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get user's AI friend preferences.
    Requires WorkOS authentication.
    """
    try:
        result = await ai_friend_agent.get_user_preferences(user_id=user["id"])
        
        return {
            "success": True,
            "preferences": result
        }
        
    except Exception as e:
        logger.error(f"Get friend preferences endpoint failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@ai_friend_router.put("/preferences")
async def update_friend_preferences(
    preferences_update: FriendPreferencesUpdate,
    user=Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Update user's AI friend preferences.
    Requires WorkOS authentication.
    """
    try:
        result = await ai_friend_agent.update_user_preferences(
            user_id=user["id"],
            preferences=preferences_update.dict(exclude_unset=True)
        )
        
        if result.get('success'):
            logger.info(f"AI friend preferences updated for user {user["id"]}")
            return result
        else:
            logger.error(f"Preferences update failed: {result.get('error')}")
            raise HTTPException(status_code=500, detail=result.get('error', 'Update failed'))
            
    except Exception as e:
        logger.error(f"Update friend preferences endpoint failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Analytics
@ai_friend_router.get("/analytics")
async def get_friend_analytics(
    user=Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get user's AI friend interaction analytics.
    Requires WorkOS authentication.
    """
    try:
        result = await ai_friend_agent.get_user_analytics(user_id=user["id"])
        
        return {
            "success": True,
            "analytics": result
        }
        
    except Exception as e:
        logger.error(f"Get friend analytics endpoint failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@ai_friend_router.get("/personality-analytics")
async def get_personality_analytics(
    user=Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get personality effectiveness analytics for the user.
    Requires WorkOS authentication.
    """
    try:
        result = await ai_friend_agent.get_personality_analytics(user_id=user["id"])
        
        return {
            "success": True,
            "personality_analytics": result
        }
        
    except Exception as e:
        logger.error(f"Get personality analytics endpoint failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Mood Tracking
@ai_friend_router.post("/mood-tracking")
async def track_mood(
    mood_data: MoodTrackingRequest,
    user=Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Track mood before/after AI friend interaction.
    Requires WorkOS authentication.
    """
    try:
        result = await ai_friend_agent.track_mood(
            user_id=user["id"],
            mood_data=mood_data.dict()
        )
        
        if result.get('success'):
            logger.info(f"Mood tracked for user {user["id"]}")
            return result
        else:
            logger.error(f"Mood tracking failed: {result.get('error')}")
            raise HTTPException(status_code=500, detail=result.get('error', 'Mood tracking failed'))
            
    except Exception as e:
        logger.error(f"Mood tracking endpoint failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@ai_friend_router.get("/mood-trends")
async def get_mood_trends(
    days: int = 30,
    user=Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get mood improvement trends from AI friend interactions.
    Requires WorkOS authentication.
    """
    try:
        result = await ai_friend_agent.get_mood_trends(
            user_id=user["id"],
            days=days
        )
        
        return {
            "success": True,
            "mood_trends": result
        }
        
    except Exception as e:
        logger.error(f"Get mood trends endpoint failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Health endpoint
@ai_friend_router.get("/health")
async def ai_friend_health():
    """Check AI friend service health"""
    return {
        "service": "ai_friend",
        "status": "healthy",
        "features": {
            "personalities_available": len(ai_friend_agent.personalities),
            "elevenlabs_integration": "configured" if ai_friend_agent.elevenlabs_auth else "not_configured",
            "gemini_analysis": "configured" if ai_friend_agent.model else "not_configured"
        },
        "personalities": list(ai_friend_agent.personalities.keys()),
        "timestamp": datetime.now().isoformat()
    } 