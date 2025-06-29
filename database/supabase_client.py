import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import json
from supabase import create_client, Client
from cryptography.fernet import Fernet
from config import settings
import uuid

logger = logging.getLogger(__name__)

class SupabaseClient:
    """Enhanced Supabase client with encryption for journal data"""
    
    def __init__(self):
        if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_KEY:
            raise ValueError("Supabase configuration missing")
        
        self.client: Client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_KEY
        )
        
        # Initialize encryption
        if not settings.FERNET_KEY:
            raise ValueError("FERNET_KEY required for encryption")
        self.fernet = Fernet(settings.FERNET_KEY.encode())
        
        logger.info("Enhanced Supabase client initialized with encryption")
    
    @property
    def table(self):
        """Expose the underlying Supabase client's table method"""
        return self.client.table
    
    def encrypt_text(self, text: str) -> str:
        """Encrypt sensitive text using Fernet"""
        return self.fernet.encrypt(text.encode()).decode()
    
    def decrypt_text(self, encrypted_text: str) -> str:
        """Decrypt encrypted text"""
        return self.fernet.decrypt(encrypted_text.encode()).decode()
    
    async def create_journal_entry(self, entry_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new journal entry with enhanced crisis assessment"""
        try:
            # Handle both legacy and new crisis data formats
            crisis_level = 1
            crisis_indicators = []
            crisis_reasoning = None
            
            if "crisis_assessment" in entry_data:
                # New enhanced format
                crisis_assessment = entry_data["crisis_assessment"]
                crisis_level = crisis_assessment.get("level", 1)
                crisis_indicators = crisis_assessment.get("indicators", [])
                crisis_reasoning = crisis_assessment.get("reasoning")
            elif entry_data.get("crisis_detected", False):
                # Legacy format - assume high risk if detected
                crisis_level = 4
                crisis_indicators = ["Legacy detection"]
                crisis_reasoning = "Detected via legacy keyword matching"
            
            encrypted_entry = {
                "entry_id": entry_data["entry_id"],
                "user_id": entry_data["user_id"],
                "created_at": entry_data["timestamp"],
                "encrypted_raw_text": entry_data["encrypted_raw_text"],
                "encrypted_normalized_text": entry_data["encrypted_normalized_text"],
                "encrypted_insights": entry_data["encrypted_insights"],
                "emotions": json.dumps(entry_data["emotions"]),
                "patterns": json.dumps(entry_data["patterns"]),
                "crisis_detected": entry_data.get("crisis_detected", crisis_level >= 3),
                "crisis_level": crisis_level,
                "crisis_indicators": json.dumps(crisis_indicators),
                "crisis_reasoning": crisis_reasoning,
                "embedding_vector": entry_data.get("embedding_vector"),
                "tags": json.dumps(entry_data.get("tags", [])),
                "metadata": json.dumps(entry_data.get("metadata", {}))
            }
            
            result = self.client.table("journal_entries").insert(encrypted_entry).execute()
            
            if result.data:
                logger.info(f"Enhanced journal entry created: {entry_data['entry_id']} (Crisis Level: {crisis_level})")
                return result.data[0]
            else:
                raise Exception("Failed to create journal entry")
                
        except Exception as e:
            logger.error(f"Failed to create journal entry: {e}")
            raise
    
    async def get_journal_entries(self, user_id: str, limit: int = 10, offset: int = 0) -> Dict[str, Any]:
        """Get journal entries for a user with pagination and enhanced data"""
        try:
            # Get total count
            count_result = self.client.table("journal_entries")\
                .select("*", count="exact")\
                .eq("user_id", user_id)\
                .execute()
            
            total_count = count_result.count
            
            # Get entries with pagination
            result = self.client.table("journal_entries")\
                .select("*")\
                .eq("user_id", user_id)\
                .order("created_at", desc=True)\
                .limit(limit)\
                .offset(offset)\
                .execute()
            
            # Decrypt and format entries
            decrypted_entries = []
            for entry in result.data:
                # Handle both legacy and new data formats
                decrypted_insights = self.decrypt_text(entry["encrypted_insights"])
                
                # Parse insights - could be legacy JSON or new unified string
                try:
                    parsed_insights = json.loads(decrypted_insights)
                    if isinstance(parsed_insights, dict):
                        # Legacy format - keep as is for backward compatibility
                        therapeutic_insights = parsed_insights
                        therapeutic_insight = None
                    else:
                        # Shouldn't happen, but handle gracefully
                        therapeutic_insight = str(parsed_insights)
                        therapeutic_insights = None
                except (json.JSONDecodeError, TypeError):
                    # New unified format - single string insight
                    therapeutic_insight = decrypted_insights
                    therapeutic_insights = None
                
                # Handle crisis assessment
                crisis_assessment = None
                if entry.get("crisis_level") is not None:
                    # New enhanced format - handle None values properly
                    crisis_reasoning = entry.get("crisis_reasoning")
                    if crisis_reasoning is None:
                        crisis_reasoning = "Legacy entry - no detailed reasoning available"
                    
                    crisis_assessment = {
                        "level": entry["crisis_level"],
                        "indicators": json.loads(entry.get("crisis_indicators", "[]")),
                        "reasoning": crisis_reasoning,
                        "immediate_action_needed": entry["crisis_level"] >= 4,
                        "recommended_resources": self._get_crisis_resources_for_level(entry["crisis_level"])
                    }
                
                decrypted_entry = {
                    "entry_id": entry.get("entry_id", entry["id"]),  # Handle legacy entries
                    "user_id": entry["user_id"],
                    "timestamp": entry["created_at"],
                    "normalized_journal": self.decrypt_text(entry["encrypted_normalized_text"]),
                    "emotions": json.loads(entry["emotions"]),
                    "patterns": json.loads(entry["patterns"]),
                    "crisis_detected": entry["crisis_detected"],
                    "tags": json.loads(entry.get("tags", "[]")),
                    "metadata": json.loads(entry.get("metadata", "{}"))
                }
                
                # Add format-specific fields
                if therapeutic_insight:
                    decrypted_entry["therapeutic_insight"] = therapeutic_insight
                if therapeutic_insights:
                    decrypted_entry["therapeutic_insights"] = therapeutic_insights
                if crisis_assessment:
                    decrypted_entry["crisis_assessment"] = crisis_assessment
                
                decrypted_entries.append(decrypted_entry)
            
            return {
                "entries": decrypted_entries,
                "total_count": total_count,
                "has_next": offset + limit < total_count,
                "has_previous": offset > 0
            }
            
        except Exception as e:
            logger.error(f"Failed to get journal entries: {e}")
            raise
    
    def _get_crisis_resources_for_level(self, crisis_level: int) -> List[str]:
        """Get appropriate crisis resources based on level"""
        if crisis_level >= 5:
            return ["911 Emergency Services", "988 Suicide & Crisis Lifeline", "Crisis Text Line"]
        elif crisis_level >= 4:
            return ["988 Suicide & Crisis Lifeline", "Crisis Text Line", "Emergency Services"]
        elif crisis_level >= 3:
            return ["988 Suicide & Crisis Lifeline", "Crisis Text Line"]
        else:
            return []
    
    async def get_crisis_entries(self, user_id: str, days: int = 30) -> List[Dict[str, Any]]:
        """Get crisis entries for a user within specified days"""
        try:
            from datetime import datetime, timedelta
            
            cutoff_date = (datetime.utcnow() - timedelta(days=days)).isoformat()
            
            result = self.client.table("journal_entries")\
                .select("entry_id, created_at, crisis_level, crisis_indicators, crisis_reasoning, emotions")\
                .eq("user_id", user_id)\
                .gte("crisis_level", 3)\
                .gte("created_at", cutoff_date)\
                .order("crisis_level", desc=True)\
                .order("created_at", desc=True)\
                .execute()
            
            crisis_entries = []
            for entry in result.data:
                crisis_entries.append({
                    "entry_id": entry["entry_id"],
                    "timestamp": entry["created_at"],
                    "crisis_level": entry["crisis_level"],
                    "crisis_indicators": json.loads(entry.get("crisis_indicators", "[]")),
                    "crisis_reasoning": entry.get("crisis_reasoning"),
                    "primary_emotion": json.loads(entry["emotions"]).get("primary")
                })
            
            return crisis_entries
            
        except Exception as e:
            logger.error(f"Failed to get crisis entries: {e}")
            raise
    
    async def get_emotion_trends(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Get emotion trends for a user over specified days"""
        try:
            from datetime import datetime, timedelta
            
            cutoff_date = (datetime.utcnow() - timedelta(days=days)).isoformat()
            
            result = self.client.table("journal_entries")\
                .select("created_at, emotions")\
                .eq("user_id", user_id)\
                .gte("created_at", cutoff_date)\
                .order("created_at", desc=True)\
                .execute()
            
            # Process emotion data
            emotion_data = []
            for entry in result.data:
                emotions = json.loads(entry["emotions"])
                emotion_entry = {
                    "date": entry["created_at"][:10],  # Extract date part
                    "primary": emotions.get("primary"),
                    **emotions.get("analysis", {})
                }
                emotion_data.append(emotion_entry)
            
            return {
                "period_days": days,
                "total_entries": len(emotion_data),
                "emotion_data": emotion_data
            }
            
        except Exception as e:
            logger.error(f"Failed to get emotion trends: {e}")
            raise

# Global client instance - lazy initialization to avoid import-time errors
_supabase_client = None

def get_supabase_client():
    """Get or create the global Supabase client instance"""
    global _supabase_client
    if _supabase_client is None:
        try:
            _supabase_client = SupabaseClient()
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            # Return a mock client for development/testing
            _supabase_client = MockSupabaseClient()
    return _supabase_client

class MockSupabaseClient:
    """Mock Supabase client for when real client fails to initialize"""
    
    def __init__(self):
        logger.warning("Using mock Supabase client - database operations will not work")
    
    @property
    def table(self):
        """Mock table method that returns a mock table"""
        return MockTable()
    
    def encrypt_text(self, text: str) -> str:
        return text  # No encryption in mock
    
    def decrypt_text(self, encrypted_text: str) -> str:
        return encrypted_text  # No decryption in mock
    
    async def create_journal_entry(self, entry_data: Dict[str, Any]) -> Dict[str, Any]:
        """Mock journal entry creation"""
        return {"id": "mock_entry_id", **entry_data}
    
    async def get_journal_entries(self, user_id: str, limit: int = 10, offset: int = 0) -> Dict[str, Any]:
        """Mock journal entries retrieval"""
        return {
            "entries": [],
            "total_count": 0,
            "has_next": False,
            "has_previous": False
        }

class MockTable:
    """Mock table for development/testing"""
    
    def __init__(self):
        self.table_name = "mock_table"
    
    def select(self, *args, **kwargs):
        return self
    
    def insert(self, data, **kwargs):
        # Return realistic mock data for inserts
        if isinstance(data, dict):
            return MockResult([{**data, "id": f"mock_{uuid.uuid4()}"}])
        elif isinstance(data, list):
            return MockResult([{**item, "id": f"mock_{uuid.uuid4()}"} for item in data])
        return MockResult([])
    
    def update(self, *args, **kwargs):
        return self
    
    def eq(self, *args, **kwargs):
        return self
    
    def gte(self, *args, **kwargs):
        return self
    
    def lte(self, *args, **kwargs):
        return self
    
    def order(self, *args, **kwargs):
        return self
    
    def limit(self, *args, **kwargs):
        return self
    
    def offset(self, *args, **kwargs):
        return self
    
    def execute(self):
        """Mock execute that returns realistic empty data"""
        return MockResult([])

class MockResult:
    """Mock result class"""
    
    def __init__(self, data=None):
        self.data = data or []
        self.count = len(self.data) if data else 0

# Create the global instance
supabase_client = get_supabase_client() 