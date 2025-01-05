import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
app = Flask(__name__)

# Configuration
app.config['TIMEOUT'] = 300  # 5 minutes timeout
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or "development_key"
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# File upload configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Create upload folder if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
logger.info(f"Upload folder created/verified at: {UPLOAD_FOLDER}")

try:
    # Initialize database
    db.init_app(app)
    logger.info("Database initialized successfully")

    with app.app_context():
        # Import models first
        from models import (
            EventReport,
            ActivityLog,
            SecurityDecision,
            SecurityInsight,
            RiskAssessment,
            AssessmentTemplate,
            ChatMessage
        )
        logger.info("Successfully imported models")

        # Create database tables
        db.create_all()
        logger.info("Database tables created successfully")

        # Import routes after database initialization
        import routes  # noqa: F401
        logger.info("Routes imported successfully")

except Exception as e:
    logger.error(f"Failed to initialize application: {str(e)}")
    raise