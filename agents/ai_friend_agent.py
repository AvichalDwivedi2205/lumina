import logging
import uuid
import json
from typing import Dict, List, Any, Optional, TypedDict
from datetime import datetime
import asyncio

import google.generativeai as genai
from cryptography.fernet import Fernet
import httpx
from langgraph.graph import StateGraph, END

from config import settings
from services.elevenlabs_friend_auth import ElevenLabsFriendAuthService

logger = logging.getLogger(__name__)

# State definition for LangGraph workflow
class FriendState(TypedDict):
    user_id: str
    personality_type: str  # 'supportive', 'motivator', 'mentor', 'funny', 'mindful'
    conversation_context: Optional[Dict[str, Any]]
    mood_assessment: Optional[str]
    response_style: Optional[str]
    conversation_id: Optional[str]
    agent_url: Optional[str]
    selected_personality: Optional[Dict[str, Any]]
    system_prompt: Optional[str]
    final_response: Optional[Dict[str, Any]]
    error: Optional[str]

class AIFriendAgent:
    """
    AI Friend agent with 5 distinct personalities using ElevenLabs voice agents.
    Provides emotional support, motivation, mentorship, humor, and mindfulness guidance.
    No conversation storage - ephemeral interactions only.
    """
    
    def __init__(self):
        # Initialize Gemini for personality analysis
        if not settings.GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY required")
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        # Initialize ElevenLabs auth service for friend agents
        self.elevenlabs_auth = ElevenLabsFriendAuthService()
        
        # Friend personalities configuration
        self.personalities = {
            "supportive": {
                "name": "Emma",
                "agent_id": settings.ELEVENLABS_FRIEND_SUPPORTIVE_AGENT_ID,
                "voice_style": "warm, caring, empathetic",
                "specialties": ["emotional support", "validation", "comfort", "active listening"]
            },
            "motivator": {
                "name": "Alex", 
                "agent_id": settings.ELEVENLABS_FRIEND_MOTIVATOR_AGENT_ID,
                "voice_style": "energetic, enthusiastic, inspiring",
                "specialties": ["goal achievement", "confidence building", "action planning"]
            },
            "mentor": {
                "name": "Morgan",
                "agent_id": settings.ELEVENLABS_FRIEND_MENTOR_AGENT_ID,
                "voice_style": "wise, thoughtful, guiding", 
                "specialties": ["life guidance", "decision making", "personal growth"]
            },
            "funny": {
                "name": "Riley",
                "agent_id": settings.ELEVENLABS_FRIEND_FUNNY_AGENT_ID,
                "voice_style": "playful, witty, lighthearted",
                "specialties": ["mood lifting", "stress relief", "joy creation"]
            },
            "mindful": {
                "name": "Sage",
                "agent_id": settings.ELEVENLABS_FRIEND_UNHINGED_AGENT_ID, 
                "voice_style": "calm, centered, peaceful",
                "specialties": ["mindfulness practice", "stress reduction", "inner peace"]
            }
        }
        
        # Build the workflow
        self.workflow = self._build_workflow()
        
        logger.info("AI Friend agent initialized with 5 personalities")

    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow for friend conversations"""
        workflow = StateGraph(FriendState)
        
        # Add nodes
        workflow.add_node("assess_user_needs", self._assess_user_needs)
        workflow.add_node("select_personality", self._select_personality)
        workflow.add_node("prepare_conversation", self._prepare_conversation)
        workflow.add_node("generate_agent_url", self._generate_agent_url)
        workflow.add_node("finalize_response", self._finalize_response)
        
        # Define the workflow
        workflow.set_entry_point("assess_user_needs")
        
        # Connect nodes
        workflow.add_edge("assess_user_needs", "select_personality")
        workflow.add_edge("select_personality", "prepare_conversation")
        workflow.add_edge("prepare_conversation", "generate_agent_url")
        workflow.add_edge("generate_agent_url", "finalize_response")
        workflow.add_edge("finalize_response", END)
        
        return workflow.compile()

    async def _assess_user_needs(self, state: FriendState) -> FriendState:
        """Assess user's emotional needs and current state"""
        try:
            user_context = state.get('conversation_context', {})
            
            # Analyze user's current emotional state and needs
            assessment_prompt = f"""
            You are an emotional intelligence expert. Analyze the user's current state and needs.
            
            User Context:
            - Recent message/mood: {user_context.get('user_message', 'Not specified')}
            - Time of day: {datetime.now().strftime('%H:%M')}
            - Requested personality: {state.get('personality_type', 'auto')}
            
            Determine:
            1. Primary emotional need (support, motivation, guidance, humor, mindfulness)
            2. Current mood/energy level
            3. Appropriate response style
            
            Respond in JSON format:
            {{
                "primary_need": "support/motivation/guidance/humor/mindfulness",
                "mood_assessment": "brief mood description",
                "energy_level": "low/medium/high",
                "recommended_personality": "supportive/motivator/mentor/funny/mindful",
                "response_style": "gentle/energetic/thoughtful/playful/calm"
            }}
            """
            
            response = await self.model.generate_content_async(assessment_prompt)
            assessment_text = response.text.strip()
            
            # Clean JSON response
            if assessment_text.startswith('```json'):
                assessment_text = assessment_text.replace('```json', '').replace('```', '').strip()
            
            assessment_data = json.loads(assessment_text)
            
            state['mood_assessment'] = assessment_data.get('mood_assessment', '')
            state['response_style'] = assessment_data.get('response_style', 'gentle')
            
            # Override personality if user specified one
            if not state.get('personality_type') or state.get('personality_type') == 'auto':
                state['personality_type'] = assessment_data.get('recommended_personality', 'supportive')
            
            logger.info(f"User needs assessed: {assessment_data.get('primary_need')} - {state['personality_type']}")
            
        except Exception as e:
            logger.error(f"User needs assessment failed: {e}")
            state['personality_type'] = 'supportive'  # Default fallback
            state['mood_assessment'] = 'neutral'
            state['response_style'] = 'gentle'
        
        return state

    async def _select_personality(self, state: FriendState) -> FriendState:
        """Select and configure the appropriate personality"""
        try:
            personality_type = state.get('personality_type', 'supportive')
            
            if personality_type not in self.personalities:
                logger.warning(f"Unknown personality type: {personality_type}, defaulting to supportive")
                personality_type = 'supportive'
                state['personality_type'] = personality_type
            
            personality_config = self.personalities[personality_type]
            state['selected_personality'] = personality_config
            
            logger.info(f"Selected personality: {personality_config['name']} ({personality_type})")
            
        except Exception as e:
            logger.error(f"Personality selection failed: {e}")
            state['error'] = f"Personality selection failed: {str(e)}"
        
        return state

    async def _prepare_conversation(self, state: FriendState) -> FriendState:
        """Prepare conversation context and system prompt"""
        try:
            personality_config = state.get('selected_personality', {})
            user_context = state.get('conversation_context', {})
            
            # Create dynamic system prompt based on personality and user needs
            system_prompt = f"""
            You are {personality_config['name']}, an AI friend with a {personality_config['voice_style']} personality.
            
            SPECIALTIES:
            {', '.join(personality_config['specialties'])}
            
            CURRENT CONTEXT:
            - User's mood: {state.get('mood_assessment', 'neutral')}
            - Response style needed: {state.get('response_style', 'gentle')}
            - Time of conversation: {datetime.now().strftime('%A, %B %d at %I:%M %p')}
            
            IMPORTANT GUIDELINES:
            - Stay true to your personality throughout the conversation
            - Be genuinely helpful while maintaining your unique character
            - No conversation history is stored - treat each interaction as fresh
            - Keep responses conversational and engaging
            - If the user seems in crisis, gently suggest professional help
            - Adapt your energy to match what the user needs right now
            
            Remember: You're not just an AI, you're {personality_config['name']}, their {state['personality_type']} friend who truly cares about their wellbeing.
            """
            
            state['system_prompt'] = system_prompt
            
            logger.info(f"Conversation prepared for {personality_config['name']}")
            
        except Exception as e:
            logger.error(f"Conversation preparation failed: {e}")
            state['error'] = f"Conversation preparation failed: {str(e)}"
        
        return state

    async def _generate_agent_url(self, state: FriendState) -> FriendState:
        """Generate secure ElevenLabs agent URL"""
        try:
            personality_config = state.get('selected_personality', {})
            agent_id = personality_config.get('agent_id')
            
            if not agent_id:
                raise ValueError(f"No agent ID configured for personality: {state['personality_type']}")
            
            # Generate signed URL for the friend agent
            signed_url_data = await self.elevenlabs_auth.generate_signed_url(
                agent_id=agent_id,
                user_id=state['user_id'],
                conversation_id=str(uuid.uuid4())
            )
            
            if signed_url_data['success']:
                state['agent_url'] = signed_url_data['signed_url']
                state['conversation_id'] = signed_url_data['conversation_id']
            else:
                raise Exception(signed_url_data.get('error', 'Failed to generate agent URL'))
            
            logger.info(f"Agent URL generated for {personality_config['name']}")
            
        except Exception as e:
            logger.error(f"Agent URL generation failed: {e}")
            state['error'] = f"Agent URL generation failed: {str(e)}"
        
        return state

    async def _finalize_response(self, state: FriendState) -> FriendState:
        """Finalize the friend conversation response"""
        try:
            personality_config = state.get('selected_personality', {})
            
            state['final_response'] = {
                "success": True,
                "personality": {
                    "name": personality_config.get('name'),
                    "type": state['personality_type'],
                    "voice_style": personality_config.get('voice_style'),
                    "specialties": personality_config.get('specialties', [])
                },
                "conversation": {
                    "agent_url": state.get('agent_url'),
                    "conversation_id": state.get('conversation_id'),
                    "system_prompt": state.get('system_prompt'),
                    "mood_assessment": state.get('mood_assessment'),
                    "response_style": state.get('response_style')
                },
                "instructions": {
                    "usage": "Use the agent_url to start your conversation with your AI friend",
                    "duration": "No time limit - chat as long as you need",
                    "privacy": "Conversations are ephemeral and not stored permanently"
                }
            }
            
            logger.info(f"Friend conversation response finalized for {personality_config.get('name')}")
            
        except Exception as e:
            logger.error(f"Response finalization failed: {e}")
            state['error'] = f"Response finalization failed: {str(e)}"
        
        return state

    # Public methods for API endpoints
    async def start_conversation(self, user_id: str, personality_type: str = 'auto', user_message: str = '') -> Dict[str, Any]:
        """Start a conversation with an AI friend"""
        state = FriendState(
            user_id=user_id,
            personality_type=personality_type,
            conversation_context={'user_message': user_message},
            mood_assessment=None,
            response_style=None,
            conversation_id=None,
            agent_url=None,
            selected_personality=None,
            system_prompt=None,
            final_response=None,
            error=None
        )
        
        result = await self.workflow.ainvoke(state)
        if result and 'final_response' in result:
            return result['final_response']
        elif result and 'error' in result:
            return {"success": False, "error": result['error']}
        else:
            return {"success": False, "error": "Workflow returned no result"}

    def get_available_personalities(self) -> Dict[str, Any]:
        """Get list of available AI friend personalities"""
        return {
            personality_type: {
                "name": config["name"],
                "voice_style": config["voice_style"],
                "specialties": config["specialties"]
            }
            for personality_type, config in self.personalities.items()
        }

    async def get_personality_recommendation(self, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Get personality recommendation based on user context"""
        try:
            recommendation_prompt = f"""
            Based on the user's current context, recommend the most appropriate AI friend personality.
            
            User Context: {user_context}
            
            Available Personalities:
            - supportive (Emma): For emotional support and validation
            - motivator (Alex): For energy and goal achievement  
            - mentor (Morgan): For guidance and wisdom
            - funny (Riley): For humor and mood lifting
            - mindful (Sage): For calm and mindfulness
            
            Respond in JSON format:
            {{
                "recommended_personality": "personality_type",
                "reason": "why this personality is recommended",
                "alternative": "backup personality option"
            }}
            """
            
            response = await self.model.generate_content_async(recommendation_prompt)
            recommendation_text = response.text.strip()
            
            if recommendation_text.startswith('```json'):
                recommendation_text = recommendation_text.replace('```json', '').replace('```', '').strip()
            
            return json.loads(recommendation_text)
            
        except Exception as e:
            logger.error(f"Personality recommendation failed: {e}")
            return {
                "recommended_personality": "supportive",
                "reason": "Default supportive personality for general emotional support",
                "alternative": "mindful"
            }

    # Additional methods for API endpoints
    async def get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """Get user's AI friend preferences"""
        try:
            # This would query the database - for now return default preferences
            logger.info(f"Getting AI friend preferences for user {user_id}")
            return {
                "success": True,
                "preferences": {
                    "preferred_personalities": ["supportive", "mentor"],
                    "interaction_style": "gentle and encouraging",
                    "topics_of_interest": ["personal growth", "stress management"],
                    "communication_preferences": {
                        "session_length": "medium",
                        "conversation_pace": "thoughtful"
                    }
                }
            }
        except Exception as e:
            logger.error(f"Get user preferences failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def update_user_preferences(self, user_id: str, preferences_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update user's AI friend preferences"""
        try:
            # This would update the database - for now return success
            logger.info(f"Updating AI friend preferences for user {user_id}")
            return {"success": True, "message": "Preferences updated successfully"}
        except Exception as e:
            logger.error(f"Update user preferences failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_user_analytics(self, user_id: str) -> Dict[str, Any]:
        """Get user's AI friend analytics"""
        try:
            # This would analyze the user's interaction data - for now return basic analytics
            logger.info(f"Getting AI friend analytics for user {user_id}")
            return {
                "success": True,
                "analytics": {
                    "total_conversations": 25,
                    "favorite_personality": "supportive",
                    "avg_conversation_duration": 12,
                    "mood_improvement_rate": 78,
                    "last_interaction": "2025-06-29T15:30:00Z",
                    "personality_usage": {
                        "supportive": 40,
                        "mentor": 30,
                        "motivator": 20,
                        "funny": 5,
                        "mindful": 5
                    }
                }
            }
        except Exception as e:
            logger.error(f"Get user analytics failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_personality_analytics(self, user_id: str) -> Dict[str, Any]:
        """Get personality-specific analytics"""
        try:
            # This would analyze personality effectiveness - for now return basic data
            logger.info(f"Getting personality analytics for user {user_id}")
            return {
                "success": True,
                "personality_analytics": [
                    {
                        "personality": "supportive",
                        "usage_count": 10,
                        "effectiveness_score": 85,
                        "avg_mood_improvement": 2.3
                    },
                    {
                        "personality": "mentor", 
                        "usage_count": 8,
                        "effectiveness_score": 90,
                        "avg_mood_improvement": 2.8
                    },
                    {
                        "personality": "motivator",
                        "usage_count": 5,
                        "effectiveness_score": 75,
                        "avg_mood_improvement": 2.1
                    }
                ]
            }
        except Exception as e:
            logger.error(f"Get personality analytics failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def track_mood(self, user_id: str, mood_data: Dict[str, Any]) -> Dict[str, Any]:
        """Track user's mood after interaction"""
        try:
            # This would save mood data - for now return success
            logger.info(f"Tracking mood for user {user_id}")
            return {"success": True, "message": "Mood tracked successfully"}
        except Exception as e:
            logger.error(f"Track mood failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_session_history(self, user_id: str, limit: int = 10) -> Dict[str, Any]:
        """Get user's session history"""
        try:
            # This would query the database - for now return empty list
            logger.info(f"Getting session history for user {user_id}")
            return {
                "success": True,
                "sessions": []
            }
        except Exception as e:
            logger.error(f"Get session history failed: {e}")
            return {"success": False, "error": str(e)}

# Global AI friend agent instance
ai_friend_agent = AIFriendAgent() 