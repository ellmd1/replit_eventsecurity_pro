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
    activity_logs = db.relationship('ActivityLog', backref='event_report', lazy=True)
    scenarios = db.relationship('EventScenario', backref='event_report', lazy=True)
    estimated_risk_level = db.Column(db.String(50))
    templates = db.relationship('AssessmentTemplate', backref='event_report', lazy=True)

class ActivityLog(db.Model):
    """Enhanced logging system for tracking all user interactions"""
    id = db.Column(db.Integer, primary_key=True)
    event_report_id = db.Column(db.Integer, db.ForeignKey('event_report.id'), nullable=True)
    activity_type = db.Column(db.String(50), nullable=False)  # view, search, compare, template_use
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    ended_at = db.Column(db.DateTime)
    duration_seconds = db.Column(db.Integer)

    # User context
    user_identifier = db.Column(db.String(100))  # IP or session ID for anonymous tracking
    session_id = db.Column(db.String(100))

    # Activity details
    search_query = db.Column(db.String(500))  # Store search terms used
    filters_applied = db.Column(db.JSON, default=dict)  # Store any filters used
    interaction_details = db.Column(db.JSON, default=dict)  # Store specific actions taken

    # Analysis context
    related_resources = db.Column(db.JSON, default=list)  # Other reports/templates viewed in session
    user_decisions = db.Column(db.JSON, default=list)  # Track decisions made during analysis
    notes = db.Column(db.Text)  # Additional context or observations

    def calculate_duration(self):
        if self.ended_at and self.started_at:
            self.duration_seconds = int((self.ended_at - self.started_at).total_seconds())
        return self.duration_seconds

    def end_activity(self):
        self.ended_at = datetime.utcnow()
        self.calculate_duration()

    def add_decision(self, decision_type, details):
        if not self.user_decisions:
            self.user_decisions = []
        self.user_decisions.append({
            'type': decision_type,
            'details': details,
            'timestamp': datetime.utcnow().isoformat()
        })

    def add_related_resource(self, resource_type, resource_id):
        if not self.related_resources:
            self.related_resources = []
        self.related_resources.append({
            'type': resource_type,
            'id': resource_id,
            'timestamp': datetime.utcnow().isoformat()
        })

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
