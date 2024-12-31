import os
import logging
import json
from datetime import datetime
from typing import List, Dict, Any

from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from sqlalchemy import create_engine, text
import numpy as np
from app import db
from models import EventReport, ActivityLog

class VectorStore:
    def __init__(self):
        self.embeddings = OpenAIEmbeddings(openai_api_key=os.environ.get('OPENAI_API_KEY'))
        self.engine = create_engine(os.environ['DATABASE_URL'])
        self.initialize_store()

    def initialize_store(self):
        """Initialize the vector store and ensure the table exists."""
        try:
            with self.engine.connect() as conn:
                # Create vector extension if not exists
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

                # Create the embeddings table with proper vector type
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS document_embeddings (
                        id SERIAL PRIMARY KEY,
                        content TEXT NOT NULL,
                        embedding vector(1536),
                        metadata JSONB DEFAULT '{}'::jsonb,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    )
                """))

                # Create index for similarity search
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS document_embeddings_embedding_idx 
                    ON document_embeddings 
                    USING ivfflat (embedding vector_cosine_ops)
                    WITH (lists = 100)
                """))

                conn.commit()
                logging.info("Vector store initialized successfully")
        except Exception as e:
            logging.error(f"Failed to initialize vector store: {e}")
            raise

    def create_embedding(self, text: str) -> List[float]:
        """Create an embedding for a given text."""
        try:
            embedding = self.embeddings.embed_query(text)
            return embedding
        except Exception as e:
            logging.error(f"Failed to create embedding: {e}")
            raise

    def add_document(self, content: str, metadata: Dict[str, Any] = {}):
        """Add a document to the vector store."""
        try:
            embedding = self.create_embedding(content)

            # Convert embedding to PostgreSQL array format
            embedding_str = f"{{{','.join(map(str, embedding))}}}"

            # Convert metadata to JSON string
            metadata_json = json.dumps(metadata or {})

            with self.engine.connect() as conn:
                query = text("""
                    INSERT INTO document_embeddings (content, embedding, metadata)
                    VALUES (%(content)s, %(embedding)s, %(metadata)s)
                """)
                conn.execute(query, {
                    'content': content,
                    'embedding': embedding_str,
                    'metadata': metadata_json
                })
                conn.commit()
                logging.info(f"Successfully added document: {metadata.get('report_id', 'unknown')}")
        except Exception as e:
            logging.error(f"Failed to add document: {str(e)}")
            raise

    def search_similar(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search for similar documents using cosine similarity."""
        try:
            query_embedding = self.create_embedding(query)
            query_embedding_str = f"{{{','.join(map(str, query_embedding))}}}"

            with self.engine.connect() as conn:
                query = text("""
                    SELECT content, metadata,
                           1 - (embedding <=> %(embedding)s::vector) as similarity
                    FROM document_embeddings
                    WHERE embedding IS NOT NULL
                    ORDER BY embedding <=> %(embedding)s::vector
                    LIMIT %(limit)s
                """)

                result = conn.execute(query, {
                    'embedding': query_embedding_str,
                    'limit': limit
                })

                return [{
                    'content': row.content,
                    'metadata': row.metadata if isinstance(row.metadata, dict) else json.loads(row.metadata),
                    'similarity': float(row.similarity)
                } for row in result]
        except Exception as e:
            logging.error(f"Failed to search similar documents: {e}")
            return []

    def index_event_report(self, report: EventReport):
        """Index an event report's content in the vector store."""
        try:
            # Combine all relevant text fields
            content = f"""
            Title: {report.title}
            Description: {report.description}
            Location: {report.location}
            Risk Level: {report.risk_level}
            Venue Type: {report.venue_type}
            Security Staff Count: {report.security_staff_count}
            Security Measures: {report.security_measures}
            Incident Summary: {report.incident_summary}
            Lessons Learned: {report.lessons_learned}
            Recommendations: {report.recommendations}
            Security Protocols: {report.security_protocols}
            Emergency Response Plan: {report.emergency_response_plan}
            Post Event Analysis: {report.post_event_analysis}
            """

            metadata = {
                'report_id': report.id,
                'date': report.date.isoformat() if report.date else None,
                'risk_level': report.risk_level,
                'venue_type': report.venue_type,
                'doc_type': 'event_report'
            }

            # Split content into chunks for better retrieval
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200
            )
            chunks = text_splitter.split_text(content)

            # Add each chunk to vector store
            for chunk in chunks:
                self.add_document(chunk, metadata)

            logging.info(f"Successfully indexed report {report.id}")
        except Exception as e:
            logging.error(f"Failed to index event report {report.id}: {e}")
            raise

    def index_all_reports(self):
        """Index all existing event reports."""
        try:
            reports = EventReport.query.all()
            for report in reports:
                try:
                    self.index_event_report(report)
                    logging.info(f"Indexed report {report.id}")
                except Exception as e:
                    logging.error(f"Failed to index report {report.id}: {e}")
                    continue
            logging.info("Completed indexing all reports")
        except Exception as e:
            logging.error(f"Failed to get reports for indexing: {e}")
            raise

# Create a singleton instance
vector_store = VectorStore()