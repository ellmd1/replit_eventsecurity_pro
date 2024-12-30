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
    security_staff_count = db.Column(db.Integer, default=0)
    security_staff_roles = db.Column(db.JSON, default=dict)
    incidents_reported = db.Column(db.Integer, default=0)
    incident_summary = db.Column(db.Text)
    attendance = db.Column(db.Integer)
    security_measures = db.Column(db.Text)
    incident_response = db.Column(db.Text)
    lessons_learned = db.Column(db.Text)
    recommendations = db.Column(db.Text)
    security_protocols = db.Column(db.Text)
    emergency_response_plan = db.Column(db.Text)
    post_event_analysis = db.Column(db.Text)
    access_logs = db.relationship('AccessLog', backref='event_report', lazy=True)
    scenarios = db.relationship('EventScenario', backref='event_report', lazy=True)
    estimated_risk_level = db.Column(db.String(50))
    templates = db.relationship('AssessmentTemplate', backref='event_report', lazy=True)

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
    elements = db.Column(db.JSON, nullable=False, default=list)
    connections = db.Column(db.JSON, nullable=False, default=list)
    estimated_risk_level = db.Column(db.String(50))

class AssessmentTemplate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    event_report_id = db.Column(db.Integer, db.ForeignKey('event_report.id'))
    configuration = db.Column(db.JSON, nullable=False, default=dict)
    security_requirements = db.Column(db.JSON, default=list)
    risk_factors = db.Column(db.JSON, default=list)
    mitigation_strategies = db.Column(db.JSON, default=list)
    template_type = db.Column(db.String(50))
    min_capacity = db.Column(db.Integer)
    max_capacity = db.Column(db.Integer)
    is_default = db.Column(db.Boolean, default=False)

    def calculate_baseline_risk(self):
        risk_scores = []
        for factor in self.risk_factors:
            if factor.get('severity') and factor.get('likelihood'):
                risk_scores.append(factor['severity'] * factor['likelihood'])

        if not risk_scores:
            return 'Low'

        avg_score = sum(risk_scores) / len(risk_scores)
        if avg_score >= 7:
            return 'High'
        elif avg_score >= 4:
            return 'Medium'
        return 'Low'