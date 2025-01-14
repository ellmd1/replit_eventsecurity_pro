
from datetime import datetime
from app import app, db
from models import EventReport

with app.app_context():
    papal_visit = EventReport(
        title="Pope Benedict XVI's Papal Visit",
        description="Historic papal visit drawing thousands of faithful followers. Major religious and cultural event with international significance.",
        date=datetime.now(),
        location="London",
        risk_level="High",
        incident_type="Religious Event",
        venue_type="Outdoor",
        attendance=50000,
        security_staff_count=0,
        incidents_reported=0,
        security_measures="Very High security level required\nCAT A Event\nInternational significance requiring specialized security protocols",
        security_protocols="Contact: +44 20 7946 0958\nEmail: info@vatican.va\nDoors Open: 10:00\nMain Event: 12:00-14:00",
        created_at=datetime.utcnow()
    )

    db.session.add(papal_visit)
    db.session.commit()
    print(f"Added papal visit event with ID: {papal_visit.id}")
