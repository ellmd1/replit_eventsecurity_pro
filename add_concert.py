
from datetime import datetime
from app import app, db
from models import EventReport

with app.app_context():
    concert = EventReport(
        title="GFGH Live at The Lowry",
        description="Intimate concert performance in The Lowry's prestigious venue. Evening of contemporary music with special guest appearances.",
        date=datetime.now(),
        location="The Lowry, Pier 8, Salford Quays, Manchester, M50 3AZ, United Kingdom",
        risk_level="Medium",
        incident_type="Music Event",
        venue_type="Indoor",
        attendance=1730,
        security_staff_count=0,
        incidents_reported=2,
        security_measures="Medium security level required\nCAT B Event\nAdult demographics\nHistorical incidents: 2",
        security_protocols="Contact: +44 161 876 2000\nEmail: info@livenation.co.uk\nDoors Open: 18:00\nSupport Act: 19:00-19:45\nMain Act: 20:00-22:30\nTicket Price: £45.00",
        created_at=datetime.utcnow()
    )

    db.session.add(concert)
    db.session.commit()
    print(f"Added concert event with ID: {concert.id}")
