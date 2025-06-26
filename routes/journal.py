from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Dict, Any, Optional
import logging

from auth import get_current_user
from config import settings
from agents.journaling_agent import journaling_agent
from database.supabase_client import supabase_client
from models.journal import (
    JournalEntryRequest, 
    JournalAnalysisResponse, 
    JournalHistoryResponse,
    EmotionalState,
    EmotionAnalysis,
    TherapeuticInsights,
    CrisisResourcesResponse
)

logger = logging.getLogger(__name__)

# Create journal router
journal_router = APIRouter(prefix="/journal", tags=["journaling"])

@journal_router.post("/entry", response_model=JournalAnalysisResponse)
async def create_journal_entry(
    entry_request: JournalEntryRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Process and store a new journal entry with therapeutic analysis.
    
    This endpoint:
    1. Normalizes the raw journal entry
    2. Performs multi-modal therapeutic analysis (CBT, DBT, ACT)
    3. Detects crisis indicators
    4. Generates embeddings for future analysis
    5. Encrypts and stores data securely
    6. Returns structured therapeutic insights
    """
    try:
        user_id = current_user["id"]
        
        # Process the journal entry through our LangGraph workflow
        logger.info(f"Processing journal entry for user {user_id}")
        processed_data = await journaling_agent.process_journal_entry(
            raw_entry=entry_request.entry_text,
            user_id=user_id
        )
        
        # Handle crisis situations
        if processed_data["crisis_detected"]:
            logger.warning(f"Crisis indicators detected for user {user_id}")
            # TODO: Implement crisis intervention protocols
            # - Send alert to crisis response team
            # - Provide immediate resources
            # - Flag for priority follow-up
        
        # Convert to response model
        response = JournalAnalysisResponse(
            entry_id=processed_data["entry_id"],
            user_id=user_id,
            timestamp=processed_data["timestamp"],
            normalized_journal=processed_data["normalized_journal"],
            emotions=EmotionalState(
                primary=processed_data["emotions"]["primary"],
                secondary=processed_data["emotions"]["secondary"],
                analysis=EmotionAnalysis(**processed_data["emotions"]["analysis"])
            ),
            patterns=processed_data["patterns"],
            therapeutic_insights=TherapeuticInsights(**processed_data["therapeutic_insights"]),
            crisis_detected=processed_data["crisis_detected"],
            embedding_ready=processed_data["embedding_ready"]
        )
        
        logger.info(f"Journal entry processed successfully: {processed_data['entry_id']}")
        return response
        
    except ValueError as e:
        logger.error(f"Journal processing validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Journal processing failed: {e}")
        raise HTTPException(status_code=500, detail="Journal processing failed")

@journal_router.get("/entries", response_model=JournalHistoryResponse)
async def get_journal_history(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=50, description="Entries per page"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Retrieve user's journal history with pagination.
    Returns decrypted insights but keeps raw entries encrypted for security.
    """
    try:
        user_id = current_user["id"]
        offset = (page - 1) * page_size
        
        # Get entries from Supabase
        history_data = await supabase_client.get_journal_entries(
            user_id=user_id,
            limit=page_size,
            offset=offset
        )
        
        # Convert to response models
        entries = []
        for entry in history_data["entries"]:
            analysis_response = JournalAnalysisResponse(
                entry_id=entry["entry_id"],
                user_id=entry["user_id"],
                timestamp=entry["timestamp"],
                normalized_journal=entry["normalized_journal"],
                emotions=EmotionalState(
                    primary=entry["emotions"]["primary"],
                    secondary=entry["emotions"]["secondary"],
                    analysis=EmotionAnalysis(**entry["emotions"]["analysis"])
                ),
                patterns=entry["patterns"],
                therapeutic_insights=TherapeuticInsights(**entry["therapeutic_insights"]),
                crisis_detected=entry["crisis_detected"],
                embedding_ready=True  # Assume processed entries have embeddings
            )
            entries.append(analysis_response)
        
        response = JournalHistoryResponse(
            entries=entries,
            total_count=history_data["total_count"],
            page=page,
            page_size=page_size,
            has_next=history_data["has_next"],
            has_previous=history_data["has_previous"]
        )
        
        logger.info(f"Retrieved {len(entries)} journal entries for user {user_id}")
        return response
        
    except Exception as e:
        logger.error(f"Failed to retrieve journal history for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve journal history")

@journal_router.get("/insights/summary")
async def get_insights_summary(
    days: int = Query(30, ge=1, le=365, description="Days to analyze"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Generate therapeutic insights summary over specified time period.
    Provides pattern analysis and progress tracking.
    """
    try:
        user_id = current_user["id"]
        
        # TODO: Implement comprehensive analysis across multiple entries
        # This would include:
        # - Emotional trend analysis over time
        # - Cognitive pattern frequency analysis
        # - Progress marker tracking
        # - Therapeutic recommendation updates
        # - Crisis incident tracking
        
        return {
            "message": "Insights summary endpoint - implementation pending",
            "user_id": user_id,
            "analysis_period_days": days,
            "note": "This will provide longitudinal analysis of journal entries"
        }
        
    except Exception as e:
        logger.error(f"Failed to generate insights summary for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate insights summary")

@journal_router.get("/crisis/resources", response_model=CrisisResourcesResponse)
async def get_crisis_resources():
    """
    Provide immediate crisis intervention resources.
    Available without authentication for emergency access.
    """
    return CrisisResourcesResponse(
        immediate_help={
            "suicide_prevention_lifeline": {
                "phone": "988",
                "text": "Text HOME to 741741",
                "chat": "https://suicidepreventionlifeline.org/chat/",
                "description": "24/7 free and confidential support"
            },
            "crisis_text_line": {
                "text": "741741",
                "description": "24/7 crisis support via text message"
            },
            "emergency": {
                "phone": "911",
                "description": "For immediate life-threatening emergencies"
            },
            "international": {
                "website": "https://findahelpline.com",
                "description": "Find crisis helplines worldwide"
            }
        },
        mental_health_resources={
            "nami_helpline": {
                "phone": "1-800-950-NAMI (6264)",
                "description": "National Alliance on Mental Illness support"
            },
            "samhsa_helpline": {
                "phone": "1-800-662-4357",
                "description": "Substance Abuse and Mental Health Services"
            },
            "therapy_platforms": {
                "betterhelp": "https://www.betterhelp.com",
                "psychology_today": "https://www.psychologytoday.com/us/therapists",
                "open_path": "https://openpathcollective.org"
            }
        },
        note="If you're experiencing thoughts of self-harm or suicide, please reach out immediately. You are not alone, and help is available."
    )

@journal_router.get("/health")
async def journal_health_check():
    """Health check for journal service components"""
    try:
        # Test agent initialization
        agent_healthy = journaling_agent is not None
        
        # Test database connection (basic check)
        db_healthy = supabase_client is not None
        
        return {
            "status": "healthy" if agent_healthy and db_healthy else "degraded",
            "components": {
                "journaling_agent": "healthy" if agent_healthy else "error",
                "database": "healthy" if db_healthy else "error",
                "encryption": "healthy" if journaling_agent.fernet else "error"
            },
            "features": {
                "normalization": True,
                "multi_modal_analysis": True,
                "crisis_detection": True,
                "embedding_generation": bool(settings.HF_API_KEY),
                "encrypted_storage": True
            }
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "error",
            "error": str(e)
        } 