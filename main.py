from app import app
import os
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    try:
        port = int(os.environ.get('PORT', 3000))
        logger.info(f"Starting Flask application on port {port}")

        app.run(
            host='0.0.0.0',
            port=port,
            debug=True,
            use_reloader=True
        )
    except Exception as e:
        logger.error(f"Failed to start Flask application: {str(e)}")
        raise