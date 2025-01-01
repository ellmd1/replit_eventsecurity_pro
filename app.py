import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from flask_cors import CORS

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
app = Flask(__name__)

# Enable CORS for development
CORS(app, 
     resources={r"/*": {
         "origins": ["*"],
         "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
         "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"]
     }},
     supports_credentials=True)

# Configuration
app.config['ENV'] = 'development'
app.config['DEBUG'] = True
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or "development_key"
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Security headers for development
@app.after_request
def after_request(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'GET,PUT,POST,DELETE,OPTIONS'
    return response

# Initialize extensions
db.init_app(app)

try:
    with app.app_context():
        # Import models here to avoid circular imports
        import models  # noqa: F401
        import routes  # noqa: F401

        # Create database tables
        db.create_all()
        logger.info("Database tables created successfully")
except Exception as e:
    logger.error(f"Error initializing application: {str(e)}")
    raise