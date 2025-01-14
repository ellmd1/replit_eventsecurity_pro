
from datetime import datetime
from app import app, db
from models import EventReport

with app.app_context():
    book_tour = EventReport(
        title="Michelle Obama's Book Tour",
        description="Intimate evening with former First Lady discussing her bestselling memoir. Exclusive Q&A session and book signing opportunity.",
        date=datetime.now(),
        location="London's Southbank Centre",
        risk_level="High",
        incident_type="Cultural Event",
        venue_type="Indoor",
        attendance=2000,
        security_staff_count=0,
        incidents_reported=1,
        security_measures="High security level required\nCAT B Event\nMixed demographics\nHistorical incidents: 1",
        security_protocols="Contact: +44 20 7921 0600\nEmail: info@southbankcentre.co.uk\nDoors Open: 18:00\nMain Event: 19:00-21:00\nTicket Price: £75.00",
        created_at=datetime.utcnow()
    )

    db.session.add(book_tour)
    db.session.commit()
    print(f"Added book tour event with ID: {book_tour.id}")
