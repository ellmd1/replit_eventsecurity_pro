import os
import logging
from typing import List, Tuple
import json

try:
    from sentence_transformers import SentenceTransformer
    from sqlalchemy import select, func
    from openai import OpenAI
    from app import db
    from models import EventReport, EventEmbedding

    # Initialize OpenAI client
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    # Initialize the sentence transformer model
    model = SentenceTransformer('all-MiniLM-L6-v2')

    def get_embedding(text: str) -> List[float]:
        """Generate embeddings for a given text using sentence-transformers"""
        return model.encode(text).tolist()

    def create_event_embedding(event: EventReport):
        """Create or update embeddings for an event report"""
        # Combine relevant text fields for embedding
        text_to_embed = f"{event.title} {event.description} {event.incident_summary or ''} "
        text_to_embed += f"{event.security_measures or ''} {event.lessons_learned or ''} "
        text_to_embed += f"{event.recommendations or ''} {event.security_protocols or ''} "
        text_to_embed += f"{event.emergency_response_plan or ''} {event.post_event_analysis or ''}"

        embedding = get_embedding(text_to_embed)

        # Create or update embedding
        existing_embedding = event.embeddings
        if existing_embedding:
            existing_embedding.embedding = embedding
        else:
            new_embedding = EventEmbedding(event_report_id=event.id, embedding=embedding)
            db.session.add(new_embedding)

        db.session.commit()

    def find_similar_events(query: str, limit: int = 5) -> List[EventReport]:
        """Find similar events using vector similarity search"""
        query_embedding = get_embedding(query)

        # Perform similarity search using cosine distance
        similar_events = (
            db.session.query(EventReport)
            .join(EventEmbedding)
            .order_by(
                func.cosine_distance(EventEmbedding.embedding, query_embedding)
            )
            .limit(limit)
            .all()
        )

        return similar_events

    def get_chat_response(query: str, chat_history: List[dict]) -> Tuple[str, List[EventReport]]:
        """
        Generate a response using RAG approach:
        1. Find relevant events using vector similarity
        2. Use these events as context for the LLM
        3. Generate a natural, conversational response
        """
        try:
            # Find similar events
            similar_events = find_similar_events(query)

            # Create context from similar events
            context = "Here are some relevant security events:\n"
            for event in similar_events:
                context += f"- {event.title} ({event.date.strftime('%Y-%m-%d')}): {event.risk_level} risk level\n"
                context += f"  Location: {event.location}\n"
                context += f"  Description: {event.description[:200]}...\n"
                if event.lessons_learned:
                    context += f"  Lessons Learned: {event.lessons_learned[:200]}...\n"
                context += "\n"

            # Create messages for chat completion
            messages = [
                {"role": "system", "content": """You are a helpful security consultant AI. 
                 Use the provided event information to give detailed, relevant advice.
                 Be conversational but professional. If you're not sure about something,
                 say so. Always reference specific events when they support your response."""},
                *[{"role": msg["role"], "content": msg["content"]} for msg in chat_history[-5:]],
                {"role": "user", "content": f"Context:\n{context}\n\nUser Query: {query}"}
            ]

            # Get response from OpenAI
            response = client.chat.completions.create(
                model="gpt-4o",  # Released May 13, 2024, do not change unless requested
                messages=messages,
                max_tokens=500
            )

            return response.choices[0].message.content, similar_events

        except Exception as e:
            logging.error(f"Error in chat response generation: {str(e)}")
            return "I apologize, but I encountered an error processing your request. Please try again.", []

    def update_all_embeddings():
        """Update embeddings for all event reports"""
        events = EventReport.query.all()
        for event in events:
            create_event_embedding(event)

except ImportError as e:
    logging.error(f"Failed to import required modules: {str(e)}")
    raise