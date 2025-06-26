import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import json
from supabase import create_client, Client
from cryptography.fernet import Fernet
from config import settings

logger = logging.getLogger(__name__)

class SupabaseClient:
    """Supabase client with encryption for journal data"""
    
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
        
        logger.info("Supabase client initialized with encryption")
    
    def encrypt_text(self, text: str) -> str:
        """Encrypt sensitive text using Fernet"""
        return self.fernet.encrypt(text.encode()).decode()
    
    def decrypt_text(self, encrypted_text: str) -> str:
        """Decrypt encrypted text"""
        return self.fernet.decrypt(encrypted_text.encode()).decode()
    
    async def create_journal_entry(self, entry_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new journal entry with encryption"""
        try:
            encrypted_entry = {
                "id": entry_data["entry_id"],
                "user_id": entry_data["user_id"],
                "created_at": entry_data["timestamp"],
                "encrypted_raw_text": entry_data["encrypted_raw_text"],
                "encrypted_normalized_text": entry_data["encrypted_normalized_text"],
                "encrypted_insights": entry_data["encrypted_insights"],
                "emotions": json.dumps(entry_data["emotions"]),
                "patterns": json.dumps(entry_data["patterns"]),
                "crisis_detected": entry_data["crisis_detected"],
                "embedding_vector": entry_data.get("embedding_vector"),
                "tags": json.dumps(entry_data.get("tags", [])),
                "metadata": json.dumps(entry_data.get("metadata", {}))
            }
            
            result = self.client.table("journal_entries").insert(encrypted_entry).execute()
            
            if result.data:
                logger.info(f"Journal entry created: {entry_data['entry_id']}")
                return result.data[0]
            else:
                raise Exception("Failed to create journal entry")
                
        except Exception as e:
            logger.error(f"Failed to create journal entry: {e}")
            raise
    
    async def get_journal_entries(self, user_id: str, limit: int = 10, offset: int = 0) -> Dict[str, Any]:
        """Get journal entries for a user with pagination"""
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
            
            # Decrypt sensitive data
            decrypted_entries = []
            for entry in result.data:
                decrypted_entry = {
                    "entry_id": entry["id"],
                    "user_id": entry["user_id"],
                    "timestamp": entry["created_at"],
                    "normalized_journal": self.decrypt_text(entry["encrypted_normalized_text"]),
                    "emotions": json.loads(entry["emotions"]),
                    "patterns": json.loads(entry["patterns"]),
                    "therapeutic_insights": json.loads(self.decrypt_text(entry["encrypted_insights"])),
                    "crisis_detected": entry["crisis_detected"],
                    "tags": json.loads(entry.get("tags", "[]")),
                    "metadata": json.loads(entry.get("metadata", "{}"))
                }
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

# Global client instance
supabase_client = SupabaseClient() 