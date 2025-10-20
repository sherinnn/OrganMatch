import os

class Config:
    """Flask configuration"""
    
    # Use SESSION_SECRET from environment or generate a random one
    SECRET_KEY = os.getenv('SESSION_SECRET', os.urandom(24))
    
    # Flask settings
    DEBUG = os.getenv('FLASK_ENV', 'development') == 'development'
    TESTING = False
    
    # CORS settings
    CORS_HEADERS = 'Content-Type'
    
    # AWS Configuration (optional)
    AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
    AWS_GATEWAY_ID = os.getenv('AWS_GATEWAY_ID', '')
    AWS_MODEL_ID = os.getenv('AWS_MODEL_ID', '')
    AWS_AGENT_ID = os.getenv('AWS_AGENT_ID', '')
    AWS_AGENT_ALIAS_ID = os.getenv('AWS_AGENT_ALIAS_ID', '')
