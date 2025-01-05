from datetime import datetime
from app import db

class ChatMessage(db.Model):
    """Model for storing chat messages and history"""
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(100), nullable=False, index=True)
    message = db.Column(db.Text, nullable=False)
    is_user = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    category = db.Column(db.String(50))
    read = db.Column(db.Boolean, default=False)

    @property
    def formatted_timestamp(self):
        return self.created_at.strftime("%Y-%m-%d %H:%M")

class SecurityInsight(db.Model):
    """Model for storing AI-generated security insights"""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    key_findings = db.Column(db.JSON, nullable=True)
    icon = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

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
    estimated_risk_level = db.Column(db.String(50))
    risk_assessments = db.relationship('RiskAssessment', backref='event_report', lazy=True)

class SecurityDecision(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    author = db.Column(db.String(100))
    attachments = db.Column(db.JSON, default=list)
    event_report_id = db.Column(db.Integer, db.ForeignKey('event_report.id'), nullable=True)
    event_report = db.relationship('EventReport', backref=db.backref('security_decisions', lazy=True))

    def add_attachment(self, filename, file_path, file_type, file_size):
        """Add a new file attachment to the decision"""
        if not self.attachments:
            self.attachments = []

        self.attachments.append({
            'filename': filename,
            'file_path': file_path,
            'file_type': file_type,
            'file_size': file_size,
            'uploaded_at': datetime.utcnow().isoformat(),
            'upload_by': self.author
        })

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

class AssessmentTemplate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
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