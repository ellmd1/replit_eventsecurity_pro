from app import app
import os
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    try:
        # Always use port 3000 for Replit, but allow override from environment
        port = int(os.environ.get('PORT', 3000))
        logger.info(f"Starting Flask application on port {port}")

        # Run the application with explicit host and port binding
        app.run(
            host='0.0.0.0',  # Required for external access
            port=port,
            debug=True,  # Enable debug mode for development
            use_reloader=True  # Enable auto-reloader
        )
    except Exception as e:
        logger.error(f"Failed to start Flask application: {str(e)}")
        raise