from datetime import datetime
from app import db
from pgvector.sqlalchemy import Vector

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

    # Enhanced security details
    security_staff_count = db.Column(db.Integer, default=0)
    security_staff_roles = db.Column(db.JSON, default=dict)  # Different types of security personnel
    incidents_reported = db.Column(db.Integer, default=0)
    incident_summary = db.Column(db.Text)  # Summary of security incidents

    # Fields for detailed risk assessment
    attendance = db.Column(db.Integer)
    security_measures = db.Column(db.Text)
    incident_response = db.Column(db.Text)
    lessons_learned = db.Column(db.Text)
    recommendations = db.Column(db.Text)

    # Additional assessment fields
    security_protocols = db.Column(db.Text)  # Detailed security protocols used
    emergency_response_plan = db.Column(db.Text)  # Emergency response procedures
    post_event_analysis = db.Column(db.Text)  # Analysis after the event

    access_logs = db.relationship('AccessLog', backref='event_report', lazy=True)
    scenarios = db.relationship('EventScenario', backref='event_report', lazy=True)
    embeddings = db.relationship('EventEmbedding', backref='event_report', lazy=True, uselist=False)

class EventEmbedding(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_report_id = db.Column(db.Integer, db.ForeignKey('event_report.id'), nullable=False)
    # Store embeddings as a vector with 384 dimensions (default for sentence-transformers)
    embedding = db.Column(Vector(384))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class AccessLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_report_id = db.Column(db.Integer, db.ForeignKey('event_report.id'), nullable=False)
    accessed_at = db.Column(db.DateTime, default=datetime.utcnow)
    purpose = db.Column(db.String(200))
    assessor_name = db.Column(db.String(100), nullable=False)
    assessment_context = db.Column(db.String(200))
    similar_event_details = db.Column(db.Text)

class EventScenario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    event_report_id = db.Column(db.Integer, db.ForeignKey('event_report.id'))

    # Store the scenario elements as JSON
    elements = db.Column(db.JSON, nullable=False, default=list)
    connections = db.Column(db.JSON, nullable=False, default=list)

    # Calculate estimated risk level based on elements
    estimated_risk_level = db.Column(db.String(50))