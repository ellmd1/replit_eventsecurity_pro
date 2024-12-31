import os
import logging
import json
from datetime import datetime
from sqlalchemy import extract
from openai import OpenAI
from vector_store import vector_store
from models import ActivityLog, db

# Initialize OpenAI client
# the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
# do not change this unless explicitly requested by the user
client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))

def process_natural_language_query(query: str, db_query, session_id=None):
    """Process natural language query using OpenAI and convert to database filters"""
    try:
        # Start activity tracking
        log = ActivityLog(
            activity_type='chat_query',
            session_id=session_id,
            search_query=query,
            started_at=datetime.utcnow()
        )
        db.session.add(log)

        # First, search for relevant context using vector store
        similar_docs = vector_store.search_similar(query, limit=3)
        context = "\n".join([doc['content'] for doc in similar_docs])

        # Log retrieved documents
        log.related_resources = [{
            'type': 'similar_document',
            'content_preview': doc['content'][:200],
            'similarity_score': doc['similarity']
        } for doc in similar_docs]

        # Create a prompt that explains the task and available filters
        prompt = f"""Based on this natural language query: "{query}"
        And considering this relevant context:
        {context}

        Extract relevant search parameters and categorize them. The available filters are:
        - risk_level (High, Medium, Low)
        - venue_type (stadium, arena, convention center, outdoor, indoor)
        - incident_type (concert, sports, festival)
        - attendance (small: <1000, medium: 1000-5000, large: 5000-15000, very large: >15000)
        - date ranges (this year, last year, recent)
        - location (any text)

        Respond with JSON in this format:
        {{
            "filters": {{
                "risk_level": "string or null",
                "venue_type": "string or null",
                "incident_type": "string or null",
                "attendance_range": "string or null",
                "date_filter": "string or null",
                "location": "string or null"
            }},
            "explanation": "Brief explanation of how you interpreted the query",
            "suggested_followup_questions": ["question1", "question2"]
        }}"""

        # Get AI response
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )

        # Parse AI response
        result = json.loads(response.choices[0].message.content)
        logging.debug(f"AI interpretation: {result}")

        # Log the AI's interpretation
        log.interaction_details = {
            'interpreted_filters': result.get('filters', {}),
            'explanation': result.get('explanation', ''),
            'followup_questions': result.get('suggested_followup_questions', [])
        }

        # Apply filters based on AI interpretation
        filters = result.get('filters', {})
        for filter_name, value in filters.items():
            if not value or value == "null":
                continue

            if filter_name == 'risk_level' and value in ['High', 'Medium', 'Low']:
                db_query = db_query.filter_by(risk_level=value)

            elif filter_name == 'venue_type':
                db_query = db_query.filter(db_query.whereclause.model.venue_type.ilike(f'%{value}%'))

            elif filter_name == 'incident_type':
                db_query = db_query.filter(db_query.whereclause.model.incident_type.ilike(f'%{value}%'))

            elif filter_name == 'attendance_range':
                if value == 'small':
                    db_query = db_query.filter(db_query.whereclause.model.attendance < 1000)
                elif value == 'medium':
                    db_query = db_query.filter(db_query.whereclause.model.attendance.between(1000, 5000))
                elif value == 'large':
                    db_query = db_query.filter(db_query.whereclause.model.attendance.between(5000, 15000))
                elif value == 'very large':
                    db_query = db_query.filter(db_query.whereclause.model.attendance > 15000)

            elif filter_name == 'date_filter':
                current_year = datetime.now().year
                if value == 'this year':
                    db_query = db_query.filter(extract('year', db_query.whereclause.model.date) == current_year)
                elif value == 'last year':
                    db_query = db_query.filter(extract('year', db_query.whereclause.model.date) == current_year - 1)
                elif value == 'recent':
                    db_query = db_query.order_by(db_query.whereclause.model.date.desc())

            elif filter_name == 'location':
                db_query = db_query.filter(db_query.whereclause.model.location.ilike(f'%{value}%'))

        # Complete activity log
        log.ended_at = datetime.utcnow()
        log.calculate_duration()
        db.session.commit()

        return db_query, result.get('explanation', 'Query processed successfully')

    except Exception as e:
        logging.error(f"Error processing query with AI: {str(e)}")
        if 'log' in locals():
            log.ended_at = datetime.utcnow()
            log.calculate_duration()
            log.notes = f"Error: {str(e)}"
            db.session.commit()
        return db_query, "I had trouble understanding that query. Please try rephrasing it."

def generate_response_summary(events, query_explanation, search_context=None, session_id=None):
    """Generate a natural language summary of the search results"""
    if not events:
        return "I couldn't find any events matching your criteria. Try adjusting your search terms."

    try:
        # Start activity tracking
        log = ActivityLog(
            activity_type='response_generation',
            session_id=session_id,
            started_at=datetime.utcnow()
        )
        db.session.add(log)

        event_descriptions = "\n".join([
            f"- {event.title} ({event.date.strftime('%Y-%m-%d')}): {event.risk_level} risk, {event.location}"
            for event in events[:3]
        ])

        context_summary = ""
        if search_context:
            context_summary = "\nRelevant context from similar events:\n" + search_context

        # Log the events being summarized
        log.related_resources = [{
            'type': 'summarized_event',
            'event_id': event.id,
            'event_title': event.title
        } for event in events[:3]]

        prompt = f"""Create a natural, conversational summary of these search results:
        Query interpretation: {query_explanation}
        Number of events found: {len(events)}
        Sample events:
        {event_descriptions}
        {context_summary}

        Keep the response concise and friendly. Mention the total number of events and briefly highlight key patterns.
        Also suggest up to 3 follow-up questions based on the current results."""

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=250
        )

        summary = response.choices[0].message.content

        # Complete activity log
        log.ended_at = datetime.utcnow()
        log.calculate_duration()
        log.interaction_details = {
            'summary_length': len(summary),
            'events_summarized': len(events)
        }
        db.session.commit()

        return summary

    except Exception as e:
        logging.error(f"Error generating response summary: {str(e)}")
        if 'log' in locals():
            log.ended_at = datetime.utcnow()
            log.calculate_duration()
            log.notes = f"Error: {str(e)}"
            db.session.commit()
        return f"I found {len(events)} events matching your criteria."