from flask import render_template, request, redirect, url_for, jsonify, g, session, send_file
from app import app, db
from models import EventReport, ActivityLog, SecurityDecision
from datetime import datetime, timedelta
import logging
from sqlalchemy import or_, func, extract, and_
import uuid
import weasyprint
import tempfile
import os

def get_or_create_session_id():
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    return session['session_id']

def start_activity_tracking(activity_type, event_report_id=None):
    log = ActivityLog(
        activity_type=activity_type,
        event_report_id=event_report_id,
        session_id=get_or_create_session_id(),
        user_identifier=request.remote_addr
    )
    db.session.add(log)
    db.session.commit()
    return log

def end_activity_tracking(log):
    log.end_activity()
    db.session.commit()
    return log

@app.before_request
def before_request():
    g.start_time = datetime.utcnow()
    g.activity_log = None

@app.after_request
def after_request(response):
    if hasattr(g, 'activity_log') and g.activity_log:
        end_activity_tracking(g.activity_log)
    return response

@app.route('/')
def dashboard():
    log = start_activity_tracking('dashboard_view')
    g.activity_log = log

    upcoming_events = EventReport.query.order_by(EventReport.date.desc()).limit(5).all()
    recent_decisions = SecurityDecision.query.order_by(SecurityDecision.created_at.desc()).limit(5).all()

    risk_levels = {
        'High': len([e for e in upcoming_events if e.risk_level == 'High']),
        'Medium': len([e for e in upcoming_events if e.risk_level == 'Medium']),
        'Low': len([e for e in upcoming_events if e.risk_level == 'Low'])
    }

    log.interaction_details = {
        'viewed_events_count': len(upcoming_events),
        'viewed_decisions_count': len(recent_decisions)
    }
    db.session.commit()

    return render_template('dashboard.html', 
                         upcoming_events=upcoming_events,
                         recent_decisions=recent_decisions,
                         risk_levels=risk_levels)

@app.route('/decisions')
def decision_log():
    log = start_activity_tracking('view_decision_log')
    g.activity_log = log

    impact_level = request.args.get('impact')
    query = SecurityDecision.query

    if impact_level:
        query = query.filter(SecurityDecision.impact_level == impact_level.capitalize())

    decisions = query.order_by(SecurityDecision.created_at.desc()).all()
    events = EventReport.query.order_by(EventReport.date.desc()).all()

    log.interaction_details = {
        'filter_applied': impact_level,
        'results_count': len(decisions)
    }
    db.session.commit()

    return render_template('decision_log.html', 
                         decisions=decisions,
                         events=events)

@app.route('/decision/<int:decision_id>')
def view_decision(decision_id):
    decision = SecurityDecision.query.get_or_404(decision_id)
    log = start_activity_tracking('view_decision_details', 
                                decision.event_report_id if decision.event_report else None)
    g.activity_log = log

    related_decisions = []
    if decision.related_decisions:
        related_ids = [rd['decision_id'] for rd in decision.related_decisions]
        related_decisions = SecurityDecision.query.filter(SecurityDecision.id.in_(related_ids)).all()

    return render_template('view_decision.html', 
                         decision=decision,
                         related_decisions=related_decisions)

@app.route('/log_decision', methods=['POST'])
def log_decision():
    try:
        decision = SecurityDecision(
            event_report_id=request.form.get('event_report_id'),
            decision_type=request.form['decision_type'],
            description=request.form['description'],
            impact_level=request.form['impact_level'],
            implementation_date=datetime.strptime(request.form['implementation_date'], '%Y-%m-%d') 
                              if request.form.get('implementation_date') else None,
            expected_outcome=request.form.get('expected_outcome')
        )
        db.session.add(decision)
        db.session.commit()

        return redirect(url_for('decision_log'))
    except Exception as e:
        logging.error(f"Error logging decision: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/update_decision/<int:decision_id>', methods=['POST'])
def update_decision(decision_id):
    try:
        decision = SecurityDecision.query.get_or_404(decision_id)

        if 'outcome' in request.form:
            decision.update_outcome(
                request.form['outcome'],
                request.form['outcome_type'],
                int(request.form['effectiveness'])
            )

        if 'lesson' in request.form:
            decision.add_lesson_learned(request.form['lesson'])

        db.session.commit()
        return redirect(url_for('view_decision', decision_id=decision_id))
    except Exception as e:
        logging.error(f"Error updating decision: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/browse')
def index():
    search_query = request.args.get('search', '')
    risk_level = request.args.get('risk_level', '')

    log = start_activity_tracking('browse_events')
    g.activity_log = log
    log.search_query = search_query
    log.filters_applied = {'risk_level': risk_level} if risk_level else {}

    query = EventReport.query
    if search_query:
        query = query.filter(
            or_(EventReport.title.ilike(f'%{search_query}%'),
                EventReport.description.ilike(f'%{search_query}%'),
                EventReport.lessons_learned.ilike(f'%{search_query}%'),
                EventReport.recommendations.ilike(f'%{search_query}%'))
        )
    if risk_level:
        query = query.filter(EventReport.risk_level == risk_level)

    reports = query.order_by(EventReport.date.desc()).limit(5).all()
    log.interaction_details = {'results_count': len(reports)}
    db.session.commit()

    return render_template('index.html', reports=reports)

@app.route('/report/<int:report_id>')
def view_report(report_id):
    report = EventReport.query.get_or_404(report_id)
    log = start_activity_tracking('view_report', report_id)
    g.activity_log = log

    # Add document details to the log
    log.interaction_details = {
        'document_type': 'event_report',
        'document_title': report.title,
        'document_date': report.date.strftime('%Y-%m-%d'),
        'risk_level': report.risk_level,
        'venue_type': report.venue_type,
        'location': report.location
    }
    db.session.commit()

    return render_template('view_report.html', report=report)

@app.route('/comparative-search')
def comparative_search():
    log = start_activity_tracking('comparative_search')
    g.activity_log = log

    filters = {
        'location': request.args.get('location', ''),
        'event_type': request.args.get('event_type', ''),
        'attendance_range': request.args.get('attendance_range', ''),
        'venue_type': request.args.get('venue_type', ''),
        'risk_level': request.args.get('risk_level', ''),
        'date_range': request.args.get('date_range', '')
    }
    log.filters_applied = {k: v for k, v in filters.items() if v}

    if not any(filters.values()):
        return render_template('comparative_search.html',
                             venue_types=get_venue_types(),
                             event_types=get_event_types(),
                             similar_events=[])

    query = EventReport.query

    if filters['location']:
        query = query.filter(EventReport.location.ilike(f"%{filters['location']}%"))
    if filters['event_type']:
        query = query.filter(EventReport.incident_type == filters['event_type'])
    if filters['venue_type']:
        query = query.filter(EventReport.venue_type == filters['venue_type'])
    if filters['risk_level']:
        query = query.filter(EventReport.risk_level == filters['risk_level'])

    if filters['attendance_range']:
        if filters['attendance_range'] == 'small':
            query = query.filter(EventReport.attendance < 1000)
        elif filters['attendance_range'] == 'medium':
            query = query.filter(EventReport.attendance.between(1000, 5000))
        elif filters['attendance_range'] == 'large':
            query = query.filter(EventReport.attendance.between(5000, 15000))
        elif filters['attendance_range'] == 'xlarge':
            query = query.filter(EventReport.attendance > 15000)

    if filters['date_range']:
        today = datetime.utcnow()
        if filters['date_range'] == 'recent':
            query = query.filter(EventReport.date >= today - timedelta(days=30))
        elif filters['date_range'] == 'past_3m':
            query = query.filter(EventReport.date >= today - timedelta(days=90))
        elif filters['date_range'] == 'past_6m':
            query = query.filter(EventReport.date >= today - timedelta(days=180))
        elif filters['date_range'] == 'past_year':
            query = query.filter(EventReport.date >= today - timedelta(days=365))

    similar_events = query.order_by(EventReport.date.desc()).limit(3).all()
    log.interaction_details = {'results_count': len(similar_events)}
    db.session.commit()

    return render_template('comparative_search.html',
                         similar_events=similar_events,
                         venue_types=get_venue_types(),
                         event_types=get_event_types())



@app.route('/compare-reports')
def compare_reports():
    """Handle report comparison functionality"""
    # Get all reports for selection
    reports = EventReport.query.order_by(EventReport.date.desc()).all()

    # Get selected report IDs from query parameters
    report1_id = request.args.get('report1')
    report2_id = request.args.get('report2')

    report1 = None
    report2 = None

    # If both reports are selected, fetch their data
    if report1_id and report2_id:
        report1 = EventReport.query.get_or_404(report1_id)
        report2 = EventReport.query.get_or_404(report2_id)

        # Log the comparison activity
        log = start_activity_tracking('compare_reports')
        log.interaction_details = {
            'report1_id': report1_id,
            'report2_id': report2_id
        }
        g.activity_log = log

    return render_template('report_comparison.html',
                         reports=reports,
                         report1=report1,
                         report2=report2,
                         report1_id=report1_id,
                         report2_id=report2_id)

@app.route('/access_logs')
def view_access_logs():
    logs = ActivityLog.query.order_by(ActivityLog.started_at.desc()).all()
    return render_template('access_log.html', logs=logs)

@app.route('/chat')
def chat():
    log = start_activity_tracking('chat')
    g.activity_log = log
    return render_template('chat.html')

@app.route('/chat_query', methods=['POST'])
def chat_query():
    try:
        query = request.json.get('query', '')
        event_query = EventReport.query

        # Process query using natural language
        events = event_query.limit(5).all()
        response = f"Based on your query: '{query}', here are some relevant events."

        # Format events for display
        event_list = []
        for event in events:
            event_list.append({
                'id': event.id,
                'title': event.title,
                'date': event.date.strftime('%Y-%m-%d'),
                'location': event.location,
                'risk_level': event.risk_level,
                'venue_type': event.venue_type,
                'attendance': event.attendance,
                'security_measures': event.security_measures[:150] if event.security_measures else None,
                'incidents_reported': event.incidents_reported,
                'incident_summary': event.incident_summary[:150] if event.incident_summary else None
            })

        return jsonify({
            'status': 'success',
            'response': response,
            'events': event_list
        })
    except Exception as e:
        logging.error(f"Error processing chat query: {str(e)}")
        return jsonify({
            'status': 'error',
            'response': 'Sorry, I encountered an error processing your query.',
            'events': []
        }), 500

@app.route('/templates')
def list_templates():
    templates = AssessmentTemplate.query.order_by(AssessmentTemplate.created_at.desc()).all()
    return render_template('templates/list.html', templates=templates)

@app.route('/templates/new', methods=['GET', 'POST'])
def create_template():
    if request.method == 'POST':
        try:
            template = AssessmentTemplate(
                title=request.form['title'],
                description=request.form['description'],
                template_type=request.form['template_type'],
                min_capacity=int(request.form.get('min_capacity', 0)),
                max_capacity=int(request.form.get('max_capacity', 0)),
                configuration=request.json.get('configuration', {}),
                security_requirements=request.json.get('security_requirements', []),
                risk_factors=request.json.get('risk_factors', []),
                mitigation_strategies=request.json.get('mitigation_strategies', [])
            )
            db.session.add(template)
            db.session.commit()
            return jsonify({'status': 'success', 'id': template.id})
        except Exception as e:
            logging.error(f"Error creating template: {str(e)}")
            return jsonify({'status': 'error', 'message': str(e)}), 500

    return render_template('templates/create.html')

@app.route('/templates/<int:template_id>')
def view_template(template_id):
    template = AssessmentTemplate.query.get_or_404(template_id)
    return render_template('templates/view.html', template=template)

@app.route('/templates/<int:template_id>/edit', methods=['GET', 'POST'])
def edit_template(template_id):
    template = AssessmentTemplate.query.get_or_404(template_id)
    if request.method == 'POST':
        try:
            template.title = request.form['title']
            template.description = request.form['description']
            template.template_type = request.form['template_type']
            template.min_capacity = int(request.form.get('min_capacity', 0))
            template.max_capacity = int(request.form.get('max_capacity', 0))
            template.configuration = request.json.get('configuration', {})
            template.security_requirements = request.json.get('security_requirements', [])
            template.risk_factors = request.json.get('risk_factors', [])
            template.mitigation_strategies = request.json.get('mitigation_strategies', [])
            template.updated_at = datetime.utcnow()

            db.session.commit()
            return jsonify({'status': 'success'})
        except Exception as e:
            logging.error(f"Error updating template: {str(e)}")
            return jsonify({'status': 'error', 'message': str(e)}), 500

    return render_template('templates/edit.html', template=template)

def get_venue_types():
    types = db.session.query(
        EventReport.venue_type
    ).filter(
        EventReport.venue_type.isnot(None)
    ).distinct().order_by(EventReport.venue_type).all()
    return [t[0] for t in types if t[0]]

def get_event_types():
    types = db.session.query(
        EventReport.incident_type
    ).filter(
        EventReport.incident_type.isnot(None)
    ).distinct().order_by(EventReport.incident_type).all()
    return [t[0] for t in types if t[0]]

@app.route('/report/<int:report_id>/export')
def export_report_pdf(report_id):
    """Export a report as PDF"""
    report = EventReport.query.get_or_404(report_id)

    # Log the export activity
    log = start_activity_tracking('export_report_pdf', report_id)
    g.activity_log = log

    # Generate HTML content
    html = render_template('pdf/report_pdf.html', report=report)

    # Create a temporary file for the PDF
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
        # Generate PDF from HTML
        pdf = weasyprint.HTML(string=html).write_pdf()
        tmp.write(pdf)
        tmp_path = tmp.name

    try:
        # Send the PDF file
        return send_file(
            tmp_path,
            download_name=f'report_{report.id}_{datetime.now().strftime("%Y%m%d")}.pdf',
            as_attachment=True,
            mimetype='application/pdf'
        )
    finally:
        # Clean up the temporary file after sending
        os.unlink(tmp_path)