from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import List, Dict, Any, Optional
import logging
import json

from auth import get_current_user
from agents.mental_exercise_agent import mental_exercise_agent
from services.elevenlabs_auth import elevenlabs_auth
from models.therapy_models import (
    MentalExerciseCreate, MentalExerciseComplete, MentalExerciseResponse,
    ExerciseHistory, AvailableExercises, ExerciseWebhookData
)
from config import settings

logger = logging.getLogger(__name__)

exercises_router = APIRouter(prefix="/exercises", tags=["mental_exercises"])

@exercises_router.get("/available", response_model=Dict[str, AvailableExercises])
async def get_available_exercises() -> Dict[str, AvailableExercises]:
    """
    Get list of available mental health exercises.
    Public endpoint for discovering exercise options.
    """
    try:
        exercises = mental_exercise_agent.get_available_exercises()
        
        return {
            exercise_type: AvailableExercises(
                exercise_type=exercise_type,
                **exercise_info
            )
            for exercise_type, exercise_info in exercises.items()
        }
        
    except Exception as e:
        logger.error(f"Failed to get available exercises: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve available exercises: {str(e)}"
        )

@exercises_router.post("/start", response_model=MentalExerciseResponse)
async def start_mental_exercise(
    exercise_data: MentalExerciseCreate,
    user=Depends(get_current_user)
) -> MentalExerciseResponse:
    """
    Start a new mental exercise session.
    Requires WorkOS authentication.
    """
    try:
        # Validate exercise type
        available_exercises = mental_exercise_agent.get_available_exercises()
        if exercise_data.exercise_type not in available_exercises:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid exercise type. Available types: {list(available_exercises.keys())}"
            )
        
        # Validate mood rating if provided
        if exercise_data.mood_before is not None:
            if exercise_data.mood_before < 1 or exercise_data.mood_before > 10:
                raise HTTPException(
                    status_code=400,
                    detail="Mood rating must be between 1 and 10"
                )
        
        # Check if ElevenLabs is configured
        if not settings.is_elevenlabs_configured:
            raise HTTPException(
                status_code=503,
                detail="ElevenLabs not configured. Please check API settings."
            )
        
        # Start exercise session using the agent
        result = await mental_exercise_agent.start_exercise(
            user_id=user["id"],
            exercise_type=exercise_data.exercise_type,
            mood_before=exercise_data.mood_before
        )
        
        if not result['success']:
            raise HTTPException(
                status_code=500,
                detail=result.get('error', 'Failed to start exercise session')
            )
        
        logger.info(f"Exercise session started for user {user["id"]}: {result['exercise_id']} ({exercise_data.exercise_type})")
        
        return MentalExerciseResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Exercise session start failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

@exercises_router.post("/exercise/{exercise_id}/agent-url")
async def get_exercise_agent_url(
    exercise_id: str,
    exercise_type: str,
    user=Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get a secure signed URL for ElevenLabs exercise agent access.
    This endpoint provides time-limited URLs for client-side agent connections.
    """
    try:
        # Validate exercise type
        available_exercises = mental_exercise_agent.get_available_exercises()
        if exercise_type not in available_exercises:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid exercise type. Available types: {list(available_exercises.keys())}"
            )
        
        # Generate secure signed URL
        result = await elevenlabs_auth.get_exercise_agent_url(
            exercise_type=exercise_type,
            user_id=user["id"],
            exercise_id=exercise_id
        )
        
        if not result['success']:
            raise HTTPException(
                status_code=500,
                detail=result.get('error', 'Failed to generate agent URL')
            )
        
        logger.info(f"Generated exercise agent URL for user {user["id"]}, exercise {exercise_id}")
        
        return {
            'agent_url': result['agent_url'],
            'expires_at': result['expires_at'],
            'agent_config': result['agent_config']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Agent URL generation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate agent URL: {str(e)}"
        )

@exercises_router.post("/complete", response_model=Dict[str, Any])
async def complete_mental_exercise(
    completion_data: MentalExerciseComplete,
    user=Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Complete a mental exercise session with mood rating.
    Requires WorkOS authentication.
    """
    try:
        # Validate mood rating
        if completion_data.mood_after < 1 or completion_data.mood_after > 10:
            raise HTTPException(
                status_code=400,
                detail="Mood rating must be between 1 and 10"
            )
        
        # Complete exercise session using the agent
        result = await mental_exercise_agent.complete_exercise(
            exercise_id=completion_data.exercise_id,
            mood_after=completion_data.mood_after,
            exercise_notes=completion_data.exercise_notes
        )
        
        if not result['success']:
            raise HTTPException(
                status_code=500,
                detail=result.get('error', 'Failed to complete exercise session')
            )
        
        logger.info(f"Exercise session completed for user {user["id"]}: {completion_data.exercise_id}")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Exercise completion failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

@exercises_router.get("/history", response_model=List[ExerciseHistory])
async def get_exercise_history(
    exercise_type: Optional[str] = None,
    limit: int = 10,
    user=Depends(get_current_user)
) -> List[ExerciseHistory]:
    """
    Get user's mental exercise history.
    Requires WorkOS authentication.
    """
    try:
        if limit < 1 or limit > 50:
            raise HTTPException(
                status_code=400,
                detail="Limit must be between 1 and 50"
            )
        
        # Validate exercise type if provided
        if exercise_type:
            available_exercises = mental_exercise_agent.get_available_exercises()
            if exercise_type not in available_exercises:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid exercise type. Available types: {list(available_exercises.keys())}"
                )
        
        exercises = await mental_exercise_agent.get_exercise_history(
            user_id=user["id"],
            exercise_type=exercise_type,
            limit=limit
        )
        
        return [ExerciseHistory(**exercise) for exercise in exercises]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Exercise history retrieval failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve exercise history: {str(e)}"
        )

@exercises_router.get("/analytics")
async def get_exercise_analytics(
    user=Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get user's exercise analytics and progress insights.
    Requires WorkOS authentication.
    """
    try:
        # Get all exercise history for analytics
        all_exercises = await mental_exercise_agent.get_exercise_history(
            user_id=user["id"],
            limit=100
        )
        
        if not all_exercises:
            return {
                "total_exercises": 0,
                "completion_rate": 0.0,
                "average_mood_improvement": 0.0,
                "most_effective_exercise": None,
                "streak_days": 0,
                "exercise_breakdown": {}
            }
        
        # Calculate analytics
        completed_exercises = [ex for ex in all_exercises if ex['completion_status'] == 'completed']
        completion_rate = len(completed_exercises) / len(all_exercises) if all_exercises else 0.0
        
        # Calculate average mood improvement
        mood_improvements = []
        for exercise in completed_exercises:
            if exercise.get('mood_before') and exercise.get('mood_after'):
                improvement = exercise['mood_after'] - exercise['mood_before']
                mood_improvements.append(improvement)
        
        avg_mood_improvement = sum(mood_improvements) / len(mood_improvements) if mood_improvements else 0.0
        
        # Exercise type breakdown
        exercise_breakdown = {}
        for exercise in all_exercises:
            ex_type = exercise['exercise_type']
            if ex_type not in exercise_breakdown:
                exercise_breakdown[ex_type] = {
                    "total": 0,
                    "completed": 0,
                    "avg_mood_improvement": 0.0
                }
            
            exercise_breakdown[ex_type]["total"] += 1
            if exercise['completion_status'] == 'completed':
                exercise_breakdown[ex_type]["completed"] += 1
        
        # Calculate most effective exercise type
        most_effective = None
        best_improvement = 0.0
        
        for ex_type, data in exercise_breakdown.items():
            type_exercises = [ex for ex in completed_exercises if ex['exercise_type'] == ex_type]
            type_improvements = [
                ex['mood_after'] - ex['mood_before'] 
                for ex in type_exercises 
                if ex.get('mood_before') and ex.get('mood_after')
            ]
            
            if type_improvements:
                avg_improvement = sum(type_improvements) / len(type_improvements)
                exercise_breakdown[ex_type]["avg_mood_improvement"] = avg_improvement
                
                if avg_improvement > best_improvement:
                    best_improvement = avg_improvement
                    most_effective = ex_type
        
        return {
            "total_exercises": len(all_exercises),
            "completed_exercises": len(completed_exercises),
            "completion_rate": round(completion_rate * 100, 1),
            "average_mood_improvement": round(avg_mood_improvement, 1),
            "most_effective_exercise": most_effective,
            "exercise_breakdown": exercise_breakdown,
            "recent_trend": "improving" if avg_mood_improvement > 0 else "stable"
        }
        
    except Exception as e:
        logger.error(f"Exercise analytics calculation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to calculate exercise analytics: {str(e)}"
        )

@exercises_router.post("/webhook/completion")
async def exercise_completion_webhook(
    request: Request,
    background_tasks: BackgroundTasks
) -> JSONResponse:
    """
    Webhook endpoint for exercise completion from ElevenLabs agents.
    """
    try:
        body = await request.body()
        
        # Verify webhook signature (basic security for MVP)
        if not _verify_elevenlabs_signature(request, body):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")
        
        webhook_data = json.loads(body.decode())
        
        # Process in background
        background_tasks.add_task(
            _process_exercise_completion_webhook,
            webhook_data
        )
        
        return JSONResponse(
            status_code=200,
            content={"status": "received", "message": "Exercise completion processed"}
        )
        
    except json.JSONDecodeError:
        logger.error("Invalid JSON in exercise completion webhook")
        raise HTTPException(status_code=400, detail="Invalid JSON data")
    except Exception as e:
        logger.error(f"Exercise completion webhook failed: {e}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")

@exercises_router.post("/webhook/mood-tracking")
async def exercise_mood_tracking_webhook(
    request: Request,
    background_tasks: BackgroundTasks
) -> JSONResponse:
    """
    Webhook endpoint for mood tracking during exercises.
    """
    try:
        body = await request.body()
        
        if not _verify_elevenlabs_signature(request, body):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")
        
        webhook_data = json.loads(body.decode())
        
        background_tasks.add_task(
            _process_mood_tracking_webhook,
            webhook_data
        )
        
        return JSONResponse(
            status_code=200,
            content={"status": "received", "message": "Mood tracking processed"}
        )
        
    except json.JSONDecodeError:
        logger.error("Invalid JSON in mood tracking webhook")
        raise HTTPException(status_code=400, detail="Invalid JSON data")
    except Exception as e:
        logger.error(f"Mood tracking webhook failed: {e}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")

@exercises_router.get("/recommendations")
async def get_exercise_recommendations(
    user=Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get personalized exercise recommendations based on user history and therapy sessions.
    Requires WorkOS authentication.
    """
    try:
        # Get recent exercise history
        recent_exercises = await mental_exercise_agent.get_exercise_history(
            user_id=user["id"],
            limit=10
        )
        
        # Get available exercises
        available_exercises = mental_exercise_agent.get_available_exercises()
        
        # Simple recommendation logic for MVP
        recommendations = []
        
        if not recent_exercises:
            # New user - recommend starting with mindfulness
            recommendations.append({
                "exercise_type": "mindfulness",
                "reason": "Great starting point for building awareness and reducing stress",
                "priority": "high"
            })
        else:
            # Analyze recent performance
            completed_types = set()
            avg_improvements = {}
            
            for exercise in recent_exercises:
                if exercise['completion_status'] == 'completed':
                    completed_types.add(exercise['exercise_type'])
                    
                    if exercise.get('mood_improvement'):
                        ex_type = exercise['exercise_type']
                        if ex_type not in avg_improvements:
                            avg_improvements[ex_type] = []
                        avg_improvements[ex_type].append(exercise['mood_improvement'])
            
            # Recommend exercises not tried recently
            all_types = set(available_exercises.keys())
            untried_types = all_types - completed_types
            
            for ex_type in untried_types:
                recommendations.append({
                    "exercise_type": ex_type,
                    "reason": f"You haven't tried {available_exercises[ex_type]['name']} yet",
                    "priority": "medium"
                })
            
            # Recommend most effective exercise if available
            if avg_improvements:
                best_type = max(avg_improvements.keys(), 
                              key=lambda x: sum(avg_improvements[x]) / len(avg_improvements[x]))
                recommendations.insert(0, {
                    "exercise_type": best_type,
                    "reason": f"This has been most effective for you recently",
                    "priority": "high"
                })
        
        return {
            "recommendations": recommendations[:3],  # Limit to top 3
            "available_exercises": available_exercises
        }
        
    except Exception as e:
        logger.error(f"Exercise recommendations failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get exercise recommendations: {str(e)}"
        )

# Helper functions for webhook processing

def _verify_elevenlabs_signature(request: Request, body: bytes) -> bool:
    """
    Verify ElevenLabs webhook signature for security.
    For MVP, we'll allow all requests. In production, implement proper HMAC verification.
    """
    # For MVP testing, allow all webhook requests
    # TODO: Implement proper signature verification in production using elevenlabs_auth.verify_webhook_signature
    return True

async def _process_exercise_completion_webhook(webhook_data: Dict[str, Any]) -> None:
    """Process exercise completion webhook data in background"""
    try:
        exercise_id = webhook_data.get('exercise_id')
        completion_status = webhook_data.get('completion_status')
        
        if not exercise_id:
            logger.error("No exercise_id in completion webhook")
            return
        
        logger.info(f"Exercise completion processed: {exercise_id} - {completion_status}")
        
        # Additional processing can be added here
        # e.g., updating completion statistics, triggering notifications
        
    except Exception as e:
        logger.error(f"Background exercise completion processing failed: {e}")

async def _process_mood_tracking_webhook(webhook_data: Dict[str, Any]) -> None:
    """Process mood tracking webhook data in background"""
    try:
        exercise_id = webhook_data.get('exercise_id')
        mood_data = webhook_data.get('mood_tracking', {})
        
        if not exercise_id:
            logger.error("No exercise_id in mood tracking webhook")
            return
        
        logger.info(f"Mood tracking processed for exercise: {exercise_id}")
        
        # Additional mood tracking processing can be added here
        
    except Exception as e:
        logger.error(f"Background mood tracking processing failed: {e}") 