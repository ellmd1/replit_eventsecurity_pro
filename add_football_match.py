
from datetime import datetime
from app import app, db
from models import EventReport

with app.app_context():
    football_match = EventReport(
        title="Manchester City vs. Leicester City - Premier League Match",
        description="High-stakes competitive fixture with passionate supporter base at the iconic Etihad Stadium",
        date=datetime.now(),
        location="Etihad Stadium, Manchester",
        risk_level="High",
        incident_type="Sports Event",
        venue_type="Stadium",
        attendance=55000,
        security_staff_count=0,
        incidents_reported=5,
        security_measures="CAT A Event\nMedium security level\nAdult demographics\nHistorical incidents: 5",
        security_protocols="Contact: +44 161 444 1894\nEmail: info@mancity.com\nDoors Open: 17:00\nKickoff: 19:45\nTicket Price: £50.00",
        created_at=datetime.utcnow()
    )

    db.session.add(football_match)
    db.session.commit()
    print(f"Added football match event with ID: {football_match.id}")
