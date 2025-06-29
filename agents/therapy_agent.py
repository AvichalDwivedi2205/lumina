import logging
import uuid
import json
import asyncio
from typing import Dict, List, Any, Optional, TypedDict
from datetime import datetime, timedelta
import httpx

import google.generativeai as genai
from cryptography.fernet import Fernet
from langgraph.graph import StateGraph, END

from config import settings
from database.supabase_client import supabase_client

logger = logging.getLogger(__name__)

# State definition for LangGraph therapy workflow
class TherapyState(TypedDict):
    user_id: str
    session_id: Optional[str]
    therapist_type: str  # "male" or "female"
    session_mode: str    # "voice" or "video"
    session_context: Optional[Dict[str, Any]]
    therapy_notes: Optional[Dict[str, Any]]
    exercise_recommendations: Optional[List[Dict[str, Any]]]
    crisis_assessment: Optional[Dict[str, Any]]
    session_summary: Optional[str]
    reflection_questions: Optional[List[str]]
    error: Optional[str]

class TherapyAgent:
    """
    Therapy agent using LangGraph orchestration for managing therapeutic conversations
    with ElevenLabs voice agents and Tavus video personas.
    """
    
    def __init__(self):
        # Initialize encryption
        if not settings.FERNET_KEY:
            raise ValueError("FERNET_KEY must be configured")
        self.fernet = Fernet(settings.FERNET_KEY.encode())
        
        # Initialize Gemini for analysis
        if not settings.GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY required")
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        # HTTP client for API calls
        self.http_client = httpx.AsyncClient(timeout=30.0)
        
        # Therapeutic frameworks and patterns
        self.therapeutic_frameworks = {
            "CBT": "Cognitive Behavioral Therapy - identifying and restructuring negative thought patterns",
            "DBT": "Dialectical Behavior Therapy - emotion regulation and distress tolerance skills", 
            "ACT": "Acceptance and Commitment Therapy - psychological flexibility and values-based action",
            "Trauma_Informed": "Trauma-informed care - safety, trustworthiness, collaboration"
        }
        
        # Exercise types mapping
        self.exercise_types = {
            "mindfulness": {
                "name": "Mindfulness Practice",
                "duration": 10,
                "description": "Guided meditation and present-moment awareness",
                "agent_id": settings.ELEVENLABS_MINDFULNESS_AGENT_ID
            },
            "cbt_tools": {
                "name": "CBT Tools",
                "duration": 10, 
                "description": "Cognitive restructuring and thought challenging exercises",
                "agent_id": settings.ELEVENLABS_CBT_AGENT_ID
            },
            "behavioral_activation": {
                "name": "Behavioral Activation",
                "duration": 10,
                "description": "Activity planning and mood enhancement exercises",
                "agent_id": settings.ELEVENLABS_BEHAVIORAL_AGENT_ID
            },
            "self_compassion": {
                "name": "Self-Compassion",
                "duration": 10,
                "description": "Self-kindness and emotion regulation practices",
                "agent_id": settings.ELEVENLABS_COMPASSION_AGENT_ID
            }
        }
        
        # Build the workflow
        self.workflow = self._build_workflow()
        
        logger.info("Therapy agent initialized with LangGraph orchestration")
    
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow for therapy session management"""
        workflow = StateGraph(TherapyState)
        
        # Add nodes
        workflow.add_node("prepare_session", self._prepare_session)
        workflow.add_node("load_context", self._load_session_context)
        workflow.add_node("initiate_conversation", self._initiate_conversation)
        workflow.add_node("process_session_end", self._process_session_end)
        workflow.add_node("analyze_session", self._analyze_session)
        workflow.add_node("recommend_exercises", self._recommend_exercises)
        workflow.add_node("generate_reflection", self._generate_reflection_questions)
        workflow.add_node("store_session", self._store_session_data)
        
        # Define the flow
        workflow.set_entry_point("prepare_session")
        workflow.add_edge("prepare_session", "load_context")
        workflow.add_edge("load_context", "initiate_conversation")
        workflow.add_edge("initiate_conversation", "process_session_end")
        workflow.add_edge("process_session_end", "analyze_session")
        workflow.add_edge("analyze_session", "recommend_exercises")
        workflow.add_edge("recommend_exercises", "generate_reflection")
        workflow.add_edge("generate_reflection", "store_session")
        workflow.add_edge("store_session", END)
        
        return workflow.compile()
    
    async def _prepare_session(self, state: TherapyState) -> TherapyState:
        """Prepare therapy session with user context"""
        try:
            # Generate session ID
            state['session_id'] = str(uuid.uuid4())
            
            # Validate therapist type and mode
            if state['therapist_type'] not in ['male', 'female']:
                raise ValueError("Invalid therapist type. Must be 'male' or 'female'")
            
            if state['session_mode'] not in ['voice', 'video']:
                raise ValueError("Invalid session mode. Must be 'voice' or 'video'")
            
            logger.info(f"Session prepared: {state['session_id']} for user {state['user_id']}")
            
        except Exception as e:
            logger.error(f"Session preparation failed: {e}")
            state['error'] = f"Session preparation failed: {str(e)}"
        
        return state
    
    async def _load_session_context(self, state: TherapyState) -> TherapyState:
        """Load previous session context and therapy notes"""
        try:
            # Query previous sessions for context
            response = supabase_client.table("therapy_sessions") \
                .select("*") \
                .eq("user_id", state['user_id']) \
                .order("created_at", desc=True) \
                .limit(5) \
                .execute()
            
            previous_sessions = response.data if response.data else []
            
            # Decrypt and compile session context
            session_context = {
                "previous_sessions_count": len(previous_sessions),
                "recent_patterns": [],
                "ongoing_goals": [],
                "preferred_interventions": [],
                "last_session_summary": None
            }
            
            if previous_sessions:
                # Decrypt the most recent session notes
                latest_session = previous_sessions[0]
                if latest_session.get('encrypted_notes'):
                    try:
                        decrypted_notes = self.fernet.decrypt(
                            latest_session['encrypted_notes'].encode()
                        ).decode()
                        notes_data = json.loads(decrypted_notes)
                        
                        session_context['recent_patterns'] = notes_data.get('patterns', [])
                        session_context['ongoing_goals'] = notes_data.get('treatment_goals', [])
                        session_context['last_session_summary'] = notes_data.get('session_summary', '')
                        
                    except Exception as decrypt_error:
                        logger.warning(f"Could not decrypt previous session notes: {decrypt_error}")
            
            state['session_context'] = session_context
            logger.info(f"Session context loaded for user {state['user_id']}")
            
        except Exception as e:
            logger.error(f"Loading session context failed: {e}")
            state['session_context'] = {"previous_sessions_count": 0}
            
        return state
    
    async def _initiate_conversation(self, state: TherapyState) -> TherapyState:
        """Initiate conversation with ElevenLabs or Tavus agent"""
        try:
            if state['session_mode'] == 'voice':
                await self._start_elevenlabs_conversation(state)
            elif state['session_mode'] == 'video':
                await self._start_tavus_conversation(state)
            
            logger.info(f"Conversation initiated for session {state['session_id']}")
            
        except Exception as e:
            logger.error(f"Conversation initiation failed: {e}")
            state['error'] = f"Conversation initiation failed: {str(e)}"
        
        return state
    
    async def _start_elevenlabs_conversation(self, state: TherapyState) -> TherapyState:
        """Start ElevenLabs voice conversation"""
        try:
            # Get agent ID based on therapist type
            agent_id = (settings.ELEVENLABS_MALE_THERAPIST_AGENT_ID 
                       if state['therapist_type'] == 'male' 
                       else settings.ELEVENLABS_FEMALE_THERAPIST_AGENT_ID)
            
            if not agent_id:
                raise ValueError(f"No agent ID configured for {state['therapist_type']} therapist")
            
            # Prepare conversation context for ElevenLabs
            conversation_context = self._prepare_conversation_context(state)
            
            # ElevenLabs conversation will be initiated via webhook
            # Store the agent configuration for webhook processing
            state['agent_config'] = {
                'agent_id': agent_id,
                'conversation_context': conversation_context,
                'session_duration': settings.THERAPY_SESSION_DURATION
            }
            
            logger.info(f"ElevenLabs conversation prepared with agent {agent_id}")
            
        except Exception as e:
            logger.error(f"ElevenLabs conversation setup failed: {e}")
            state['error'] = f"ElevenLabs setup failed: {str(e)}"
        
        return state
    
    async def _start_tavus_conversation(self, state: TherapyState) -> TherapyState:
        """Start Tavus video conversation"""
        try:
            # Get persona ID based on therapist type
            persona_id = (settings.TAVUS_MALE_THERAPIST_PERSONA_ID 
                         if state['therapist_type'] == 'male' 
                         else settings.TAVUS_FEMALE_THERAPIST_PERSONA_ID)
            
            if not persona_id:
                raise ValueError(f"No persona ID configured for {state['therapist_type']} therapist")
            
            # Prepare conversation context
            conversation_context = self._prepare_conversation_context(state)
            
            # Tavus API call to create conversation
            headers = {
                "x-api-key": settings.TAVUS_API_KEY,
                "Content-Type": "application/json"
            }
            
            payload = {
                "persona_id": persona_id,
                "conversational_context": conversation_context,
                "max_call_duration": settings.THERAPY_SESSION_DURATION,
                "callback_url": f"{settings.WORKOS_REDIRECT_URI.replace('/auth/callback', '')}/therapy/webhook/tavus-callback"
            }
            
            response = await self.http_client.post(
                "https://tavusapi.com/v2/conversations",
                headers=headers,
                json=payload
            )
            
            if response.status_code == 201:
                conversation_data = response.json()
                state['tavus_conversation'] = conversation_data
                logger.info(f"Tavus conversation created: {conversation_data.get('conversation_id')}")
            else:
                raise Exception(f"Tavus API error: {response.status_code} - {response.text}")
            
        except Exception as e:
            logger.error(f"Tavus conversation setup failed: {e}")
            state['error'] = f"Tavus setup failed: {str(e)}"
        
        return state
    
    def _prepare_conversation_context(self, state: TherapyState) -> str:
        """Prepare context string for conversation agents"""
        context = state.get('session_context', {})
        
        context_parts = [
            f"This is session #{context.get('previous_sessions_count', 0) + 1} with this client.",
        ]
        
        if context.get('recent_patterns'):
            context_parts.append(f"Recent patterns observed: {', '.join(context['recent_patterns'])}")
        
        if context.get('ongoing_goals'):
            context_parts.append(f"Current treatment goals: {', '.join(context['ongoing_goals'])}")
        
        if context.get('last_session_summary'):
            context_parts.append(f"Last session summary: {context['last_session_summary']}")
        
        return " ".join(context_parts)
    
    async def _process_session_end(self, state: TherapyState) -> TherapyState:
        """Process session end and prepare for analysis"""
        try:
            # This would be called when session ends
            # For now, we'll simulate session completion
            state['session_completed'] = True
            logger.info(f"Session {state['session_id']} marked as completed")
            
        except Exception as e:
            logger.error(f"Session end processing failed: {e}")
            state['error'] = f"Session end processing failed: {str(e)}"
        
        return state
    
    async def _analyze_session(self, state: TherapyState) -> TherapyState:
        """Analyze therapy session using LLM"""
        try:
            # This will be populated by webhook data in real implementation
            # For now, create a template structure
            if not state.get('therapy_notes'):
                state['therapy_notes'] = {
                    "session_date": datetime.now().isoformat(),
                    "mood_rating": None,
                    "key_topics": [],
                    "cognitive_patterns": [],
                    "interventions_used": [],
                    "progress_notes": "",
                    "homework_assigned": "",
                    "treatment_goals": []
                }
            
            # Generate session summary using LLM
            analysis_prompt = f"""
            You are a licensed therapist reviewing a therapy session. Based on the session context and notes, 
            provide a comprehensive session summary.
            
            Session Context: {state.get('session_context', {})}
            Therapy Notes: {state.get('therapy_notes', {})}
            
            Provide a structured analysis in JSON format:
            {{
                "session_summary": "Brief summary of key session content and progress",
                "therapeutic_progress": "Assessment of client's progress toward goals",
                "patterns_observed": ["pattern1", "pattern2"],
                "interventions_effectiveness": "How well did interventions work",
                "next_session_focus": "Recommended focus for next session"
            }}
            """
            
            response = await self.model.generate_content_async(analysis_prompt)
            analysis_text = response.text.strip()
            
            if analysis_text.startswith('```json'):
                analysis_text = analysis_text.replace('```json', '').replace('```', '').strip()
            
            analysis_data = json.loads(analysis_text)
            state['session_summary'] = analysis_data.get('session_summary', '')
            
            logger.info(f"Session analysis completed for {state['session_id']}")
            
        except Exception as e:
            logger.error(f"Session analysis failed: {e}")
            state['session_summary'] = "Session analysis could not be completed"
            
        return state
    
    async def _recommend_exercises(self, state: TherapyState) -> TherapyState:
        """Recommend therapeutic exercises based on session content"""
        try:
            session_notes = state.get('therapy_notes', {})
            patterns = session_notes.get('cognitive_patterns', [])
            topics = session_notes.get('key_topics', [])
            
            # Use LLM to recommend appropriate exercises
            recommendation_prompt = f"""
            Based on this therapy session, recommend 1-2 appropriate therapeutic exercises.
            
            Session patterns: {patterns}
            Key topics: {topics}
            Available exercises:
            1. mindfulness - for anxiety, stress, emotional regulation
            2. cbt_tools - for negative thinking patterns, cognitive distortions
            3. behavioral_activation - for depression, low motivation, inactivity
            4. self_compassion - for self-criticism, shame, harsh self-judgment
            
            Respond in JSON format:
            {{
                "recommendations": [
                    {{
                        "exercise_type": "exercise_name",
                        "rationale": "why this exercise is recommended",
                        "priority": "high/medium/low"
                    }}
                ]
            }}
            """
            
            response = await self.model.generate_content_async(recommendation_prompt)
            recommendation_text = response.text.strip()
            
            if recommendation_text.startswith('```json'):
                recommendation_text = recommendation_text.replace('```json', '').replace('```', '').strip()
            
            recommendations_data = json.loads(recommendation_text)
            state['exercise_recommendations'] = recommendations_data.get('recommendations', [])
            
            logger.info(f"Exercise recommendations generated for {state['session_id']}")
            
        except Exception as e:
            logger.error(f"Exercise recommendation failed: {e}")
            state['exercise_recommendations'] = []
            
        return state
    
    async def _generate_reflection_questions(self, state: TherapyState) -> TherapyState:
        """Generate post-session reflection questions"""
        try:
            session_summary = state.get('session_summary', '')
            
            reflection_prompt = f"""
            Generate 3-4 thoughtful reflection questions for a client after their therapy session.
            
            Session Summary: {session_summary}
            
            Create questions that:
            - Encourage deeper self-reflection
            - Connect to session themes
            - Are actionable and specific
            - Promote insight and growth
            
            Respond in JSON format:
            {{
                "reflection_questions": [
                    "Question 1",
                    "Question 2",
                    "Question 3",
                    "Question 4"
                ]
            }}
            """
            
            response = await self.model.generate_content_async(reflection_prompt)
            reflection_text = response.text.strip()
            
            if reflection_text.startswith('```json'):
                reflection_text = reflection_text.replace('```json', '').replace('```', '').strip()
            
            reflection_data = json.loads(reflection_text)
            state['reflection_questions'] = reflection_data.get('reflection_questions', [])
            
            logger.info(f"Reflection questions generated for {state['session_id']}")
            
        except Exception as e:
            logger.error(f"Reflection question generation failed: {e}")
            state['reflection_questions'] = [
                "What was the most important insight from today's session?",
                "How do you want to apply what we discussed this week?",
                "What would you like to focus on in our next session?"
            ]
            
        return state
    
    async def _store_session_data(self, state: TherapyState) -> TherapyState:
        """Store encrypted session data in database"""
        try:
            # Prepare session data for storage
            session_data = {
                "session_id": state['session_id'],
                "therapist_type": state['therapist_type'],
                "session_mode": state['session_mode'],
                "therapy_notes": state.get('therapy_notes', {}),
                "session_summary": state.get('session_summary', ''),
                "exercise_recommendations": state.get('exercise_recommendations', []),
                "reflection_questions": state.get('reflection_questions', [])
            }
            
            # Encrypt sensitive data
            encrypted_notes = self.fernet.encrypt(
                json.dumps(session_data).encode()
            ).decode()
            
            # Store in database
            insert_data = {
                "id": state['session_id'],
                "user_id": state['user_id'],
                "therapist_type": state['therapist_type'],
                "session_mode": state['session_mode'],
                "session_date": datetime.now().isoformat(),
                "duration_minutes": settings.THERAPY_SESSION_DURATION // 60,
                "encrypted_notes": encrypted_notes,
                "session_summary": state.get('session_summary', ''),
                "exercises_recommended": json.dumps(state.get('exercise_recommendations', [])),
                "created_at": datetime.now().isoformat()
            }
            
            response = supabase_client.table("therapy_sessions").insert(insert_data).execute()
            
            if response.data:
                logger.info(f"Session data stored for {state['session_id']}")
            else:
                logger.error(f"Failed to store session data: {response}")
                
        except Exception as e:
            logger.error(f"Session data storage failed: {e}")
            state['error'] = f"Session storage failed: {str(e)}"
        
        return state
    
    async def start_therapy_session(self, user_id: str, therapist_type: str, session_mode: str) -> Dict[str, Any]:
        """Start a new therapy session"""
        try:
            initial_state = TherapyState(
                user_id=user_id,
                therapist_type=therapist_type,
                session_mode=session_mode,
                session_id=None,
                session_context=None,
                therapy_notes=None,
                exercise_recommendations=None,
                crisis_assessment=None,
                session_summary=None,
                reflection_questions=None,
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
                "session_id": final_state['session_id'],
                "agent_config": final_state.get('agent_config'),
                "tavus_conversation": final_state.get('tavus_conversation'),
                "session_context": final_state.get('session_context')
            }
            
        except Exception as e:
            logger.error(f"Therapy session start failed: {e}")
            return {
                "success": False,
                "error": f"Failed to start therapy session: {str(e)}"
            }
    
    async def process_session_webhook(self, session_id: str, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process webhook data from ElevenLabs/Tavus during session"""
        try:
            # This will be called by webhook endpoints
            # Process and store real-time session data
            
            # Basic crisis detection
            if settings.CRISIS_DETECTION_ENABLED:
                crisis_check = await self._check_crisis_indicators(webhook_data)
                if crisis_check.get('crisis_detected'):
                    logger.warning(f"Crisis indicators detected in session {session_id}")
                    return {
                        "success": True,
                        "crisis_detected": True,
                        "crisis_resources": crisis_check.get('resources', {})
                    }
            
            return {
                "success": True,
                "crisis_detected": False
            }
            
        except Exception as e:
            logger.error(f"Webhook processing failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _check_crisis_indicators(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """Basic crisis detection for MVP"""
        crisis_keywords = [
            "suicide", "kill myself", "end it all", "not worth living",
            "hurt myself", "self-harm", "cutting", "overdose",
            "hopeless", "can't go on", "want to die"
        ]
        
        # Extract text from webhook data (this will vary by provider)
        text_content = webhook_data.get('transcript', '').lower()
        
        detected_keywords = [kw for kw in crisis_keywords if kw in text_content]
        
        if detected_keywords:
            return {
                "crisis_detected": True,
                "level": "high" if any(kw in ["suicide", "kill myself", "want to die"] for kw in detected_keywords) else "medium",
                "keywords": detected_keywords,
                "resources": {
                    "crisis_line": "988 - Suicide & Crisis Lifeline",
                    "text_line": "Text HOME to 741741",
                    "emergency": "Call 911 if in immediate danger"
                }
            }
        
        return {"crisis_detected": False}
    
    async def get_session_history(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get user's therapy session history"""
        try:
            response = supabase_client.table("therapy_sessions") \
                .select("*") \
                .eq("user_id", user_id) \
                .order("created_at", desc=True) \
                .limit(limit) \
                .execute()
            
            sessions = response.data if response.data else []
            
            # Decrypt session data for return
            decrypted_sessions = []
            for session in sessions:
                try:
                    if session.get('encrypted_notes'):
                        decrypted_notes = self.fernet.decrypt(
                            session['encrypted_notes'].encode()
                        ).decode()
                        session_data = json.loads(decrypted_notes)
                        
                        decrypted_sessions.append({
                            "session_id": session['id'],
                            "session_date": session['session_date'],
                            "therapist_type": session['therapist_type'],
                            "session_mode": session['session_mode'],
                            "session_summary": session['session_summary'],
                            "exercises_recommended": json.loads(session.get('exercises_recommended', '[]')),
                            "reflection_questions": session_data.get('reflection_questions', [])
                        })
                except Exception as decrypt_error:
                    logger.warning(f"Could not decrypt session {session['id']}: {decrypt_error}")
            
            return decrypted_sessions
            
        except Exception as e:
            logger.error(f"Session history retrieval failed: {e}")
            return []

# Global therapy agent instance
therapy_agent = TherapyAgent() 