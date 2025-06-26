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
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    @property
    def is_workos_configured(self) -> bool:
        """Check if WorkOS is properly configured"""
        return bool(self.WORKOS_API_KEY and self.WORKOS_CLIENT_ID)
    
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