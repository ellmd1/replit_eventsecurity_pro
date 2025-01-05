from app import app
import os
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    try:
        # Get port from environment variable or default to 3000 (Replit's preferred port)
        port = int(os.environ.get('PORT', 3000))
        logger.info(f"Starting Flask application on port {port}")

        # Run the application with the correct host and port
        app.run(
            host='0.0.0.0',  # Required for Replit
            port=port,
            debug=True  # Enable debug mode for better error messages
        )
    except Exception as e:
        logger.error(f"Failed to start Flask application: {str(e)}")
        raise