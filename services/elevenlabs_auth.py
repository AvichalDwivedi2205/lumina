import time
import hmac
import hashlib
import json
from typing import Dict, Any, Optional
from urllib.parse import urlencode
import httpx
from fastapi import HTTPException
import structlog

from config import settings

logger = structlog.get_logger(__name__)

class ElevenLabsAuthService:
    """
    Service for handling ElevenLabs authentication and secure agent access.
    Generates signed URLs for client-side use while keeping API keys server-side.
    """
    
    def __init__(self):
        self.therapy_api_key = settings.ELEVENLABS_THERAPY_API_KEY
        self.exercise_api_key = settings.ELEVENLABS_EXERCISE_API_KEY
        self.http_client = httpx.AsyncClient(timeout=30.0)
        
        # Agent ID mappings
        self.therapy_agents = {
            'male': settings.ELEVENLABS_MALE_THERAPIST_AGENT_ID,
            'female': settings.ELEVENLABS_FEMALE_THERAPIST_AGENT_ID
        }
        
        self.exercise_agents = {
            'mindfulness': settings.ELEVENLABS_MINDFULNESS_AGENT_ID,
            'cbt_tools': settings.ELEVENLABS_CBT_AGENT_ID,
            'behavioral_activation': settings.ELEVENLABS_BEHAVIORAL_AGENT_ID,
            'self_compassion': settings.ELEVENLABS_COMPASSION_AGENT_ID
        }
    
    async def get_therapy_agent_url(
        self, 
        therapist_type: str, 
        user_id: str, 
        session_id: str,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate a secure signed URL for therapy agent access.
        
        Args:
            therapist_type: 'male' or 'female'
            user_id: User identifier
            session_id: Therapy session identifier
            additional_context: Optional context for the agent
            
        Returns:
            Dict containing signed URL and configuration
        """
        try:
            if therapist_type not in self.therapy_agents:
                raise ValueError(f"Invalid therapist type: {therapist_type}")
            
            agent_id = self.therapy_agents[therapist_type]
            if not agent_id:
                raise ValueError(f"No agent ID configured for {therapist_type} therapist")
            
            # Generate signed URL using therapy API key
            signed_data = await self._generate_signed_url(
                api_key=self.therapy_api_key,
                agent_id=agent_id,
                user_id=user_id,
                session_id=session_id,
                agent_type='therapy',
                additional_context=additional_context
            )
            
            logger.info(f"Generated therapy agent URL for {therapist_type} therapist, session {session_id}")
            
            return {
                'success': True,
                'agent_url': signed_data['url'],
                'expires_at': signed_data['expires_at'],
                'agent_config': {
                    'agent_id': agent_id,
                    'therapist_type': therapist_type,
                    'session_duration': settings.THERAPY_SESSION_DURATION,
                    'crisis_detection_enabled': settings.CRISIS_DETECTION_ENABLED
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to generate therapy agent URL: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def get_exercise_agent_url(
        self, 
        exercise_type: str, 
        user_id: str, 
        exercise_id: str,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate a secure signed URL for exercise agent access.
        
        Args:
            exercise_type: Type of mental exercise
            user_id: User identifier
            exercise_id: Exercise session identifier
            additional_context: Optional context for the agent
            
        Returns:
            Dict containing signed URL and configuration
        """
        try:
            if exercise_type not in self.exercise_agents:
                raise ValueError(f"Invalid exercise type: {exercise_type}")
            
            agent_id = self.exercise_agents[exercise_type]
            if not agent_id:
                raise ValueError(f"No agent ID configured for {exercise_type} exercise")
            
            # Generate signed URL using exercise API key
            signed_data = await self._generate_signed_url(
                api_key=self.exercise_api_key,
                agent_id=agent_id,
                user_id=user_id,
                session_id=exercise_id,
                agent_type='exercise',
                additional_context=additional_context
            )
            
            logger.info(f"Generated exercise agent URL for {exercise_type}, exercise {exercise_id}")
            
            return {
                'success': True,
                'agent_url': signed_data['url'],
                'expires_at': signed_data['expires_at'],
                'agent_config': {
                    'agent_id': agent_id,
                    'exercise_type': exercise_type,
                    'session_duration': settings.EXERCISE_SESSION_DURATION
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to generate exercise agent URL: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _generate_signed_url(
        self,
        api_key: str,
        agent_id: str,
        user_id: str,
        session_id: str,
        agent_type: str,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate a signed URL for ElevenLabs agent access.
        This implements the ElevenLabs authentication flow.
        """
        try:
            # Current timestamp
            timestamp = int(time.time())
            # URL expires in 15 minutes (ElevenLabs standard)
            expires_at = timestamp + (15 * 60)
            
            # Prepare the payload for signing
            payload = {
                'agent_id': agent_id,
                'user_id': user_id,
                'session_id': session_id,
                'agent_type': agent_type,
                'timestamp': timestamp,
                'expires_at': expires_at
            }
            
            if additional_context:
                payload['context'] = additional_context
            
            # Create signature using HMAC-SHA256
            payload_string = json.dumps(payload, sort_keys=True)
            signature = hmac.new(
                api_key.encode('utf-8'),
                payload_string.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            # Prepare query parameters
            query_params = {
                'agent_id': agent_id,
                'user_id': user_id,
                'session_id': session_id,
                'timestamp': timestamp,
                'expires_at': expires_at,
                'signature': signature
            }
            
            # Add context if provided
            if additional_context:
                query_params['context'] = json.dumps(additional_context)
            
            # Build the signed URL
            base_url = "wss://api.elevenlabs.io/v1/convai/conversation"
            signed_url = f"{base_url}?{urlencode(query_params)}"
            
            return {
                'url': signed_url,
                'expires_at': expires_at,
                'signature': signature
            }
            
        except Exception as e:
            logger.error(f"Failed to generate signed URL: {e}")
            raise
    
    async def verify_webhook_signature(self, request_body: bytes, signature: str, api_key: str) -> bool:
        """
        Verify webhook signature from ElevenLabs.
        
        Args:
            request_body: Raw request body bytes
            signature: Signature from webhook headers
            api_key: API key to verify against
            
        Returns:
            True if signature is valid, False otherwise
        """
        try:
            # Generate expected signature
            expected_signature = hmac.new(
                api_key.encode('utf-8'),
                request_body,
                hashlib.sha256
            ).hexdigest()
            
            # Compare signatures securely
            return hmac.compare_digest(signature, expected_signature)
            
        except Exception as e:
            logger.error(f"Webhook signature verification failed: {e}")
            return False
    
    async def get_agent_status(self, agent_id: str, api_key: str) -> Dict[str, Any]:
        """
        Check the status of an ElevenLabs agent.
        
        Args:
            agent_id: Agent identifier
            api_key: API key for authentication
            
        Returns:
            Agent status information
        """
        try:
            headers = {
                'xi-api-key': api_key,
                'Content-Type': 'application/json'
            }
            
            response = await self.http_client.get(
                f"https://api.elevenlabs.io/v1/convai/agents/{agent_id}",
                headers=headers
            )
            
            if response.status_code == 200:
                agent_data = response.json()
                return {
                    'success': True,
                    'agent_id': agent_id,
                    'status': 'active',
                    'name': agent_data.get('name', 'Unknown'),
                    'config': agent_data.get('config', {})
                }
            else:
                logger.warning(f"Agent status check failed: {response.status_code}")
                return {
                    'success': False,
                    'agent_id': agent_id,
                    'status': 'unknown',
                    'error': f"HTTP {response.status_code}"
                }
                
        except Exception as e:
            logger.error(f"Failed to check agent status: {e}")
            return {
                'success': False,
                'agent_id': agent_id,
                'status': 'error',
                'error': str(e)
            }
    
    async def get_all_agent_statuses(self) -> Dict[str, Any]:
        """
        Get status of all configured agents.
        
        Returns:
            Dict containing status of all therapy and exercise agents
        """
        statuses = {
            'therapy_agents': {},
            'exercise_agents': {}
        }
        
        # Check therapy agents
        for therapist_type, agent_id in self.therapy_agents.items():
            if agent_id:
                status = await self.get_agent_status(agent_id, self.therapy_api_key)
                statuses['therapy_agents'][therapist_type] = status
        
        # Check exercise agents
        for exercise_type, agent_id in self.exercise_agents.items():
            if agent_id:
                status = await self.get_agent_status(agent_id, self.exercise_api_key)
                statuses['exercise_agents'][exercise_type] = status
        
        return statuses
    
    def get_available_agents(self) -> Dict[str, Any]:
        """
        Get list of available agents and their configurations.
        
        Returns:
            Dict containing available therapy and exercise agents
        """
        return {
            'therapy_agents': {
                therapist_type: {
                    'agent_id': agent_id,
                    'configured': bool(agent_id),
                    'api_key_configured': bool(self.therapy_api_key)
                }
                for therapist_type, agent_id in self.therapy_agents.items()
            },
            'exercise_agents': {
                exercise_type: {
                    'agent_id': agent_id,
                    'configured': bool(agent_id),
                    'api_key_configured': bool(self.exercise_api_key)
                }
                for exercise_type, agent_id in self.exercise_agents.items()
            }
        }
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.http_client.aclose()

# Global instance
elevenlabs_auth = ElevenLabsAuthService() 