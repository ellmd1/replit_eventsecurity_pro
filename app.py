import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy.orm import DeclarativeBase

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

# Initialize extensions
db = SQLAlchemy(model_class=Base)

# Create the Flask application
def create_app():
    app = Flask(__name__)

    # Configuration
    app.secret_key = os.environ.get("FLASK_SECRET_KEY") or "development_key"
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }

    # Initialize extensions with app
    db.init_app(app)
    migrate = Migrate(app, db)

    with app.app_context():
        try:
            # Import models and register routes
            import models  # noqa: F401
            from routes import init_routes

            # Initialize routes
            init_routes(app, db)

            # Create tables
            db.create_all()
            logging.info("Database tables created successfully")

            # Verify OpenAI API key
            if not os.environ.get("OPENAI_API_KEY"):
                logging.warning("OPENAI_API_KEY not found in environment variables")

        except Exception as e:
            logging.error(f"Error during app initialization: {str(e)}")
            raise

    return app

# Create the app instance
app = create_app()