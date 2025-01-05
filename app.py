import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Configure secret key
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or "development_key"

# Configure database
if not os.environ.get("DATABASE_URL"):
    logger.error("DATABASE_URL environment variable not set")
    raise RuntimeError("DATABASE_URL must be set")

app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# File upload configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize SQLAlchemy with the app
class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
db.init_app(app)

try:
    # Create tables
    with app.app_context():
        # Import models here to avoid circular imports
        import models  # noqa: F401
        logger.info("Creating database tables...")
        db.create_all()
        logger.info("Database tables created successfully")
except Exception as e:
    logger.error(f"Failed to initialize database: {str(e)}")
    raise

# Import routes after everything is initialized
try:
    import routes  # noqa: F401
    logger.info("Routes imported successfully")
except Exception as e:
    logger.error(f"Failed to import routes: {str(e)}")
    raise

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)