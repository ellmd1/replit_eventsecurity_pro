import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize eventlet first
logger.info("Initializing eventlet")
import eventlet
eventlet.monkey_patch()

logger.info("Importing Flask app and dependencies")
from app import app
from socket_init import init_socket

# Initialize SocketIO after app is created
socketio = init_socket(app)

# Import routes after socketio is initialized
import routes  # noqa: F401

if __name__ == "__main__":
    logger.info("Starting Flask-SocketIO server")
    try:
        socketio.run(app, host="0.0.0.0", port=5000, debug=True, use_reloader=True, log_output=True)
    except Exception as e:
        logger.error(f"Failed to start server: {str(e)}")
        raise