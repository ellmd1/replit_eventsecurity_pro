import http.server
import socketserver
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
PORT = 8000

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def log_message(self, format, *args):
        logger.info(format % args)

if __name__ == "__main__":
    try:
        with socketserver.TCPServer(("0.0.0.0", PORT), Handler) as httpd:
            logger.info(f"Server started at port {PORT}")
            httpd.serve_forever()
    except Exception as e:
        logger.error(f"Server error: {str(e)}")
        raise