import os
import logging
from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

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

# Initialize extensions
db.init_app(app)

# Basic routes
@app.route('/')
@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/index')
def index():
    return render_template('index.html')

@app.route('/chat')
def chat():
    return render_template('chat.html')

@app.route('/scenario-builder')
def scenario_builder():
    return render_template('scenario_builder.html')

@app.route('/comparative_search')
def comparative_search():
    return render_template('comparative_search.html')

@app.route('/view_access_logs')
def view_access_logs():
    return render_template('access_log.html')

try:
    with app.app_context():
        # Import models here to avoid circular imports
        import models  # noqa: F401

        # Create database tables
        db.create_all()
        logger.info("Database tables created successfully")
except Exception as e:
    logger.error(f"Error initializing application: {str(e)}")
    raise