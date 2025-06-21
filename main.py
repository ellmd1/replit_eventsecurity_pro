import logging
import os
import argparse
from app import app

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Flask app.")
    parser.add_argument('--port', type=int, default=5000, help='Port to run the server on (default: 5000)')
    args = parser.parse_args()
    try:
        # Ensure UPLOAD_FOLDER exists
        upload_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
        os.makedirs(upload_folder, exist_ok=True)
        logger.info(f"Upload folder verified at: {upload_folder}")

        # Start the Flask application
        logger.info(f"Starting Flask application on port {args.port}...")
        app.run(host='0.0.0.0', port=args.port, debug=True, threaded=True)
    except Exception as e:
        logger.error(f"Failed to start Flask application: {str(e)}")
        raise