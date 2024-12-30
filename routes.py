from flask import render_template, request, redirect, url_for, jsonify
from app import app, db
from models import EventReport, AccessLog
from datetime import datetime
import logging

@app.route('/')
def index():
    search_query = request.args.get('search', '')
    risk_level = request.args.get('risk_level', '')
    
    query = EventReport.query
    
    if search_query:
        query = query.filter(
            (EventReport.title.ilike(f'%{search_query}%')) |
            (EventReport.description.ilike(f'%{search_query}%'))
        )
    
    if risk_level:
        query = query.filter(EventReport.risk_level == risk_level)
        
    reports = query.order_by(EventReport.date.desc()).all()
    return render_template('index.html', reports=reports)

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
            purpose=data['purpose']
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
