
from app import app, db
from models import EventReport

with app.app_context():
    EventReport.query.delete()
    db.session.commit()
    print("All events cleared from database")
