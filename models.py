from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    role = db.Column(db.String(20), default='user')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

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
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref='event_reports')

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

class AccessLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_report_id = db.Column(db.Integer, db.ForeignKey('event_report.id'), nullable=False)
    accessed_at = db.Column(db.DateTime, default=datetime.utcnow)
    purpose = db.Column(db.String(200))
    assessor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    assessor = db.relationship('User', backref='access_logs')
    assessment_context = db.Column(db.String(200))
    similar_event_details = db.Column(db.Text)

class EventScenario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    event_report_id = db.Column(db.Integer, db.ForeignKey('event_report.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref='scenarios')

    # Store the scenario elements as JSON
    elements = db.Column(db.JSON, nullable=False, default=list)
    connections = db.Column(db.JSON, nullable=False, default=list)

    # Calculate estimated risk level based on elements
    estimated_risk_level = db.Column(db.String(50))