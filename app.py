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
    """Verify database connection and create extension if needed"""
    try:
        with app.app_context():
            # Test database connection
            db.session.execute(text("SELECT 1"))
            logger.info("Database connection successful")

            # Check if vector extension exists
            result = db.session.execute(text(
                "SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')"
            ))
            vector_exists = result.scalar()

            if not vector_exists:
                logger.info("Creating vector extension...")
                db.session.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                db.session.commit()
                logger.info("Vector extension created successfully")
            else:
                logger.info("Vector extension already exists")

            return True
    except Exception as e:
        logger.error(f"Database verification failed: {str(e)}", exc_info=True)
        return False

def init_database():
    """Initialize database tables"""
    try:
        with app.app_context():
            # Import models first
            import models

            # Create all tables
            db.create_all()
            logger.info("Database tables created successfully")

            return True
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}", exc_info=True)
        return False

def init_vector_store():
    """Initialize vector store and index documents"""
    try:
        with app.app_context():
            from vector_store import vector_store

            # Initialize store tables
            vector_store.initialize_store()
            logger.info("Vector store initialized successfully")

            # Index existing documents if any
            import models
            docs = db.session.query(models.EventReport).count()
            if docs > 0:
                logger.info(f"Found {docs} documents to index")
                vector_store.index_all_reports()
            else:
                logger.info("No documents to index")

            return True
    except Exception as e:
        logger.error(f"Vector store initialization failed: {str(e)}", exc_info=True)
        return False

# Initialize all components with proper error handling
with app.app_context():
    try:
        # Verify database first
        if not verify_database():
            logger.error("Database verification failed - continuing with limited functionality")

        # Initialize database
        if not init_database():
            logger.error("Database initialization failed - continuing with limited functionality")

        # Import routes after database is ready
        import routes

        # Initialize vector store last
        if not init_vector_store():
            logger.error("Vector store initialization failed - continuing with limited functionality")

        logger.info("Application initialization completed successfully")
    except Exception as e:
        logger.error(f"Application initialization failed: {str(e)}", exc_info=True)
        logger.warning("Continuing with limited functionality")