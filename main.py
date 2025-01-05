import logging
from app import app

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    try:
        port = 3000  # Change to a different port
        logger.info(f"Starting Flask server on port {port}...")
        app.run(host='0.0.0.0', port=port, debug=True)
    except Exception as e:
        logger.error(f"Failed to start server: {str(e)}")
        raise