"""
Configuration module for the bot
"""
import os
from dotenv import load_dotenv

class BotConfig:
    """Configuration class to handle environment variables and settings"""
    def __init__(self):
        load_dotenv(override=True)
        
        # Channel configuration
        self.DEFAULT_CHANNEL = 1327357851827572872
        
        # Environment detection
        self.ENV = os.getenv("ENV")
        if self.ENV == "dev":
            print("[DEBUG] ~~~~~~~~~~~~ Running in development mode ~~~~~~~~~~~~")
            self.TOKEN = os.getenv("DEV_TOKEN")
            self.SUPABASE_URL = os.getenv("DEV_SUPABASE_URL")
            self.SUPABASE_KEY = os.getenv("DEV_SUPABASE_KEY")
            # TODO: [WARNING] Hardcoded club ID for single club usage
            self.DEFAULT_CLUB_ID = "club-1"
        else:
            self.TOKEN = os.getenv("TOKEN")
            self.SUPABASE_URL = os.getenv("SUPABASE_URL")
            self.SUPABASE_KEY = os.getenv("SUPABASE_KEY")
            # TODO: [WARNING] Hardcoded club ID for single club usage
            self.DEFAULT_CLUB_ID = "0f01ad5e-0665-4f02-8cdd-8d55ecb26ac3"
        
        # Brains configuration
        self.BRAINS_SUPABASE_URL = os.getenv("BRAINS_SUPABASE_URL")
        self.BRAINS_SUPABASE_KEY = os.getenv("BRAINS_SUPABASE_KEY")

        # API Keys    
        self.KEY_WEATHER = os.getenv("KEY_WEATHER")
        self.KEY_OPENAI = os.getenv("KEY_OPEN_AI")
        
        # Print debug information
        self._debug_print()
        
        # Validate configuration
        self._validate()
    
    def _debug_print(self):
        """Print debug information about configuration"""
        print(f"[DEBUG] TOKEN: {'SET' if self.TOKEN else 'NOT SET'}")
        print(f"[DEBUG] KEY_WEATHER: {'SET' if self.KEY_WEATHER else 'NOT SET'}")
        print(f"[DEBUG] KEY_OPENAI: {'SET' if self.KEY_OPENAI else 'NOT SET'}")
    
    def _validate(self):
        """Validate that required configuration is present"""
        if not self.TOKEN:
            raise ValueError("[ERROR] TOKEN environment variable is not set.")