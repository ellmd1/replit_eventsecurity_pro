from flask import render_template, request, redirect, url_for, jsonify
from app import app, db
from models import EventReport, AccessLog
from datetime import datetime
import logging
from sqlalchemy import or_, func, extract, case

@app.route('/')
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

    reports = query.order_by(EventReport.date.desc()).all()
    return render_template('index.html', reports=reports)

@app.route('/comparative-search')
def comparative_search():
    location = request.args.get('location', '')
    event_type = request.args.get('event_type', '')
    attendance_range = request.args.get('attendance_range', '')
    venue_type = request.args.get('venue_type', '')

    # Get unique venue types from the database
    venue_types = db.session.query(
        EventReport.venue_type
    ).filter(
        EventReport.venue_type.isnot(None)
    ).distinct().order_by(EventReport.venue_type).all()
    venue_types = [vt[0] for vt in venue_types]

    # Get unique event types from the database
    event_types = db.session.query(
        EventReport.incident_type
    ).filter(
        EventReport.incident_type.isnot(None)
    ).distinct().order_by(EventReport.incident_type).all()
    event_types = [et[0] for et in event_types]

    query = EventReport.query

    # Apply filters based on search parameters
    if location:
        query = query.filter(EventReport.location.ilike(f'%{location}%'))
        logging.debug(f"Filtering by location: {location}")

    if event_type:
        query = query.filter(EventReport.incident_type == event_type)
        logging.debug(f"Filtering by event type: {event_type}")

    if venue_type:
        query = query.filter(EventReport.venue_type == venue_type)
        logging.debug(f"Filtering by venue type: {venue_type}")

    # Handle attendance ranges
    if attendance_range:
        logging.debug(f"Filtering by attendance range: {attendance_range}")
        if attendance_range == 'small':
            query = query.filter(EventReport.attendance < 1000)
        elif attendance_range == 'medium':
            query = query.filter(EventReport.attendance.between(1000, 5000))
        elif attendance_range == 'large':
            query = query.filter(EventReport.attendance.between(5000, 15000))
        elif attendance_range == 'xlarge':
            query = query.filter(EventReport.attendance > 15000)

    # Execute query and get results
    similar_events = query.order_by(EventReport.date.desc()).all()
    logging.debug(f"Found {len(similar_events)} matching events")

    # Log the IDs of found events for debugging
    if similar_events:
        event_ids = [event.id for event in similar_events]
        logging.debug(f"Found event IDs: {event_ids}")

    return render_template('comparative_search.html', 
                         similar_events=similar_events,
                         venue_types=venue_types,
                         event_types=event_types)

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

@app.route('/chat_query', methods=['POST'])
def chat_query():
    try:
        query = request.json.get('query', '').lower()

        # Initialize base query
        event_query = EventReport.query

        # Process natural language query
        if 'high risk' in query or 'highest risk' in query:
            event_query = event_query.filter(EventReport.risk_level == 'High')
        elif 'medium risk' in query or 'moderate risk' in query:
            event_query = event_query.filter(EventReport.risk_level == 'Medium')
        elif 'low risk' in query or 'lowest risk' in query:
            event_query = event_query.filter(EventReport.risk_level == 'Low')

        if 'recent' in query or 'latest' in query:
            event_query = event_query.order_by(EventReport.date.desc())

        if 'this year' in query:
            current_year = datetime.now().year
            event_query = event_query.filter(extract('year', EventReport.date) == current_year)

        # Search for specific venue types
        venue_types = ['stadium', 'arena', 'convention center', 'outdoor', 'indoor']
        for venue_type in venue_types:
            if venue_type in query:
                event_query = event_query.filter(EventReport.venue_type.ilike(f'%{venue_type}%'))

        # Search for specific event types
        if 'concert' in query:
            event_query = event_query.filter(EventReport.incident_type.ilike('%concert%'))
        elif 'sport' in query:
            event_query = event_query.filter(EventReport.incident_type.ilike('%sport%'))
        elif 'festival' in query:
            event_query = event_query.filter(EventReport.incident_type.ilike('%festival%'))

        # Handle attendance queries
        if 'large' in query and 'attendance' in query:
            event_query = event_query.filter(EventReport.attendance > 5000)
        elif 'small' in query and 'attendance' in query:
            event_query = event_query.filter(EventReport.attendance < 1000)

        # Get results
        events = event_query.limit(5).all()

        # Format response
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

        # Generate response message
        if events:
            response = f"I found {len(events)} relevant events based on your query."
        else:
            response = "I couldn't find any events matching your criteria. Try a different query?"

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