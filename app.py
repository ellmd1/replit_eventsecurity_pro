import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.sql import text

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
app = Flask(__name__)

# Configuration
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or "development_key"
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize the database
db.init_app(app)

def init_database():
    """Initialize database tables and vector extension"""
    try:
        with app.app_context():
            # Import models first
            import models

            # Enable vector extension first
            try:
                db.session.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                db.session.commit()
                logger.info("Vector extension enabled successfully")
            except Exception as ve:
                logger.error(f"Failed to enable vector extension: {str(ve)}")
                raise

            # Create all tables
            try:
                db.create_all()
                logger.info("Database tables created successfully")
            except Exception as te:
                logger.error(f"Failed to create tables: {str(te)}")
                raise

            logger.info("Database initialization completed successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        raise

def init_vector_store():
    """Initialize vector store after app context is available"""
    logger.info("Starting vector store initialization...")
    from vector_store import vector_store
    try:
        with app.app_context():
            vector_store.initialize_store()
            vector_store.index_all_reports()
            logger.info("Successfully initialized vector store with existing reports")
    except Exception as e:
        logger.error(f"Failed to initialize vector store: {str(e)}")
        # Don't raise here - allow app to continue even if vector store fails

# Initialize everything within app context
with app.app_context():
    try:
        # Initialize database first
        init_database()

        # Import routes after database is ready
        import routes

        # Initialize vector store last
        init_vector_store()

        logger.info("Application initialization completed successfully")
    except Exception as e:
        logger.error(f"Application initialization failed: {str(e)}")
        # Continue startup even if there are initialization issues
        pass