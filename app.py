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

# Import models and create tables
with app.app_context():
    import models  # noqa: F401
    db.create_all()
    logger.info("Database tables created successfully")

# Import routes - this needs to happen after db initialization but before other middleware
import routes  # noqa: F401
logger.info("Routes imported successfully")

# Simplify CORS configuration for debugging
CORS(app)

# Request logging middleware
@app.before_request
def log_request_info():
    logger.debug('Headers: %s', dict(request.headers))
    logger.debug('Body: %s', request.get_data())
    logger.debug('URL: %s', request.url)
    logger.debug('Method: %s', request.method)
    logger.debug('Endpoint: %s', request.endpoint)

@app.after_request
def add_security_headers(response):
    response.headers['Content-Security-Policy'] = "default-src * 'unsafe-inline' 'unsafe-eval'; img-src * data:; style-src * 'unsafe-inline';"
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response

# Basic test routes
@app.route('/ping')
def ping():
    logger.debug("Ping route accessed")
    return "pong"

@app.route('/')
def root():
    logger.debug("Root route accessed")
    return "Welcome to the Event Safety Platform"

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