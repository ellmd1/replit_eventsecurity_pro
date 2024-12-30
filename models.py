from datetime import datetime
from app import db

class EventReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    location = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    risk_level = db.Column(db.String(50), nullable=False)
    incident_type = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    venue_type = db.Column(db.String(50))

    attendance = db.Column(db.Integer)
    security_measures = db.Column(db.Text)
    incident_response = db.Column(db.Text)
    lessons_learned = db.Column(db.Text)
    recommendations = db.Column(db.Text)

    access_logs = db.relationship('AccessLog', backref='event_report', lazy=True)

class AccessLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_report_id = db.Column(db.Integer, db.ForeignKey('event_report.id'), nullable=False)
    accessed_at = db.Column(db.DateTime, default=datetime.utcnow)
    purpose = db.Column(db.String(200))
    assessor_name = db.Column(db.String(100), nullable=False)
    assessment_context = db.Column(db.String(200))
    similar_event_details = db.Column(db.Text)

class ChatHistory(db.Model):
    __tablename__ = 'chat_history'
    id = db.Column(db.Integer, primary_key=True)
    query = db.Column(db.Text, nullable=False)
    response = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    events_found = db.Column(db.Integer)  # Number of events found
    search_explanation = db.Column(db.Text)  # AI's interpretation of the query