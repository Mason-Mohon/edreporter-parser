"""Flask application entry point for EdReporter PDF Segmentation Tool."""

from flask import Flask, render_template
from flask_cors import CORS

from .config import Config
from .logger import logger


def create_app(config_class=Config):
    """Create and configure Flask application.
    
    Args:
        config_class: Configuration class to use
        
    Returns:
        Configured Flask app instance
    """
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Enable CORS
    CORS(app)
    
    # Ensure directories exist
    Config.ensure_directories()
    
    # Register routes
    from . import routes
    routes.register_routes(app)
    
    logger.info("EdReporter Flask application initialized")
    logger.info(f"Data directory: {Config.DATA_DIR}")
    logger.info(f"Output directory: {Config.OUTPUT_DIR}")
    
    return app


# Create app instance
app = create_app()


@app.route('/')
def index():
    """Render main application page."""
    logger.info("Main page accessed")
    return render_template('index.html')


if __name__ == '__main__':
    logger.info("Starting EdReporter Flask application in debug mode")
    app.run(debug=True, host='0.0.0.0', port=5000)
