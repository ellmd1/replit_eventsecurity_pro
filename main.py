import os
import logging
from flask_cors import CORS

# Configure logging with more details
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from app import app

# Enable CORS for all routes
CORS(app, resources={
    r"/*": {
        "origins": "*",
        "allow_headers": "*",
        "expose_headers": "*"
    }
})

if __name__ == "__main__":
    try:
        logger.info("Starting Flask application...")
        app.run(host="0.0.0.0", port=5000, debug=True)
    except Exception as e:
        logger.error(f"Failed to start Flask application: {str(e)}", exc_info=True)
        raise