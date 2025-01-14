import logging
import os
from app import app

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    try:
        # Ensure UPLOAD_FOLDER exists
        upload_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
        os.makedirs(upload_folder, exist_ok=True)
        logger.info(f"Upload folder verified at: {upload_folder}")

        # Start the Flask application
        logger.info("Starting Flask application...")
        app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
    except Exception as e:
        logger.error(f"Failed to start Flask application: {str(e)}")
        raise