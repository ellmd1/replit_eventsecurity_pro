import os
import logging

logger = logging.getLogger(__name__)

try:
    from flask import Flask
    from flask_sqlalchemy import SQLAlchemy
    from sqlalchemy.orm import DeclarativeBase

    logger.info("Initializing Flask application")

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

    # Initialize database
    logger.info("Initializing database")
    db.init_app(app)

    with app.app_context():
        logger.info("Creating database tables")
        import models  # noqa: F401
        db.create_all()
        logger.info("Database initialization complete")

except Exception as e:
    logger.error(f"Failed to initialize application: {str(e)}")
    raise