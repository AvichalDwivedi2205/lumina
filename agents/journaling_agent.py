import logging
import uuid
import json
import re
from typing import Dict, List, Any, Optional, TypedDict
from datetime import datetime
import asyncio

import google.generativeai as genai
from cryptography.fernet import Fernet
import requests
from langgraph.graph import StateGraph, END

from config import settings
from database.supabase_client import supabase_client

logger = logging.getLogger(__name__)

# State definition for LangGraph workflow
class JournalState(TypedDict):
    raw_entry: str
    user_id: str
    normalized_entry: Optional[str]
    emotions: Optional[Dict[str, Any]]
    patterns: Optional[List[str]]
    therapeutic_insight: Optional[str]  # Single unified insight
    crisis_assessment: Optional[Dict[str, Any]]  # Enhanced LLM-based crisis detection
    embedding_vector: Optional[List[float]]
    entry_id: Optional[str]
    error: Optional[str]

class JournalingAgent:
    """
    Enhanced journaling agent with LLM-based crisis detection, unified therapeutic insights,
    and scientifically-grounded emotion framework.
    """
    
    def __init__(self):
        # Initialize encryption
        if not settings.FERNET_KEY:
            raise ValueError("FERNET_KEY must be configured")
        self.fernet = Fernet(settings.FERNET_KEY.encode())
        
        # Initialize Gemini
        if not settings.GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY required")
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        # Fixed 6-emotion framework (Ekman's basic emotions)
        self.core_emotions = {
            "joy": "Happiness, contentment, satisfaction, pleasure",
            "sadness": "Grief, disappointment, melancholy, sorrow", 
            "anger": "Frustration, irritation, rage, annoyance",
            "fear": "Anxiety, worry, panic, nervousness",
            "disgust": "Revulsion, contempt, aversion, distaste",
            "surprise": "Shock, amazement, confusion, astonishment"
        }
        
        # Build the workflow
        self.workflow = self._build_workflow()
        
        logger.info("Enhanced journaling agent initialized with LLM crisis detection")
    
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow for journal processing"""
        workflow = StateGraph(JournalState)
        
        # Add nodes
        workflow.add_node("normalize", self._normalize_entry)
        workflow.add_node("analyze", self._analyze_entry)
        workflow.add_node("assess_crisis", self._assess_crisis_llm)  # Enhanced LLM-based
        workflow.add_node("generate_embedding", self._generate_embedding)
        workflow.add_node("store_entry", self._store_entry)
        
        # Define the flow
        workflow.set_entry_point("normalize")
        workflow.add_edge("normalize", "analyze")
        workflow.add_edge("analyze", "assess_crisis")
        workflow.add_edge("assess_crisis", "generate_embedding")
        workflow.add_edge("generate_embedding", "store_entry")
        workflow.add_edge("store_entry", END)
        
        return workflow.compile()
    
    async def _normalize_entry(self, state: JournalState) -> JournalState:
        """Normalize journal entry for better analysis"""
        try:
            normalization_prompt = f"""
            You are a mental health AI assistant. Normalize this journal entry by making vague statements clearer while preserving the person's authentic voice and emotional expression.

            GUIDELINES:
            - Keep their authentic voice - don't change their style
            - Make vague statements more specific (e.g., "felt bad" → "felt anxious and overwhelmed")
            - Add context where entries are unclear
            - Preserve all emotional content
            - Structure fragmented thoughts coherently
            - Do NOT analyze or interpret - only clarify

            Raw journal entry:
            "{state['raw_entry']}"

            Provide only the normalized version - no analysis or commentary:
            """
            
            response = await self.model.generate_content_async(normalization_prompt)
            normalized = response.text.strip()
            
            # Basic validation - ensure no analysis leaked through
            analysis_words = ['suggests', 'indicates', 'shows', 'reveals', 'pattern', 'recommend']
            if any(word in normalized.lower() for word in analysis_words):
                logger.warning("Analysis detected in normalization, using original")
                normalized = state['raw_entry']
            
            state['normalized_entry'] = normalized
            logger.info(f"Entry normalized for user {state['user_id']}")
            
        except Exception as e:
            logger.error(f"Normalization failed: {e}")
            state['normalized_entry'] = state['raw_entry']  # Fallback
            state['error'] = f"Normalization failed: {str(e)}"
        
        return state
    
    async def _analyze_entry(self, state: JournalState) -> JournalState:
        """Perform unified therapeutic analysis with fixed emotion framework"""
        try:
            # Create emotion descriptions for the prompt
            emotion_descriptions = "\n".join([f"- {emotion}: {desc}" for emotion, desc in self.core_emotions.items()])
            
            analysis_prompt = f"""
            You are a licensed mental health professional. Analyze this journal entry and provide structured therapeutic insights.

            CORE EMOTIONS FRAMEWORK (rate 0-10 for each):
            {emotion_descriptions}

            Journal Entry: "{state['normalized_entry']}"

            Provide analysis in this EXACT JSON format:
            {{
                "emotions": {{
                    "primary": "one of the 6 core emotions above",
                    "secondary": ["additional emotions from the 6 core emotions"],
                    "analysis": {{
                        "joy": 0-10,
                        "sadness": 0-10,
                        "anger": 0-10,
                        "fear": 0-10,
                        "disgust": 0-10,
                        "surprise": 0-10
                    }}
                }},
                "patterns": [
                    "specific cognitive or behavioral pattern 1",
                    "specific cognitive or behavioral pattern 2"
                ],
                "therapeutic_insight": "A single, unified therapeutic insight that integrates the best of CBT (thought challenging), DBT (emotion regulation), and ACT (values-based action) approaches. Make it specific, actionable, and easy to understand. Start with acknowledging their experience, then provide one clear technique or strategy they can use today."
            }}

            CRITICAL: 
            - Use ONLY the 6 core emotions listed above
            - Provide ONE unified therapeutic insight, not separate CBT/DBT/ACT insights
            - Make the insight practical and immediately actionable
            - Respond ONLY with valid JSON
            """
            
            response = await self.model.generate_content_async(analysis_prompt)
            analysis_text = response.text.strip()
            
            # Clean JSON response
            if analysis_text.startswith('```json'):
                analysis_text = analysis_text.replace('```json', '').replace('```', '').strip()
            
            analysis_data = json.loads(analysis_text)
            
            state['emotions'] = analysis_data['emotions']
            state['patterns'] = analysis_data['patterns']
            state['therapeutic_insight'] = analysis_data['therapeutic_insight']
            
            logger.info(f"Analysis completed for user {state['user_id']}")
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in analysis: {e}")
            state['error'] = "Analysis failed - invalid response format"
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            state['error'] = f"Analysis failed: {str(e)}"
        
        return state
    
    async def _assess_crisis_llm(self, state: JournalState) -> JournalState:
        """Enhanced LLM-based crisis assessment"""
        try:
            crisis_prompt = f"""
            You are a crisis intervention specialist. Assess this journal entry for crisis indicators.

            CRISIS LEVELS:
            1 = No crisis indicators - normal emotional expression
            2 = Mild distress - monitoring recommended, no immediate action needed
            3 = Moderate concern - check-in recommended within 24-48 hours
            4 = High risk - immediate intervention needed, contact crisis services
            5 = Imminent danger - emergency response required immediately

            LOOK FOR:
            - Suicidal ideation (thoughts of death, wanting to die)
            - Self-harm indicators (cutting, burning, other self-injury)
            - Hopelessness and helplessness
            - Social withdrawal and isolation
            - Substance abuse escalation
            - Psychotic symptoms
            - Plans, means, or timeline for self-harm
            - Giving away possessions or saying goodbye

            Journal Entry: "{state['normalized_entry']}"

            Provide assessment in this EXACT JSON format:
            {{
                "level": 1-5,
                "indicators": ["list of specific crisis indicators found, or empty list if none"],
                "reasoning": "Brief explanation of the assessment",
                "immediate_action_needed": true/false,
                "recommended_resources": ["list of appropriate resources based on level"]
            }}

            CRITICAL: Respond ONLY with valid JSON. Be thorough but not overly cautious.
            """
            
            response = await self.model.generate_content_async(crisis_prompt)
            crisis_text = response.text.strip()
            
            # Clean JSON response
            if crisis_text.startswith('```json'):
                crisis_text = crisis_text.replace('```json', '').replace('```', '').strip()
            
            crisis_data = json.loads(crisis_text)
            
            state['crisis_assessment'] = crisis_data
            
            # Log crisis situations
            if crisis_data['level'] >= 3:
                logger.warning(f"Crisis level {crisis_data['level']} detected for user {state['user_id']}: {crisis_data['reasoning']}")
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in crisis assessment: {e}")
            # Fallback to basic keyword detection
            state['crisis_assessment'] = self._fallback_crisis_detection(state)
        except Exception as e:
            logger.error(f"Crisis assessment failed: {e}")
            state['crisis_assessment'] = self._fallback_crisis_detection(state)
        
        return state
    
    def _fallback_crisis_detection(self, state: JournalState) -> Dict[str, Any]:
        """Fallback keyword-based crisis detection"""
        crisis_keywords = [
            'suicide', 'kill myself', 'end it all', 'want to die', 
            'hurt myself', 'self harm', 'cut myself', 'overdose',
            'no point living', 'better off dead', 'end my life'
        ]
        
        text_to_check = f"{state['raw_entry']} {state['normalized_entry']}".lower()
        crisis_detected = any(keyword in text_to_check for keyword in crisis_keywords)
        
        if crisis_detected:
            return {
                "level": 4,
                "indicators": ["Crisis keywords detected"],
                "reasoning": "Keyword-based detection triggered",
                "immediate_action_needed": True,
                "recommended_resources": ["988 Suicide & Crisis Lifeline", "Crisis Text Line", "Emergency Services"]
            }
        else:
            return {
                "level": 1,
                "indicators": [],
                "reasoning": "No crisis indicators detected",
                "immediate_action_needed": False,
                "recommended_resources": []
            }
    
    async def _generate_embedding(self, state: JournalState) -> JournalState:
        """Generate embedding using Hugging Face API"""
        try:
            if not settings.HF_API_KEY:
                logger.warning("HF_API_KEY not configured, skipping embedding")
                state['embedding_vector'] = None
                return state
            
            # Prepare text for embedding
            embedding_text = f"{state['normalized_entry']} {state['emotions']['primary']} {' '.join(state['patterns'])}"
            
            # Call Hugging Face API
            headers = {"Authorization": f"Bearer {settings.HF_API_KEY}"}
            api_url = "https://api-inference.huggingface.co/pipeline/feature-extraction/sentence-transformers/all-mpnet-base-v2"
            
            response = requests.post(
                api_url,
                headers=headers,
                json={"inputs": embedding_text}
            )
            
            if response.status_code == 200:
                state['embedding_vector'] = response.json()
                logger.info(f"Embedding generated for user {state['user_id']}")
            else:
                logger.error(f"Embedding API failed: {response.status_code}")
                state['embedding_vector'] = None
            
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            state['embedding_vector'] = None
        
        return state
    
    async def _store_entry(self, state: JournalState) -> JournalState:
        """Store encrypted journal entry in Supabase"""
        try:
            # Generate entry ID
            entry_id = str(uuid.uuid4())
            state['entry_id'] = entry_id
            
            # Encrypt sensitive data
            encrypted_raw = self.fernet.encrypt(state['raw_entry'].encode()).decode()
            encrypted_normalized = self.fernet.encrypt(state['normalized_entry'].encode()).decode()
            encrypted_insight = self.fernet.encrypt(state['therapeutic_insight'].encode()).decode()
            
            # Prepare data for storage
            entry_data = {
                "entry_id": entry_id,
                "user_id": state['user_id'],
                "timestamp": datetime.utcnow().isoformat(),
                "encrypted_raw_text": encrypted_raw,
                "encrypted_normalized_text": encrypted_normalized,
                "encrypted_insights": encrypted_insight,  # Single insight now
                "emotions": state['emotions'],
                "patterns": state['patterns'],
                "crisis_detected": state['crisis_assessment']['level'] >= 3,  # Level 3+ is crisis
                "embedding_vector": state['embedding_vector'],
                "metadata": {
                    "agent_version": "2.0.0",  # Updated version
                    "processing_timestamp": datetime.utcnow().isoformat(),
                    "crisis_level": state['crisis_assessment']['level'],
                    "emotion_framework": "ekman_6_emotions"
                }
            }
            
            # Store in Supabase
            await supabase_client.create_journal_entry(entry_data)
            logger.info(f"Journal entry stored: {entry_id}")
            
        except Exception as e:
            logger.error(f"Storage failed: {e}")
            state['error'] = f"Storage failed: {str(e)}"
        
        return state
    
    async def process_journal_entry(self, raw_entry: str, user_id: str) -> Dict[str, Any]:
        """
        Process a journal entry through the complete enhanced workflow
        
        Args:
            raw_entry: Raw journal text
            user_id: User ID
            
        Returns:
            Processing results with enhanced crisis assessment and unified insights
        """
        try:
            # Initialize state
            initial_state: JournalState = {
                "raw_entry": raw_entry,
                "user_id": user_id,
                "normalized_entry": None,
                "emotions": None,
                "patterns": None,
                "therapeutic_insight": None,
                "crisis_assessment": None,
                "embedding_vector": None,
                "entry_id": None,
                "error": None
            }
            
            # Run the workflow
            final_state = await self.workflow.ainvoke(initial_state)
            
            if final_state.get('error'):
                raise ValueError(final_state['error'])
            
            # Return processed results
            return {
                "entry_id": final_state['entry_id'],
                "user_id": user_id,
                "timestamp": datetime.utcnow().isoformat(),
                "normalized_journal": final_state['normalized_entry'],
                "emotions": final_state['emotions'],
                "patterns": final_state['patterns'],
                "therapeutic_insight": final_state['therapeutic_insight'],  # Single unified insight
                "crisis_assessment": final_state['crisis_assessment'],  # Enhanced crisis data
                "embedding_ready": final_state['embedding_vector'] is not None
            }
            
        except Exception as e:
            logger.error(f"Journal processing failed for user {user_id}: {e}")
            raise ValueError(f"Processing failed: {str(e)}")

# Global agent instance
journaling_agent = JournalingAgent()
