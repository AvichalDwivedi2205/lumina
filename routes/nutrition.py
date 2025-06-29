from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from typing import Dict, List, Any, Optional
import logging
import base64
from datetime import datetime

from models.nutrition_models import *
from agents.nutrition_agent import nutrition_agent
from auth import get_current_user

logger = logging.getLogger(__name__)

nutrition_router = APIRouter(prefix="/nutrition", tags=["nutrition"])

# Food Image Analysis and Logging
@nutrition_router.post("/analyze-food-image")
async def analyze_food_image(
    image: UploadFile = File(...),
    user=Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Analyze food image using Gemini Vision and log nutrition data.
    Requires WorkOS authentication.
    """
    try:
        # Validate image file
        if not image.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        # Read and encode image
        image_data = await image.read()
        encoded_image = base64.b64encode(image_data).decode('utf-8')
        
        # Analyze with nutrition agent
        result = await nutrition_agent.analyze_food_image(
            user_id=user["id"],
            image_data=encoded_image
        )
        
        if result.get('success'):
            logger.info(f"Food image analyzed successfully for user {user["id"]}")
            return result
        else:
            logger.error(f"Food image analysis failed: {result.get('error')}")
            raise HTTPException(status_code=500, detail=result.get('error', 'Analysis failed'))
            
    except Exception as e:
        logger.error(f"Food image analysis endpoint failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@nutrition_router.post("/log-food")
async def log_food_manually(
    food_data: FoodLogRequest,
    user=Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Manually log food entry without image.
    Requires WorkOS authentication.
    """
    try:
        # Convert Pydantic model to dict
        food_dict = food_data.dict()
        
        # Log with nutrition agent
        result = await nutrition_agent.log_food_manually(
            user_id=user["id"],
            food_data=food_dict
        )
        
        if result.get('success'):
            logger.info(f"Food logged manually for user {user["id"]}")
            return result
        else:
            logger.error(f"Manual food logging failed: {result.get('error')}")
            raise HTTPException(status_code=500, detail=result.get('error', 'Logging failed'))
            
    except Exception as e:
        logger.error(f"Manual food logging endpoint failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Meal Planning
@nutrition_router.post("/generate-meal-plan")
async def generate_meal_plan(
    user=Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Generate personalized weekly meal plan.
    Requires WorkOS authentication.
    """
    try:
        result = await nutrition_agent.generate_meal_plan(user_id=user["id"])
        
        if result.get('success'):
            logger.info(f"Meal plan generated for user {user["id"]}")
            return result
        else:
            logger.error(f"Meal plan generation failed: {result.get('error')}")
            raise HTTPException(status_code=500, detail=result.get('error', 'Generation failed'))
            
    except Exception as e:
        logger.error(f"Meal plan generation endpoint failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@nutrition_router.get("/meal-plans")
async def get_meal_plans(
    limit: int = 10,
    user=Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get user's meal plan history.
    Requires WorkOS authentication.
    """
    try:
        # Get meal plans from database (implement in agent)
        result = await nutrition_agent.get_meal_plan_history(
            user_id=user["id"],
            limit=limit
        )
        
        return {
            "success": True,
            "meal_plans": result
        }
        
    except Exception as e:
        logger.error(f"Get meal plans endpoint failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Nutrition Consultation
@nutrition_router.post("/consultation")
async def nutrition_consultation(
    consultation_request: ConsultationRequest,
    user=Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get nutrition consultation from AI nutritionist.
    Requires WorkOS authentication.
    """
    try:
        result = await nutrition_agent.provide_consultation(
            user_id=user["id"],
            query=consultation_request.query
        )
        
        if result.get('success'):
            logger.info(f"Nutrition consultation provided for user {user["id"]}")
            return result
        else:
            logger.error(f"Nutrition consultation failed: {result.get('error')}")
            raise HTTPException(status_code=500, detail=result.get('error', 'Consultation failed'))
            
    except Exception as e:
        logger.error(f"Nutrition consultation endpoint failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@nutrition_router.get("/consultation-history")
async def get_consultation_history(
    limit: int = 20,
    user=Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get user's nutrition consultation history.
    Requires WorkOS authentication.
    """
    try:
        result = await nutrition_agent.get_consultation_history(
            user_id=user["id"],
            limit=limit
        )
        
        return {
            "success": True,
            "consultations": result
        }
        
    except Exception as e:
        logger.error(f"Get consultation history endpoint failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Calorie Tracking
@nutrition_router.get("/calorie-tracking")
async def get_calorie_tracking(
    user=Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get daily calorie tracking progress.
    Requires WorkOS authentication.
    """
    try:
        result = await nutrition_agent.get_calorie_tracking(user_id=user["id"])
        
        if result.get('success'):
            return result
        else:
            logger.error(f"Calorie tracking failed: {result.get('error')}")
            raise HTTPException(status_code=500, detail=result.get('error', 'Tracking failed'))
            
    except Exception as e:
        logger.error(f"Calorie tracking endpoint failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@nutrition_router.get("/food-logs")
async def get_food_logs(
    days: int = 7,
    user=Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get user's food log history.
    Requires WorkOS authentication.
    """
    try:
        result = await nutrition_agent.get_food_log_history(
            user_id=user["id"],
            days=days
        )
        
        return {
            "success": True,
            "food_logs": result
        }
        
    except Exception as e:
        logger.error(f"Get food logs endpoint failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# User Profile Management
@nutrition_router.get("/profile")
async def get_nutrition_profile(
    user=Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get user's nutrition profile.
    Requires WorkOS authentication.
    """
    try:
        result = await nutrition_agent.get_user_profile(user_id=user["id"])
        
        return {
            "success": True,
            "profile": result
        }
        
    except Exception as e:
        logger.error(f"Get nutrition profile endpoint failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@nutrition_router.put("/profile")
async def update_nutrition_profile(
    profile_update: NutritionProfileUpdate,
    user=Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Update user's nutrition profile.
    Requires WorkOS authentication.
    """
    try:
        result = await nutrition_agent.update_user_profile(
            user_id=user["id"],
            profile_data=profile_update.dict(exclude_unset=True)
        )
        
        if result.get('success'):
            logger.info(f"Nutrition profile updated for user {user["id"]}")
            return result
        else:
            logger.error(f"Profile update failed: {result.get('error')}")
            raise HTTPException(status_code=500, detail=result.get('error', 'Update failed'))
            
    except Exception as e:
        logger.error(f"Update nutrition profile endpoint failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Analytics
@nutrition_router.get("/analytics")
async def get_nutrition_analytics(
    period: str = "week",  # week, month, year
    user=Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get nutrition analytics for the user.
    Requires WorkOS authentication.
    """
    try:
        result = await nutrition_agent.get_nutrition_analytics(
            user_id=user["id"],
            period=period
        )
        
        return {
            "success": True,
            "analytics": result
        }
        
    except Exception as e:
        logger.error(f"Get nutrition analytics endpoint failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Health endpoint
@nutrition_router.get("/health")
async def nutrition_health():
    """Check nutrition service health"""
    return {
        "service": "nutrition",
        "status": "healthy",
        "features": {
            "gemini_vision": "configured" if nutrition_agent.vision_model else "not_configured",
            "usda_api": "configured" if nutrition_agent.usda_api_key else "not_configured",
            "encryption": "enabled"
        },
        "timestamp": datetime.now().isoformat()
    } 