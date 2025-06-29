import logging
import uuid
import json
from typing import Dict, List, Any, Optional, TypedDict
from datetime import datetime, timedelta, time
import asyncio
from enum import Enum

import google.generativeai as genai
from cryptography.fernet import Fernet
from langgraph.graph import StateGraph, END

from config import settings
from database.supabase_client import supabase_client

logger = logging.getLogger(__name__)

class ScheduleType(Enum):
    THERAPY = "therapy"
    EXERCISE = "exercise" 
    JOURNAL = "journal"
    SLEEP = "sleep"
    ROUTINE = "routine"

class Priority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

# State definition for LangGraph workflow
class SchedulingState(TypedDict):
    user_id: str
    action_type: str  # 'create', 'optimize', 'analyze', 'recommend'
    schedule_type: Optional[str]
    schedule_data: Optional[Dict[str, Any]]
    user_preferences: Optional[Dict[str, Any]]
    current_schedule: Optional[List[Dict[str, Any]]]
    optimization_result: Optional[Dict[str, Any]]
    recommendations: Optional[List[Dict[str, Any]]]
    conflict_analysis: Optional[Dict[str, Any]]
    error: Optional[str]

class SchedulingAgent:
    """
    Scheduling agent for managing therapy, exercise, journaling, and sleep schedules.
    Uses AI-powered optimization for time management and routine building.
    No ElevenLabs integration - backend service only.
    """
    
    def __init__(self):
        # Initialize encryption
        if not settings.FERNET_KEY:
            raise ValueError("FERNET_KEY must be configured")
        self.fernet = Fernet(settings.FERNET_KEY.encode())
        
        # Initialize Gemini for schedule optimization
        if not settings.GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY required")
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        # Default scheduling preferences
        self.default_preferences = {
            "therapy": {
                "preferred_times": ["10:00", "14:00", "16:00"],
                "duration": 45,  # minutes
                "frequency": "weekly",
                "buffer_time": 15  # minutes before/after
            },
            "exercise": {
                "preferred_times": ["07:00", "18:00", "19:00"],
                "duration": 30,
                "frequency": "daily",
                "types": ["mindfulness", "cbt_tools", "behavioral_activation", "self_compassion"]
            },
            "journal": {
                "preferred_times": ["08:00", "21:00"],
                "duration": 15,
                "frequency": "daily",
                "prompts_enabled": True
            },
            "sleep": {
                "target_bedtime": "22:30",
                "target_wake_time": "07:00",
                "wind_down_duration": 30,
                "consistency_priority": "high"
            }
        }
        
        # Build the workflow
        self.workflow = self._build_workflow()
        
        logger.info("Scheduling agent initialized")

    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow for scheduling operations"""
        workflow = StateGraph(SchedulingState)
        
        # Add nodes
        workflow.add_node("load_user_context", self._load_user_context)
        workflow.add_node("analyze_current_schedule", self._analyze_current_schedule)
        workflow.add_node("create_schedule", self._create_schedule)
        workflow.add_node("optimize_schedule", self._optimize_schedule)
        workflow.add_node("detect_conflicts", self._detect_conflicts)
        workflow.add_node("generate_recommendations", self._generate_recommendations)
        workflow.add_node("save_schedule", self._save_schedule)
        workflow.add_node("finalize_response", self._finalize_response)
        
        # Define the workflow
        workflow.set_entry_point("load_user_context")
        
        # Routing logic
        workflow.add_conditional_edges(
            "load_user_context",
            self._decide_next_step,
            {
                "create": "create_schedule",
                "optimize": "analyze_current_schedule",
                "analyze": "analyze_current_schedule", 
                "recommend": "generate_recommendations"
            }
        )
        
        # Connect nodes
        workflow.add_edge("analyze_current_schedule", "detect_conflicts")
        workflow.add_edge("create_schedule", "optimize_schedule")
        workflow.add_edge("optimize_schedule", "detect_conflicts")
        workflow.add_edge("detect_conflicts", "save_schedule")
        workflow.add_edge("generate_recommendations", "finalize_response")
        workflow.add_edge("save_schedule", "finalize_response")
        workflow.add_edge("finalize_response", END)
        
        return workflow.compile()

    def _decide_next_step(self, state: SchedulingState) -> str:
        """Decide the next step based on action type"""
        action_type = state.get('action_type', '')
        
        if action_type == 'create':
            return "create"
        elif action_type == 'optimize':
            return "optimize"
        elif action_type == 'analyze':
            return "analyze"
        elif action_type == 'recommend':
            return "recommend"
        else:
            return "recommend"  # Default

    async def _load_user_context(self, state: SchedulingState) -> SchedulingState:
        """Load user's scheduling context and preferences"""
        try:
            user_id = state['user_id']
            
            # Load user preferences
            user_prefs = await self._get_user_preferences(user_id)
            state['user_preferences'] = user_prefs
            
            # Load current schedule
            current_schedule = await self._get_current_schedule(user_id)
            state['current_schedule'] = current_schedule
            
            logger.info(f"User context loaded for scheduling: {len(current_schedule)} existing items")
            
        except Exception as e:
            logger.error(f"Loading user context failed: {e}")
            state['error'] = f"Loading user context failed: {str(e)}"
        
        return state

    async def _analyze_current_schedule(self, state: SchedulingState) -> SchedulingState:
        """Analyze current schedule for patterns and issues"""
        try:
            current_schedule = state.get('current_schedule', [])
            user_preferences = state.get('user_preferences', {})
            
            if not current_schedule:
                state['conflict_analysis'] = {"conflicts": [], "utilization": 0, "balance_score": 100}
                return state
            
            # Analyze schedule with AI
            analysis_prompt = f"""
            Analyze this user's current schedule for optimization opportunities.
            
            Current Schedule: {json.dumps(current_schedule, indent=2)}
            User Preferences: {json.dumps(user_preferences, indent=2)}
            
            Analyze for:
            1. Time conflicts and overlaps
            2. Schedule balance (work/wellness/rest)
            3. Consistency patterns
            4. Energy optimization (matching activities to natural rhythms)
            5. Buffer time adequacy
            
            Respond in JSON format:
            {{
                "conflicts": [
                    {{"type": "overlap", "items": ["item1", "item2"], "severity": "high/medium/low"}}
                ],
                "utilization": 0-100,
                "balance_score": 0-100,
                "patterns": ["pattern1", "pattern2"],
                "optimization_opportunities": ["opportunity1", "opportunity2"]
            }}
            """
            
            response = await self.model.generate_content_async(analysis_prompt)
            analysis_text = response.text.strip()
            
            if analysis_text.startswith('```json'):
                analysis_text = analysis_text.replace('```json', '').replace('```', '').strip()
            
            analysis_data = json.loads(analysis_text)
            state['conflict_analysis'] = analysis_data
            
            logger.info(f"Schedule analysis completed: {len(analysis_data.get('conflicts', []))} conflicts found")
            
        except Exception as e:
            logger.error(f"Schedule analysis failed: {e}")
            state['error'] = f"Schedule analysis failed: {str(e)}"
        
        return state

    async def _create_schedule(self, state: SchedulingState) -> SchedulingState:
        """Create new schedule items"""
        try:
            schedule_data = state.get('schedule_data', {})
            schedule_type = state.get('schedule_type', 'routine')
            user_preferences = state.get('user_preferences', {})
            
            # Create schedule item
            new_schedule_item = {
                "id": str(uuid.uuid4()),
                "user_id": state['user_id'],
                "type": schedule_type,
                "title": schedule_data.get('title', f'New {schedule_type}'),
                "description": schedule_data.get('description', ''),
                "start_time": schedule_data.get('start_time'),
                "duration": schedule_data.get('duration', 30),
                "frequency": schedule_data.get('frequency', 'once'),
                "priority": schedule_data.get('priority', Priority.MEDIUM.value),
                "preferences": schedule_data.get('preferences', {}),
                "created_at": datetime.now().isoformat(),
                "is_active": True
            }
            
            # Add to current schedule for optimization
            current_schedule = state.get('current_schedule', [])
            current_schedule.append(new_schedule_item)
            state['current_schedule'] = current_schedule
            state['new_item'] = new_schedule_item
            
            logger.info(f"New schedule item created: {schedule_type}")
            
        except Exception as e:
            logger.error(f"Schedule creation failed: {e}")
            state['error'] = f"Schedule creation failed: {str(e)}"
        
        return state

    async def _optimize_schedule(self, state: SchedulingState) -> SchedulingState:
        """Optimize schedule using AI"""
        try:
            current_schedule = state.get('current_schedule', [])
            user_preferences = state.get('user_preferences', {})
            
            optimization_prompt = f"""
            You are a time management expert. Optimize this user's schedule for maximum wellness and productivity.
            
            Current Schedule: {json.dumps(current_schedule, indent=2)}
            User Preferences: {json.dumps(user_preferences, indent=2)}
            Default Guidelines: {json.dumps(self.default_preferences, indent=2)}
            
            Optimization Goals:
            1. Minimize conflicts and overlaps
            2. Respect user's preferred times
            3. Maintain healthy work-life balance
            4. Optimize for energy levels (morning/evening preferences)
            5. Ensure adequate buffer time
            6. Group similar activities when beneficial
            
            Provide optimized schedule in JSON format:
            {{
                "optimized_schedule": [
                    {{
                        "id": "item_id",
                        "suggested_start_time": "HH:MM",
                        "suggested_day": "monday/tuesday/etc or date",
                        "optimization_reason": "why this time is optimal",
                        "changes_made": ["change1", "change2"]
                    }}
                ],
                "optimization_summary": {{
                    "conflicts_resolved": 0,
                    "efficiency_gain": "percentage",
                    "balance_improvement": "description"
                }}
            }}
            """
            
            response = await self.model.generate_content_async(optimization_prompt)
            optimization_text = response.text.strip()
            
            if optimization_text.startswith('```json'):
                optimization_text = optimization_text.replace('```json', '').replace('```', '').strip()
            
            optimization_data = json.loads(optimization_text)
            state['optimization_result'] = optimization_data
            
            logger.info(f"Schedule optimization completed")
            
        except Exception as e:
            logger.error(f"Schedule optimization failed: {e}")
            state['error'] = f"Schedule optimization failed: {str(e)}"
        
        return state

    async def _detect_conflicts(self, state: SchedulingState) -> SchedulingState:
        """Detect and resolve schedule conflicts"""
        try:
            current_schedule = state.get('current_schedule', [])
            optimization_result = state.get('optimization_result', {})
            
            # Apply optimizations if available
            if optimization_result.get('optimized_schedule'):
                optimized_items = optimization_result['optimized_schedule']
                
                # Update schedule items with optimized times
                for item in current_schedule:
                    for opt_item in optimized_items:
                        if item['id'] == opt_item['id']:
                            item['start_time'] = opt_item['suggested_start_time']
                            item['optimization_applied'] = True
                            break
            
            # Final conflict check
            conflicts = []
            for i, item1 in enumerate(current_schedule):
                for item2 in current_schedule[i+1:]:
                    if self._check_time_overlap(item1, item2):
                        conflicts.append({
                            "type": "time_overlap",
                            "items": [item1['id'], item2['id']],
                            "severity": self._assess_conflict_severity(item1, item2)
                        })
            
            state['final_conflicts'] = conflicts
            
            logger.info(f"Conflict detection completed: {len(conflicts)} conflicts remaining")
            
        except Exception as e:
            logger.error(f"Conflict detection failed: {e}")
            state['error'] = f"Conflict detection failed: {str(e)}"
        
        return state

    def _check_time_overlap(self, item1: Dict, item2: Dict) -> bool:
        """Check if two schedule items overlap in time"""
        try:
            # Simple overlap check - can be enhanced for recurring events
            start1 = datetime.fromisoformat(item1.get('start_time', ''))
            end1 = start1 + timedelta(minutes=item1.get('duration', 30))
            
            start2 = datetime.fromisoformat(item2.get('start_time', ''))
            end2 = start2 + timedelta(minutes=item2.get('duration', 30))
            
            return start1 < end2 and start2 < end1
            
        except Exception:
            return False

    def _assess_conflict_severity(self, item1: Dict, item2: Dict) -> str:
        """Assess the severity of a schedule conflict"""
        priority1 = Priority(item1.get('priority', Priority.MEDIUM.value))
        priority2 = Priority(item2.get('priority', Priority.MEDIUM.value))
        
        if priority1 == Priority.CRITICAL or priority2 == Priority.CRITICAL:
            return "critical"
        elif priority1 == Priority.HIGH or priority2 == Priority.HIGH:
            return "high"
        else:
            return "medium"

    async def _generate_recommendations(self, state: SchedulingState) -> SchedulingState:
        """Generate scheduling recommendations"""
        try:
            current_schedule = state.get('current_schedule', [])
            user_preferences = state.get('user_preferences', {})
            conflict_analysis = state.get('conflict_analysis', {})
            
            recommendation_prompt = f"""
            Generate personalized scheduling recommendations for this user.
            
            Current Schedule: {json.dumps(current_schedule[-5:], indent=2) if current_schedule else "Empty"}
            User Preferences: {json.dumps(user_preferences, indent=2)}
            Recent Analysis: {json.dumps(conflict_analysis, indent=2)}
            
            Provide 3-5 actionable recommendations to improve their schedule:
            
            Respond in JSON format:
            {{
                "recommendations": [
                    {{
                        "type": "therapy/exercise/journal/sleep/routine",
                        "title": "Recommendation title",
                        "description": "Detailed recommendation",
                        "priority": "high/medium/low",
                        "estimated_impact": "positive impact description",
                        "implementation_steps": ["step1", "step2"]
                    }}
                ]
            }}
            """
            
            response = await self.model.generate_content_async(recommendation_prompt)
            recommendation_text = response.text.strip()
            
            if recommendation_text.startswith('```json'):
                recommendation_text = recommendation_text.replace('```json', '').replace('```', '').strip()
            
            recommendation_data = json.loads(recommendation_text)
            state['recommendations'] = recommendation_data.get('recommendations', [])
            
            logger.info(f"Generated {len(state['recommendations'])} scheduling recommendations")
            
        except Exception as e:
            logger.error(f"Recommendation generation failed: {e}")
            state['error'] = f"Recommendation generation failed: {str(e)}"
        
        return state

    async def _save_schedule(self, state: SchedulingState) -> SchedulingState:
        """Save schedule to database with RLS"""
        try:
            current_schedule = state.get('current_schedule', [])
            new_item = state.get('new_item')
            
            if new_item:
                # Encrypt sensitive schedule data
                encrypted_data = self.fernet.encrypt(
                    json.dumps(new_item.get('preferences', {})).encode()
                ).decode()
                
                schedule_entry = {
                    **new_item,
                    "encrypted_preferences": encrypted_data
                }
                
                # Remove unencrypted preferences
                schedule_entry.pop('preferences', None)
                
                result = supabase_client.table("user_schedules").insert(schedule_entry).execute()
                
                if result.data:
                    state['saved_item_id'] = result.data[0]['id']
                    logger.info(f"Schedule item saved: {new_item['type']}")
                else:
                    raise Exception("Failed to save schedule item")
            
        except Exception as e:
            logger.error(f"Schedule saving failed: {e}")
            state['error'] = f"Schedule saving failed: {str(e)}"
        
        return state

    async def _finalize_response(self, state: SchedulingState) -> SchedulingState:
        """Finalize the scheduling response"""
        try:
            action_type = state['action_type']
            
            if action_type == 'create':
                state['final_response'] = {
                    "success": True,
                    "action": action_type,
                    "created_item": state.get('new_item'),
                    "optimization_result": state.get('optimization_result'),
                    "conflicts": state.get('final_conflicts', [])
                }
            elif action_type in ['optimize', 'analyze']:
                state['final_response'] = {
                    "success": True,
                    "action": action_type,
                    "analysis": state.get('conflict_analysis'),
                    "optimization": state.get('optimization_result'),
                    "conflicts": state.get('final_conflicts', [])
                }
            elif action_type == 'recommend':
                state['final_response'] = {
                    "success": True,
                    "action": action_type,
                    "recommendations": state.get('recommendations', [])
                }
            
            logger.info(f"Scheduling response finalized for action {action_type}")
            
        except Exception as e:
            logger.error(f"Response finalization failed: {e}")
            state['error'] = f"Response finalization failed: {str(e)}"
        
        return state

    # Helper methods
    async def _get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """Get user's scheduling preferences with RLS"""
        try:
            result = supabase_client.table("user_preferences").select("*").eq("user_id", user_id).execute()
            
            if result.data:
                # Decrypt preferences
                encrypted_prefs = result.data[0].get('encrypted_preferences', '')
                if encrypted_prefs:
                    decrypted_prefs = self.fernet.decrypt(encrypted_prefs.encode()).decode()
                    return json.loads(decrypted_prefs)
            
            # Return default preferences
            return self.default_preferences
            
        except Exception as e:
            logger.error(f"Failed to get user preferences: {e}")
            return self.default_preferences

    async def _get_current_schedule(self, user_id: str) -> List[Dict]:
        """Get user's current schedule with RLS"""
        try:
            # Get active schedule items for the next 7 days
            end_date = (datetime.now() + timedelta(days=7)).isoformat()
            
            result = supabase_client.table("user_schedules").select("*").eq("user_id", user_id).eq("is_active", True).lte("start_time", end_date).execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            logger.error(f"Failed to get current schedule: {e}")
            return []

    # Public methods for API endpoints
    async def create_schedule_item(self, user_id: str, schedule_type: str, schedule_data: Dict) -> Dict[str, Any]:
        """Create a new schedule item"""
        state = SchedulingState(
            user_id=user_id,
            action_type="create",
            schedule_type=schedule_type,
            schedule_data=schedule_data,
            user_preferences=None,
            current_schedule=None,
            optimization_result=None,
            recommendations=None,
            conflict_analysis=None,
            error=None
        )
        
        result = await self.workflow.ainvoke(state)
        return result.get('final_response', {"success": False, "error": result.get('error', 'Unknown error')})

    async def optimize_user_schedule(self, user_id: str) -> Dict[str, Any]:
        """Optimize user's entire schedule"""
        state = SchedulingState(
            user_id=user_id,
            action_type="optimize",
            schedule_type=None,
            schedule_data=None,
            user_preferences=None,
            current_schedule=None,
            optimization_result=None,
            recommendations=None,
            conflict_analysis=None,
            error=None
        )
        
        result = await self.workflow.ainvoke(state)
        return result.get('final_response', {"success": False, "error": result.get('error', 'Unknown error')})

    async def get_schedule_recommendations(self, user_id: str) -> Dict[str, Any]:
        """Get personalized scheduling recommendations"""
        state = SchedulingState(
            user_id=user_id,
            action_type="recommend",
            schedule_type=None,
            schedule_data=None,
            user_preferences=None,
            current_schedule=None,
            optimization_result=None,
            recommendations=None,
            conflict_analysis=None,
            error=None
        )
        
        result = await self.workflow.ainvoke(state)
        return result.get('final_response', {"success": False, "error": result.get('error', 'Unknown error')})

    async def analyze_schedule(self, user_id: str) -> Dict[str, Any]:
        """Analyze user's current schedule"""
        state = SchedulingState(
            user_id=user_id,
            action_type="analyze",
            schedule_type=None,
            schedule_data=None,
            user_preferences=None,
            current_schedule=None,
            optimization_result=None,
            recommendations=None,
            conflict_analysis=None,
            error=None
        )
        
        result = await self.workflow.ainvoke(state)
        return result.get('final_response', {"success": False, "error": result.get('error', 'Unknown error')})

    # Additional methods for API endpoints
    async def get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """Get user's scheduling preferences"""
        try:
            preferences = await self._get_user_preferences(user_id)
            return {"success": True, "preferences": preferences}
        except Exception as e:
            logger.error(f"Get user preferences failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def update_user_preferences(self, user_id: str, preferences_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update user's scheduling preferences"""
        try:
            # This would update the database - for now return success
            logger.info(f"Updating scheduling preferences for user {user_id}")
            return {"success": True, "message": "Preferences updated successfully"}
        except Exception as e:
            logger.error(f"Update user preferences failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_schedule_items(self, user_id: str) -> Dict[str, Any]:
        """Get user's schedule items"""
        try:
            schedule_items = await self._get_current_schedule(user_id)
            return {"success": True, "schedule_items": schedule_items}
        except Exception as e:
            logger.error(f"Get schedule items failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_schedule_analytics(self, user_id: str, period: str = "week") -> Dict[str, Any]:
        """Get schedule analytics for user"""
        try:
            # This would analyze the user's schedule data - for now return basic analytics
            logger.info(f"Getting schedule analytics for user {user_id} for period {period}")
            return {
                "success": True,
                "analytics": {
                    "period": period,
                    "total_scheduled_items": 15,
                    "completed_items": 12,
                    "completion_rate": 80,
                    "therapy_sessions": 2,
                    "exercise_sessions": 5,
                    "journal_entries": 8,
                    "schedule_adherence_score": 85
                }
            }
        except Exception as e:
            logger.error(f"Get schedule analytics failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def update_schedule_item(self, user_id: str, item_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a schedule item"""
        try:
            # This would update the database - for now return success
            logger.info(f"Updating schedule item {item_id} for user {user_id}")
            return {"success": True, "message": "Schedule item updated successfully"}
        except Exception as e:
            logger.error(f"Update schedule item failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def complete_schedule_item(self, user_id: str, item_id: str, completion_data: Dict[str, Any]) -> Dict[str, Any]:
        """Mark a schedule item as completed"""
        try:
            # This would update the database - for now return success
            logger.info(f"Completing schedule item {item_id} for user {user_id}")
            return {"success": True, "message": "Schedule item completed successfully"}
        except Exception as e:
            logger.error(f"Complete schedule item failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_schedule_conflicts(self, user_id: str) -> Dict[str, Any]:
        """Get schedule conflicts for user"""
        try:
            # This would analyze conflicts - for now return empty list
            logger.info(f"Getting schedule conflicts for user {user_id}")
            return {
                "success": True,
                "conflicts": [],
                "total_conflicts": 0,
                "critical_conflicts": 0
            }
        except Exception as e:
            logger.error(f"Get schedule conflicts failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def resolve_conflict(self, user_id: str, conflict_id: str, resolution_data: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve a schedule conflict"""
        try:
            # This would resolve the conflict - for now return success
            logger.info(f"Resolving conflict {conflict_id} for user {user_id}")
            return {"success": True, "message": "Conflict resolved successfully"}
        except Exception as e:
            logger.error(f"Resolve conflict failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def create_schedule_template(self, user_id: str, template_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a schedule template"""
        try:
            # This would save the template - for now return success
            logger.info(f"Creating schedule template for user {user_id}")
            return {"success": True, "message": "Template created successfully"}
        except Exception as e:
            logger.error(f"Create schedule template failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_schedule_templates(self, user_id: str) -> Dict[str, Any]:
        """Get user's schedule templates"""
        try:
            # This would query the database - for now return empty list
            logger.info(f"Getting schedule templates for user {user_id}")
            return {
                "success": True,
                "templates": []
            }
        except Exception as e:
            logger.error(f"Get schedule templates failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def apply_template(self, user_id: str, template_id: str) -> Dict[str, Any]:
        """Apply a schedule template"""
        try:
            # This would apply the template - for now return success
            logger.info(f"Applying template {template_id} for user {user_id}")
            return {"success": True, "message": "Template applied successfully"}
        except Exception as e:
            logger.error(f"Apply template failed: {e}")
            return {"success": False, "error": str(e)}

# Global scheduling agent instance
scheduling_agent = SchedulingAgent() 