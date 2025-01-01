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
    security_decisions = db.relationship('SecurityDecision', backref='event_report', lazy=True)
    estimated_risk_level = db.Column(db.String(50))
    risk_assessments = db.relationship('RiskAssessment', backref='event_report', lazy=True)

    @property
    def formatted_date(self):
        """Return the date in DD-MM-YYYY format"""
        return self.date.strftime('%d-%m-%Y') if self.date else None

class RiskAssessment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_report_id = db.Column(db.Integer, db.ForeignKey('event_report.id'), nullable=False)
    assessment_date = db.Column(db.DateTime, default=datetime.utcnow)
    risk_factors = db.Column(db.JSON, default=list)
    overall_risk_level = db.Column(db.String(50), nullable=False)
    assessor_notes = db.Column(db.Text)
    mitigation_measures = db.Column(db.JSON, default=list)
    residual_risk_level = db.Column(db.String(50))
    review_date = db.Column(db.DateTime)
    status = db.Column(db.String(50), default='Active')

    def calculate_overall_risk(self):
        if not self.risk_factors:
            return 'Low'

        total_score = 0
        for factor in self.risk_factors:
            if isinstance(factor, dict) and 'severity' in factor and 'likelihood' in factor:
                total_score += factor['severity'] * factor['likelihood']

        avg_score = total_score / len(self.risk_factors)
        if avg_score >= 7:
            return 'High'
        elif avg_score >= 4:
            return 'Medium'
        return 'Low'

class ActivityLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_report_id = db.Column(db.Integer, db.ForeignKey('event_report.id'), nullable=True)
    activity_type = db.Column(db.String(50), nullable=False)
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    ended_at = db.Column(db.DateTime)
    duration_seconds = db.Column(db.Integer)
    user_identifier = db.Column(db.String(100))
    session_id = db.Column(db.String(100))
    search_query = db.Column(db.String(500))
    filters_applied = db.Column(db.JSON, default=dict)
    interaction_details = db.Column(db.JSON, default=dict)
    related_resources = db.Column(db.JSON, default=list)
    user_decisions = db.Column(db.JSON, default=list)
    notes = db.Column(db.Text)

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

class SecurityDecision(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_report_id = db.Column(db.Integer, db.ForeignKey('event_report.id'), nullable=True)
    decision_type = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=False)
    impact_level = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    implementation_date = db.Column(db.DateTime)
    expected_outcome = db.Column(db.Text)
    actual_outcome = db.Column(db.Text)
    outcome_type = db.Column(db.String(20))
    status = db.Column(db.String(20), default='Pending')
    effectiveness_rating = db.Column(db.Integer)
    lessons_learned = db.Column(db.Text)
    related_decisions = db.Column(db.JSON, default=list)
    supporting_documents = db.Column(db.JSON, default=list)

    def update_outcome(self, outcome_text, outcome_type, effectiveness):
        self.actual_outcome = outcome_text
        self.outcome_type = outcome_type
        self.effectiveness_rating = effectiveness
        self.status = 'Implemented'

    def add_lesson_learned(self, lesson):
        self.lessons_learned = lesson

    def link_related_decision(self, decision_id, relationship_type):
        if not self.related_decisions:
            self.related_decisions = []
        self.related_decisions.append({
            'decision_id': decision_id,
            'relationship_type': relationship_type,
            'added_at': datetime.utcnow().isoformat()
        })