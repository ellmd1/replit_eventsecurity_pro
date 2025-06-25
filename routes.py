import json
import logging
import os
import tempfile
import uuid
from datetime import datetime, timedelta
from docx import Document
from flask import (
    abort,
    flash,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    send_from_directory,
    session,
    url_for,
)
from openai import OpenAI
from sqlalchemy import extract, func, or_, case
import weasyprint
from werkzeug.utils import secure_filename
from typing import List

from app import app, db
from models import (
    EventReport,
    SecurityDecision,
    AssessmentTemplate,
    SecurityInsight,
    ActivityLog,
    RiskAssessment,
)

# Configure logging
logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# ----- Event Card helpers -----
CARD_FIELDS: List[str] = [
    "title",
    "date",
    "location",
    "incident_type",
    "description",
    "risk_level",
    "venue_type",
    "attendance",
]


def _populate_event_card(event: "EventReport", form_data):
    """Populate or update the top-level Event Card fields on an EventReport."""
    for field in CARD_FIELDS:
        value = form_data.get(field)
        if field == "date":
            setattr(event, field, datetime.strptime(value, "%Y-%m-%d") if value else None)
        elif field == "attendance":
            setattr(event, field, int(value) if value else 0)
        else:
            setattr(event, field, value)


# ────────────────────────────────────────────────────────────────
#  Event Card stage
# ────────────────────────────────────────────────────────────────


@app.route("/event-card")
def event_card_select():
    """Stage-0: choose to create a new Event Card or edit an existing one."""
    cards = (
        EventReport.query.order_by(EventReport.date.desc())
        .with_entities(EventReport.id, EventReport.title, EventReport.date, EventReport.location)
        .all()
    )
    return render_template("event_card_select.html", cards=cards)


@app.route("/event-card/new", methods=["GET", "POST"])
def new_event_card():
    if request.method == "POST":
        event = EventReport()
        _populate_event_card(event, request.form)
        db.session.add(event)
        db.session.commit()
        flash("Event Card created. Add a risk assessment.", "success")
        return redirect(url_for("add_risk_assessment", event_id=event.id))
    return render_template("event_card_form.html", event=None)


@app.route("/event-card/<int:event_id>/edit", methods=["GET", "POST"])
def edit_event_card(event_id):
    event = EventReport.query.get_or_404(event_id)
    if request.method == "POST":
        _populate_event_card(event, request.form)
        db.session.commit()
        flash("Event Card updated. Continue to risk assessment.", "success")
        return redirect(url_for("add_risk_assessment", event_id=event.id))
    return render_template("event_card_form.html", event=event)


# ────────────────────────────────────────────────────────────────
#  Event Report Details stage
# ────────────────────────────────────────────────────────────────


@app.route("/event-report/<int:event_id>/build", methods=["GET", "POST"])
def build_event_report(event_id):
    """Stage-1: fill in the rest of the Event Report once an Event Card exists."""
    report = EventReport.query.get_or_404(event_id)
    if request.method == "POST":
        try:
            # Re-use logic from original create_event_report POST handler for lower fields
            attendance_str = request.form.get("attendance")  # may come back again; safe
            staff_count_str = request.form.get("security_staff_count")
            incidents_str = request.form.get("incidents_reported")

            report.description = request.form.get("description")
            report.risk_level = request.form.get("risk_level") or report.risk_level
            report.venue_type = request.form.get("venue_type") or report.venue_type
            report.attendance = int(attendance_str) if attendance_str and attendance_str.isdigit() else report.attendance
            report.security_staff_count = (
                int(staff_count_str) if staff_count_str and staff_count_str.isdigit() else report.security_staff_count
            )
            report.incidents_reported = (
                int(incidents_str) if incidents_str and incidents_str.isdigit() else report.incidents_reported
            )
            report.security_protocols = request.form.get("security_protocols")
            report.emergency_response_plan = request.form.get("emergency_response_plan")

            db.session.commit()
            flash("Event report details saved!", "success")
            return redirect(url_for("view_report", report_id=report.id))
        except Exception as e:
            logger.error(f"Error updating event report details: {e}")
            flash("Error saving details. Please check the inputs and try again.", "danger")

    return render_template("event_report_details.html", report=report)


@app.route("/create-risk-assessment")
def create_risk_assessment():
    """Render the page to create a new risk assessment"""
    return render_template("create_risk_assessment.html")


@app.route("/create-event-report", methods=["GET", "POST"])
def create_event_report():
    """Render the page to create a new event report and handle form submission"""
    if request.method == "POST":
        try:
            date_str = request.form.get("date")
            attendance_str = request.form.get("attendance")
            staff_count_str = request.form.get("security_staff_count")
            incidents_str = request.form.get("incidents_reported")

            report_data = {
                'title': request.form.get("title"),
                'date': datetime.strptime(date_str, "%Y-%m-%d") if date_str else None,
                'location': request.form.get("location"),
                'description': request.form.get("description"),
                'risk_level': request.form.get("risk_level"),
                'incident_type': request.form.get("incident_type"),
                'venue_type': request.form.get("venue_type"),
                'attendance': int(attendance_str) if attendance_str and attendance_str.isdigit() else 0,
                'security_staff_count': int(staff_count_str) if staff_count_str and staff_count_str.isdigit() else 0,
                'incidents_reported': int(incidents_str) if incidents_str and incidents_str.isdigit() else 0,
                'security_measures': request.form.get("security_measures"),
                'security_protocols': request.form.get("security_protocols"),
                'emergency_response_plan': request.form.get("emergency_response_plan"),
                'lessons_learned': request.form.get("lessons_learned"),
                'recommendations': request.form.get("recommendations"),
                'incident_response': request.form.get("incident_response"),
            }
            new_report = EventReport(**report_data)
            db.session.add(new_report)
            db.session.commit()
            flash("Event report created successfully!", "success")
            return redirect(url_for("view_report", report_id=new_report.id))
        except Exception as e:
            logger.error(f"Error creating event report: {e}")
            flash("Error creating report. Please check the data and try again.", "danger")

    # For create mode, explicitly pass report as None so the template can conditionally
    # render form fields without errors when accessing the variable.
    return render_template("create_event_report.html", report=None)


@app.route("/edit-event-report/<int:report_id>", methods=["GET", "POST"])
def edit_event_report(report_id):
    """Edit an existing event report"""
    report = EventReport.query.get_or_404(report_id)

    if request.method == "POST":
        try:
            # Update fields from form
            report.title = request.form.get("title")
            date_str = request.form.get("date")
            report.date = datetime.strptime(date_str, "%Y-%m-%d") if date_str else report.date
            report.location = request.form.get("location")
            report.description = request.form.get("description")
            report.risk_level = request.form.get("risk_level")
            report.incident_type = request.form.get("incident_type")
            report.venue_type = request.form.get("venue_type")
            attendance = request.form.get("attendance")
            report.attendance = int(attendance) if attendance else None
            report.security_staff_count = int(request.form.get("security_staff_count", 0))
            report.incidents_reported = int(request.form.get("incidents_reported", 0))
            report.security_measures = request.form.get("security_measures")
            report.security_protocols = request.form.get("security_protocols")
            report.emergency_response_plan = request.form.get("emergency_response_plan")
            report.lessons_learned = request.form.get("lessons_learned")
            report.recommendations = request.form.get("recommendations")
            report.incident_response = request.form.get("incident_response")

            db.session.commit()
            flash("Report updated successfully!", "success")
            return redirect(url_for("view_report", report_id=report.id))
        except Exception as e:
            logger.error(f"Error updating event report: {e}")
            flash("Error updating report. Please check the data and try again.", "danger")

    # GET
    return render_template("create_event_report.html", report=report)


# Template Management Routes
@app.route("/templates")
def list_templates():
    templates = AssessmentTemplate.query.order_by(
        AssessmentTemplate.created_at.desc()
    ).all()
    return render_template("templates/list.html", templates=templates)


@app.route("/templates/new", methods=["GET", "POST"])
def create_template():
    if request.method == "POST":
        try:
            data = request.form
            security_requirements_str = data.get("security_requirements", '[]')
            risk_factors_str = data.get("risk_factors", '[]')
            mitigation_strategies_str = data.get("mitigation_strategies", '[]')

            security_requirements = json.loads(security_requirements_str)
            risk_factors = json.loads(risk_factors_str)
            mitigation_strategies = json.loads(mitigation_strategies_str)

            template_data = {
                "title": data.get("title"),
                "description": data.get("description"),
                "template_type": data.get("template_type"),
                "min_capacity": int(data.get("min_capacity", 0)),
                "max_capacity": int(data.get("max_capacity", 0)),
                "security_requirements": security_requirements,
                "risk_factors": risk_factors,
                "mitigation_strategies": mitigation_strategies,
                "is_default": False,
                "configuration": {
                    "version": "1.0",
                    "created_at": datetime.utcnow().isoformat(),
                    "last_modified": datetime.utcnow().isoformat()
                }
            }

            template = AssessmentTemplate(**template_data)

            db.session.add(template)
            db.session.commit()

            logger.info(f"Created new template: {template.id}")
            return jsonify({"status": "success", "id": template.id})

        except Exception as e:
            logger.error(f"Error creating template: {str(e)}")
            return jsonify({"status": "error", "message": str(e)}), 500

    return render_template("templates/create.html")


@app.route("/templates/<int:template_id>")
def view_template(template_id):
    template = AssessmentTemplate.query.get_or_404(template_id)
    return render_template("templates/view.html", template=template)


@app.route("/templates/<int:template_id>/edit", methods=["GET", "POST"])
def edit_template(template_id):
    template = AssessmentTemplate.query.get_or_404(template_id)
    if request.method == "POST":
        try:
            data = request.form
            config = request.json
            template.title = data.get("title", template.title)
            template.description = data.get("description", template.description)
            template.template_type = data.get("template_type", template.template_type)
            template.min_capacity = int(data.get("min_capacity", template.min_capacity))
            template.max_capacity = int(data.get("max_capacity", template.max_capacity))
            if config:
                template.configuration = config.get("configuration", template.configuration)
                template.security_requirements = config.get(
                    "security_requirements", template.security_requirements
                )
                template.risk_factors = config.get("risk_factors", template.risk_factors)
                template.mitigation_strategies = config.get(
                    "mitigation_strategies", template.mitigation_strategies
                )
            template.updated_at = datetime.utcnow()

            db.session.commit()
            return jsonify({"status": "success"})
        except Exception as e:
            logger.error(f"Error updating template: {str(e)}")
            return jsonify({"status": "error", "message": str(e)}), 500

    return render_template("templates/edit.html", template=template)

# Report and Export Routes
@app.route("/report/<int:report_id>/export")
def export_report_pdf(report_id):
    """Export a report as PDF"""
    report = EventReport.query.get_or_404(report_id)

    # Log the export activity
    log = start_activity_tracking("export_report_pdf", event_report_id=report_id)
    g.activity_log = log

    # Generate HTML content
    html = render_template("pdf/report_pdf.html", report=report, datetime=datetime)

    # Create a temporary file for the PDF
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        # Generate PDF from HTML
        pdf = weasyprint.HTML(string=html).write_pdf()
        if pdf:
            tmp.write(pdf)
        tmp_path = tmp.name

    try:
        # Send the PDF file
        return send_file(
            tmp_path,
            download_name=f"report_{report.id}_{datetime.now().strftime('%Y%m%d')}.pdf",
            as_attachment=True,
            mimetype="application/pdf",
        )
    finally:
        # Clean up the temporary file after sending
        os.unlink(tmp_path)


@app.route("/export-decisions")
def export_decisions():
    """Export all decisions as PDF"""
    try:
        decisions = SecurityDecision.query.order_by(SecurityDecision.created_at.desc()).all()

        # Log the export activity
        log = start_activity_tracking(activity_type="export_decisions_pdf")
        g.activity_log = log

        # Generate HTML content
        html = render_template(
            "pdf/decision_log_pdf.html",
            decisions=decisions,
            datetime=datetime
        )

        # Create a temporary file for the PDF
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            # Generate PDF from HTML
            pdf = weasyprint.HTML(string=html).write_pdf()
            if pdf:
                tmp.write(pdf)
            tmp_path = tmp.name

        try:
            # Send the PDF file
            return send_file(
                tmp_path,
                download_name=f"decision_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                as_attachment=True,
                mimetype="application/pdf",
            )
        finally:
            # Clean up the temporary file after sending
            os.unlink(tmp_path)
    except Exception as e:
        logger.error(f"Error exporting decisions: {str(e)}")
        abort(500)


@app.route("/report/<int:report_id>/save-to-decision", methods=["POST"])
def save_report_to_decision(report_id):
    """Save a report as a decision in the decision log"""
    try:
        report = EventReport.query.get_or_404(report_id)

        # Create the decision entry
        decision = SecurityDecision.from_report(
            report,
            description=f"""Report Documentation: {report.title}

Risk Level: {report.risk_level}
Location: {report.location}
Date: {report.date.strftime('%Y-%m-%d')}

Description: {report.description}

Additional Notes: {request.form.get('description', '')}""",
            decision_type=request.form.get("decision_type", "Report Documentation"),
            author=request.form.get("author", "System (Report Save)")
        )

        db.session.add(decision)
        db.session.commit()

        logger.info(f"Saved report {report_id} to decision log as decision {decision.id}")

        # For AJAX requests, return JSON response
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({"status": "success", "decision_id": decision.id})

        # For regular form submissions, redirect back to report view
        flash("Report successfully saved to decision log", "success")
        return redirect(url_for('view_report', report_id=report_id))

    except Exception as e:
        logger.error(f"Error saving report to decision: {str(e)}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({"status": "error", "message": str(e)}), 500
        flash(f"Error saving to decision log: {str(e)}", "error")
        return redirect(url_for('view_report', report_id=report_id))

# Activity Tracking Functions
def get_or_create_session_id():
    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())
    return session["session_id"]


def start_activity_tracking(activity_type, event_report_id=None):
    """Start tracking a user activity and return the log entry"""
    log_data = {
        "activity_type": activity_type,
        "event_report_id": event_report_id,
        "user_identifier": request.remote_addr,
        "session_id": get_or_create_session_id(),
        "interaction_details": {
            "user_agent": request.user_agent.string
        }
    }
    log = ActivityLog(**log_data)
    db.session.add(log)
    db.session.commit()
    return log


def end_activity_tracking(log):
    log.end_activity()
    db.session.commit()
    return log

# Request Hooks
@app.before_request
def before_request():
    g.start_time = datetime.utcnow()
    g.activity_log = None


@app.after_request
def after_request(response):
    if hasattr(g, "activity_log") and g.activity_log:
        end_activity_tracking(g.activity_log)
    return response

# Main Routes
@app.route("/")
def dashboard():
    log = start_activity_tracking("dashboard_view")
    g.activity_log = log

    upcoming_events = EventReport.query.order_by(EventReport.date.desc()).limit(5).all()
    recent_decisions = SecurityDecision.query.order_by(SecurityDecision.created_at.desc()).limit(5).all()

    # Get high-risk events and security threats
    high_risk_events = EventReport.query.filter(
        EventReport.risk_level == "High", EventReport.date >= datetime.utcnow()
    ).order_by(EventReport.date).limit(3).all()

    security_threats = []
    for event in high_risk_events:
        if event.security_measures:
            threats = {
                "event": event.title,
                "date": event.date,
                "location": event.location,
                "risk_level": event.risk_level,
                "measures": event.security_measures[:200] + "..."
                if len(event.security_measures) > 200
                else event.security_measures,
            }
            security_threats.append(threats)

    risk_levels = {
        "High": len([e for e in upcoming_events if e.risk_level == "High"]),
        "Medium": len([e for e in upcoming_events if e.risk_level == "Medium"]),
        "Low": len([e for e in upcoming_events if e.risk_level == "Low"]),
    }

    log.interaction_details = {
        "viewed_events_count": len(upcoming_events),
        "viewed_decisions_count": len(recent_decisions),
        "security_threats_count": len(security_threats),
    }
    db.session.commit()

    return render_template(
        "dashboard.html",
        upcoming_events=upcoming_events,
        recent_decisions=recent_decisions,
        risk_levels=risk_levels,
        security_threats=security_threats,
    )

# Insights Routes and Functions
@app.route("/insights")
def insights():
    """Display the AI insights page"""
    insights = SecurityInsight.query.order_by(SecurityInsight.created_at.desc()).limit(6).all()
    return render_template("insights.html", insights=insights)


@app.route("/generate_insights", methods=["POST"])
def generate_insights():
    """Generate AI-powered insights for selected events"""
    try:
        json_data = request.get_json()
        if not json_data:
            return jsonify({"status": "error", "message": "Invalid JSON payload"}), 400

        event_ids = json_data.get("event_ids", [])
        if not event_ids:
            return jsonify({"status": "error", "message": "No event IDs provided"}), 400

        insights_request = json_data.get("request", "general")
        logger.info("Starting insights generation process")

        # Verify OpenAI API key
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            logger.error("OpenAI API key not found")
            return jsonify({"status": "error",
                            "message": "OpenAI API key not configured. Please check your environment settings."
                           }), 500

        # Fetch relevant data from database
        try:
            events = EventReport.query.filter(EventReport.id.in_(event_ids)).all()
            decisions = SecurityDecision.query.filter(SecurityDecision.event_report_id.in_(event_ids)).all()
            logger.info(f"Retrieved {len(events)} events and {len(decisions)} decisions for analysis")
        except Exception as db_error:
            logger.error(f"Database error: {str(db_error)}")
            return jsonify({
                "status": "error",
                "message": "Error accessing database. Please try again."
            }), 500

        # Prepare data for analysis
        try:
            events_data = [
                {
                    "title": event.title,
                    "date": event.date.strftime("%Y-%m-%d"),
                    "risk_level": event.risk_level,
                    "location": event.location,
                    "attendance": event.attendance,
                    "incidents_reported": event.incidents_reported,
                    "incident_summary": event.incident_summary[:200] if event.incident_summary else None,
                    "security_measures": event.security_measures[:200] if event.security_measures else None,
                    "venue_type": event.venue_type
                }
                for event in events
            ]

            decisions_data = [
                {
                    "description": decision.description[:200] if decision.description else None,
                    "created_at": decision.created_at.strftime("%Y-%m-%d"),
                    "outcome": decision.outcome[:200] if hasattr(decision, "outcome") and decision.outcome else None,
                    "effectiveness": decision.effectiveness if hasattr(decision, "effectiveness") else None
                }
                for decision in decisions
            ]
            logger.info("Data prepared for analysis")
        except Exception as prep_error:
            logger.error(f"Error preparing data: {str(prep_error)}")
            return jsonify({
                "status": "error",
                "message": "Error preparing data for analysis. Please try again."
            }), 500

        # Create prompt for OpenAI
        analysis_prompt = f"""As a security analyst, analyze this event and decision data:

Events Data: {json.dumps(events_data)}
Decisions Data: {json.dumps(decisions_data)}

Generate security insights following this JSON structure:
{{
    "insights": [
        {{
            "title": "Brief insight title",
            "description": "Detailed analysis of the insight",
            "data": [
                "Key finding 1",
                "Key finding 2",
                "Key finding 3"
            ],
            "icon": "One of: alert-circle, trending-up, shield, users, calendar"
        }}
    ]
}}"""

        # Get insights from OpenAI
        try:
            logger.info("Sending request to OpenAI")
            response = client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a security analyst. You must respond with a valid JSON object following the exact structure specified in the user's prompt. Do not include any additional text or explanation outside of the JSON object."
                    },
                    {"role": "user", "content": analysis_prompt}
                ],
                max_tokens=2000,
                temperature=0.7
            )
            logger.info("Received response from OpenAI")
        except Exception as openai_error:
            logger.error(f"OpenAI API error: {str(openai_error)}")
            return jsonify({
                "status": "error",
                "message": "Error communicating with AI service. Please try again."
            }), 500

        # Parse the response and save insights
        try:
            response_content = response.choices[0].message.content or "{}"
            insights_data = json.loads(response_content)
            logger.info(f"Parsed OpenAI response: {insights_data}")

            if not isinstance(insights_data, dict) or 'insights' not in insights_data:
                raise ValueError("Invalid response format from OpenAI")

            # Delete existing insights before adding new ones
            SecurityInsight.query.delete()

            # Save new insights to database
            for result in insights_data['insights']:
                key_findings_str = result.get("data")
                key_findings = json.loads(key_findings_str) if isinstance(key_findings_str, str) else []

                # Store the generated insight
                insight_data = {
                    "title": f"AI Insight for Events: {', '.join(map(str, event_ids))}",
                    "description": result.get('description', ''),
                    "key_findings": key_findings,
                    "icon": "cpu",
                }
                insight = SecurityInsight(**insight_data)
                db.session.add(insight)

            db.session.commit()
            logger.info("Successfully saved insights to database")
            return jsonify({
                "status": "success",
                "message": "New insights generated successfully"
            })

        except json.JSONDecodeError as json_error:
            logger.error(f"JSON parsing error: {str(json_error)}")
            return jsonify({
                "status": "error",
                "message": "Error processing AI response. Please try again."
            }), 500
        except Exception as save_error:
            logger.error(f"Database save error: {str(save_error)}")
            return jsonify({
                "status": "error",
                "message": "Error saving insights. Please try again."
            }), 500

    except Exception as e:
        logger.error(f"Unexpected error in generate_insights: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "An unexpected error occurred. Please try again."
        }), 500

# Utility Functions
def get_venue_types():
    """Get unique venue types from the database"""
    types = (
        db.session.query(EventReport.venue_type)
        .filter(EventReport.venue_type.isnot(None))
        .distinct()
        .order_by(EventReport.venue_type)
        .all()
    )
    return [t[0] for t in types if t[0]]


def get_event_types():
    """Get unique event types from the database"""
    types = (
        db.session.query(EventReport.incident_type)
        .filter(EventReport.incident_type.isnot(None))
        .distinct()
        .order_by(EventReport.incident_type)
        .all()
    )
    return [t[0] for t in types if t[0]]


def summarize_file_content(file_path, file_type):
    """Summarize file content using GPT"""
    try:
        content = ""
        logger.info(f"Attempting to read file: {file_path} of type: {file_type}")

        # Handle different file types
        if file_type.startswith("image/"):
            return f"[Image File] Type: {file_type}"

        elif file_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            try:
                doc = Document(file_path)
                content = "\n".join([paragraph.text for paragraph in doc.paragraphs])
                logger.info("Successfully extracted content from DOCX file")
            except Exception as e:
                logger.error(f"Error reading DOCX file: {str(e)}")
                return "Error reading DOCX file"

        elif file_type.startswith("text/") or "text" in file_type:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                logger.info("Successfully read text file")
            except UnicodeDecodeError:
                # Try binary mode if text mode fails
                with open(file_path, "rb") as f:
                    content = f.read().decode("utf-8", errors="ignore")
                logger.info("Successfully read file in binary mode")

        elif file_type == "application/pdf":
            # For now, return a message for PDF files
            return "PDF file uploaded (content extraction not supported)"

        if not content.strip():
            logger.warning(f"No content extracted from file of type: {file_type}")
            return f"File uploaded successfully (type: {file_type})"

        logger.info("Sending content to GPT for summarization")
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that summarizes documents. Provide a concise summary of the content.",
                },
                {
                    "role": "user",
                    "content": f"Please summarize this document content in 2-3 sentences:\n\n{content[:4000]}",  # Limit content length
                },
            ],
            max_tokens=150,
        )

        summary = response.choices[0].message.content
        logger.info("Successfully generated summary")
        return summary

    except Exception as e:
        logger.error(f"Error in summarize_file_content: {str(e)}")
        return f"File uploaded successfully, but summary generation failed: {str(e)}"


@app.route("/decisions", methods=["GET", "POST"])
def decision_log():
    if request.method == "POST":
        try:
            # Handle JSON requests from chat save functionality
            if request.is_json:
                data = request.get_json()
                if not data:
                    return jsonify({"status": "error", "message": "Invalid JSON"}), 400
                decision_data = {
                    "description": data.get("description", ""),
                    "author": data.get("author", "Anonymous"),
                }
                decision = SecurityDecision(**decision_data)  # type: ignore
                db.session.add(decision)
                db.session.commit()
                return jsonify({"status": "success", "id": decision.id})

            # Handle form data and file uploads
            if not os.path.exists(app.config["UPLOAD_FOLDER"]):
                os.makedirs(app.config["UPLOAD_FOLDER"])

            uploaded_files = request.files.getlist("attachments")
            file_metadata = []
            summaries = []

            for file in uploaded_files:
                if file and file.filename:
                    try:
                        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_")
                        original_filename = secure_filename(file.filename)
                        filename = timestamp + original_filename
                        file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                        file.save(file_path)

                        summary = summarize_file_content(file_path, file.content_type)
                        summaries.append(summary)

                        file_metadata.append({
                                "filename": filename,
                                "original_filename": original_filename,
                                "file_path": file_path,
                                "file_type": file.content_type,
                                "file_size": os.path.getsize(file_path),
                                "uploaded_at": datetime.utcnow().isoformat(),
                            })
                    except Exception as e:
                        logger.error(f"Error processing file {file.filename}: {str(e)}")
                        return jsonify({"status": "error", "message": f"Error processing file {file.filename}"}), 500

            description = request.form.get("description", "")
            if summaries:
                description = description or "File upload"
                description += "\\n\\nFile Summaries:\\n" + "\\n\\n".join(summaries)

            decision_data = {
                "description": description,
                "author": request.form.get("author", "Anonymous"),
            }
            decision = SecurityDecision(**decision_data)  # type: ignore

            for metadata in file_metadata:
                decision.add_attachment(
                    metadata["filename"],
                    metadata["file_path"],
                    metadata["file_type"],
                    metadata["file_size"],
                )

            db.session.add(decision)
            db.session.commit()

            return jsonify({
                    "status": "success",
                    "decision": {
                        "id": decision.id,
                        "description": decision.description,
                        "author": decision.author,
                        "created_at": decision.created_at.strftime("%d/%m/%Y, %H:%M:%S"),
                        "attachments": [
                            {"filename": att["filename"], "uploaded_at": att["uploaded_at"], "file_type": att["file_type"]}
                            for att in decision.attachments
                        ] if decision.attachments else [],
                    },
                })
        except Exception as e:
            logger.error(f"Error in decision_log POST handler: {str(e)}")
            # For now, we'll just log the error and continue
            pass

    # GET request - display the log
    decisions = SecurityDecision.query.order_by(SecurityDecision.created_at.desc()).all()
    return render_template("decision_log.html", decisions=decisions)

@app.route("/decision/attachment/<path:filename>")
def download_attachment(filename):
    """Download an attachment file"""
    try:
        return send_from_directory(
            app.config["UPLOAD_FOLDER"], filename, as_attachment=True
        )
    except Exception as e:
        logger.error(f"Error downloading attachment: {str(e)}")
        abort(404)


@app.route("/view-all-events")
def view_all_events():
    events = EventReport.query.all()
    return render_template("index.html", reports=events)

@app.route("/browse")
def index():
    search_query = request.args.get("search", "")
    risk_level = request.args.get("risk_level", "")

    log = start_activity_tracking("browse_events")
    g.activity_log = log
    log.search_query = search_query
    log.filters_applied = {"risk_level": risk_level} if risk_level else {}

    query = EventReport.query
    if search_query:
        query = query.filter(
            or_(
                EventReport.title.ilike(f"%{search_query}%"),
                EventReport.description.ilike(f"%{search_query}%"),
                EventReport.lessons_learned.ilike(f"%{search_query}%"),
                EventReport.recommendations.ilike(f"%{search_query}%"),
            )
        )
    if risk_level:
        query = query.filter(EventReport.risk_level == risk_level)

    reports = query.order_by(EventReport.date.desc()).all()
    log.interaction_details = {"results_count": len(reports)}
    db.session.commit()

    return render_template("index.html", reports=reports)


@app.route("/report/<int:report_id>")
def view_report(report_id):
    report = EventReport.query.get_or_404(report_id)
    log = start_activity_tracking("view_report", report_id)
    g.activity_log = log

    # Add document details to the log
    log.interaction_details = {
        "document_type": "event_report",
        "document_title": report.title,
        "document_date": report.date.strftime("%Y-%m-%d"),
        "risk_level": report.risk_level,
        "venue_type": report.venue_type,
        "location": report.location,
    }
    db.session.commit()

    return render_template("view_report.html", report=report)


@app.route("/comparative-search")
def comparative_search():
    log = start_activity_tracking("comparative_search")
    g.activity_log = log

    filters = {
        "location": request.args.get("location", ""),
        "event_type": request.args.get("event_type", ""),
        "attendance_range": request.args.get("attendance_range", ""),
        "venue_type": request.args.get("venue_type", ""),
        "risk_level": request.args.get("risk_level", ""),
        "date_range": request.args.get("date_range", ""),
    }
    log.filters_applied = {k: v for k, v in filters.items() if v}

    if not any(filters.values()):
        return render_template(
            "comparative_search.html",
            venue_types=get_venue_types(),
            event_types=get_event_types(),
            similar_events=[],
        )

    query = EventReport.query

    if filters["location"]:
        query = query.filter(EventReport.location.ilike(f"%{filters['location']}%"))
    if filters["event_type"]:
        query = query.filter(EventReport.incident_type == filters["event_type"])
    if filters["venue_type"]:
        query = query.filter(EventReport.venue_type == filters["venue_type"])
    if filters["risk_level"]:
        query = query.filter(EventReport.risk_level == filters["risk_level"])

    if filters["attendance_range"]:
        if filters["attendance_range"] == "small":
            query = query.filter(EventReport.attendance < 1000)
        elif filters["attendance_range"] == "medium":
            query = query.filter(EventReport.attendance.between(1000, 5000))
        elif filters["attendance_range"] == "large":
            query = query.filter(EventReport.attendance.between(5000, 15000))
        elif filters["attendance_range"] == "xlarge":
            query = query.filter(EventReport.attendance > 15000)

    if filters["date_range"]:
        today = datetime.utcnow()
        if filters["date_range"] == "recent":
            query = query.filter(EventReport.date >= today - timedelta(days=30))
        elif filters["date_range"] == "past_3m":
            query = query.filter(EventReport.date >= today - timedelta(days=90))
        elif filters["date_range"] == "past_6m":
            query = query.filter(EventReport.date >= today - timedelta(days=180))
        elif filters["date_range"] == "past_year":
            query = query.filter(EventReport.date >= today - timedelta(days=365))

    similar_events = query.order_by(EventReport.date.desc()).limit(3).all()
    log.interaction_details = {"results_count": len(similar_events)}
    db.session.commit()

    return render_template(
        "comparative_search.html",
        similar_events=similar_events,
        venue_types=get_venue_types(),
        event_types=get_event_types(),
    )


@app.route("/compare-reports")
def compare_reports():
    """Handle report comparison functionality"""
    # Get all reports for selection
    reports = EventReport.query.order_by(EventReport.date.desc()).all()

    # Get selected report IDs from query parameters
    report1_id = request.args.get("report1")
    report2_id = request.args.get("report2")

    report1 = None
    report2 = None

    # If both reports are selected, fetch their data
    if report1_id and report2_id:
        report1 = EventReport.query.get_or_404(report1_id)
        report2 = EventReport.query.get_or_404(report2_id)

        # Log the comparison activity
        log = start_activity_tracking("compare_reports")
        log.interaction_details = {"report1_id": report1_id, "report2_id": report2_id}
        g.activity_log = log

    return render_template(
        "report_comparison.html",
        reports=reports,
        report1=report1,
        report2=report2,
        report1_id=report1_id,
        report2_id=report2_id,
    )

# Access Logs and Chat Routes
@app.route("/access_logs")
def view_access_logs():
    logs = ActivityLog.query.order_by(ActivityLog.started_at.desc()).all()
    return render_template("access_log.html", logs=logs)


@app.route("/document-library")
def document_library():
    """Render the document library page"""
    return render_template("document_library.html")


@app.route("/chat")
def chat():
    log = start_activity_tracking("chat")
    g.activity_log = log
    return render_template("chat.html")


@app.route("/chat_query", methods=["POST"])
def chat_query():
    try:
        json_data = request.get_json()
        if not json_data:
            return jsonify({"status": "error", "message": "Invalid JSON payload"}), 400
        query = json_data.get("query")
        logger.info(f"Received chat query: {query}")

        # First, get relevant events
        event_query = EventReport.query
        events = event_query.limit(5).all()

        # Format events data for GPT context
        events_context = []
        for event in events:
            event_info = {
                "title": event.title,
                "date": event.date.strftime("%Y-%m-%d"),
                "location": event.location,
                "risk_level": event.risk_level,
                "venue_type": event.venue_type,
                "attendance": event.attendance,
                "incidents_reported": event.incidents_reported,
                "incident_summary": event.incident_summary[:150] if event.incident_summary else None,
                "security_measures": event.security_measures[:150] if event.security_measures else None,
            }
            events_context.append(event_info)

        # Create message for GPT
        system_message = """You are a helpful public event safety risk assessment assistant. 
        You help users understand event safety information and provide insights about security measures. 
        Be concise but informative in your responses. When discussing events, focus on safety aspects 
        and risk management. Format your response in a conversational tone."""

        # Prepare the context and query for GPT
        context_message = (
            f"Here is information about recent events:\n{str(events_context)}\n\nUser query: {query}"
        )

        logger.info("Sending request to GPT")
        response = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": context_message},
            ],
            max_tokens=300,
            temperature=0.7,
        )

        ai_response = response.choices[0].message.content
        logger.info("Successfully received GPT response")

        # Format events for display
        event_list = []
        for event in events:
            event_list.append(
                {
                    "id": event.id,
                    "title": event.title,
                    "date": event.date.strftime("%Y-%m-%d"),
                    "location": event.location,
                    "risk_level": event.risk_level,
                    "venue_type": event.venue_type,
                    "attendance": event.attendance,
                    "security_measures": event.security_measures[:150]
                    if event.security_measures
                    else None,
                    "incidents_reported": event.incidents_reported,
                    "incident_summary": event.incident_summary[:150]
                    if event.incident_summary
                    else None,
                }
            )

        return jsonify(
            {
                "status": "success",
                "response": ai_response,
                "events": event_list,
            }
        )
    except Exception as e:
        logger.error(f"Error processing chat query: {str(e)}")
        logger.error(f"Error processing chat query: {str(e)}")
        error_message = "API configuration error. Please check the OpenAI API key." if "openai" in str(e).lower() else "I encountered an error processing your query. Please try again."
        return jsonify(
            {
                "status": "error",
                "response": error_message,
                "events": [],
            }
        ), 500


@app.route("/decision/<int:decision_id>")
def view_decision(decision_id):
    decision = SecurityDecision.query.get_or_404(decision_id)
    log = start_activity_tracking(
        "view_decision_details",
        decision.event_report_id if decision.event_report else None,
    )
    g.activity_log = log

    return render_template(
        "view_decision.html", decision=decision
    )


@app.route("/log_decision", methods=["POST"])
def log_decision():
    try:
        decision_data = {
            "event_report_id": request.form.get("event_report_id"),
            "decision_type": request.form.get("decision_type"),
            "description": request.form.get("description"),
            "impact_level": request.form.get("impact_level"),
            "implementation_date": datetime.strptime(
                request.form["implementation_date"], "%Y-%m-%d"
            )
            if request.form.get("implementation_date")
            else None,
            "expected_outcome": request.form.get("expected_outcome"),
        }
        decision = SecurityDecision(**decision_data)  # type: ignore
        db.session.add(decision)
        db.session.commit()

        return redirect(url_for("decision_log"))
    except Exception as e:
        logger.error(f"Error logging decision: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/update_decision/<int:decision_id>", methods=["POST"])
def update_decision(decision_id):
    try:
        decision = SecurityDecision.query.get_or_404(decision_id)

        if "outcome" in request.form:
            decision.update_outcome(
                request.form["outcome"],
                request.form["outcome_type"],
                int(request.form["effectiveness"]),
            )

        if "lesson" in request.form:
            decision.add_lesson_learned(request.form["lesson"])

        db.session.commit()
        return redirect(url_for("view_decision", decision_id=decision_id))
    except Exception as e:
        logger.error(f"Error updating decision: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/get_decision_categories")
def get_decision_categories():
    """Get unique decision categories from the database"""
    categories = (
        db.session.query(SecurityDecision.decision_type)
        .filter(SecurityDecision.decision_type.isnot(None))
        .distinct()
        .all()
    )
    return [c[0] for c in categories if c[0]]

@app.route("/modeling")
def modeling():
    """Display the modeling interface with risk analysis data"""
    try:
        # Get event type distribution data
        event_types = []
        event_type_query = db.session.query(
            EventReport.incident_type,
            func.count(EventReport.id).label('count'),
            func.avg(case(
                {'High': 3, 'Medium': 2, 'Low': 1},
                value=EventReport.risk_level
            )).label('avg_risk'),
            func.count(case((EventReport.incidents_reported > 0, 1))).label('incidents')
        ).group_by(EventReport.incident_type).all()

        for event_type in event_type_query:
            if event_type.incident_type:  # Skip None values
                risk_level = 'Medium'
                if event_type.avg_risk:
                    if event_type.avg_risk >= 2.5:
                        risk_level = 'High'
                    elif event_type.avg_risk <= 1.5:
                        risk_level = 'Low'

                event_types.append({
                    'name': event_type.incident_type,
                    'count': event_type.count,
                    'risk_level': risk_level,
                    'risk_level_class': {
                        'High': 'danger',
                        'Medium': 'warning',
                        'Low': 'success'
                    }[risk_level],
                    'incidents': event_type.incidents
                })

        # Get security level distribution data
        security_levels_query = db.session.query(
            EventReport.risk_level,
            func.count(EventReport.id)
        ).group_by(EventReport.risk_level).all()

        security_labels = ['Low', 'Medium', 'High']
        security_levels_data = [0] * len(security_labels)

        if security_levels_query:
            security_levels_map = {level: count for level, count in security_levels_query}
            security_levels_data = [security_levels_map.get(level, 0) for level in security_labels]
        else:
            # Placeholder data if no events are in the database
            security_levels_data = [5, 12, 3]

        # Get incident data for the chart
        incident_data_query = db.session.query(
            extract('month', EventReport.date).label('month'),
            func.count(EventReport.id)
        ).filter(
            EventReport.incidents_reported > 0
        ).group_by('month').order_by('month').all()

        incident_labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                         'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        incident_counts = [0] * 12
        
        if incident_data_query:
            for month, count in incident_data_query:
                if month:
                    incident_counts[month - 1] = count
        else:
            # Placeholder data
            incident_counts = [2, 1, 4, 0, 3, 5, 2, 1, 6, 8, 4, 3]

        # Generate security recommendations
        recommendations = [
            {
                'title': 'Enhanced Security Staffing',
                'description': 'Increase security personnel for high-risk events',
                'priority': 'High'
            },
            {
                'title': 'Emergency Response Planning',
                'description': 'Update emergency protocols based on recent incidents',
                'priority': 'Medium'
            },
            {
                'title': 'Staff Training Program',
                'description': 'Conduct regular security awareness training sessions',
                'priority': 'Medium'
            }
        ]

        return render_template(
            'modeling.html',
            event_types=event_types,
            security_labels=security_labels,
            security_levels_data=security_levels_data,
            incident_labels=incident_labels,
            incident_data=incident_counts,
            recommendations=recommendations
        )
    except Exception as e:
        logger.error(f"Error in modeling route: {str(e)}")
        return render_template('modeling.html', error=str(e))

@app.route("/calculate_risk", methods=["POST"])
def calculate_risk():
    """Calculate a predictive risk score based on event parameters"""
    try:
        data = request.get_json()
        event_type = data.get("event_type")
        attendance = int(data.get("attendance", 0))
        venue_type = data.get("venue_type")

        # Base score
        score = 10
        breakdown = {"Base Score": score}

        # Event type contribution
        event_type_query = db.session.query(
            func.avg(case(
                {'High': 3, 'Medium': 2, 'Low': 1},
                value=EventReport.risk_level
            )).label('avg_risk')
        ).filter(EventReport.incident_type == event_type).first()

        avg_risk = event_type_query.avg_risk if event_type_query and event_type_query.avg_risk else 2
        
        if avg_risk >= 2.5:
            event_risk_contribution = 30
            breakdown["Event Type Risk (High)"] = event_risk_contribution
        elif avg_risk <= 1.5:
            event_risk_contribution = 5
            breakdown["Event Type Risk (Low)"] = event_risk_contribution
        else:
            event_risk_contribution = 15
            breakdown["Event Type Risk (Medium)"] = event_risk_contribution
        score += event_risk_contribution

        # Attendance contribution
        attendance_contribution = min(int(attendance / 1000), 50)
        breakdown["Attendance Contribution"] = attendance_contribution
        score += attendance_contribution

        # Venue type contribution
        venue_scores = {
            "stadium": 20, "arena": 15, "outdoor": 10,
            "theater": 5, "conference_center": 5
        }
        venue_contribution = venue_scores.get(venue_type, 0)
        breakdown["Venue Contribution"] = venue_contribution
        score += venue_contribution
        
        return jsonify({
            "risk_score": score,
            "breakdown": breakdown
        })
    except Exception as e:
        logger.error(f"Error in calculate_risk route: {str(e)}")
        return jsonify({"error": str(e)}), 500

# ─────────── Risk Assessment stage ──────────

@app.route("/event-report/<int:event_id>/risk-assessment", methods=["GET", "POST"])
def add_risk_assessment(event_id):
    report = EventReport.query.get_or_404(event_id)
    if request.method == "POST":
        overall = request.form.get("overall_risk_level", "Medium")
        status = request.form.get("status", "Active")
        date_str = request.form.get("assessment_date")
        assessment_date = datetime.strptime(date_str, "%Y-%m-%d") if date_str else datetime.utcnow()

        factors = [f.strip() for f in request.form.get("risk_factors", "").splitlines() if f.strip()]
        measures = [m.strip() for m in request.form.get("mitigation_measures", "").splitlines() if m.strip()]

        assessment = RiskAssessment(
            event_report_id=event_id,
            assessment_date=assessment_date,
            overall_risk_level=overall,
            risk_factors=factors,
            mitigation_measures=measures,
            status=status,
        )
        db.session.add(assessment)
        db.session.commit()

        flash("Risk assessment saved. Continue with recommendations.", "success")
        return redirect(url_for("build_event_report", event_id=event_id))

    return render_template("risk_assessment_form.html", report=report, now=datetime.utcnow())