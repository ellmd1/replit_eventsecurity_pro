import logging
logger = logging.getLogger(__name__)

try:
    from flask_socketio import SocketIO
    from app import app

    logger.info("Initializing SocketIO")
    socketio = SocketIO(app, 
                       async_mode='eventlet', 
                       logger=True, 
                       engineio_logger=True, 
                       cors_allowed_origins="*")
    logger.info("SocketIO initialization complete")
except Exception as e:
    logger.error(f"Failed to initialize SocketIO: {str(e)}")
    raise