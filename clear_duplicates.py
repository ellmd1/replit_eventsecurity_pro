
from app import app, db
from models import EventReport

with app.app_context():
    # Get all papal visit events
    papal_visits = EventReport.query.filter_by(
        title="Pope Benedict XVI's Papal Visit"
    ).all()
    
    # Keep the first one, delete the rest
    if len(papal_visits) > 1:
        for visit in papal_visits[1:]:
            db.session.delete(visit)
        db.session.commit()
        print(f"Removed {len(papal_visits) - 1} duplicate papal visit events")
    else:
        print("No duplicates found")
