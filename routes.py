from flask import render_template, request, redirect, url_for, jsonify
from app import app, db
from models import EventReport, AccessLog
from datetime import datetime
import logging
from sqlalchemy import or_, func

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

    # If no search or filter is applied, show only the latest 5 reports
    if not search_query and not risk_level:
        reports = query.order_by(EventReport.date.desc()).limit(5).all()
    else:
        # When searching or filtering, show all matching reports
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

    if event_type:
        query = query.filter(EventReport.incident_type.ilike(f'%{event_type}%'))

    if venue_type:
        query = query.filter(EventReport.venue_type == venue_type)

    # Handle attendance ranges
    if attendance_range:
        if attendance_range == 'small':
            query = query.filter(EventReport.attendance < 1000)
        elif attendance_range == 'medium':
            query = query.filter(EventReport.attendance.between(1000, 5000))
        elif attendance_range == 'large':
            query = query.filter(EventReport.attendance.between(5000, 15000))
        elif attendance_range == 'xlarge':
            query = query.filter(EventReport.attendance > 15000)

    # Sort by date descending and get all matching events
    similar_events = query.order_by(EventReport.date.desc()).all() if any([location, event_type, attendance_range, venue_type]) else []

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