"""Configuration for EdReporter Flask application."""

import os
from pathlib import Path


class Config:
    """Flask application configuration."""
    
    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    
    # Application paths
    BASE_DIR = Path(__file__).parent.parent
    DATA_DIR = BASE_DIR / 'data'
    OUTPUT_DIR = BASE_DIR / 'out'
    
    # PDF processing settings
    DEFAULT_DPI = 200
    MIN_DPI = 150
    MAX_DPI = 300
    
    # OCR settings
    DEFAULT_OCR_LANG = 'eng'
    DEFAULT_TESSERACT_PSM = 6
    
    # UI settings
    CANVAS_MAX_WIDTH = 1400
    SIDEBAR_WIDTH = 350
    
    # Session settings
    SESSION_TYPE = 'filesystem'
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hour
    
    @classmethod
    def ensure_directories(cls):
        """Ensure required directories exist."""
        cls.DATA_DIR.mkdir(parents=True, exist_ok=True)
        cls.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
