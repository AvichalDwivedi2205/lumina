from pydantic import BaseModel, Field, validator
from typing import Dict, List, Any, Optional
from datetime import datetime, time, date
from enum import Enum

class ScheduleType(str, Enum):
    THERAPY = "therapy"
    EXERCISE = "exercise"
    JOURNAL = "journal"
    SLEEP = "sleep"
    ROUTINE = "routine"

class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class Frequency(str, Enum):
    ONCE = "once"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CUSTOM = "custom"

class ConflictType(str, Enum):
    TIME_OVERLAP = "time_overlap"
    RESOURCE_CONFLICT = "resource_conflict"
    PRIORITY_CONFLICT = "priority_conflict"

class ResolutionStatus(str, Enum):
    UNRESOLVED = "unresolved"
    RESOLVED = "resolved"
    IGNORED = "ignored"

class TemplateType(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"

# Schedule Creation Models
class ScheduleCreateRequest(BaseModel):
    schedule_type: ScheduleType
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    start_time: datetime = Field(..., description="When the scheduled item should start")
    duration: int = Field(..., ge=5, le=480, description="Duration in minutes")
    frequency: Frequency = Field(Frequency.ONCE, description="How often this repeats")
    frequency_data: Optional[Dict[str, Any]] = Field(None, description="Custom frequency rules")
    priority: Priority = Field(Priority.MEDIUM, description="Priority level")
    preferences: Optional[Dict[str, Any]] = Field(None, description="Specific preferences for this item")
    
    class Config:
        json_schema_extra = {
            "example": {
                "schedule_type": "therapy",
                "title": "Weekly Therapy Session",
                "description": "Regular therapy session focusing on anxiety management",
                "start_time": "2024-01-15T14:00:00Z",
                "duration": 45,
                "frequency": "weekly",
                "frequency_data": {
                    "days_of_week": [1],  # Monday
                    "end_date": "2024-12-31"
                },
                "priority": "high",
                "preferences": {
                    "therapist_preference": "Dr. Smith",
                    "session_type": "video"
                }
            }
        }

class ScheduleUpdateRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    start_time: Optional[datetime] = None
    duration: Optional[int] = Field(None, ge=5, le=480)
    frequency: Optional[Frequency] = None
    frequency_data: Optional[Dict[str, Any]] = None
    priority: Optional[Priority] = None
    preferences: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "start_time": "2024-01-15T15:00:00Z",
                "duration": 60,
                "priority": "critical",
                "preferences": {
                    "reminder_minutes": 30
                }
            }
        }

# Schedule Completion Models
class ScheduleCompletionRequest(BaseModel):
    completion_notes: Optional[str] = Field(None, max_length=300)
    effectiveness_rating: Optional[int] = Field(None, ge=1, le=5, description="How effective was this activity (1-5)")
    mood_before: Optional[str] = Field(None, description="Mood before the activity")
    mood_after: Optional[str] = Field(None, description="Mood after the activity")
    duration_actual: Optional[int] = Field(None, ge=1, description="Actual duration in minutes")
    
    class Config:
        json_schema_extra = {
            "example": {
                "completion_notes": "Great session, made good progress on anxiety techniques",
                "effectiveness_rating": 4,
                "mood_before": "anxious",
                "mood_after": "calm",
                "duration_actual": 50
            }
        }

# Conflict Resolution Models
class ConflictResolutionRequest(BaseModel):
    resolution_action: str = Field(..., description="Action taken to resolve conflict")
    resolution_notes: Optional[str] = Field(None, max_length=500)
    priority_override: Optional[str] = Field(None, description="Which item takes priority")
    reschedule_data: Optional[Dict[str, Any]] = Field(None, description="Rescheduling information")
    
    class Config:
        json_schema_extra = {
            "example": {
                "resolution_action": "reschedule_lower_priority",
                "resolution_notes": "Moved exercise session to accommodate urgent therapy appointment",
                "priority_override": "therapy",
                "reschedule_data": {
                    "new_start_time": "2024-01-15T18:00:00Z",
                    "reason": "conflict_resolution"
                }
            }
        }

# User Preferences Models
class SchedulingPreferencesUpdate(BaseModel):
    timezone: Optional[str] = Field(None, description="User's timezone")
    work_schedule: Optional[Dict[str, Any]] = Field(None, description="Work hours and days")
    sleep_preferences: Optional[Dict[str, Any]] = Field(None, description="Sleep schedule preferences")
    notification_preferences: Optional[Dict[str, Any]] = Field(None, description="Notification settings")
    therapy_preferences: Optional[Dict[str, Any]] = Field(None, description="Therapy scheduling preferences")
    exercise_preferences: Optional[Dict[str, Any]] = Field(None, description="Exercise scheduling preferences")
    journal_preferences: Optional[Dict[str, Any]] = Field(None, description="Journaling preferences")
    
    class Config:
        json_schema_extra = {
            "example": {
                "timezone": "America/New_York",
                "work_schedule": {
                    "work_days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
                    "work_hours": {
                        "start": "09:00",
                        "end": "17:00"
                    }
                },
                "sleep_preferences": {
                    "target_bedtime": "22:30",
                    "target_wake_time": "07:00",
                    "wind_down_duration": 30
                },
                "therapy_preferences": {
                    "preferred_times": ["14:00", "16:00"],
                    "buffer_time": 15,
                    "frequency": "weekly"
                }
            }
        }

# Template Models
class ScheduleTemplateRequest(BaseModel):
    template_name: str = Field(..., min_length=1, max_length=100)
    template_type: TemplateType
    template_data: Dict[str, Any] = Field(..., description="Template structure and rules")
    description: Optional[str] = Field(None, max_length=300)
    
    class Config:
        json_schema_extra = {
            "example": {
                "template_name": "Weekly Wellness Routine",
                "template_type": "weekly",
                "template_data": {
                    "monday": [
                        {"type": "exercise", "time": "07:00", "duration": 30},
                        {"type": "journal", "time": "21:00", "duration": 15}
                    ],
                    "wednesday": [
                        {"type": "therapy", "time": "14:00", "duration": 45}
                    ],
                    "friday": [
                        {"type": "exercise", "time": "18:00", "duration": 45}
                    ]
                },
                "description": "Balanced weekly routine for mental health and fitness"
            }
        }

# Response Models
class ScheduleItem(BaseModel):
    id: str
    type: ScheduleType
    title: str
    description: Optional[str] = None
    start_time: datetime
    duration: int
    frequency: Frequency
    priority: Priority
    is_active: bool
    is_completed: bool
    completion_date: Optional[datetime] = None
    optimization_applied: bool
    created_at: datetime
    updated_at: datetime

class ScheduleCreateResponse(BaseModel):
    success: bool
    created_item: Optional[ScheduleItem] = None
    optimization_result: Optional[Dict[str, Any]] = None
    conflicts: Optional[List[Dict[str, Any]]] = None
    recommendations: Optional[List[str]] = None
    error: Optional[str] = None

class ScheduleItemsResponse(BaseModel):
    success: bool
    schedule_items: List[ScheduleItem]
    summary: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class ScheduleUpdateResponse(BaseModel):
    success: bool
    updated_item: Optional[ScheduleItem] = None
    conflicts_detected: Optional[List[Dict[str, Any]]] = None
    optimization_suggestions: Optional[List[str]] = None
    error: Optional[str] = None

# Optimization Models
class OptimizationResult(BaseModel):
    optimized_schedule: List[Dict[str, Any]]
    optimization_summary: Dict[str, Any]
    conflicts_resolved: int
    efficiency_gain: str
    balance_improvement: str

class ScheduleOptimizationResponse(BaseModel):
    success: bool
    optimization: Optional[OptimizationResult] = None
    conflicts: Optional[List[Dict[str, Any]]] = None
    user_approval_required: Optional[bool] = None
    error: Optional[str] = None

# Analysis Models
class ConflictInfo(BaseModel):
    id: str
    conflict_type: ConflictType
    schedule_item_1: str
    schedule_item_2: str
    severity: str
    resolution_status: ResolutionStatus
    resolution_notes: Optional[str] = None
    detected_at: datetime

class ScheduleAnalysisResponse(BaseModel):
    success: bool
    conflicts: List[ConflictInfo]
    utilization: Optional[float] = None
    balance_score: Optional[float] = None
    patterns: Optional[List[str]] = None
    optimization_opportunities: Optional[List[str]] = None
    error: Optional[str] = None

# Recommendations Models
class ScheduleRecommendation(BaseModel):
    id: str
    recommendation_type: ScheduleType
    title: str
    description: str
    priority: str
    recommendation_data: Dict[str, Any]
    is_applied: bool
    expires_at: Optional[datetime] = None
    created_at: datetime

class ScheduleRecommendationsResponse(BaseModel):
    success: bool
    recommendations: List[ScheduleRecommendation]
    personalization_score: Optional[float] = None
    error: Optional[str] = None

# Templates Response Models
class ScheduleTemplate(BaseModel):
    id: str
    template_name: str
    template_type: TemplateType
    template_data: Dict[str, Any]
    is_active: bool
    usage_count: int
    last_used_at: Optional[datetime] = None
    created_at: datetime

class ScheduleTemplatesResponse(BaseModel):
    success: bool
    templates: List[ScheduleTemplate]
    error: Optional[str] = None

# Analytics Models
class ScheduleAnalytics(BaseModel):
    period: str
    total_scheduled_items: int
    completed_items: int
    completion_rate: float
    therapy_sessions: int
    exercise_sessions: int
    journal_entries: int
    sleep_hours: Optional[float] = None
    schedule_adherence_score: float
    optimization_suggestions: List[str]

class SchedulingAnalyticsResponse(BaseModel):
    success: bool
    analytics: Optional[ScheduleAnalytics] = None
    trends: Optional[Dict[str, Any]] = None
    insights: Optional[List[str]] = None
    error: Optional[str] = None

# User Preferences Response Models
class SchedulingPreferences(BaseModel):
    timezone: str
    work_schedule: Dict[str, Any]
    sleep_preferences: Dict[str, Any]
    notification_preferences: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

class SchedulingPreferencesResponse(BaseModel):
    success: bool
    preferences: Optional[SchedulingPreferences] = None
    error: Optional[str] = None

# Conflicts Response Models
class ScheduleConflictsResponse(BaseModel):
    success: bool
    conflicts: List[ConflictInfo]
    total_conflicts: int
    critical_conflicts: int
    resolution_suggestions: Optional[List[str]] = None
    error: Optional[str] = None

# Validation helpers
@validator('start_time')
def validate_start_time(cls, v):
    if v and v < datetime.now():
        raise ValueError('Start time cannot be in the past')
    return v

@validator('duration')
def validate_duration(cls, v):
    if v is not None and (v < 5 or v > 480):
        raise ValueError('Duration must be between 5 and 480 minutes')
    return v

@validator('effectiveness_rating')
def validate_effectiveness_rating(cls, v):
    if v is not None and (v < 1 or v > 5):
        raise ValueError('Effectiveness rating must be between 1 and 5')
    return v

@validator('title')
def validate_title(cls, v):
    if v and len(v.strip()) < 1:
        raise ValueError('Title cannot be empty')
    return v.strip() if v else v 