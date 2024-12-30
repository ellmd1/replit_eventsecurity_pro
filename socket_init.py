import logging
import eventlet
eventlet.monkey_patch()

logger = logging.getLogger(__name__)

try:
    from flask_socketio import SocketIO

    logger.info("Initializing SocketIO")
    socketio = None

    def init_socket(app):
        global socketio
        socketio = SocketIO(
            app,
            async_mode='eventlet',
            logger=True,
            engineio_logger=True,
            cors_allowed_origins="*",
            ping_timeout=60
        )
        logger.info("SocketIO initialization complete")
        return socketio

except Exception as e:
    logger.error(f"Failed to initialize SocketIO: {str(e)}")
    raise