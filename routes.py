from flask import render_template, request, redirect, url_for, jsonify
from app import app, db
from models import EventReport, AccessLog, EventScenario # Added EventScenario import
from datetime import datetime
import logging
from sqlalchemy import or_, func, extract
from chat_processor import process_natural_language_query, generate_response_summary

@app.route('/')
def dashboard():
    # Get 5 upcoming events ordered by date
    upcoming_events = EventReport.query.order_by(EventReport.date.desc()).limit(5).all()
    
    # Calculate risk levels distribution for chart
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
    
    # Only get the 5 most recent reports
    reports = query.order_by(EventReport.date.desc()).limit(5).all()
    return render_template('index.html', reports=reports)

@app.route('/comparative-search')
def comparative_search():
    # Only show results if there are search parameters
    if not any(request.args.values()):
        return render_template('comparative_search.html', 
                             venue_types=get_venue_types(),
                             event_types=get_event_types(),
                             similar_events=[])
    
    location = request.args.get('location', '')
    event_type = request.args.get('event_type', '')
    attendance_range = request.args.get('attendance_range', '')
    venue_type = request.args.get('venue_type', '')
    
    query = EventReport.query
    
    if location:
        query = query.filter(EventReport.location.ilike(f'%{location}%'))
    if event_type:
        query = query.filter(EventReport.incident_type == event_type)
    if venue_type:
        query = query.filter(EventReport.venue_type == venue_type)
    if attendance_range:
        if attendance_range == 'small':
            query = query.filter(EventReport.attendance < 1000)
        elif attendance_range == 'medium':
            query = query.filter(EventReport.attendance.between(1000, 5000))
        elif attendance_range == 'large':
            query = query.filter(EventReport.attendance.between(5000, 15000))
        elif attendance_range == 'xlarge':
            query = query.filter(EventReport.attendance > 15000)
    
    similar_events = query.order_by(EventReport.date.desc()).all()
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
        event_query, explanation = process_natural_language_query(query, event_query)
        events = event_query.limit(5).all()
        response = generate_response_summary(events, explanation)
        
        event_list = []
        for event in events:
            event_list.append({
                'id': event.id,
                'title': event.title,
                'date': event.date.strftime('%Y-%m-%d'),
                'location': event.location,
                'risk_level': event.risk_level,
                'incident_type': event.incident_type,
                'attendance': event.attendance
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
    return render_template('scenario_builder.html')

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
    """Calculate overall risk level based on element risk levels"""
    risk_levels = [element['riskLevel'] for element in elements]
    high_count = risk_levels.count('High')
    medium_count = risk_levels.count('Medium')

    if high_count > 0:
        return 'High'
    elif medium_count > 0:
        return 'Medium'
    return 'Low'

@app.route('/report-comparison/<int:report1_id>/<int:report2_id>')
def compare_reports(report1_id, report2_id):
    report1 = EventReport.query.get_or_404(report1_id)
    report2 = EventReport.query.get_or_404(report2_id)

    # Calculate similarities and differences
    comparison = {
        'security_staff': {
            'difference': abs(report1.security_staff_count - report2.security_staff_count),
            'percentage': calculate_percentage_difference(report1.security_staff_count, report2.security_staff_count)
        },
        'incidents': {
            'difference': abs(report1.incidents_reported - report2.incidents_reported),
            'percentage': calculate_percentage_difference(report1.incidents_reported, report2.incidents_reported)
        },
        'attendance': {
            'difference': abs(report1.attendance - report2.attendance),
            'percentage': calculate_percentage_difference(report1.attendance, report2.attendance)
        }
    }

    return render_template('report_comparison.html', 
                         report1=report1, 
                         report2=report2,
                         comparison=comparison)

def calculate_percentage_difference(val1, val2):
    if not val1 or not val2:
        return 0
    try:
        avg = (val1 + val2) / 2
        return round(abs(val1 - val2) / avg * 100, 1)
    except ZeroDivisionError:
        return 0