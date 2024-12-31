import logging
import os
import traceback
from flask import render_template, request, redirect, url_for, jsonify, g, session
from app import app, db
from models import EventReport, ActivityLog, EventScenario, AssessmentTemplate
from datetime import datetime, timedelta
from sqlalchemy import or_, func, extract, and_
import uuid
from vector_store import vector_store
from chat_processor import process_natural_language_query, generate_response_summary

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

@app.route('/chat')
def chat():
    try:
        # Log environment and configuration
        logger.debug("=== Starting chat route handler ===")
        logger.debug(f"App instance path: {app.instance_path}")
        logger.debug(f"App root path: {app.root_path}")
        logger.debug(f"Template folder path: {app.template_folder}")
        logger.debug(f"Template folder exists: {os.path.exists(app.template_folder)}")

        templates = os.listdir(app.template_folder)
        logger.debug(f"Available templates: {templates}")
        logger.debug(f"chat.html exists: {'chat.html' in templates}")

        # Verify template inheritance
        logger.debug(f"base.html exists: {'base.html' in templates}")

        # Log Jinja environment
        logger.debug(f"Jinja loader: {app.jinja_loader}")
        logger.debug(f"Jinja environment: {app.jinja_env}")

        # Try rendering with debug info
        logger.debug("Attempting to render chat.html template")
        rendered = render_template('chat.html')
        logger.debug("Successfully rendered chat.html template")
        logger.debug(f"Rendered content length: {len(rendered)}")

        return rendered

    except Exception as e:
        logger.error("=== Template rendering error ===")
        logger.error(f"Error type: {type(e)}")
        logger.error(f"Error message: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")

        # Return a simple error page with debug information
        error_html = f"""
        <!DOCTYPE html>
        <html>
            <head>
                <title>Debug Info</title>
                <link href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css" rel="stylesheet">
            </head>
            <body class="bg-dark text-light">
                <div class="container py-5">
                    <h1>Template Debug Information</h1>
                    <div class="alert alert-danger">
                        <h4>Error Details:</h4>
                        <pre>{str(e)}</pre>
                    </div>
                    <div class="card bg-dark">
                        <div class="card-body">
                            <h4>Environment Information:</h4>
                            <ul>
                                <li>Template Folder: {app.template_folder}</li>
                                <li>Available Templates: {', '.join(os.listdir(app.template_folder))}</li>
                                <li>App Root Path: {app.root_path}</li>
                            </ul>
                        </div>
                    </div>
                </div>
            </body>
        </html>
        """
        return error_html, 500

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
    risk_levels = {
        'High': len([e for e in upcoming_events if e.risk_level == 'High']),
        'Medium': len([e for e in upcoming_events if e.risk_level == 'Medium']),
        'Low': len([e for e in upcoming_events if e.risk_level == 'Low'])
    }

    log.interaction_details = {'viewed_events_count': len(upcoming_events)}
    db.session.commit()

    return render_template('dashboard.html', 
                         upcoming_events=upcoming_events,
                         risk_levels=risk_levels)

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

@app.route('/scenario-builder')
def scenario_builder():
    log = start_activity_tracking('scenario_builder')
    g.activity_log = log

    template_id = request.args.get('template_id')
    template = None
    if template_id:
        template = AssessmentTemplate.query.get(template_id)
        log.interaction_details = {'template_id': template_id}
        db.session.commit()

    return render_template('scenario_builder.html', template=template)

@app.route('/access_logs')
def view_access_logs():
    logs = ActivityLog.query.order_by(ActivityLog.started_at.desc()).all()
    return render_template('access_log.html', logs=logs)

@app.route('/chat_query', methods=['POST'])
def chat_query():
    try:
        query = request.json.get('query', '')
        session_id = get_or_create_session_id()
        event_query = EventReport.query

        # Process query using natural language and vector store
        query_result, explanation = process_natural_language_query(
            query, 
            event_query, 
            session_id
        )
        events = query_result.limit(5).all()

        # Get relevant context from vector store for response generation
        similar_docs = vector_store.search_similar(query, limit=2)
        context = "\n".join([doc['content'] for doc in similar_docs])

        # Generate natural language response
        response = generate_response_summary(
            events, 
            explanation, 
            search_context=context,
            session_id=session_id
        )

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

@app.route('/save_scenario', methods=['POST'])
def save_scenario():
    try:
        data = request.json
        scenario = EventScenario(
            title=data['title'],
            elements=data['elements'],
            estimated_risk_level=calculate_scenario_risk(data['elements'])
        )
        db.session.add(scenario)
        db.session.commit()
        return jsonify({'status': 'success', 'id': scenario.id})
    except Exception as e:
        logging.error(f"Error saving scenario: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

def calculate_scenario_risk(elements):
    risk_levels = [element['riskLevel'] for element in elements]
    high_count = risk_levels.count('High')
    medium_count = risk_levels.count('Medium')
    if high_count > 0:
        return 'High'
    elif medium_count > 0:
        return 'Medium'
    return 'Low'

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