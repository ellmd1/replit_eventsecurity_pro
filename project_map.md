# SecureEvent Pro - Project Architecture Map

## Overview
SecureEvent Pro is a comprehensive security monitoring dashboard for organizations to monitor ongoing risks, generate compliant risk assessment reports, and examine compliance/generation reports. Built with Flask, PostgreSQL, and OpenAI integration for AI-powered insights.

## Tech Stack
- **Backend**: Python 3.11, Flask, SQLAlchemy
- **Database**: PostgreSQL
- **AI Integration**: OpenAI GPT-4
- **Frontend**: HTML, CSS, JavaScript (Vanilla), Bootstrap
- **File Processing**: WeasyPrint (PDF), python-docx (Word), trafilatura (web scraping)
- **Server**: Gunicorn for production, Flask dev server for development

## Core Application Structure

### Entry Points
- `main.py` - Application entry point, imports app from app.py
- `app.py` - Flask application factory, database initialization, configuration

### Database Models (`models.py`)
The application uses 6 main database tables:

#### 1. EventReport (Primary Entity)
**Purpose**: Stores security event reports and assessments
**Key Columns**:
- `id` - Primary key
- `title` - Event name
- `date` - Event date
- `location` - Event location
- `description` - Event description
- `risk_level` - Assessed risk (High/Medium/Low)
- `incident_type` - Type of event (concert, sports, festival, etc.)
- `venue_type` - Venue classification
- `attendance` - Expected/actual attendance
- `security_staff_count` - Number of security personnel
- `security_staff_roles` - JSON field with role distribution
- `incidents_reported` - Number of incidents during event
- `security_measures` - Security protocols implemented
- `incident_response` - Response procedures
- `lessons_learned` - Post-event analysis
- `recommendations` - Future improvements
**Used By**: Dashboard, View Report, Comparative Search, Decision Log

#### 2. SecurityDecision (Decision Log)
**Purpose**: Documents security decisions and their outcomes
**Key Columns**:
- `id` - Primary key
- `description` - Decision description
- `decision_type` - Category of decision
- `impact_level` - Expected impact
- `status` - Implementation status
- `event_report_id` - Foreign key to EventReport
- `implementation_date` - When decision was implemented
- `expected_outcome` - Anticipated results
- `actual_outcome` - Real results
- `effectiveness_rating` - Success rating (1-10)
- `attachments` - JSON array of file attachments
**Used By**: Decision Log, View Decision, Report PDF Export

#### 3. ActivityLog (User Tracking)
**Purpose**: Tracks user interactions and system usage
**Key Columns**:
- `id` - Primary key
- `event_report_id` - Related event (optional)
- `activity_type` - Type of activity (dashboard_view, search, etc.)
- `started_at` - Activity start time
- `ended_at` - Activity end time
- `user_identifier` - User session identifier
- `search_query` - Search terms used
- `filters_applied` - JSON of applied filters
- `interaction_details` - Additional interaction data
**Used By**: Access Logs, Activity tracking across all pages

#### 4. RiskAssessment (Risk Analysis)
**Purpose**: Detailed risk assessments for events
**Key Columns**:
- `id` - Primary key
- `event_report_id` - Foreign key to EventReport
- `assessment_date` - When assessment was conducted
- `risk_factors` - JSON array of identified risks
- `overall_risk_level` - Calculated risk level
- `mitigation_measures` - JSON array of mitigation strategies
- `residual_risk_level` - Risk after mitigation
**Used By**: Risk modeling, Event reports, Dashboard insights

#### 5. SecurityInsight (AI Insights)
**Purpose**: AI-generated security insights and analysis
**Key Columns**:
- `id` - Primary key
- `title` - Insight title
- `description` - Detailed insight description
- `key_findings` - JSON array of key findings
- `icon` - Icon identifier for UI
**Used By**: Insights page, Dashboard summary

#### 6. AssessmentTemplate (Templates)
**Purpose**: Reusable assessment templates for different event types
**Key Columns**:
- `id` - Primary key
- `title` - Template name
- `description` - Template description
- `configuration` - JSON configuration
- `security_requirements` - JSON array of requirements
- `risk_factors` - JSON array of risk factors
- `template_type` - Category of template
- `min_capacity`/`max_capacity` - Capacity ranges
**Used By**: Template management, Event creation

## Application Pages & Functionality

### 1. Dashboard (`/` - dashboard.html)
**Files Involved**: `routes.py` (dashboard function), `templates/dashboard.html`
**Functionality**: 
- Displays summary statistics
- Shows recent events and high-risk events
- Risk level distribution charts
- Quick access to key functions
**Database Tables**: EventReport, SecurityInsight, ActivityLog

### 2. View All Events (`/view_all_events` - index.html)
**Files Involved**: `routes.py` (view_all_events function), `templates/index.html`
**Functionality**:
- Lists all security events
- Search and filter capabilities
- Risk level indicators
- Navigation to individual reports
**Database Tables**: EventReport, ActivityLog

### 3. Individual Event Report (`/view_report/<id>` - view_report.html)
**Files Involved**: `routes.py` (view_report function), `templates/view_report.html`
**Functionality**:
- Detailed event information
- Risk assessments
- Incident reports
- File attachments
- Export to PDF
**Database Tables**: EventReport, RiskAssessment, ActivityLog

### 4. Comparative Search (`/comparative_search` - comparative_search.html)
**Files Involved**: `routes.py` (comparative_search, compare_reports functions), `templates/comparative_search.html`, `templates/report_comparison.html`
**Functionality**:
- Side-by-side event comparison
- Filter-based search
- Similarity analysis
**Database Tables**: EventReport, ActivityLog

### 5. Chat Interface (`/chat` - chat.html)
**Files Involved**: `routes.py` (chat, chat_query functions), `templates/chat.html`, `chat_processor.py`, `static/js/main.js`
**Functionality**:
- Natural language queries
- AI-powered search
- Conversational interface
- Query result saving
**Database Tables**: EventReport, ActivityLog
**AI Integration**: OpenAI GPT-4 for query processing

### 6. Decision Log (`/decision_log` - decision_log.html)
**Files Involved**: `routes.py` (decision_log, log_decision, update_decision functions), `templates/decision_log.html`
**Functionality**:
- Document security decisions
- Track implementation status
- File attachments
- Decision categorization
**Database Tables**: SecurityDecision, EventReport, ActivityLog

### 7. Individual Decision View (`/view_decision/<id>` - view_decision.html)
**Files Involved**: `routes.py` (view_decision function), `templates/view_decision.html`
**Functionality**:
- Detailed decision information
- Implementation tracking
- Effectiveness rating
- File downloads
**Database Tables**: SecurityDecision

### 8. AI Insights (`/insights` - insights.html)
**Files Involved**: `routes.py` (insights, generate_insights functions), `templates/insights.html`
**Functionality**:
- AI-generated security insights
- Pattern recognition
- Trend analysis
- Recommendation generation
**Database Tables**: SecurityInsight, EventReport
**AI Integration**: OpenAI GPT-4 for insight generation

### 9. Risk Modeling (`/modeling` - modeling.html)
**Files Involved**: `routes.py` (modeling function), `templates/modeling.html`
**Functionality**:
- Risk analysis visualization
- Statistical modeling
- Scenario planning
**Database Tables**: EventReport, RiskAssessment

### 10. Scenario Builder (`/scenario_builder` - scenario_builder.html)
**Files Involved**: `routes.py`, `templates/scenario_builder.html`, `static/js/scenario_builder.js`
**Functionality**:
- Interactive scenario creation
- Drag-and-drop interface
- Scenario saving and management
**Database Tables**: EventReport (for scenario storage)

### 11. Access Logs (`/access_logs` - access_log.html)
**Files Involved**: `routes.py` (view_access_logs function), `templates/access_log.html`
**Functionality**:
- User activity monitoring
- Session tracking
- System usage analytics
**Database Tables**: ActivityLog

### 12. Template Management (`/templates/*` - templates/list.html, templates/create.html)
**Files Involved**: `routes.py` (list_templates, create_template, view_template, edit_template functions)
**Functionality**:
- Create assessment templates
- Manage reusable configurations
- Template library
**Database Tables**: AssessmentTemplate

## File Organization

### Backend Structure
- `app.py` - Flask app configuration, database setup, logging
- `models.py` - SQLAlchemy models for all database tables
- `routes.py` - All HTTP routes and view functions
- `chat_processor.py` - AI chat processing and natural language query handling
- `main.py` - Application entry point

### Frontend Structure
- `templates/base.html` - Base template with common layout
- `templates/*.html` - Individual page templates
- `templates/pdf/*.html` - PDF export templates
- `static/js/main.js` - Main JavaScript functionality, chat interface
- `static/js/scenario_builder.js` - Scenario builder interactive features

### Data Management
- `uploads/` - User-uploaded files (PDFs, images, documents)
- `attached_assets/` - System-generated attachments
- Database managed via PostgreSQL

## API Integrations

### OpenAI Integration
**Files**: `chat_processor.py`, `routes.py` (insights functions)
**Models Used**: GPT-4-turbo-preview
**Functionality**:
- Natural language query processing
- Security insight generation
- Pattern analysis
- Risk assessment assistance

## Key Workflows

### 1. Event Report Creation → Risk Assessment → Decision Documentation
1. User creates event report (EventReport table)
2. System generates risk assessment (RiskAssessment table)
3. User documents decisions (SecurityDecision table)
4. Activity logged throughout (ActivityLog table)

### 2. AI-Powered Search and Analysis
1. User submits natural language query (chat interface)
2. OpenAI processes query (chat_processor.py)
3. System filters database results
4. Results displayed with explanations
5. User can save decisions from search results

### 3. Compliance Reporting
1. System aggregates event data
2. Generates PDF reports (WeasyPrint)
3. Includes risk assessments and decisions
4. Exports for compliance purposes

## Security & Compliance Features
- Session-based user tracking
- File upload validation and storage
- PDF generation for reports
- Activity logging for audit trails
- Risk level categorization
- Decision documentation and tracking

## External Dependencies
- OpenAI API for AI features
- PostgreSQL for data persistence
- WeasyPrint for PDF generation
- Bootstrap for UI styling
- Various Python libraries for file processing

This architecture enables comprehensive security event management with AI-powered insights, compliance reporting, and decision tracking capabilities.