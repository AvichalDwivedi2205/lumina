import time
import hmac
import hashlib
import json
import uuid
from typing import Dict, Any, Optional
from urllib.parse import urlencode
import httpx
from fastapi import HTTPException
import structlog

from config import settings

logger = structlog.get_logger(__name__)

class ElevenLabsFriendAuthService:
    """
    Service for handling ElevenLabs authentication for AI Friend agents.
    Generates signed URLs for client-side use while keeping API keys server-side.
    """
    
    def __init__(self):
        self.api_key = settings.ELEVENLABS_FRIEND_API_KEY
        self.http_client = httpx.AsyncClient(timeout=30.0)
        
        # Friend agent ID mappings
        self.friend_agents = {
            'supportive': settings.ELEVENLABS_FRIEND_SUPPORTIVE_AGENT_ID,
            'motivator': settings.ELEVENLABS_FRIEND_MOTIVATOR_AGENT_ID,
            'mentor': settings.ELEVENLABS_FRIEND_MENTOR_AGENT_ID,
            'funny': settings.ELEVENLABS_FRIEND_FUNNY_AGENT_ID,
            'mindful': settings.ELEVENLABS_FRIEND_UNHINGED_AGENT_ID
        }
    
    async def generate_signed_url(
        self, 
        agent_id: str,
        user_id: str,
        conversation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a secure signed URL for friend agent access.
        
        Args:
            agent_id: ElevenLabs agent identifier
            user_id: User identifier
            conversation_id: Optional conversation identifier
            
        Returns:
            Dict containing signed URL and configuration
        """
        try:
            if not self.api_key:
                raise ValueError("ELEVENLABS_FRIEND_API_KEY not configured")
            
            if not agent_id:
                raise ValueError("Agent ID is required")
            
            # Generate conversation ID if not provided
            if not conversation_id:
                conversation_id = str(uuid.uuid4())
            
            # Generate signed URL
            signed_data = await self._generate_signed_url(
                api_key=self.api_key,
                agent_id=agent_id,
                user_id=user_id,
                conversation_id=conversation_id
            )
            
            logger.info(f"Generated friend agent URL for agent {agent_id}")
            
            return {
                'success': True,
                'signed_url': signed_data['url'],
                'conversation_id': conversation_id,
                'expires_at': signed_data['expires_at']
            }
            
        except Exception as e:
            logger.error(f"Failed to generate friend agent URL: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _generate_signed_url(
        self,
        api_key: str,
        agent_id: str,
        user_id: str,
        conversation_id: str
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
                'conversation_id': conversation_id,
                'timestamp': timestamp,
                'expires_at': expires_at
            }
            
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
                'conversation_id': conversation_id,
                'timestamp': timestamp,
                'expires_at': expires_at,
                'signature': signature
            }
            
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
    
    async def get_agent_status(self, agent_id: str) -> Dict[str, Any]:
        """
        Check the status of an ElevenLabs friend agent.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            Agent status information
        """
        try:
            headers = {
                'xi-api-key': self.api_key,
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
                logger.warning(f"Friend agent status check failed: {response.status_code}")
                return {
                    'success': False,
                    'agent_id': agent_id,
                    'status': 'unknown',
                    'error': f"HTTP {response.status_code}"
                }
                
        except Exception as e:
            logger.error(f"Failed to check friend agent status: {e}")
            return {
                'success': False,
                'agent_id': agent_id,
                'status': 'error',
                'error': str(e)
            }
    
    async def get_all_agent_statuses(self) -> Dict[str, Any]:
        """
        Get status of all configured friend agents.
        
        Returns:
            Dict containing status of all friend agents
        """
        statuses = {}
        
        # Check friend agents
        for personality_type, agent_id in self.friend_agents.items():
            if agent_id:
                status = await self.get_agent_status(agent_id)
                statuses[personality_type] = status
        
        return statuses
    
    def get_available_agents(self) -> Dict[str, Any]:
        """
        Get list of available friend agents and their configurations.
        
        Returns:
            Dict containing available friend agents
        """
        return {
            personality_type: {
                'agent_id': agent_id,
                'configured': bool(agent_id),
                'api_key_configured': bool(self.api_key)
            }
            for personality_type, agent_id in self.friend_agents.items()
        }
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.http_client.aclose()

# Global instance
elevenlabs_friend_auth = ElevenLabsFriendAuthService() 