import os
import logging
from flask import Flask, jsonify, request, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.sql import text
from flask_cors import CORS

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
app = Flask(__name__, 
           static_url_path='/static',
           static_folder='static',
           template_folder='templates')

# Enable CORS with specific configuration for Replit
CORS(app, 
     resources={r"/*": {
         "origins": ["*", "https://*.repl.co", "https://*.replit.com"],
         "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"],
         "expose_headers": ["Content-Range", "X-Content-Range"]
     }},
     supports_credentials=True)

# Configuration
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or "development_key"
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
# Add static file configuration
app.config["STATIC_FOLDER"] = "static"
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB max file size

# Initialize the database
db.init_app(app)

# Request logging middleware
@app.before_request
def log_request_info():
    logger.debug('Headers: %s', dict(request.headers))
    logger.debug('Body: %s', request.get_data())
    logger.debug('URL: %s', request.url)

@app.after_request
def add_security_headers(response):
    # Allow iframe embedding from Replit domains
    response.headers['Content-Security-Policy'] = "frame-ancestors 'self' https://*.repl.co https://*.replit.com"
    response.headers['X-Frame-Options'] = 'ALLOW-FROM https://*.repl.co https://*.replit.com'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    # CORS headers
    response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    return response

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    logger.error(f"404 Error: {request.url}")
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"500 Error: {str(error)}")
    db.session.rollback()
    return jsonify({"error": "Internal server error"}), 500

# Explicit route for serving static files
@app.route('/static/<path:path>')
def serve_static(path):
    logger.debug(f"Serving static file: {path}")
    return send_from_directory('static', path)

def verify_database():
    """Verify database connection and vector extension availability"""
    try:
        with app.app_context():
            # Test database connection
            db.session.execute(text("SELECT 1"))
            logger.info("Database connection verified")

            # Check if vector extension is available
            result = db.session.execute(text(
                "SELECT extname FROM pg_extension WHERE extname = 'vector'"
            ))
            if not result.fetchone():
                logger.info("Vector extension not found, attempting to create...")
                db.session.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                db.session.commit()
                logger.info("Vector extension created successfully")
            else:
                logger.info("Vector extension is already installed")

            return True
    except Exception as e:
        logger.error(f"Database verification failed: {str(e)}", exc_info=True)
        return False

# Initialize all components
with app.app_context():
    try:
        # First verify and setup database
        if not verify_database():
            logger.error("Database verification failed")
            raise Exception("Database verification failed")

        # Then initialize database tables
        import models  # noqa: F401
        db.create_all()
        logger.info("Database tables created successfully")

        # Import routes after database is ready
        import routes
        logger.info("Routes imported successfully")

        logger.info("Application initialization completed successfully")
    except Exception as e:
        logger.error(f"Critical error during application initialization: {str(e)}", exc_info=True)
        raise