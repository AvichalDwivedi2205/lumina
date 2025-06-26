from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum

class JournalEntryRequest(BaseModel):
    """Request model for journal entry submission"""
    entry_text: str = Field(..., min_length=10, max_length=10000, description="Raw journal entry text")
    tags: Optional[List[str]] = Field(default=[], description="Optional tags for categorization")
    
    @validator('entry_text')
    def validate_entry_text(cls, v):
        if not v.strip():
            raise ValueError("Journal entry cannot be empty")
        return v.strip()

class EmotionAnalysis(BaseModel):
    """6-emotion analysis with intensity scoring"""
    anxiety: int = Field(ge=0, le=10)
    depression: int = Field(ge=0, le=10)
    anger: int = Field(ge=0, le=10)
    joy: int = Field(ge=0, le=10)
    fear: int = Field(ge=0, le=10)
    sadness: int = Field(ge=0, le=10)

class EmotionalState(BaseModel):
    """Complete emotional state analysis"""
    primary: str
    secondary: List[str]
    analysis: EmotionAnalysis

class TherapeuticInsights(BaseModel):
    """Multi-modal therapeutic insights"""
    cbt: str = Field(description="Cognitive Behavioral Therapy insight")
    dbt: str = Field(description="Dialectical Behavior Therapy insight")
    act: str = Field(description="Acceptance and Commitment Therapy insight")

class JournalAnalysisResponse(BaseModel):
    """Complete journal analysis response"""
    entry_id: str
    user_id: str
    timestamp: str
    normalized_journal: str
    emotions: EmotionalState
    patterns: List[str]
    therapeutic_insights: TherapeuticInsights
    crisis_detected: bool
    embedding_ready: bool

class JournalHistoryResponse(BaseModel):
    """Journal history with pagination"""
    entries: List[JournalAnalysisResponse]
    total_count: int
    page: int
    page_size: int
    has_next: bool
    has_previous: bool

class CrisisResourcesResponse(BaseModel):
    """Crisis intervention resources"""
    immediate_help: Dict[str, Any]
    mental_health_resources: Dict[str, Any]
    note: str 