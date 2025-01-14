
from datetime import datetime
from app import app, db
from models import EventReport

with app.app_context():
    reinterment = EventReport(
        title="Reinterment of King Richard III",
        description="Historic ceremony marking the reburial of a medieval English monarch. Unique blend of royal, religious, and historical significance.",
        date=datetime.now(),
        location="Leicester Cathedral",
        risk_level="Medium",
        incident_type="Historical Event",
        venue_type="Outdoor",
        attendance=10000,
        security_staff_count=0,
        incidents_reported=0,
        security_measures="Medium security level required\nCAT B Event\nMixed demographics\nHistorical incidents: 0",
        security_protocols="Contact: +44 116 261 5200\nEmail: info@leicestercathedral.org\nDoors Open: 10:00\nMain Event: 12:00-14:00\nTicket Price: Free",
        created_at=datetime.utcnow()
    )

    db.session.add(reinterment)
    db.session.commit()
    print(f"Added reinterment event with ID: {reinterment.id}")
