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

# Basic Flask configuration
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'dev')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['DEBUG'] = True  # Enable debug mode

if not app.config['SQLALCHEMY_DATABASE_URI']:
    logger.error("No DATABASE_URL environment variable found!")
    raise ValueError("DATABASE_URL environment variable is required")

# File upload configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

try:
    # Initialize db
    db.init_app(app)

    with app.app_context():
        logger.info("Creating database tables...")
        import models  # Import models here to avoid circular imports
        db.create_all()  # Create database tables
        logger.info("Database tables created successfully")
except Exception as e:
    logger.error(f"Error initializing database: {str(e)}")
    raise

import routes  # Import routes after db initialization

if __name__ == "__main__":
    # Get port from environment variable or default to 3000 (Replit's preferred port)
    port = int(os.environ.get('PORT', 3000))
    app.run(host='0.0.0.0', port=port)