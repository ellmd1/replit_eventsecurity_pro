import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

# Configure logging
logging.basicConfig(level=logging.DEBUG)

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

def init_vector_store():
    """Initialize vector store after app context is available"""
    with app.app_context():
        from vector_store import vector_store
        try:
            vector_store.index_all_reports()
            logging.info("Successfully initialized vector store with existing reports")
        except Exception as e:
            logging.error(f"Failed to initialize vector store: {e}")

# Initialize everything within app context
with app.app_context():
    import models
    import routes
    db.create_all()
    init_vector_store()