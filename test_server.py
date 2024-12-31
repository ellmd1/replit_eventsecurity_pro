import logging
import traceback
from flask import Flask

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create minimal Flask app
app = Flask(__name__)

@app.route('/test')
def test():
    try:
        logger.debug("Test route accessed")
        return "Test server is working!"
    except Exception as e:
        logger.error(f"Error in test route: {str(e)}")
        logger.error(traceback.format_exc())
        return f"Error: {str(e)}", 500

if __name__ == '__main__':
    try:
        logger.info("Starting test Flask server...")
        # Use port 5001 to avoid conflict
        app.run(host='0.0.0.0', port=5001, debug=True)
    except Exception as e:
        logger.error(f"Failed to start Flask server: {str(e)}")
        logger.error(traceback.format_exc())
        raise