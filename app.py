import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

# Configure logging
logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass

try:
    logger.info("Initializing Flask application and database")
    db = SQLAlchemy(model_class=Base)
    app = Flask(__name__)

    # Basic Flask configuration
    app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'dev')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # File upload configuration
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    logger.info(f"Upload folder created at: {UPLOAD_FOLDER}")

    # Verify database URL
    if not app.config['SQLALCHEMY_DATABASE_URI']:
        logger.error("No DATABASE_URL environment variable found!")
        raise ValueError("DATABASE_URL environment variable is required")

    # Log the database URL (without credentials)
    db_url = app.config['SQLALCHEMY_DATABASE_URI']
    safe_db_url = db_url.split('@')[-1] if '@' in db_url else db_url
    logger.info(f"Attempting to connect to database at: {safe_db_url}")

    # Initialize db
    db.init_app(app)
    logger.info("Database initialized successfully")

    with app.app_context():
        try:
            # Import models here to avoid circular imports
            logger.debug("Importing models")
            import models
            logger.info("Models imported successfully")

            logger.info("Starting database tables creation")
            db.create_all()
            logger.info("Database tables created successfully")
        except Exception as model_error:
            logger.error(f"Error during model import or table creation: {str(model_error)}", exc_info=True)
            raise

    try:
        # Import routes after db initialization
        logger.debug("Importing routes")
        import routes
        logger.info("Routes imported successfully")
    except Exception as route_error:
        logger.error(f"Error importing routes: {str(route_error)}", exc_info=True)
        raise

except Exception as init_error:
    logger.error(f"Error during application initialization: {str(init_error)}", exc_info=True)
    raise

# Only run the app if this file is run directly
if __name__ == "__main__":
    try:
        port = int(os.environ.get('PORT', 5000))
        logger.info(f"Starting Flask application on port {port}")
        app.run(
            host='0.0.0.0',
            port=port,
            debug=True,
            use_reloader=True
        )
    except Exception as e:
        logger.error(f"Failed to start Flask application: {str(e)}", exc_info=True)
        raise