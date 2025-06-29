from pydantic import BaseModel, Field, validator
from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum

class PersonalityType(str, Enum):
    SUPPORTIVE = "supportive"
    MOTIVATOR = "motivator"
    MENTOR = "mentor"
    FUNNY = "funny"
    MINDFUL = "mindful"
    AUTO = "auto"  # Let AI choose

class MoodLevel(str, Enum):
    VERY_LOW = "very_low"
    LOW = "low"
    NEUTRAL = "neutral"
    GOOD = "good"
    VERY_GOOD = "very_good"

class SatisfactionRating(int, Enum):
    VERY_DISSATISFIED = 1
    DISSATISFIED = 2
    NEUTRAL = 3
    SATISFIED = 4
    VERY_SATISFIED = 5

# Conversation Request Models
class FriendConversationRequest(BaseModel):
    personality_type: PersonalityType = Field(PersonalityType.AUTO, description="Preferred AI friend personality")
    user_message: Optional[str] = Field(None, max_length=500, description="Initial message or context")
    mood: Optional[MoodLevel] = Field(None, description="Current mood level")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context for personality selection")
    
    class Config:
        json_schema_extra = {
            "example": {
                "personality_type": "supportive",
                "user_message": "I'm feeling overwhelmed with work today",
                "mood": "low",
                "context": {
                    "recent_stress": "high",
                    "support_needed": "emotional"
                }
            }
        }

class PersonalityRecommendationRequest(BaseModel):
    current_mood: Optional[MoodLevel] = None
    situation: Optional[str] = Field(None, max_length=300, description="Current situation or challenge")
    support_type_needed: Optional[str] = Field(None, description="Type of support needed")
    energy_level: Optional[str] = Field(None, pattern="^(low|medium|high)$")
    time_of_day: Optional[str] = Field(None, description="Current time context")
    recent_interactions: Optional[List[str]] = Field(None, description="Recent personality types used")
    
    class Config:
        json_schema_extra = {
            "example": {
                "current_mood": "low",
                "situation": "Had a difficult day at work and feeling unmotivated",
                "support_type_needed": "encouragement",
                "energy_level": "low",
                "time_of_day": "evening",
                "recent_interactions": ["mentor", "supportive"]
            }
        }

# Session Management Models
class SessionFeedback(BaseModel):
    satisfaction_rating: SatisfactionRating
    mood_after: Optional[MoodLevel] = None
    helpful_aspects: Optional[List[str]] = Field(None, description="What was most helpful")
    improvement_suggestions: Optional[str] = Field(None, max_length=500)
    would_use_again: Optional[bool] = None
    session_notes: Optional[str] = Field(None, max_length=300, description="Additional notes about the session")
    
    class Config:
        json_schema_extra = {
            "example": {
                "satisfaction_rating": 4,
                "mood_after": "good",
                "helpful_aspects": ["active listening", "practical advice"],
                "improvement_suggestions": "Could be more specific with action steps",
                "would_use_again": True,
                "session_notes": "Really appreciated the empathetic approach"
            }
        }

class MoodTrackingRequest(BaseModel):
    mood_before: MoodLevel
    mood_after: Optional[MoodLevel] = None
    personality_used: PersonalityType
    mood_improvement_score: Optional[int] = Field(None, ge=-5, le=5, description="Mood change score (-5 to +5)")
    interaction_notes: Optional[str] = Field(None, max_length=200)
    
    class Config:
        json_schema_extra = {
            "example": {
                "mood_before": "low",
                "mood_after": "good",
                "personality_used": "supportive",
                "mood_improvement_score": 3,
                "interaction_notes": "Felt much better after talking through my concerns"
            }
        }

# User Preferences Models
class FriendPreferencesUpdate(BaseModel):
    preferred_personalities: Optional[List[PersonalityType]] = Field(None, description="Preferred personality types")
    interaction_style: Optional[str] = Field(None, description="Preferred interaction style")
    topics_of_interest: Optional[List[str]] = Field(None, description="Topics user enjoys discussing")
    communication_preferences: Optional[Dict[str, Any]] = Field(None, description="Communication preferences")
    availability_schedule: Optional[Dict[str, Any]] = Field(None, description="When user typically wants to chat")
    
    class Config:
        json_schema_extra = {
            "example": {
                "preferred_personalities": ["supportive", "mentor"],
                "interaction_style": "gentle and encouraging",
                "topics_of_interest": ["personal growth", "stress management", "goal setting"],
                "communication_preferences": {
                    "session_length": "medium",
                    "conversation_pace": "thoughtful"
                },
                "availability_schedule": {
                    "preferred_times": ["morning", "evening"],
                    "timezone": "EST"
                }
            }
        }

# Response Models
class PersonalityInfo(BaseModel):
    name: str
    type: PersonalityType
    voice_style: str
    specialties: List[str]
    description: Optional[str] = None

class FriendConversationResponse(BaseModel):
    success: bool
    personality: Optional[PersonalityInfo] = None
    conversation: Optional[Dict[str, Any]] = None
    instructions: Optional[Dict[str, str]] = None
    error: Optional[str] = None

class PersonalityRecommendationResponse(BaseModel):
    success: bool
    recommended_personality: Optional[PersonalityType] = None
    reason: Optional[str] = None
    alternative: Optional[PersonalityType] = None
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    error: Optional[str] = None

class PersonalitiesResponse(BaseModel):
    success: bool
    personalities: Optional[Dict[str, PersonalityInfo]] = None
    error: Optional[str] = None

# Session History Models
class FriendSessionSummary(BaseModel):
    id: str
    personality_type: PersonalityType
    session_start: datetime
    session_end: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    satisfaction_rating: Optional[SatisfactionRating] = None
    mood_improvement: Optional[int] = None

class FriendSessionHistoryResponse(BaseModel):
    success: bool
    sessions: List[FriendSessionSummary]
    summary: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

# Analytics Models
class PersonalityAnalytics(BaseModel):
    personality_type: PersonalityType
    usage_count: int
    total_duration_minutes: int
    average_satisfaction: Optional[float] = None
    last_used_at: Optional[datetime] = None
    effectiveness_score: Optional[float] = None

class FriendAnalyticsResponse(BaseModel):
    success: bool
    total_sessions: Optional[int] = None
    personalities_used: Optional[int] = None
    avg_session_duration: Optional[float] = None
    avg_satisfaction: Optional[float] = None
    last_interaction: Optional[datetime] = None
    days_since_last_interaction: Optional[int] = None
    personality_breakdown: Optional[List[PersonalityAnalytics]] = None
    error: Optional[str] = None

class MoodTrendData(BaseModel):
    week: datetime
    personality_used: PersonalityType
    avg_mood_improvement: float
    interactions_count: int

class MoodTrendsResponse(BaseModel):
    success: bool
    mood_trends: List[MoodTrendData]
    overall_improvement: Optional[float] = None
    most_effective_personality: Optional[PersonalityType] = None
    error: Optional[str] = None

# User Preferences Response Models
class FriendPreferences(BaseModel):
    preferred_personalities: List[PersonalityType]
    interaction_history: Dict[str, Any]
    mood_patterns: Dict[str, Any]
    last_interaction_at: Optional[datetime] = None
    total_conversations: int
    favorite_personality: Optional[PersonalityType] = None
    created_at: datetime
    updated_at: datetime

class FriendPreferencesResponse(BaseModel):
    success: bool
    preferences: Optional[FriendPreferences] = None
    error: Optional[str] = None

# Session End Models
class SessionEndResponse(BaseModel):
    success: bool
    session_summary: Optional[Dict[str, Any]] = None
    mood_improvement: Optional[int] = None
    recommendations: Optional[List[str]] = None
    next_session_suggestions: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

# Mood Tracking Response Models
class MoodTrackingResponse(BaseModel):
    success: bool
    mood_entry_id: Optional[str] = None
    improvement_detected: Optional[bool] = None
    personality_effectiveness: Optional[float] = None
    error: Optional[str] = None

# Validation helpers
@validator('satisfaction_rating')
def validate_satisfaction_rating(cls, v):
    if v is not None and v not in [1, 2, 3, 4, 5]:
        raise ValueError('Satisfaction rating must be between 1 and 5')
    return v

@validator('mood_improvement_score')
def validate_mood_improvement(cls, v):
    if v is not None and (v < -5 or v > 5):
        raise ValueError('Mood improvement score must be between -5 and 5')
    return v

@validator('user_message')
def validate_user_message(cls, v):
    if v is not None and len(v.strip()) < 3:
        raise ValueError('User message must be at least 3 characters long')
    return v 