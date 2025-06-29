from pydantic import BaseModel, Field, validator
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, date
from enum import Enum

class MealType(str, Enum):
    BREAKFAST = "breakfast"
    LUNCH = "lunch"
    DINNER = "dinner"
    SNACK = "snack"

class ActivityLevel(str, Enum):
    SEDENTARY = "sedentary"
    LIGHTLY_ACTIVE = "lightly_active"
    MODERATELY_ACTIVE = "moderately_active"
    VERY_ACTIVE = "very_active"
    EXTREMELY_ACTIVE = "extremely_active"

class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    PREFER_NOT_TO_SAY = "prefer_not_to_say"

# Food Logging Models
class FoodItem(BaseModel):
    name: str = Field(..., description="Name of the food item")
    category: Optional[str] = Field(None, description="Food category")
    estimated_portion: str = Field(..., description="Estimated portion size")
    preparation_method: Optional[str] = Field(None, description="Cooking/preparation method")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="AI confidence in identification")

class FoodLogRequest(BaseModel):
    meal_type: MealType
    foods_identified: List[FoodItem]
    meal_description: Optional[str] = Field(None, description="Additional meal description")
    
    class Config:
        json_schema_extra = {
            "example": {
                "meal_type": "lunch",
                "foods_identified": [
                    {
                        "name": "grilled chicken breast",
                        "category": "protein",
                        "estimated_portion": "4 oz",
                        "preparation_method": "grilled",
                        "confidence": 0.95
                    },
                    {
                        "name": "brown rice",
                        "category": "grain",
                        "estimated_portion": "1/2 cup",
                        "preparation_method": "steamed",
                        "confidence": 0.90
                    }
                ],
                "meal_description": "Healthy lunch with lean protein and whole grains"
            }
        }

# Nutrition Profile Models
class NutritionProfileUpdate(BaseModel):
    daily_calorie_goal: Optional[int] = Field(None, ge=800, le=5000)
    dietary_restrictions: Optional[List[str]] = Field(None, description="List of dietary restrictions")
    food_preferences: Optional[List[str]] = Field(None, description="List of food preferences")
    goals: Optional[List[str]] = Field(None, description="Nutrition goals")
    height_cm: Optional[int] = Field(None, ge=100, le=250)
    weight_kg: Optional[float] = Field(None, ge=30.0, le=300.0)
    age: Optional[int] = Field(None, ge=13, le=120)
    gender: Optional[Gender] = None
    activity_level: Optional[ActivityLevel] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "daily_calorie_goal": 2200,
                "dietary_restrictions": ["vegetarian", "gluten-free"],
                "food_preferences": ["mediterranean", "high-protein"],
                "goals": ["weight_loss", "muscle_gain"],
                "height_cm": 170,
                "weight_kg": 70.5,
                "age": 28,
                "gender": "female",
                "activity_level": "moderately_active"
            }
        }

# Consultation Models
class ConsultationRequest(BaseModel):
    query: str = Field(..., min_length=10, max_length=1000, description="Nutrition question or concern")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context for the consultation")
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "I'm trying to lose weight but I'm always hungry after workouts. What should I eat post-workout?",
                "context": {
                    "workout_type": "strength training",
                    "workout_duration": 60,
                    "current_goal": "weight_loss"
                }
            }
        }

# Meal Plan Models
class MealPlanRequest(BaseModel):
    preferences: Optional[Dict[str, Any]] = Field(None, description="Specific preferences for this meal plan")
    exclude_ingredients: Optional[List[str]] = Field(None, description="Ingredients to exclude")
    focus_areas: Optional[List[str]] = Field(None, description="Areas to focus on (e.g., high-protein, low-carb)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "preferences": {
                    "cuisine_types": ["mediterranean", "asian"],
                    "prep_time_max": 30,
                    "budget_friendly": True
                },
                "exclude_ingredients": ["shellfish", "nuts"],
                "focus_areas": ["high-protein", "anti-inflammatory"]
            }
        }

# Response Models
class NutrientInfo(BaseModel):
    amount: float
    unit: str
    percent_dv: Optional[float] = Field(None, description="Percentage of daily value")

class NutritionAnalysis(BaseModel):
    calories: NutrientInfo
    protein: NutrientInfo
    carbs: NutrientInfo
    fat: NutrientInfo
    fiber: Optional[NutrientInfo] = None
    sodium: Optional[NutrientInfo] = None
    sugar: Optional[NutrientInfo] = None

class FoodAnalysisResponse(BaseModel):
    success: bool
    food_entry_id: Optional[str] = None
    nutrition_analysis: Optional[NutritionAnalysis] = None
    calorie_tracking: Optional[Dict[str, Any]] = None
    recommendations: Optional[List[str]] = None
    error: Optional[str] = None

class MealPlanResponse(BaseModel):
    success: bool
    meal_plan: Optional[Dict[str, Any]] = None
    shopping_list: Optional[Dict[str, List[str]]] = None
    prep_instructions: Optional[List[str]] = None
    nutrition_summary: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class ConsultationResponse(BaseModel):
    success: bool
    consultation_response: Optional[str] = None
    related_topics: Optional[List[str]] = None
    follow_up_questions: Optional[List[str]] = None
    error: Optional[str] = None

class CalorieTrackingResponse(BaseModel):
    success: bool
    daily_goal: Optional[int] = None
    consumed_calories: Optional[float] = None
    remaining_calories: Optional[float] = None
    progress_percent: Optional[float] = None
    macros: Optional[Dict[str, Any]] = None
    meals_logged: Optional[int] = None
    status: Optional[str] = None
    error: Optional[str] = None

# Analytics Models
class NutritionAnalyticsRequest(BaseModel):
    period: str = Field("week", pattern="^(week|month|year)$")
    include_trends: bool = Field(True, description="Include trend analysis")
    include_recommendations: bool = Field(True, description="Include improvement recommendations")

class NutritionAnalyticsResponse(BaseModel):
    success: bool
    period: str
    analytics: Optional[Dict[str, Any]] = None
    trends: Optional[Dict[str, Any]] = None
    recommendations: Optional[List[str]] = None
    error: Optional[str] = None

# Food Log History Models
class FoodLogSummary(BaseModel):
    id: str
    meal_type: MealType
    total_calories: float
    logged_at: datetime
    foods_count: int
    has_image: bool

class FoodLogHistoryResponse(BaseModel):
    success: bool
    food_logs: List[FoodLogSummary]
    summary: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

# Meal Plan History Models
class MealPlanSummary(BaseModel):
    id: str
    week_start_date: date
    average_daily_calories: float
    is_active: bool
    created_at: datetime

class MealPlanHistoryResponse(BaseModel):
    success: bool
    meal_plans: List[MealPlanSummary]
    error: Optional[str] = None

# Consultation History Models
class ConsultationSummary(BaseModel):
    id: str
    query: str
    consultation_type: str
    tags: List[str]
    created_at: datetime

class ConsultationHistoryResponse(BaseModel):
    success: bool
    consultations: List[ConsultationSummary]
    error: Optional[str] = None

# User Profile Models
class NutritionProfile(BaseModel):
    daily_calorie_goal: int
    dietary_restrictions: List[str]
    food_preferences: List[str]
    goals: List[str]
    height_cm: Optional[int] = None
    weight_kg: Optional[float] = None
    age: Optional[int] = None
    gender: Optional[Gender] = None
    activity_level: ActivityLevel
    created_at: datetime
    updated_at: datetime

class NutritionProfileResponse(BaseModel):
    success: bool
    profile: Optional[NutritionProfile] = None
    error: Optional[str] = None

# Validation helpers
@validator('daily_calorie_goal')
def validate_calorie_goal(cls, v):
    if v is not None and (v < 800 or v > 5000):
        raise ValueError('Daily calorie goal must be between 800 and 5000')
    return v

@validator('weight_kg')
def validate_weight(cls, v):
    if v is not None and (v < 30.0 or v > 300.0):
        raise ValueError('Weight must be between 30.0 and 300.0 kg')
    return v

@validator('height_cm')
def validate_height(cls, v):
    if v is not None and (v < 100 or v > 250):
        raise ValueError('Height must be between 100 and 250 cm')
    return v 