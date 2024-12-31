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

            # Verify vector extension availability
            result = db.session.execute(text(
                "SELECT * FROM pg_available_extensions WHERE name = 'vector'"
            ))
            if not result.fetchone():
                raise Exception("Vector extension is not available in the database")

            logger.info("Vector extension availability verified")
            return True
    except Exception as e:
        logger.error(f"Database verification failed: {str(e)}", exc_info=True)
        return False

def init_database():
    """Initialize database tables and extensions"""
    try:
        with app.app_context():
            # Begin transaction
            db.session.execute(text("BEGIN"))
            try:
                # Create vector extension if not exists
                db.session.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

                # Import models and create tables
                import models
                db.create_all()

                # Commit transaction
                db.session.commit()
                logger.info("Database initialized successfully")
                return True
            except Exception as e:
                db.session.rollback()
                logger.error(f"Failed during database initialization: {str(e)}")
                raise
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}", exc_info=True)
        return False

def init_vector_store():
    """Initialize vector store and index documents"""
    try:
        with app.app_context():
            from vector_store import vector_store

            # Initialize store with proper error handling
            if not vector_store.initialize_store():
                raise Exception("Vector store initialization returned False")

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
        # Verify database and extension availability first
        if not verify_database():
            raise Exception("Database verification failed")
        logger.info("Database verification successful")

        # Initialize database and create tables
        if not init_database():
            raise Exception("Database initialization failed")
        logger.info("Database initialization successful")

        # Import routes after database is ready
        import routes
        logger.info("Routes imported successfully")

        # Initialize vector store last
        if not init_vector_store():
            raise Exception("Vector store initialization failed")
        logger.info("Vector store initialization successful")

        logger.info("Application initialization completed")
    except Exception as e:
        logger.error(f"Application initialization failed: {str(e)}", exc_info=True)
        raise