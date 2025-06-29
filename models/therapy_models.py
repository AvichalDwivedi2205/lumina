from typing import Optional, Dict, List, Any
from datetime import datetime
from pydantic import BaseModel, Field
import uuid

class TherapySessionCreate(BaseModel):
    """Model for creating a new therapy session"""
    therapist_type: str = Field(..., description="Type of therapist: 'male' or 'female'")
    session_mode: str = Field(..., description="Session mode: 'voice' or 'video'")

class TherapySessionResponse(BaseModel):
    """Model for therapy session response"""
    success: bool
    session_id: Optional[str] = None
    agent_config: Optional[Dict[str, Any]] = None
    tavus_conversation: Optional[Dict[str, Any]] = None
    session_context: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class TherapyWebhookData(BaseModel):
    """Model for therapy webhook data from ElevenLabs/Tavus"""
    session_id: str
    transcript: Optional[str] = None
    therapy_notes: Optional[Dict[str, Any]] = None
    exercise_recommendation: Optional[Dict[str, Any]] = None
    crisis_indicators: Optional[List[str]] = None
    mood_rating: Optional[int] = Field(None, ge=1, le=10)
    conversation_id: Optional[str] = None

class TherapyNotesData(BaseModel):
    """Model for therapy notes structure"""
    session_date: str
    mood_rating: Optional[int] = Field(None, ge=1, le=10)
    key_topics: List[str] = []
    cognitive_patterns: List[str] = []
    interventions_used: List[str] = []
    progress_notes: str = ""
    homework_assigned: str = ""
    treatment_goals: List[str] = []

class ExerciseRecommendation(BaseModel):
    """Model for exercise recommendation"""
    exercise_type: str = Field(..., description="Type of exercise to recommend")
    rationale: str = Field(..., description="Why this exercise is recommended")
    priority: str = Field(..., description="Priority level: 'low', 'medium', 'high'")

class CrisisAssessment(BaseModel):
    """Model for crisis assessment"""
    crisis_detected: bool
    level: Optional[str] = Field(None, description="Crisis level: 'low', 'medium', 'high'")
    indicators: List[str] = []
    resources: Optional[Dict[str, str]] = None

class TherapySessionHistory(BaseModel):
    """Model for therapy session history item"""
    session_id: str
    session_date: str
    therapist_type: str
    session_mode: str
    session_summary: str
    exercises_recommended: List[Dict[str, Any]] = []
    reflection_questions: List[str] = []

class MentalExerciseCreate(BaseModel):
    """Model for creating a new mental exercise session"""
    exercise_type: str = Field(..., description="Type of exercise: 'mindfulness', 'cbt_tools', 'behavioral_activation', 'self_compassion'")
    mood_before: Optional[int] = Field(None, ge=1, le=10, description="Mood rating before exercise")

class MentalExerciseComplete(BaseModel):
    """Model for completing a mental exercise"""
    exercise_id: str
    mood_after: int = Field(..., ge=1, le=10, description="Mood rating after exercise")
    exercise_notes: Optional[str] = None

class MentalExerciseResponse(BaseModel):
    """Model for mental exercise response"""
    success: bool
    exercise_id: Optional[str] = None
    agent_config: Optional[Dict[str, Any]] = None
    personalization: Optional[Dict[str, Any]] = None
    exercise_info: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class ExerciseWebhookData(BaseModel):
    """Model for exercise webhook data from ElevenLabs"""
    exercise_id: str
    completion_status: str = Field(..., description="Status: 'started', 'completed', 'interrupted'")
    transcript: Optional[str] = None
    mood_tracking: Optional[Dict[str, Any]] = None
    exercise_notes: Optional[str] = None

class ExerciseHistory(BaseModel):
    """Model for exercise history item"""
    exercise_id: str
    exercise_type: str
    session_date: str
    duration_minutes: int
    completion_status: str
    mood_before: Optional[int] = None
    mood_after: Optional[int] = None
    mood_improvement: Optional[int] = None
    effectiveness_analysis: Optional[Dict[str, Any]] = None

class AvailableExercises(BaseModel):
    """Model for available exercise types"""
    exercise_type: str
    name: str
    description: str
    duration_minutes: int
    techniques: List[str]
    benefits: List[str]

class ReflectionQuestions(BaseModel):
    """Model for post-session reflection questions"""
    session_id: str
    questions: List[str]

class SessionAnalytics(BaseModel):
    """Model for session analytics"""
    total_sessions: int
    avg_session_rating: Optional[float] = None
    most_common_topics: List[str] = []
    progress_indicators: Dict[str, Any] = {}
    exercise_completion_rate: float = 0.0 