import os
import logging
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from flask_cors import CORS

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask
app = Flask(__name__)

# Basic Configuration
app.config.update(
    SECRET_KEY=os.environ.get("FLASK_SECRET_KEY", "development_key"),
    SQLALCHEMY_DATABASE_URI=os.environ.get("DATABASE_URL"),
    SQLALCHEMY_ENGINE_OPTIONS={
        "pool_recycle": 300,
        "pool_pre_ping": True
    },
    TEMPLATES_AUTO_RELOAD=True,
    STATIC_FOLDER="static",
    TEMPLATE_FOLDER="templates"
)

# Initialize database
class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
db.init_app(app)

# Enable CORS
CORS(app)

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

# Request logging
@app.before_request
def log_request_info():
    logger.debug('Headers: %s', dict(request.headers))
    logger.debug('Body: %s', request.get_data())
    logger.debug('URL: %s', request.url)

@app.after_request
def add_security_headers(response):
    response.headers.update({
        'Content-Security-Policy': "default-src * 'unsafe-inline' 'unsafe-eval'; img-src * data:; style-src * 'unsafe-inline';",
        'X-Frame-Options': 'SAMEORIGIN',
        'X-Content-Type-Options': 'nosniff'
    })
    return response

# Initialize database and routes
with app.app_context():
    try:
        # Import models and create tables
        import models
        db.create_all()
        logger.info("Database tables created successfully")

        # Import routes
        import routes
        logger.info("Routes imported successfully")
    except Exception as e:
        logger.error(f"Error during initialization: {str(e)}")
        raise

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)