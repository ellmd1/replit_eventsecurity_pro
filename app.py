import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.sql import text

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
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

def init_database():
    """Initialize database tables"""
    try:
        with app.app_context():
            import models
            db.create_all()
            logger.info("Database tables created successfully")
            return True
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}", exc_info=True)
        return False

def init_vector_store():
    """Initialize vector store"""
    try:
        with app.app_context():
            from vector_store import vector_store
            if not vector_store.initialize_store():
                logger.error("Vector store initialization failed")
                return False
            logger.info("Vector store initialized successfully")
            return True
    except Exception as e:
        logger.error(f"Vector store initialization failed: {str(e)}", exc_info=True)
        return False

# Initialize all components
with app.app_context():
    try:
        # First verify and setup database
        if not verify_database():
            logger.error("Database verification failed")
            raise Exception("Database verification failed")

        # Then initialize database tables
        if not init_database():
            logger.error("Database initialization failed")
            raise Exception("Database initialization failed")

        # Import routes after database is ready
        import routes
        logger.info("Routes imported successfully")

        # Finally initialize vector store (non-critical)
        if not init_vector_store():
            logger.warning("Vector store initialization failed - some features may be limited")
        else:
            logger.info("Vector store initialization successful")

        logger.info("Application initialization completed successfully")
    except Exception as e:
        logger.error(f"Critical error during application initialization: {str(e)}", exc_info=True)
        raise