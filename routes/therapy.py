from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import List, Dict, Any
import logging
import json
import hmac
import hashlib

from auth import get_current_user
from agents.therapy_agent import therapy_agent
from services.elevenlabs_auth import elevenlabs_auth
from models.therapy_models import (
    TherapySessionCreate, TherapySessionResponse, TherapyWebhookData,
    TherapySessionHistory, CrisisAssessment, ReflectionQuestions
)
from config import settings

logger = logging.getLogger(__name__)

therapy_router = APIRouter(prefix="/therapy", tags=["therapy"])

@therapy_router.post("/session/start", response_model=TherapySessionResponse)
async def start_therapy_session(
    session_data: TherapySessionCreate,
    user=Depends(get_current_user)
) -> TherapySessionResponse:
    """
    Start a new therapy session with specified therapist type and mode.
    Requires WorkOS authentication.
    """
    try:
        # Validate therapist type and session mode
        if session_data.therapist_type not in ['male', 'female']:
            raise HTTPException(
                status_code=400, 
                detail="Invalid therapist type. Must be 'male' or 'female'"
            )
        
        if session_data.session_mode not in ['voice', 'video']:
            raise HTTPException(
                status_code=400,
                detail="Invalid session mode. Must be 'voice' or 'video'"
            )
        
        # Check if ElevenLabs is configured
        if not settings.is_elevenlabs_configured:
            raise HTTPException(
                status_code=503,
                detail="ElevenLabs not configured. Please check API settings."
            )
        
        # Check Tavus configuration for video sessions
        if session_data.session_mode == 'video' and not settings.is_tavus_configured:
            raise HTTPException(
                status_code=503,
                detail="Tavus not configured for video sessions. Please check API settings."
            )
        
        # Start therapy session using the agent
        result = await therapy_agent.start_therapy_session(
            user_id=user["id"],
            therapist_type=session_data.therapist_type,
            session_mode=session_data.session_mode
        )
        
        if not result['success']:
            raise HTTPException(
                status_code=500,
                detail=result.get('error', 'Failed to start therapy session')
            )
        
        logger.info(f"Therapy session started for user {user["id"]}: {result['session_id']}")
        
        return TherapySessionResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Therapy session start failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

@therapy_router.post("/session/{session_id}/agent-url")
async def get_therapy_agent_url(
    session_id: str,
    therapist_type: str,
    user=Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get a secure signed URL for ElevenLabs therapy agent access.
    This endpoint provides time-limited URLs for client-side agent connections.
    """
    try:
        if therapist_type not in ['male', 'female']:
            raise HTTPException(
                status_code=400,
                detail="Invalid therapist type. Must be 'male' or 'female'"
            )
        
        # Generate secure signed URL
        result = await elevenlabs_auth.get_therapy_agent_url(
            therapist_type=therapist_type,
            user_id=user["id"],
            session_id=session_id
        )
        
        if not result['success']:
            raise HTTPException(
                status_code=500,
                detail=result.get('error', 'Failed to generate agent URL')
            )
        
        logger.info(f"Generated therapy agent URL for user {user["id"]}, session {session_id}")
        
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

@therapy_router.get("/sessions/history", response_model=List[TherapySessionHistory])
async def get_therapy_history(
    limit: int = 10,
    user=Depends(get_current_user)
) -> List[TherapySessionHistory]:
    """
    Get user's therapy session history.
    Requires WorkOS authentication.
    """
    try:
        if limit < 1 or limit > 50:
            raise HTTPException(
                status_code=400,
                detail="Limit must be between 1 and 50"
            )
        
        sessions = await therapy_agent.get_session_history(
            user_id=user["id"],
            limit=limit
        )
        
        return [TherapySessionHistory(**session) for session in sessions]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Therapy history retrieval failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve therapy history: {str(e)}"
        )

@therapy_router.post("/webhook/notes")
async def therapy_notes_webhook(
    request: Request,
    background_tasks: BackgroundTasks
) -> JSONResponse:
    """
    Webhook endpoint for receiving therapy notes from ElevenLabs agents.
    Handles real-time note-taking during therapy sessions.
    """
    try:
        # Get request body
        body = await request.body()
        
        # Verify webhook signature (basic security)
        if not _verify_elevenlabs_signature(request, body):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")
        
        # Parse webhook data
        webhook_data = json.loads(body.decode())
        
        # Process in background to avoid blocking the webhook response
        background_tasks.add_task(
            _process_therapy_notes_webhook,
            webhook_data
        )
        
        return JSONResponse(
            status_code=200,
            content={"status": "received", "message": "Therapy notes processed"}
        )
        
    except json.JSONDecodeError:
        logger.error("Invalid JSON in therapy notes webhook")
        raise HTTPException(status_code=400, detail="Invalid JSON data")
    except Exception as e:
        logger.error(f"Therapy notes webhook failed: {e}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")

@therapy_router.post("/webhook/recommend-exercise")
async def exercise_recommendation_webhook(
    request: Request,
    background_tasks: BackgroundTasks
) -> JSONResponse:
    """
    Webhook endpoint for receiving exercise recommendations from therapy agents.
    """
    try:
        body = await request.body()
        
        if not _verify_elevenlabs_signature(request, body):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")
        
        webhook_data = json.loads(body.decode())
        
        background_tasks.add_task(
            _process_exercise_recommendation_webhook,
            webhook_data
        )
        
        return JSONResponse(
            status_code=200,
            content={"status": "received", "message": "Exercise recommendation processed"}
        )
        
    except json.JSONDecodeError:
        logger.error("Invalid JSON in exercise recommendation webhook")
        raise HTTPException(status_code=400, detail="Invalid JSON data")
    except Exception as e:
        logger.error(f"Exercise recommendation webhook failed: {e}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")

@therapy_router.post("/webhook/crisis-alert")
async def crisis_alert_webhook(
    request: Request,
    background_tasks: BackgroundTasks
) -> JSONResponse:
    """
    Webhook endpoint for crisis detection alerts from therapy agents.
    """
    try:
        body = await request.body()
        
        if not _verify_elevenlabs_signature(request, body):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")
        
        webhook_data = json.loads(body.decode())
        
        # Process crisis alerts immediately (not in background)
        crisis_response = await _process_crisis_alert_webhook(webhook_data)
        
        return JSONResponse(
            status_code=200,
            content=crisis_response
        )
        
    except json.JSONDecodeError:
        logger.error("Invalid JSON in crisis alert webhook")
        raise HTTPException(status_code=400, detail="Invalid JSON data")
    except Exception as e:
        logger.error(f"Crisis alert webhook failed: {e}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")

@therapy_router.post("/webhook/tavus-callback")
async def tavus_callback_webhook(
    request: Request,
    background_tasks: BackgroundTasks
) -> JSONResponse:
    """
    Webhook endpoint for Tavus video conversation callbacks.
    """
    try:
        body = await request.body()
        
        # Verify Tavus webhook signature if needed
        webhook_data = json.loads(body.decode())
        
        background_tasks.add_task(
            _process_tavus_callback_webhook,
            webhook_data
        )
        
        return JSONResponse(
            status_code=200,
            content={"status": "received", "message": "Tavus callback processed"}
        )
        
    except json.JSONDecodeError:
        logger.error("Invalid JSON in Tavus callback webhook")
        raise HTTPException(status_code=400, detail="Invalid JSON data")
    except Exception as e:
        logger.error(f"Tavus callback webhook failed: {e}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")

@therapy_router.get("/session/{session_id}/reflection", response_model=ReflectionQuestions)
async def get_reflection_questions(
    session_id: str,
    user=Depends(get_current_user)
) -> ReflectionQuestions:
    """
    Get reflection questions for a completed therapy session.
    """
    try:
        # Verify session belongs to user
        sessions = await therapy_agent.get_session_history(user_id=user["id"], limit=50)
        session = next((s for s in sessions if s['session_id'] == session_id), None)
        
        if not session:
            raise HTTPException(
                status_code=404,
                detail="Session not found or access denied"
            )
        
        return ReflectionQuestions(
            session_id=session_id,
            questions=session.get('reflection_questions', [])
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Reflection questions retrieval failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve reflection questions: {str(e)}"
        )

@therapy_router.get("/agents/status")
async def get_agent_status(
    user=Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get status of all ElevenLabs therapy agents.
    Requires WorkOS authentication.
    """
    try:
        statuses = await elevenlabs_auth.get_all_agent_statuses()
        return {
            'success': True,
            'agent_statuses': statuses,
            'available_agents': elevenlabs_auth.get_available_agents()
        }
        
    except Exception as e:
        logger.error(f"Failed to get agent status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve agent status: {str(e)}"
        )

@therapy_router.get("/crisis/resources")
async def get_crisis_resources() -> Dict[str, Any]:
    """
    Get crisis intervention resources.
    Public endpoint for immediate access to crisis support.
    """
    return {
        "immediate_crisis": {
            "suicide_lifeline": {
                "number": "988",
                "description": "Suicide & Crisis Lifeline - 24/7 support",
                "website": "https://988lifeline.org"
            },
            "crisis_text": {
                "number": "741741",
                "text": "HOME",
                "description": "Crisis Text Line - Text HOME to 741741"
            },
            "emergency": {
                "number": "911",
                "description": "Emergency services for immediate danger"
            }
        },
        "additional_resources": {
            "nami": {
                "website": "https://nami.org",
                "description": "National Alliance on Mental Illness"
            },
            "samhsa": {
                "website": "https://samhsa.gov",
                "description": "Substance Abuse and Mental Health Services Administration"
            }
        },
        "self_care_immediate": [
            "Take slow, deep breaths",
            "Reach out to a trusted friend or family member",
            "Remove yourself from harmful situations",
            "Practice grounding techniques (5-4-3-2-1 method)",
            "Engage in safe, comforting activities"
        ]
    }

# Helper functions for webhook processing

def _verify_elevenlabs_signature(request: Request, body: bytes) -> bool:
    """
    Verify ElevenLabs webhook signature for security.
    For MVP, we'll allow all requests. In production, implement proper HMAC verification.
    """
    # For MVP testing, allow all webhook requests
    # TODO: Implement proper signature verification in production using elevenlabs_auth.verify_webhook_signature
    return True

async def _process_therapy_notes_webhook(webhook_data: Dict[str, Any]) -> None:
    """Process therapy notes webhook data in background"""
    try:
        session_id = webhook_data.get('session_id')
        if not session_id:
            logger.error("No session_id in therapy notes webhook")
            return
        
        # Process the webhook data using the therapy agent
        result = await therapy_agent.process_session_webhook(session_id, webhook_data)
        
        if not result['success']:
            logger.error(f"Failed to process therapy notes webhook: {result.get('error')}")
        
        logger.info(f"Therapy notes processed for session {session_id}")
        
    except Exception as e:
        logger.error(f"Background therapy notes processing failed: {e}")

async def _process_exercise_recommendation_webhook(webhook_data: Dict[str, Any]) -> None:
    """Process exercise recommendation webhook data in background"""
    try:
        session_id = webhook_data.get('session_id')
        exercise_recommendation = webhook_data.get('exercise_recommendation')
        
        if not session_id or not exercise_recommendation:
            logger.error("Missing data in exercise recommendation webhook")
            return
        
        # Store exercise recommendation
        logger.info(f"Exercise recommendation processed for session {session_id}: {exercise_recommendation}")
        
    except Exception as e:
        logger.error(f"Background exercise recommendation processing failed: {e}")

async def _process_crisis_alert_webhook(webhook_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process crisis alert webhook data immediately"""
    try:
        session_id = webhook_data.get('session_id')
        crisis_indicators = webhook_data.get('crisis_indicators', [])
        
        if not session_id:
            return {"error": "No session_id provided"}
        
        # Process crisis detection
        result = await therapy_agent.process_session_webhook(session_id, webhook_data)
        
        if result.get('crisis_detected'):
            logger.critical(f"CRISIS DETECTED in session {session_id}: {crisis_indicators}")
            
            return {
                "status": "crisis_detected",
                "level": result.get('crisis_level', 'high'),
                "resources": result.get('crisis_resources', {}),
                "immediate_action_required": True
            }
        
        return {"status": "no_crisis_detected"}
        
    except Exception as e:
        logger.error(f"Crisis alert processing failed: {e}")
        return {"error": f"Crisis processing failed: {str(e)}"}

async def _process_tavus_callback_webhook(webhook_data: Dict[str, Any]) -> None:
    """Process Tavus callback webhook data in background"""
    try:
        conversation_id = webhook_data.get('conversation_id')
        event_type = webhook_data.get('event_type')
        
        if not conversation_id:
            logger.error("No conversation_id in Tavus callback webhook")
            return
        
        logger.info(f"Tavus callback processed: {event_type} for conversation {conversation_id}")
        
        # Handle different Tavus events
        if event_type == 'conversation_ended':
            # Process session completion
            pass
        elif event_type == 'transcript_ready':
            # Process transcript data
            pass
        
    except Exception as e:
        logger.error(f"Background Tavus callback processing failed: {e}") 