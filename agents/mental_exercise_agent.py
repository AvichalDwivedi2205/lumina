import logging
import uuid
import json
import asyncio
from typing import Dict, List, Any, Optional, TypedDict
from datetime import datetime
import httpx

import google.generativeai as genai
from cryptography.fernet import Fernet
from langgraph.graph import StateGraph, END

from config import settings
from database.supabase_client import supabase_client

logger = logging.getLogger(__name__)

# State definition for LangGraph mental exercise workflow
class ExerciseState(TypedDict):
    user_id: str
    exercise_id: Optional[str]
    exercise_type: str  # "mindfulness", "cbt_tools", "behavioral_activation", "self_compassion"
    session_context: Optional[Dict[str, Any]]
    mood_before: Optional[int]
    mood_after: Optional[int]
    exercise_notes: Optional[str]
    completion_status: str  # "started", "completed", "interrupted"
    duration_minutes: Optional[int]
    personalization_data: Optional[Dict[str, Any]]
    error: Optional[str]

class MentalExerciseAgent:
    """
    Mental Exercise agent using LangGraph orchestration for managing 4 types of therapeutic exercises:
    1. Mindfulness (MBSR/MBCT)
    2. CBT Tools (Cognitive restructuring)
    3. Behavioral Activation (Activity planning)
    4. Self-Compassion (DBT/ACT blend)
    """
    
    def __init__(self):
        # Initialize encryption
        if not settings.FERNET_KEY:
            raise ValueError("FERNET_KEY must be configured")
        self.fernet = Fernet(settings.FERNET_KEY.encode())
        
        # Initialize Gemini for personalization
        if not settings.GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY required")
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        # HTTP client for API calls
        self.http_client = httpx.AsyncClient(timeout=30.0)
        
        # Exercise configurations
        self.exercise_configs = {
            "mindfulness": {
                "name": "Mindfulness Practice",
                "duration": settings.EXERCISE_SESSION_DURATION,
                "description": "Guided meditation and present-moment awareness exercises",
                "agent_id": settings.ELEVENLABS_MINDFULNESS_AGENT_ID,
                "techniques": [
                    "Breath awareness meditation",
                    "Body scan practice", 
                    "Loving-kindness meditation",
                    "Mindful observation",
                    "Present moment anchoring"
                ],
                "benefits": ["Reduces anxiety", "Improves focus", "Enhances emotional regulation"]
            },
            "cbt_tools": {
                "name": "CBT Tools",
                "duration": settings.EXERCISE_SESSION_DURATION,
                "description": "Cognitive restructuring and thought challenging exercises",
                "agent_id": settings.ELEVENLABS_CBT_AGENT_ID,
                "techniques": [
                    "Thought record completion",
                    "ABC model practice",
                    "Cognitive distortion identification",
                    "Evidence examination",
                    "Balanced thinking development"
                ],
                "benefits": ["Challenges negative thoughts", "Improves mood", "Increases self-awareness"]
            },
            "behavioral_activation": {
                "name": "Behavioral Activation",
                "duration": settings.EXERCISE_SESSION_DURATION,
                "description": "Activity planning and mood enhancement exercises",
                "agent_id": settings.ELEVENLABS_BEHAVIORAL_AGENT_ID,
                "techniques": [
                    "Activity scheduling",
                    "Pleasure and mastery rating",
                    "Behavioral experiments",
                    "Goal setting and planning",
                    "Energy and mood tracking"
                ],
                "benefits": ["Increases motivation", "Improves mood", "Builds confidence"]
            },
            "self_compassion": {
                "name": "Self-Compassion Practice",
                "duration": settings.EXERCISE_SESSION_DURATION,
                "description": "Self-kindness and emotion regulation practices",
                "agent_id": settings.ELEVENLABS_COMPASSION_AGENT_ID,
                "techniques": [
                    "Self-compassion break",
                    "Loving-kindness for self",
                    "Inner critic transformation",
                    "RAIN technique practice",
                    "Self-forgiveness exercises"
                ],
                "benefits": ["Reduces self-criticism", "Improves emotional resilience", "Enhances self-acceptance"]
            }
        }
        
        # Build the workflow
        self.workflow = self._build_workflow()
        
        logger.info("Mental Exercise agent initialized with LangGraph orchestration")
    
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow for mental exercise management"""
        workflow = StateGraph(ExerciseState)
        
        # Add nodes
        workflow.add_node("prepare_exercise", self._prepare_exercise)
        workflow.add_node("load_user_context", self._load_user_context)
        workflow.add_node("personalize_exercise", self._personalize_exercise)
        workflow.add_node("initiate_exercise", self._initiate_exercise)
        workflow.add_node("monitor_progress", self._monitor_progress)
        workflow.add_node("complete_exercise", self._complete_exercise)
        workflow.add_node("analyze_effectiveness", self._analyze_effectiveness)
        workflow.add_node("store_exercise_data", self._store_exercise_data)
        
        # Define the flow
        workflow.set_entry_point("prepare_exercise")
        workflow.add_edge("prepare_exercise", "load_user_context")
        workflow.add_edge("load_user_context", "personalize_exercise")
        workflow.add_edge("personalize_exercise", "initiate_exercise")
        workflow.add_edge("initiate_exercise", "monitor_progress")
        workflow.add_edge("monitor_progress", "complete_exercise")
        workflow.add_edge("complete_exercise", "analyze_effectiveness")
        workflow.add_edge("analyze_effectiveness", "store_exercise_data")
        workflow.add_edge("store_exercise_data", END)
        
        return workflow.compile()
    
    async def _prepare_exercise(self, state: ExerciseState) -> ExerciseState:
        """Prepare exercise session with validation"""
        try:
            # Generate exercise ID
            state['exercise_id'] = str(uuid.uuid4())
            
            # Validate exercise type
            if state['exercise_type'] not in self.exercise_configs:
                raise ValueError(f"Invalid exercise type: {state['exercise_type']}")
            
            # Set initial status
            state['completion_status'] = 'started'
            state['duration_minutes'] = self.exercise_configs[state['exercise_type']]['duration'] // 60
            
            logger.info(f"Exercise prepared: {state['exercise_id']} ({state['exercise_type']}) for user {state['user_id']}")
            
        except Exception as e:
            logger.error(f"Exercise preparation failed: {e}")
            state['error'] = f"Exercise preparation failed: {str(e)}"
        
        return state
    
    async def _load_user_context(self, state: ExerciseState) -> ExerciseState:
        """Load user's exercise history and preferences"""
        try:
            # Query previous exercises for context
            response = supabase_client.table("mental_exercises") \
                .select("*") \
                .eq("user_id", state['user_id']) \
                .eq("exercise_type", state['exercise_type']) \
                .order("created_at", desc=True) \
                .limit(5) \
                .execute()
            
            previous_exercises = response.data if response.data else []
            
            # Query therapy sessions for additional context
            therapy_response = supabase_client.table("therapy_sessions") \
                .select("exercises_recommended") \
                .eq("user_id", state['user_id']) \
                .order("created_at", desc=True) \
                .limit(3) \
                .execute()
            
            therapy_sessions = therapy_response.data if therapy_response.data else []
            
            # Build session context
            session_context = {
                "previous_exercise_count": len(previous_exercises),
                "average_mood_improvement": 0,
                "preferred_techniques": [],
                "completion_rate": 0,
                "recent_therapy_recommendations": []
            }
            
            if previous_exercises:
                # Calculate average mood improvement
                mood_improvements = []
                completed_exercises = 0
                
                for exercise in previous_exercises:
                    if exercise.get('completion_status') == 'completed':
                        completed_exercises += 1
                        if exercise.get('mood_before') and exercise.get('mood_after'):
                            improvement = exercise['mood_after'] - exercise['mood_before']
                            mood_improvements.append(improvement)
                
                if mood_improvements:
                    session_context['average_mood_improvement'] = sum(mood_improvements) / len(mood_improvements)
                
                session_context['completion_rate'] = completed_exercises / len(previous_exercises) if previous_exercises else 0
            
            # Extract therapy recommendations
            for session in therapy_sessions:
                if session.get('exercises_recommended'):
                    try:
                        recommendations = json.loads(session['exercises_recommended'])
                        for rec in recommendations:
                            if rec.get('exercise_type') == state['exercise_type']:
                                session_context['recent_therapy_recommendations'].append(rec.get('rationale', ''))
                    except json.JSONDecodeError:
                        continue
            
            state['session_context'] = session_context
            logger.info(f"User context loaded for exercise {state['exercise_id']}")
            
        except Exception as e:
            logger.error(f"Loading user context failed: {e}")
            state['session_context'] = {"previous_exercise_count": 0}
            
        return state
    
    async def _personalize_exercise(self, state: ExerciseState) -> ExerciseState:
        """Personalize exercise based on user context and preferences"""
        try:
            exercise_config = self.exercise_configs[state['exercise_type']]
            session_context = state.get('session_context', {})
            
            # Use LLM to personalize the exercise
            personalization_prompt = f"""
            Personalize this {exercise_config['name']} exercise for a user based on their context.
            
            Exercise Type: {state['exercise_type']}
            Available Techniques: {exercise_config['techniques']}
            User Context:
            - Previous exercises completed: {session_context.get('previous_exercise_count', 0)}
            - Average mood improvement: {session_context.get('average_mood_improvement', 0)}
            - Completion rate: {session_context.get('completion_rate', 0)}
            - Therapy recommendations: {session_context.get('recent_therapy_recommendations', [])}
            
            Provide personalization in JSON format:
            {{
                "recommended_technique": "specific technique from the list",
                "personalization_notes": "why this technique is recommended for this user",
                "difficulty_level": "beginner/intermediate/advanced",
                "focus_areas": ["area1", "area2"],
                "motivational_message": "encouraging message for the user"
            }}
            """
            
            response = await self.model.generate_content_async(personalization_prompt)
            personalization_text = response.text.strip()
            
            if personalization_text.startswith('```json'):
                personalization_text = personalization_text.replace('```json', '').replace('```', '').strip()
            
            personalization_data = json.loads(personalization_text)
            state['personalization_data'] = personalization_data
            
            logger.info(f"Exercise personalized for {state['exercise_id']}")
            
        except Exception as e:
            logger.error(f"Exercise personalization failed: {e}")
            # Fallback to default configuration
            state['personalization_data'] = {
                "recommended_technique": self.exercise_configs[state['exercise_type']]['techniques'][0],
                "difficulty_level": "beginner",
                "focus_areas": ["general wellness"],
                "motivational_message": "Take this time for yourself and your well-being."
            }
            
        return state
    
    async def _initiate_exercise(self, state: ExerciseState) -> ExerciseState:
        """Initiate exercise with ElevenLabs agent"""
        try:
            exercise_config = self.exercise_configs[state['exercise_type']]
            agent_id = exercise_config['agent_id']
            
            if not agent_id:
                raise ValueError(f"No agent ID configured for {state['exercise_type']} exercise")
            
            # Prepare exercise context for ElevenLabs agent
            exercise_context = self._prepare_exercise_context(state)
            
            # Store agent configuration for webhook processing
            state['agent_config'] = {
                'agent_id': agent_id,
                'exercise_context': exercise_context,
                'session_duration': exercise_config['duration'],
                'personalization': state.get('personalization_data', {})
            }
            
            logger.info(f"Exercise initiated with agent {agent_id}")
            
        except Exception as e:
            logger.error(f"Exercise initiation failed: {e}")
            state['error'] = f"Exercise initiation failed: {str(e)}"
        
        return state
    
    def _prepare_exercise_context(self, state: ExerciseState) -> str:
        """Prepare context string for exercise agent"""
        exercise_config = self.exercise_configs[state['exercise_type']]
        personalization = state.get('personalization_data', {})
        session_context = state.get('session_context', {})
        
        context_parts = [
            f"This is a {exercise_config['name']} session.",
            f"Recommended technique: {personalization.get('recommended_technique', 'general practice')}",
            f"Difficulty level: {personalization.get('difficulty_level', 'beginner')}",
        ]
        
        if session_context.get('previous_exercise_count', 0) > 0:
            context_parts.append(f"User has completed {session_context['previous_exercise_count']} previous {state['exercise_type']} exercises.")
        
        if personalization.get('focus_areas'):
            context_parts.append(f"Focus on: {', '.join(personalization['focus_areas'])}")
        
        if personalization.get('motivational_message'):
            context_parts.append(f"Motivational note: {personalization['motivational_message']}")
        
        return " ".join(context_parts)
    
    async def _monitor_progress(self, state: ExerciseState) -> ExerciseState:
        """Monitor exercise progress (placeholder for real-time monitoring)"""
        try:
            # In real implementation, this would monitor the ElevenLabs conversation
            # For now, we'll simulate progress monitoring
            state['progress_monitored'] = True
            logger.info(f"Progress monitoring active for exercise {state['exercise_id']}")
            
        except Exception as e:
            logger.error(f"Progress monitoring failed: {e}")
            state['error'] = f"Progress monitoring failed: {str(e)}"
        
        return state
    
    async def _complete_exercise(self, state: ExerciseState) -> ExerciseState:
        """Handle exercise completion"""
        try:
            # This will be called when exercise completes
            state['completion_status'] = 'completed'
            
            # Record completion time
            state['completed_at'] = datetime.now().isoformat()
            
            logger.info(f"Exercise {state['exercise_id']} completed")
            
        except Exception as e:
            logger.error(f"Exercise completion processing failed: {e}")
            state['error'] = f"Exercise completion failed: {str(e)}"
        
        return state
    
    async def _analyze_effectiveness(self, state: ExerciseState) -> ExerciseState:
        """Analyze exercise effectiveness and generate insights"""
        try:
            if state.get('mood_before') and state.get('mood_after'):
                mood_improvement = state['mood_after'] - state['mood_before']
                
                # Generate effectiveness analysis
                analysis_prompt = f"""
                Analyze the effectiveness of this mental health exercise session.
                
                Exercise Type: {state['exercise_type']}
                Mood Before: {state['mood_before']}/10
                Mood After: {state['mood_after']}/10
                Mood Change: {mood_improvement}
                Completion Status: {state['completion_status']}
                Duration: {state.get('duration_minutes', 10)} minutes
                
                Provide analysis in JSON format:
                {{
                    "effectiveness_score": 1-10,
                    "mood_improvement_assessment": "description of mood change",
                    "technique_effectiveness": "how well the technique worked",
                    "recommendations": ["recommendation1", "recommendation2"],
                    "next_session_suggestions": "suggestions for next exercise session"
                }}
                """
                
                response = await self.model.generate_content_async(analysis_prompt)
                analysis_text = response.text.strip()
                
                if analysis_text.startswith('```json'):
                    analysis_text = analysis_text.replace('```json', '').replace('```', '').strip()
                
                analysis_data = json.loads(analysis_text)
                state['effectiveness_analysis'] = analysis_data
                
            logger.info(f"Effectiveness analysis completed for {state['exercise_id']}")
            
        except Exception as e:
            logger.error(f"Effectiveness analysis failed: {e}")
            state['effectiveness_analysis'] = {
                "effectiveness_score": 5,
                "mood_improvement_assessment": "Exercise completed successfully"
            }
            
        return state
    
    async def _store_exercise_data(self, state: ExerciseState) -> ExerciseState:
        """Store exercise data in database"""
        try:
            # Prepare exercise data for storage
            exercise_data = {
                "exercise_id": state['exercise_id'],
                "exercise_type": state['exercise_type'],
                "personalization_data": state.get('personalization_data', {}),
                "effectiveness_analysis": state.get('effectiveness_analysis', {}),
                "session_context": state.get('session_context', {})
            }
            
            # Encrypt sensitive data
            encrypted_notes = self.fernet.encrypt(
                json.dumps(exercise_data).encode()
            ).decode()
            
            # Store in database
            insert_data = {
                "id": state['exercise_id'],
                "user_id": state['user_id'],
                "exercise_type": state['exercise_type'],
                "session_date": datetime.now().isoformat(),
                "duration_minutes": state.get('duration_minutes', 10),
                "completion_status": state['completion_status'],
                "mood_before": state.get('mood_before'),
                "mood_after": state.get('mood_after'),
                "notes": encrypted_notes,
                "created_at": datetime.now().isoformat()
            }
            
            response = supabase_client.table("mental_exercises").insert(insert_data).execute()
            
            if response.data:
                logger.info(f"Exercise data stored for {state['exercise_id']}")
            else:
                logger.error(f"Failed to store exercise data: {response}")
                
        except Exception as e:
            logger.error(f"Exercise data storage failed: {e}")
            state['error'] = f"Exercise storage failed: {str(e)}"
        
        return state
    
    async def start_exercise(self, user_id: str, exercise_type: str, mood_before: Optional[int] = None) -> Dict[str, Any]:
        """Start a new mental exercise session"""
        try:
            initial_state = ExerciseState(
                user_id=user_id,
                exercise_type=exercise_type,
                mood_before=mood_before,
                exercise_id=None,
                session_context=None,
                mood_after=None,
                exercise_notes=None,
                completion_status='started',
                duration_minutes=None,
                personalization_data=None,
                error=None
            )
            
            # Run the workflow
            final_state = await self.workflow.ainvoke(initial_state)
            
            if final_state.get('error'):
                return {
                    "success": False,
                    "error": final_state['error']
                }
            
            return {
                "success": True,
                "exercise_id": final_state['exercise_id'],
                "agent_config": final_state.get('agent_config'),
                "personalization": final_state.get('personalization_data'),
                "exercise_info": self.exercise_configs[exercise_type]
            }
            
        except Exception as e:
            logger.error(f"Exercise start failed: {e}")
            return {
                "success": False,
                "error": f"Failed to start exercise: {str(e)}"
            }
    
    async def complete_exercise(self, exercise_id: str, mood_after: int, exercise_notes: Optional[str] = None) -> Dict[str, Any]:
        """Complete an exercise session with mood rating"""
        try:
            # Update exercise in database
            update_data = {
                "completion_status": "completed",
                "mood_after": mood_after,
                "completed_at": datetime.now().isoformat()
            }
            
            if exercise_notes:
                update_data["exercise_notes"] = exercise_notes
            
            response = supabase_client.table("mental_exercises") \
                .update(update_data) \
                .eq("id", exercise_id) \
                .execute()
            
            if response.data:
                logger.info(f"Exercise {exercise_id} completed successfully")
                return {
                    "success": True,
                    "message": "Exercise completed successfully",
                    "mood_improvement": mood_after - (response.data[0].get('mood_before', mood_after))
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to update exercise completion"
                }
                
        except Exception as e:
            logger.error(f"Exercise completion failed: {e}")
            return {
                "success": False,
                "error": f"Failed to complete exercise: {str(e)}"
            }
    
    async def get_exercise_history(self, user_id: str, exercise_type: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Get user's exercise history"""
        try:
            query = supabase_client.table("mental_exercises") \
                .select("*") \
                .eq("user_id", user_id) \
                .order("created_at", desc=True) \
                .limit(limit)
            
            if exercise_type:
                query = query.eq("exercise_type", exercise_type)
            
            response = query.execute()
            exercises = response.data if response.data else []
            
            # Decrypt exercise data for return
            decrypted_exercises = []
            for exercise in exercises:
                try:
                    exercise_info = {
                        "exercise_id": exercise['id'],
                        "exercise_type": exercise['exercise_type'],
                        "session_date": exercise['session_date'],
                        "duration_minutes": exercise['duration_minutes'],
                        "completion_status": exercise['completion_status'],
                        "mood_before": exercise.get('mood_before'),
                        "mood_after": exercise.get('mood_after'),
                        "mood_improvement": None
                    }
                    
                    if exercise.get('mood_before') and exercise.get('mood_after'):
                        exercise_info['mood_improvement'] = exercise['mood_after'] - exercise['mood_before']
                    
                    # Decrypt notes if available
                    if exercise.get('notes'):
                        try:
                            decrypted_notes = self.fernet.decrypt(
                                exercise['notes'].encode()
                            ).decode()
                            notes_data = json.loads(decrypted_notes)
                            exercise_info['effectiveness_analysis'] = notes_data.get('effectiveness_analysis', {})
                        except Exception:
                            pass  # Skip if decryption fails
                    
                    decrypted_exercises.append(exercise_info)
                    
                except Exception as decrypt_error:
                    logger.warning(f"Could not process exercise {exercise['id']}: {decrypt_error}")
            
            return decrypted_exercises
            
        except Exception as e:
            logger.error(f"Exercise history retrieval failed: {e}")
            return []
    
    def get_available_exercises(self) -> Dict[str, Any]:
        """Get list of available exercise types and their descriptions"""
        return {
            exercise_type: {
                "name": config["name"],
                "description": config["description"],
                "duration_minutes": config["duration"] // 60,
                "techniques": config["techniques"],
                "benefits": config["benefits"]
            }
            for exercise_type, config in self.exercise_configs.items()
        }

# Global mental exercise agent instance
mental_exercise_agent = MentalExerciseAgent() 