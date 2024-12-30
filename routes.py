from flask import render_template, request, redirect, url_for, jsonify
from flask_socketio import SocketIO, emit
from app import app, db
from models import EventReport, AccessLog, EventScenario
from datetime import datetime, timedelta
import logging
from sqlalchemy import or_, func, extract, and_
from chat_processor import process_natural_language_query, generate_response_summary

# Initialize SocketIO
socketio = SocketIO(app)

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
    risk_levels = [element['riskLevel'] for element in elements]
    high_count = risk_levels.count('High')
    medium_count = risk_levels.count('Medium')
    if high_count > 0:
        return 'High'
    elif medium_count > 0:
        return 'Medium'
    return 'Low'

@app.route('/security-consultant')
def security_consultant():
    """Route for the real-time security consultant chat interface"""
    return render_template('security_consultant.html')

# WebSocket event handlers
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    logging.info('Client connected')
    emit('receive_message', {
        'message': 'Connected to Security Consultant. How can I assist you today?'
    })

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    logging.info('Client disconnected')

@socketio.on('send_message')
def handle_message(data):
    """Handle incoming messages"""
    message = data.get('message', '')
    logging.info(f'Received message: {message}')

    # Emit typing indicator
    emit('typing')

    try:
        # Process the message using the chat processor
        event_query = EventReport.query
        event_query, explanation = process_natural_language_query(message, event_query)
        events = event_query.limit(3).all()

        # Generate response based on the query and events
        response = generate_response_summary(events, explanation)

        # Send the response back to the client
        emit('receive_message', {'message': response})

        # If relevant events were found, send their details
        if events:
            event_summaries = []
            for event in events:
                summary = (f"Related Event: {event.title}\n"
                         f"Risk Level: {event.risk_level}\n"
                         f"Security Staff: {event.security_staff_count}\n"
                         f"Incidents: {event.incidents_reported}")
                event_summaries.append(summary)

            emit('receive_message', {
                'message': "\n\n".join(event_summaries)
            })

    except Exception as e:
        logging.error(f"Error processing message: {str(e)}")
        emit('receive_message', {
            'message': 'I apologize, but I encountered an error processing your request. Please try rephrasing your question.'
        })

@socketio.on('quick_action')
def handle_quick_action(data):
    """Handle quick action button clicks"""
    action = data.get('action')

    responses = {
        'risk_assessment': (
            "I'll help you assess security risks for your event. "
            "Please provide the following details:\n"
            "1. Expected attendance\n"
            "2. Venue type\n"
            "3. Event duration\n"
            "4. Any specific concerns"
        ),
        'emergency_plan': (
            "Let's create an emergency response plan. "
            "I'll need to know:\n"
            "1. Venue layout\n"
            "2. Number of exits\n"
            "3. Maximum capacity\n"
            "4. Available medical facilities"
        ),
        'staff_planning': (
            "I'll help you plan security staffing. "
            "Please share:\n"
            "1. Event type\n"
            "2. Expected attendance\n"
            "3. Venue size\n"
            "4. Duration of the event"
        ),
        'venue_analysis': (
            "Let's analyze your venue's security setup. "
            "Please provide:\n"
            "1. Venue type\n"
            "2. Total square footage\n"
            "3. Number of entry/exit points\n"
            "4. Existing security measures"
        )
    }

    response = responses.get(action, "I'll help you with that. What specific information do you need?")
    emit('receive_message', {'message': response})

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)