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
    """6-emotion analysis based on Ekman's basic emotions"""
    joy: int = Field(ge=0, le=10, description="Happiness, contentment, satisfaction")
    sadness: int = Field(ge=0, le=10, description="Grief, disappointment, melancholy")
    anger: int = Field(ge=0, le=10, description="Frustration, irritation, rage")
    fear: int = Field(ge=0, le=10, description="Anxiety, worry, panic")
    disgust: int = Field(ge=0, le=10, description="Revulsion, contempt, aversion")
    surprise: int = Field(ge=0, le=10, description="Shock, amazement, confusion")

class EmotionalState(BaseModel):
    """Complete emotional state analysis"""
    primary: str = Field(description="Primary emotion from the 6 core emotions")
    secondary: List[str] = Field(description="Secondary emotions from the 6 core emotions")
    analysis: EmotionAnalysis

class CrisisAssessment(BaseModel):
    """Enhanced LLM-based crisis assessment"""
    level: int = Field(ge=1, le=5, description="Crisis level: 1=No crisis, 5=Imminent danger")
    indicators: List[str] = Field(description="Specific crisis indicators found")
    reasoning: Optional[str] = Field(default="", description="Explanation of the assessment")
    immediate_action_needed: bool = Field(description="Whether immediate intervention is needed")
    recommended_resources: List[str] = Field(description="Appropriate resources for this level")

class JournalAnalysisResponse(BaseModel):
    """Complete journal analysis response with enhanced features"""
    entry_id: str
    user_id: str
    timestamp: str
    normalized_journal: str
    emotions: EmotionalState
    patterns: List[str]
    therapeutic_insight: str = Field(description="Unified therapeutic insight integrating CBT, DBT, and ACT")
    crisis_assessment: CrisisAssessment = Field(description="Enhanced crisis assessment")
    embedding_ready: bool

    @property
    def crisis_detected(self) -> bool:
        """Backward compatibility: crisis detected if level >= 3"""
        return self.crisis_assessment.level >= 3

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

# Legacy support models (for backward compatibility)
class TherapeuticInsights(BaseModel):
    """Legacy multi-modal therapeutic insights - deprecated"""
    cbt: str = Field(description="Cognitive Behavioral Therapy insight")
    dbt: str = Field(description="Dialectical Behavior Therapy insight")
    act: str = Field(description="Acceptance and Commitment Therapy insight") 