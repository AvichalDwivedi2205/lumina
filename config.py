import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Settings:
    """Application settings"""
    
    # App Configuration
    APP_NAME: str = os.getenv("APP_NAME", "Lumina Agent")
    APP_VERSION: str = os.getenv("APP_VERSION", "1.0.0")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", 8000))
    
    # WorkOS Configuration
    WORKOS_API_KEY: str = os.getenv("WORKOS_API_KEY", "")
    WORKOS_CLIENT_ID: str = os.getenv("WORKOS_CLIENT_ID", "")
    WORKOS_REDIRECT_URI: str = os.getenv("WORKOS_REDIRECT_URI", "http://localhost:8000/auth/callback")
    
    # Supabase Configuration (for future use)
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_ANON_KEY: str = os.getenv("SUPABASE_ANON_KEY", "")
    SUPABASE_SERVICE_KEY: str = os.getenv("SUPABASE_SERVICE_KEY", "")
    
    # Security
    FERNET_KEY: str = os.getenv("FERNET_KEY", "")
    
    # AI Configuration
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    HF_API_KEY: str = os.getenv("HF_API_KEY", "")
    
    # ElevenLabs Configuration (Separate accounts)
    ELEVENLABS_THERAPY_API_KEY: str = os.getenv("ELEVENLABS_THERAPY_API_KEY", "")  # For therapy agents
    ELEVENLABS_EXERCISE_API_KEY: str = os.getenv("ELEVENLABS_EXERCISE_API_KEY", "")  # For exercise agents
    ELEVENLABS_MALE_THERAPIST_AGENT_ID: str = os.getenv("ELEVENLABS_MALE_THERAPIST_AGENT_ID", "")
    ELEVENLABS_FEMALE_THERAPIST_AGENT_ID: str = os.getenv("ELEVENLABS_FEMALE_THERAPIST_AGENT_ID", "")
    ELEVENLABS_MINDFULNESS_AGENT_ID: str = os.getenv("ELEVENLABS_MINDFULNESS_AGENT_ID", "")
    ELEVENLABS_CBT_AGENT_ID: str = os.getenv("ELEVENLABS_CBT_AGENT_ID", "")
    ELEVENLABS_BEHAVIORAL_AGENT_ID: str = os.getenv("ELEVENLABS_BEHAVIORAL_AGENT_ID", "")
    ELEVENLABS_COMPASSION_AGENT_ID: str = os.getenv("ELEVENLABS_COMPASSION_AGENT_ID", "")
    
    # AI Friend Agents (Separate Account)
    ELEVENLABS_FRIEND_API_KEY: str = os.getenv("ELEVENLABS_FRIEND_API_KEY", "")
    ELEVENLABS_FRIEND_SUPPORTIVE_AGENT_ID: str = os.getenv("ELEVENLABS_FRIEND_SUPPORTIVE_AGENT_ID", "")
    ELEVENLABS_FRIEND_MOTIVATOR_AGENT_ID: str = os.getenv("ELEVENLABS_FRIEND_MOTIVATOR_AGENT_ID", "")
    ELEVENLABS_FRIEND_MENTOR_AGENT_ID: str = os.getenv("ELEVENLABS_FRIEND_MENTOR_AGENT_ID", "")
    ELEVENLABS_FRIEND_FUNNY_AGENT_ID: str = os.getenv("ELEVENLABS_FRIEND_FUNNY_AGENT_ID", "")
    ELEVENLABS_FRIEND_UNHINGED_AGENT_ID: str = os.getenv("ELEVENLABS_FRIEND_UNHINGED_AGENT_ID", "")
    
    # Nutrition APIs
    USDA_API_KEY: str = os.getenv("USDA_API_KEY", "")
    
    # Tavus Configuration
    TAVUS_API_KEY: str = os.getenv("TAVUS_API_KEY", "")
    TAVUS_MALE_THERAPIST_PERSONA_ID: str = os.getenv("TAVUS_MALE_THERAPIST_PERSONA_ID", "")
    TAVUS_FEMALE_THERAPIST_PERSONA_ID: str = os.getenv("TAVUS_FEMALE_THERAPIST_PERSONA_ID", "")
    
    # Base URL for Gemini service (already configured)
    BASE_URL: str = os.getenv("BASE_URL", "https://a8d4-49-37-27-19.ngrok-free.app")
    
    # Session Durations
    THERAPY_SESSION_DURATION: int = int(os.getenv("THERAPY_SESSION_DURATION", 2700))  # 45 minutes
    EXERCISE_SESSION_DURATION: int = int(os.getenv("EXERCISE_SESSION_DURATION", 600))  # 10 minutes
    
    # Feature Flags
    CRISIS_DETECTION_ENABLED: bool = os.getenv("CRISIS_DETECTION_ENABLED", "true").lower() == "true"
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    @property
    def is_workos_configured(self) -> bool:
        """Check if WorkOS is properly configured"""
        return bool(self.WORKOS_API_KEY and self.WORKOS_CLIENT_ID)
    
    @property
    def is_elevenlabs_configured(self) -> bool:
        """Check if ElevenLabs is properly configured"""
        return bool(self.ELEVENLABS_THERAPY_API_KEY or self.ELEVENLABS_EXERCISE_API_KEY)
    
    @property
    def is_tavus_configured(self) -> bool:
        """Check if Tavus is properly configured"""
        return bool(self.TAVUS_API_KEY)
    
    def validate_required_settings(self):
        """Validate that required settings are present"""
        required_settings = [
            ("WORKOS_API_KEY", self.WORKOS_API_KEY),
            ("WORKOS_CLIENT_ID", self.WORKOS_CLIENT_ID),
        ]
        
        missing = [name for name, value in required_settings if not value]
        
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

# Global settings instance
settings = Settings() 