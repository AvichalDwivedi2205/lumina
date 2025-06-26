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
    therapeutic_insights: Optional[Dict[str, str]]
    crisis_detected: Optional[bool]
    embedding_vector: Optional[List[float]]
    entry_id: Optional[str]
    error: Optional[str]

class JournalingAgent:
    """
    Advanced journaling agent using LangGraph workflow for therapeutic analysis.
    Implements CBT, DBT, and ACT insights with crisis detection.
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
        self.model = genai.GenerativeModel('gemini-2.5-pro')
        
        # Crisis keywords for basic detection
        self.crisis_keywords = [
            'suicide', 'kill myself', 'end it all', 'want to die', 
            'hurt myself', 'self harm', 'cut myself', 'overdose',
            'no point living', 'better off dead', 'end my life'
        ]
        
        # Build the workflow
        self.workflow = self._build_workflow()
        
        logger.info("Journaling agent initialized with LangGraph workflow")
    
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow for journal processing"""
        workflow = StateGraph(JournalState)
        
        # Add nodes
        workflow.add_node("normalize", self._normalize_entry)
        workflow.add_node("analyze", self._analyze_entry)
        workflow.add_node("detect_crisis", self._detect_crisis)
        workflow.add_node("generate_embedding", self._generate_embedding)
        workflow.add_node("store_entry", self._store_entry)
        
        # Define the flow
        workflow.set_entry_point("normalize")
        workflow.add_edge("normalize", "analyze")
        workflow.add_edge("analyze", "detect_crisis")
        workflow.add_edge("detect_crisis", "generate_embedding")
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
        """Perform multi-modal therapeutic analysis"""
        try:
            analysis_prompt = f"""
            You are a licensed mental health professional. Analyze this journal entry and provide structured therapeutic insights using CBT, DBT, and ACT approaches.

            Journal Entry: "{state['normalized_entry']}"

            Provide analysis in this EXACT JSON format:
            {{
                "emotions": {{
                    "primary": "specific primary emotion",
                    "secondary": ["emotion1", "emotion2"],
                    "analysis": {{
                        "anxiety": 0-10,
                        "depression": 0-10,
                        "anger": 0-10,
                        "joy": 0-10,
                        "fear": 0-10,
                        "sadness": 0-10
                    }}
                }},
                "patterns": [
                    "specific cognitive or behavioral pattern 1",
                    "specific cognitive or behavioral pattern 2"
                ],
                "therapeutic_insights": {{
                    "cbt": "Specific CBT insight with actionable technique - focus on thought challenging or behavioral activation",
                    "dbt": "Specific DBT insight with skill recommendation - focus on distress tolerance, emotion regulation, interpersonal effectiveness, or mindfulness",
                    "act": "Specific ACT insight with values-based guidance - focus on psychological flexibility, acceptance, or committed action"
                }}
            }}

            CRITICAL: Respond ONLY with valid JSON. Make insights specific and actionable.
            """
            
            response = await self.model.generate_content_async(analysis_prompt)
            analysis_text = response.text.strip()
            
            # Clean JSON response
            if analysis_text.startswith('```json'):
                analysis_text = analysis_text.replace('```json', '').replace('```', '').strip()
            
            analysis_data = json.loads(analysis_text)
            
            state['emotions'] = analysis_data['emotions']
            state['patterns'] = analysis_data['patterns']
            state['therapeutic_insights'] = analysis_data['therapeutic_insights']
            
            logger.info(f"Analysis completed for user {state['user_id']}")
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in analysis: {e}")
            state['error'] = "Analysis failed - invalid response format"
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            state['error'] = f"Analysis failed: {str(e)}"
        
        return state
    
    async def _detect_crisis(self, state: JournalState) -> JournalState:
        """Basic crisis detection using keyword matching"""
        try:
            text_to_check = f"{state['raw_entry']} {state['normalized_entry']}".lower()
            
            crisis_detected = any(keyword in text_to_check for keyword in self.crisis_keywords)
            state['crisis_detected'] = crisis_detected
            
            if crisis_detected:
                logger.warning(f"Crisis indicators detected for user {state['user_id']}")
                # TODO: Implement crisis intervention protocols
            
        except Exception as e:
            logger.error(f"Crisis detection failed: {e}")
            state['crisis_detected'] = False
        
        return state
    
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
            encrypted_insights = self.fernet.encrypt(json.dumps(state['therapeutic_insights']).encode()).decode()
            
            # Prepare data for storage
            entry_data = {
                "entry_id": entry_id,
                "user_id": state['user_id'],
                "timestamp": datetime.utcnow().isoformat(),
                "encrypted_raw_text": encrypted_raw,
                "encrypted_normalized_text": encrypted_normalized,
                "encrypted_insights": encrypted_insights,
                "emotions": state['emotions'],
                "patterns": state['patterns'],
                "crisis_detected": state['crisis_detected'],
                "embedding_vector": state['embedding_vector'],
                "metadata": {
                    "agent_version": "1.0.0",
                    "processing_timestamp": datetime.utcnow().isoformat()
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
        Process a journal entry through the complete workflow
        
        Args:
            raw_entry: Raw journal text
            user_id: User ID
            
        Returns:
            Processing results
        """
        try:
            # Initialize state
            initial_state: JournalState = {
                "raw_entry": raw_entry,
                "user_id": user_id,
                "normalized_entry": None,
                "emotions": None,
                "patterns": None,
                "therapeutic_insights": None,
                "crisis_detected": None,
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
                "therapeutic_insights": final_state['therapeutic_insights'],
                "crisis_detected": final_state['crisis_detected'],
                "embedding_ready": final_state['embedding_vector'] is not None
            }
            
        except Exception as e:
            logger.error(f"Journal processing failed for user {user_id}: {e}")
            raise ValueError(f"Processing failed: {str(e)}")

# Global agent instance
journaling_agent = JournalingAgent() 