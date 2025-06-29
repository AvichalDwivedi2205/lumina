from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime

from models.scheduling_models import *
from agents.scheduling_agent import scheduling_agent
from auth import get_current_user

logger = logging.getLogger(__name__)

scheduling_router = APIRouter(prefix="/scheduling", tags=["scheduling"])

# Schedule Item Management
@scheduling_router.post("/create")
async def create_schedule_item(
    schedule_request: ScheduleCreateRequest,
    user=Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Create a new schedule item with AI optimization.
    Requires WorkOS authentication.
    """
    try:
        result = await scheduling_agent.create_schedule_item(
            user_id=user["id"],
            schedule_type=schedule_request.schedule_type,
            schedule_data=schedule_request.dict(exclude={'schedule_type'})
        )
        
        if result.get('success'):
            logger.info(f"Schedule item created for user {user["id"]}: {schedule_request.schedule_type}")
            return result
        else:
            logger.error(f"Schedule creation failed: {result.get('error')}")
            raise HTTPException(status_code=500, detail=result.get('error', 'Creation failed'))
            
    except Exception as e:
        logger.error(f"Create schedule endpoint failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@scheduling_router.get("/items")
async def get_schedule_items(
    schedule_type: Optional[str] = None,
    days_ahead: int = 7,
    user=Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get user's schedule items.
    Requires WorkOS authentication.
    """
    try:
        result = await scheduling_agent.get_schedule_items(
            user_id=user["id"],
            schedule_type=schedule_type,
            days_ahead=days_ahead
        )
        
        return {
            "success": True,
            "schedule_items": result
        }
        
    except Exception as e:
        logger.error(f"Get schedule items endpoint failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@scheduling_router.put("/items/{item_id}")
async def update_schedule_item(
    item_id: str,
    update_request: ScheduleUpdateRequest,
    user=Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Update a schedule item.
    Requires WorkOS authentication.
    """
    try:
        result = await scheduling_agent.update_schedule_item(
            user_id=user["id"],
            item_id=item_id,
            update_data=update_request.dict(exclude_unset=True)
        )
        
        if result.get('success'):
            logger.info(f"Schedule item updated: {item_id}")
            return result
        else:
            logger.error(f"Schedule update failed: {result.get('error')}")
            raise HTTPException(status_code=500, detail=result.get('error', 'Update failed'))
            
    except Exception as e:
        logger.error(f"Update schedule endpoint failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@scheduling_router.delete("/items/{item_id}")
async def delete_schedule_item(
    item_id: str,
    user=Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Delete a schedule item.
    Requires WorkOS authentication.
    """
    try:
        result = await scheduling_agent.delete_schedule_item(
            user_id=user["id"],
            item_id=item_id
        )
        
        if result.get('success'):
            logger.info(f"Schedule item deleted: {item_id}")
            return result
        else:
            logger.error(f"Schedule deletion failed: {result.get('error')}")
            raise HTTPException(status_code=500, detail=result.get('error', 'Deletion failed'))
            
    except Exception as e:
        logger.error(f"Delete schedule endpoint failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Schedule Optimization
@scheduling_router.post("/optimize")
async def optimize_schedule(
    user=Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Optimize user's entire schedule using AI.
    Requires WorkOS authentication.
    """
    try:
        result = await scheduling_agent.optimize_user_schedule(user_id=user["id"])
        
        if result.get('success'):
            logger.info(f"Schedule optimized for user {user["id"]}")
            return result
        else:
            logger.error(f"Schedule optimization failed: {result.get('error')}")
            raise HTTPException(status_code=500, detail=result.get('error', 'Optimization failed'))
            
    except Exception as e:
        logger.error(f"Optimize schedule endpoint failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@scheduling_router.get("/analyze")
async def analyze_schedule(
    user=Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Analyze user's current schedule for patterns and issues.
    Requires WorkOS authentication.
    """
    try:
        result = await scheduling_agent.analyze_schedule(user_id=user["id"])
        
        if result.get('success'):
            return result
        else:
            logger.error(f"Schedule analysis failed: {result.get('error')}")
            raise HTTPException(status_code=500, detail=result.get('error', 'Analysis failed'))
            
    except Exception as e:
        logger.error(f"Analyze schedule endpoint failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Recommendations
@scheduling_router.get("/recommendations")
async def get_schedule_recommendations(
    user=Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get AI-generated scheduling recommendations.
    Requires WorkOS authentication.
    """
    try:
        result = await scheduling_agent.get_schedule_recommendations(user_id=user["id"])
        
        if result.get('success'):
            return result
        else:
            logger.error(f"Schedule recommendations failed: {result.get('error')}")
            raise HTTPException(status_code=500, detail=result.get('error', 'Recommendations failed'))
            
    except Exception as e:
        logger.error(f"Get recommendations endpoint failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@scheduling_router.post("/recommendations/{recommendation_id}/apply")
async def apply_recommendation(
    recommendation_id: str,
    user=Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Apply a scheduling recommendation.
    Requires WorkOS authentication.
    """
    try:
        result = await scheduling_agent.apply_recommendation(
            user_id=user["id"],
            recommendation_id=recommendation_id
        )
        
        if result.get('success'):
            logger.info(f"Recommendation applied: {recommendation_id}")
            return result
        else:
            logger.error(f"Recommendation application failed: {result.get('error')}")
            raise HTTPException(status_code=500, detail=result.get('error', 'Application failed'))
            
    except Exception as e:
        logger.error(f"Apply recommendation endpoint failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Conflict Management
@scheduling_router.get("/conflicts")
async def get_schedule_conflicts(
    user=Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get current schedule conflicts.
    Requires WorkOS authentication.
    """
    try:
        result = await scheduling_agent.get_schedule_conflicts(user_id=user["id"])
        
        return {
            "success": True,
            "conflicts": result
        }
        
    except Exception as e:
        logger.error(f"Get conflicts endpoint failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@scheduling_router.post("/conflicts/{conflict_id}/resolve")
async def resolve_conflict(
    conflict_id: str,
    resolution_request: ConflictResolutionRequest,
    user=Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Resolve a schedule conflict.
    Requires WorkOS authentication.
    """
    try:
        result = await scheduling_agent.resolve_conflict(
            user_id=user["id"],
            conflict_id=conflict_id,
            resolution_data=resolution_request.dict()
        )
        
        if result.get('success'):
            logger.info(f"Conflict resolved: {conflict_id}")
            return result
        else:
            logger.error(f"Conflict resolution failed: {result.get('error')}")
            raise HTTPException(status_code=500, detail=result.get('error', 'Resolution failed'))
            
    except Exception as e:
        logger.error(f"Resolve conflict endpoint failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# User Preferences
@scheduling_router.get("/preferences")
async def get_scheduling_preferences(
    user=Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get user's scheduling preferences.
    Requires WorkOS authentication.
    """
    try:
        result = await scheduling_agent.get_user_preferences(user_id=user["id"])
        
        return {
            "success": True,
            "preferences": result
        }
        
    except Exception as e:
        logger.error(f"Get scheduling preferences endpoint failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@scheduling_router.put("/preferences")
async def update_scheduling_preferences(
    preferences_update: SchedulingPreferencesUpdate,
    user=Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Update user's scheduling preferences.
    Requires WorkOS authentication.
    """
    try:
        result = await scheduling_agent.update_user_preferences(
            user_id=user["id"],
            preferences=preferences_update.dict(exclude_unset=True)
        )
        
        if result.get('success'):
            logger.info(f"Scheduling preferences updated for user {user["id"]}")
            return result
        else:
            logger.error(f"Preferences update failed: {result.get('error')}")
            raise HTTPException(status_code=500, detail=result.get('error', 'Update failed'))
            
    except Exception as e:
        logger.error(f"Update preferences endpoint failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Templates
@scheduling_router.get("/templates")
async def get_schedule_templates(
    template_type: Optional[str] = None,
    user=Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get user's schedule templates.
    Requires WorkOS authentication.
    """
    try:
        result = await scheduling_agent.get_schedule_templates(
            user_id=user["id"],
            template_type=template_type
        )
        
        return {
            "success": True,
            "templates": result
        }
        
    except Exception as e:
        logger.error(f"Get templates endpoint failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@scheduling_router.post("/templates")
async def create_schedule_template(
    template_request: ScheduleTemplateRequest,
    user=Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Create a new schedule template.
    Requires WorkOS authentication.
    """
    try:
        result = await scheduling_agent.create_schedule_template(
            user_id=user["id"],
            template_data=template_request.dict()
        )
        
        if result.get('success'):
            logger.info(f"Schedule template created for user {user["id"]}")
            return result
        else:
            logger.error(f"Template creation failed: {result.get('error')}")
            raise HTTPException(status_code=500, detail=result.get('error', 'Creation failed'))
            
    except Exception as e:
        logger.error(f"Create template endpoint failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@scheduling_router.post("/templates/{template_id}/apply")
async def apply_schedule_template(
    template_id: str,
    user=Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Apply a schedule template.
    Requires WorkOS authentication.
    """
    try:
        result = await scheduling_agent.apply_schedule_template(
            user_id=user["id"],
            template_id=template_id
        )
        
        if result.get('success'):
            logger.info(f"Schedule template applied: {template_id}")
            return result
        else:
            logger.error(f"Template application failed: {result.get('error')}")
            raise HTTPException(status_code=500, detail=result.get('error', 'Application failed'))
            
    except Exception as e:
        logger.error(f"Apply template endpoint failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Analytics
@scheduling_router.get("/analytics")
async def get_schedule_analytics(
    period: str = "week",  # week, month, year
    user=Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get scheduling analytics for the user.
    Requires WorkOS authentication.
    """
    try:
        result = await scheduling_agent.get_schedule_analytics(
            user_id=user["id"],
            period=period
        )
        
        return {
            "success": True,
            "analytics": result
        }
        
    except Exception as e:
        logger.error(f"Get scheduling analytics endpoint failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Completion Tracking
@scheduling_router.post("/items/{item_id}/complete")
async def mark_item_complete(
    item_id: str,
    completion_data: Optional[ScheduleCompletionRequest] = None,
    user=Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Mark a schedule item as completed.
    Requires WorkOS authentication.
    """
    try:
        result = await scheduling_agent.mark_item_complete(
            user_id=user["id"],
            item_id=item_id,
            completion_data=completion_data.dict() if completion_data else {}
        )
        
        if result.get('success'):
            logger.info(f"Schedule item marked complete: {item_id}")
            return result
        else:
            logger.error(f"Item completion failed: {result.get('error')}")
            raise HTTPException(status_code=500, detail=result.get('error', 'Completion failed'))
            
    except Exception as e:
        logger.error(f"Mark complete endpoint failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Health endpoint
@scheduling_router.get("/health")
async def scheduling_health():
    """Check scheduling service health"""
    return {
        "service": "scheduling",
        "status": "healthy",
        "features": {
            "ai_optimization": "enabled",
            "conflict_detection": "enabled",
            "templates": "enabled",
            "analytics": "enabled",
            "encryption": "enabled"
        },
        "supported_types": ["therapy", "exercise", "journal", "sleep", "routine"],
        "timestamp": datetime.now().isoformat()
    } 