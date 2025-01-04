import json
import logging
import os
import tempfile
import uuid
from datetime import datetime, timedelta

from flask import (
    abort,
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
from sqlalchemy import and_, extract, func, or_
from werkzeug.utils import secure_filename

from app import app, db
from models import (
    ActivityLog,
    AssessmentTemplate,
    EventReport,
    SecurityDecision,
    SecurityInsight,
    RiskAssessment,
    ChatMessage
)

# Initialize OpenAI client
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@app.before_request
def before_request():
    g.start_time = datetime.utcnow()
    g.activity_log = None

@app.after_request
def after_request(response):
    if hasattr(g, "activity_log") and g.activity_log:
        end_activity_tracking(g.activity_log)
    return response

def get_or_create_session_id():
    """Get existing session ID or create new one"""
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
        logger.info(f"Created new session: {session['session_id']}")
    return session['session_id']

def start_activity_tracking(activity_type, event_report_id=None):
    log = ActivityLog(
        activity_type=activity_type,
        event_report_id=event_report_id,
        session_id=get_or_create_session_id(),
        user_identifier=request.remote_addr,
    )
    db.session.add(log)
    db.session.commit()
    return log

def end_activity_tracking(log):
    log.end_activity()
    db.session.commit()
    return log

@app.route("/chat")
def chat():
    """Render the chat page with chat history"""
    session_id = get_or_create_session_id()

    # Get chat messages for current session, ordered by creation time
    chat_messages = ChatMessage.query.filter_by(
        session_id=session_id
    ).order_by(ChatMessage.created_at.asc()).all()

    # Mark all messages as read
    for msg in chat_messages:
        if not msg.read:
            msg.read = True
    db.session.commit()

    # Start activity tracking
    log = start_activity_tracking("chat")
    g.activity_log = log

    return render_template("chat.html", chat_messages=chat_messages)

@app.route("/chat_query", methods=["POST"])
def chat_query():
    try:
        data = request.get_json()
        query = data.get('query')
        session_id = get_or_create_session_id()

        if not query:
            return jsonify({
                "status": "error",
                "message": "No query provided"
            }), 400

        # Save user message
        user_message = ChatMessage(
            session_id=session_id,
            message=query,
            is_user=True,
            category="question"
        )
        db.session.add(user_message)
        db.session.commit()  # Commit immediately to get message ID

        # Get recent events and decisions for context
        events = (
            EventReport.query.order_by(EventReport.created_at.desc())
            .limit(10)
            .all()
        )
        decisions = (
            SecurityDecision.query.order_by(SecurityDecision.created_at.desc())
            .limit(5)
            .all()
        )

        try:
            events_data = [
                {
                    "title": event.title,
                    "date": event.date.strftime("%Y-%m-%d"),
                    "location": event.location,
                    "risk_level": event.risk_level,
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

            # Process the query using OpenAI
            messages = [
                {"role": "system", "content": """You are an AI assistant specializing in security event analysis. 
                   Analyze the provided context and user query to provide relevant insights about security events,
                   risk assessments, and security measures. Keep responses clear and concise."""},
                {"role": "user", "content": f"""Context:
                   Recent Events: {json.dumps(events_data)}
                   Recent Decisions: {json.dumps(decisions_data)}
                   User Query: {query}"""}
            ]

            response = client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                max_tokens=500
            )

            ai_response = response.choices[0].message.content

            # Save AI response
            assistant_message = ChatMessage(
                session_id=session_id,
                message=ai_response,
                is_user=False,
                category="answer"
            )
            db.session.add(assistant_message)
            db.session.commit()

            return jsonify({
                "status": "success",
                "response": ai_response,
                "events": events_data[:3]  # Limit to 3 events for demonstration
            })

        except Exception as e:
            logger.error(f"Error processing chat query: {str(e)}")
            db.session.rollback()
            return jsonify({
                "status": "error",
                "message": "Error processing your request. Please try again."
            }), 500

    except Exception as e:
        logger.error(f"Unexpected error in chat_query: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "An unexpected error occurred. Please try again."
        }), 500

@app.route("/insights")
def insights():
    """Display the AI insights page with chat history"""
    session_id = get_or_create_session_id()

    # Get chat messages for current session, ordered by creation time
    chat_messages = ChatMessage.query.filter_by(
        session_id=session_id
    ).order_by(ChatMessage.created_at.asc()).all()

    # Get insights
    insights = SecurityInsight.query.order_by(SecurityInsight.created_at.desc()).limit(6).all()

    return render_template("insights.html", insights=insights, chat_messages=chat_messages)

@app.route("/generate_insights", methods=["POST"])
def generate_insights():
    """Generate new AI-powered insights from security data"""
    try:
        logger.info("Starting insights generation process")

        # Verify OpenAI API key
        if not os.environ.get("OPENAI_API_KEY"):
            logger.error("OpenAI API key not found")
            return jsonify({
                "status": "error",
                "message": "OpenAI API key not configured"
            }), 500

        # Get event and decision data
        events = EventReport.query.order_by(EventReport.date.desc()).limit(50).all()
        decisions = SecurityDecision.query.order_by(SecurityDecision.created_at.desc()).limit(50).all()

        events_data = [
            {
                "title": event.title,
                "date": event.date.strftime("%Y-%m-%d"),
                "risk_level": event.risk_level,
                "location": event.location,
                "attendance": event.attendance,
                "incidents_reported": event.incidents_reported,
                "security_measures": event.security_measures[:200] if event.security_measures else None,
                "venue_type": event.venue_type
            }
            for event in events
        ]

        decisions_data = [
            {
                "description": decision.description[:200] if decision.description else None,
                "created_at": decision.created_at.strftime("%Y-%m-%d")
            }
            for decision in decisions
        ]

        # Get insights from OpenAI
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": "Generate security insights from the provided event and decision data. Format as JSON."
                },
                {
                    "role": "user",
                    "content": f"Events: {json.dumps(events_data)}\nDecisions: {json.dumps(decisions_data)}"
                }
            ],
            max_tokens=1000
        )

        insights_data = json.loads(response.choices[0].message.content)

        # Save insights
        SecurityInsight.query.delete()  # Clear existing insights
        for insight in insights_data.get('insights', []):
            new_insight = SecurityInsight(
                title=insight['title'],
                description=insight['description'],
                key_findings=insight.get('findings', []),
                icon=insight.get('icon', 'alert-circle')
            )
            db.session.add(new_insight)

        db.session.commit()
        return jsonify({"status": "success"})

    except Exception as e:
        logger.error(f"Error generating insights: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

def get_venue_types():
    """Get unique venue types from the database"""
    types = (
        db.session.query(EventReport.venue_type)
        .filter(EventReport.venue_type.isnot(None))
        .distinct()
        .all()
    )
    return [t[0] for t in types if t[0]]

def get_event_types():
    """Get unique event types from the database"""
    types = (
        db.session.query(EventReport.incident_type)
        .filter(EventReport.incident_type.isnot(None))
        .distinct()
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
            logger.info("Processing POST request to /decisions")

            # Handle JSON requests from chat save functionality
            if request.is_json:
                data = request.get_json()
                decision = SecurityDecision(
                    description=data.get("description", ""),
                    author=data.get("author", "Anonymous"),
                )
                db.session.add(decision)
                db.session.commit()
                logger.info("Decision saved from chat successfully")
                return jsonify({"status": "success", "id": decision.id})

            # Handle form data and file uploads
            logger.debug(f"Request form data: {request.form}")
            logger.debug(f"Request files: {request.files}")

            if not os.path.exists(app.config["UPLOAD_FOLDER"]):
                os.makedirs(app.config["UPLOAD_FOLDER"])
                logger.info(f"Created upload folder: {app.config['UPLOAD_FOLDER']}")

            uploaded_files = request.files.getlist("attachments")
            logger.info(f"Number of files received: {len(uploaded_files)}")
            file_metadata = []
            summaries = []

            for file in uploaded_files:
                if file and file.filename:
                    try:
                        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_")
                        original_filename = secure_filename(file.filename)
                        filename = timestamp + original_filename
                        logger.info(f"Processing file: {original_filename} -> {filename}")

                        file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                        file.save(file_path)
                        logger.info(f"File saved successfully to: {file_path}")

                        # Get file summary
                        summary = summarize_file_content(file_path, file.content_type)
                        summaries.append(summary)

                        file_metadata.append(
                            {
                                "filename": filename,
                                "original_filename": original_filename,
                                "file_path": file_path,
                                "file_type": file.content_type,
                                "file_size": os.path.getsize(file_path),
                                "uploaded_at": datetime.utcnow().isoformat(),
                            }
                        )
                        logger.info(f"File metadata stored for: {filename}")
                    except Exception as e:
                        logger.error(f"Error processing file {file.filename}: {str(e)}")
                        return (
                            jsonify({"status": "error", "message": f"Error processing file {file.filename}"}),
                            500,
                        )

            # Create new decision entry
            try:
                description = request.form.get("description", "")
                if summaries:  # Add summaries to description if files were processed
                    description = description or "File upload"
                    description += "\n\nFile Summaries:\n" + "\n\n".join(summaries)

                decision = SecurityDecision(
                    description=description,
                    author=request.form.get("author", "Anonymous"),
                )
                logger.info("Created new SecurityDecision object")

                for metadata in file_metadata:
                    decision.add_attachment(
                        metadata["filename"],
                        metadata["file_path"],
                        metadata["file_type"],
                        metadata["file_size"],
                    )
                logger.info(f"Added {len(file_metadata)} attachments to decision")

                db.session.add(decision)
                db.session.commit()
                logger.info("Decision saved to database successfully")

                return jsonify(
                    {
                        "status": "success",
                        "decision": {
                            "id": decision.id,
                            "description": decision.description,
                            "author": decision.author,
                            "created_at": decision.created_at.strftime("%d/%m/%Y, %H:%M:%S"),
                            "attachments": [
                                {
                                    "filename": att["filename"],
                                    "uploaded_at": att["uploaded_at"],
                                    "file_type": att["file_type"],
                                }
                                for att in decision.attachments
                            ]
                            if decision.attachments
                            else [],
                        },
                    }
                )
            except Exception as e:
                logger.error(f"Error creating decision: {str(e)}")
                # Cleanup any uploaded files if decision creation fails
                for metadata in file_metadata:
                    try:
                        os.remove(metadata["file_path"])
                        logger.info(f"Cleaned up file: {metadata['file_path']}")
                    except Exception as cleanup_error:
                        logger.error(f"Error cleaning up file: {str(cleanup_error)}")
                return (
                    jsonify({"status": "error", "message": "Error creating decision entry"}),
                    500,
                )
        except Exception as e:
            logger.error(f"Error in decision_log POST handler: {str(e)}")
            return jsonify({"status": "error", "message": str(e)}), 500

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


def get_decision_categories():
    """Get unique decision categories from the database"""
    categories = (
        db.session.query(SecurityDecision.category)
        .filter(SecurityDecision.category.isnot(None))
        .distinct()
        .all()
    )
    return [c[0] for c in categories if c[0]]


@app.route("/decision/<int:decision_id>")
def view_decision(decision_id):
    decision = SecurityDecision.query.get_or_404(decision_id)
    log = start_activity_tracking(
        "view_decision_details",
        decision.event_report_id if decision.event_report else None,
    )
    g.activity_log = log

    related_decisions = []
    if decision.related_decisions:
        related_ids = [rd["decision_id"] for rd in decision.related_decisions]
        related_decisions = SecurityDecision.query.filter(
            SecurityDecision.id.in_(related_ids)
        ).all()

    return render_template(
        "view_decision.html", decision=decision, related_decisions=related_decisions
    )


@app.route("/log_decision", methods=["POST"])
def log_decision():
    try:
        decision = SecurityDecision(
            event_report_id=request.form.get("event_report_id"),
            decision_type=request.form["decision_type"],
            description=request.form["description"],
            impact_level=request.form["impact_level"],
            implementation_date=datetime.strptime(
                request.form["implementation_date"], "%Y-%m-%d"
            )
            if request.form.get("implementation_date")
            else None,
            expected_outcome=request.form.get("expected_outcome"),
        )
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

    reports = query.order_by(EventReport.date.desc()).limit(5).all()
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


@app.route("/access_logs")
def view_access_logs():
    logs = ActivityLog.query.order_by(ActivityLog.started_at.desc()).all()
    return render_template("access_log.html", logs=logs)


@app.route("/export-decisions")
def export_decisions():
    """Export all decisions as PDF"""
    try:
        decisions = SecurityDecision.query.order_by(SecurityDecision.created_at.desc()).all()

        # Log the export activity
        log = start_activity_tracking("export_decisions_pdf")
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


@app.route("/report/<int:report_id>/export")
def export_report_pdf(report_id):
    """Export a report as PDF"""
    report = EventReport.query.get_or_404(report_id)

    # Log the export activity
    log = start_activity_tracking("export_report_pdf", report_id)
    g.activity_log = log

    # Generate HTML content
    html = render_template("pdf/report_pdf.html", report=report, datetime=datetime)

    # Create a temporary file for the PDF
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        # Generate PDF from HTML
        pdf = weasyprint.HTML(string=html).write_pdf()
        tmp.write(pdf)
        tmp_path = tmp.name

    try:
        # Send the PDF file
        return send_file(
            tmp_path,
            download_name=f"report_{report.id}_{datetime.now().strftime('%Y%m%d')}.pdf",
            as_attachment=True,
            mimetype="application/pdf,",
        )
    finally:
        # Clean up the temporary file after sending
        os.unlink(tmp_path)