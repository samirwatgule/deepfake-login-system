import os

class Config:
    """Application configuration loaded from environment variables."""
    DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://postgres:root@localhost:5432/truth_shield')
    JWT_SECRET = os.environ.get('JWT_SECRET', 'dev-secret-key-change-in-production')
    GEO_API_URL = os.environ.get('GEO_API_URL', 'https://ipapi.co')
    
    # Risk thresholds
    RISK_ALLOW_MAX = 30
    RISK_FLAG_MAX = 70
    # Above 70 = BLOCK
    
    # Device risk weights
    NEW_DEVICE_RISK = 20
    NEW_CITY_RISK = 15
    NEW_COUNTRY_RISK = 25
    MAX_DEVICE_RISK = 40
