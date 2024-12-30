from flask import render_template, request, redirect, url_for, jsonify
from app import app, db
from models import EventReport, AccessLog, EventScenario, AssessmentTemplate
from datetime import datetime, timedelta
import logging
from sqlalchemy import or_, func, extract, and_

@app.route('/')
def dashboard():
    upcoming_events = EventReport.query.order_by(EventReport.date.desc()).limit(5).all()
    risk_levels = {
        'High': len([e for e in upcoming_events if e.risk_level == 'High']),
        'Medium': len([e for e in upcoming_events if e.risk_level == 'Medium']),
        'Low': len([e for e in upcoming_events if e.risk_level == 'Low'])
    }
    return render_template('dashboard.html', 
                         upcoming_events=upcoming_events,
                         risk_levels=risk_levels)

@app.route('/browse')
def index():
    search_query = request.args.get('search', '')
    risk_level = request.args.get('risk_level', '')
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
    return render_template('index.html', reports=reports)

@app.route('/comparative-search')
def comparative_search():
    if not any(request.args.values()):
        return render_template('comparative_search.html', 
                             venue_types=get_venue_types(),
                             event_types=get_event_types(),
                             similar_events=[])

    location = request.args.get('location', '')
    event_type = request.args.get('event_type', '')
    attendance_range = request.args.get('attendance_range', '')
    venue_type = request.args.get('venue_type', '')
    risk_level = request.args.get('risk_level', '')
    date_range = request.args.get('date_range', '')

    query = EventReport.query

    if location:
        query = query.filter(EventReport.location.ilike(f'%{location}%'))
    if event_type:
        query = query.filter(EventReport.incident_type == event_type)
    if venue_type:
        query = query.filter(EventReport.venue_type == venue_type)
    if risk_level:
        query = query.filter(EventReport.risk_level == risk_level)

    if attendance_range:
        if attendance_range == 'small':
            query = query.filter(EventReport.attendance < 1000)
        elif attendance_range == 'medium':
            query = query.filter(EventReport.attendance.between(1000, 5000))
        elif attendance_range == 'large':
            query = query.filter(EventReport.attendance.between(5000, 15000))
        elif attendance_range == 'xlarge':
            query = query.filter(EventReport.attendance > 15000)

    if date_range:
        today = datetime.utcnow()
        if date_range == 'recent':
            thirty_days_ago = today - timedelta(days=30)
            query = query.filter(EventReport.date >= thirty_days_ago)
        elif date_range == 'past_3m':
            three_months_ago = today - timedelta(days=90)
            query = query.filter(EventReport.date >= three_months_ago)
        elif date_range == 'past_6m':
            six_months_ago = today - timedelta(days=180)
            query = query.filter(EventReport.date >= six_months_ago)
        elif date_range == 'past_year':
            one_year_ago = today - timedelta(days=365)
            query = query.filter(EventReport.date >= one_year_ago)

    similar_events = query.order_by(EventReport.date.desc()).limit(3).all()

    return render_template('comparative_search.html',
                         similar_events=similar_events,
                         venue_types=get_venue_types(),
                         event_types=get_event_types())

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

@app.route('/report/<int:report_id>')
def view_report(report_id):
    report = EventReport.query.get_or_404(report_id)
    return render_template('view_report.html', report=report)

@app.route('/log_access', methods=['POST'])
def log_access():
    try:
        data = request.json
        access_log = AccessLog(
            event_report_id=data['report_id'],
            assessor_name=data['assessor_name'],
            purpose=data['purpose'],
            assessment_context=data['assessment_context'],
            similar_event_details=data['similar_event_details']
        )
        db.session.add(access_log)
        db.session.commit()
        return jsonify({'status': 'success'})
    except Exception as e:
        logging.error(f"Error logging access: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/access_logs')
def view_access_logs():
    logs = AccessLog.query.order_by(AccessLog.accessed_at.desc()).all()
    return render_template('access_log.html', logs=logs)

@app.route('/chat')
def chat():
    return render_template('chat.html')

@app.route('/chat_query', methods=['POST'])
def chat_query():
    try:
        query = request.json.get('query', '')
        event_query = EventReport.query

        # Process the query using the chat processor
        event_query, explanation = process_natural_language_query(query, event_query)
        events = event_query.limit(5).all()
        response = generate_response_summary(events, explanation)

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

@app.route('/scenario-builder')
def scenario_builder():
    template_id = request.args.get('template_id')
    template = None
    if template_id:
        template = AssessmentTemplate.query.get(template_id)
    return render_template('scenario_builder.html', template=template)

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