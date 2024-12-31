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

logger = logging.getLogger(__name__)

class VectorStore:
    def __init__(self):
        self.embeddings = OpenAIEmbeddings(openai_api_key=os.environ.get('OPENAI_API_KEY'))
        self.engine = create_engine(os.environ['DATABASE_URL'])
        logger.info("Vector store instance created")

    def initialize_store(self):
        """Initialize the vector store and ensure the table exists."""
        try:
            with self.engine.connect() as conn:
                # Create vector extension if not exists
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))

                # Create the embeddings table using parameterized query style
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS document_embeddings (
                        id SERIAL PRIMARY KEY,
                        content TEXT NOT NULL,
                        embedding vector(1536),
                        metadata JSONB DEFAULT '{}'::jsonb,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    );
                """))

                # Create index for similarity search
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS document_embeddings_embedding_idx 
                    ON document_embeddings 
                    USING ivfflat (embedding vector_cosine_ops)
                    WITH (lists = 100);
                """))
                conn.commit()
                logger.info("Vector store initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize vector store: {str(e)}", exc_info=True)
            raise

    def add_document(self, content: str, metadata: Dict[str, Any] = None):
        """Add a document to the vector store."""
        try:
            # Create embedding
            embedding = self.create_embedding(content)
            embedding_array = np.array(embedding).astype(float)  # Convert to numpy array to ensure float values
            embedding_str = f"[{','.join(str(x) for x in embedding_array)}]"
            metadata_json = json.dumps(metadata or {})

            # Insert document using parameterized query
            with self.engine.connect() as conn:
                query = """
                    INSERT INTO document_embeddings (content, embedding, metadata)
                    VALUES (%(content)s, %(embedding)s::vector, %(metadata)s::jsonb)
                """
                params = {
                    'content': content,
                    'embedding': embedding_str,
                    'metadata': metadata_json
                }
                conn.execute(text(query), params)
                conn.commit()
                logger.info(f"Successfully added document: {metadata.get('report_id', 'unknown') if metadata else 'unknown'}")

        except Exception as e:
            logger.error(f"Failed to add document: {str(e)}", exc_info=True)
            raise

    def search_similar(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search for similar documents using cosine similarity."""
        try:
            # Create query embedding
            query_embedding = self.create_embedding(query)
            query_array = np.array(query_embedding).astype(float)
            embedding_str = f"[{','.join(str(x) for x in query_array)}]"

            # Execute search using parameterized query
            with self.engine.connect() as conn:
                query = """
                    SELECT content, metadata,
                           1 - (embedding <=> %(embedding)s::vector) as similarity
                    FROM document_embeddings
                    WHERE embedding IS NOT NULL
                    ORDER BY embedding <=> %(embedding)s::vector
                    LIMIT %(limit)s
                """
                params = {
                    'embedding': embedding_str,
                    'limit': limit
                }
                result = conn.execute(text(query), params)

                return [{
                    'content': row.content,
                    'metadata': json.loads(row.metadata) if isinstance(row.metadata, str) else row.metadata,
                    'similarity': float(row.similarity)
                } for row in result]

        except Exception as e:
            logger.error(f"Failed to search similar documents: {str(e)}", exc_info=True)
            return []

    def create_embedding(self, text: str) -> List[float]:
        """Create an embedding for a given text."""
        try:
            embedding = self.embeddings.embed_query(text)
            return [float(x) for x in embedding]  # Ensure all values are float
        except Exception as e:
            logger.error(f"Failed to create embedding: {str(e)}", exc_info=True)
            raise

    def index_event_report(self, report: EventReport):
        """Index an event report's content in the vector store."""
        try:
            # Prepare content
            content = f"""
            Title: {report.title or ''}
            Description: {report.description or ''}
            Location: {report.location or ''}
            Risk Level: {report.risk_level or ''}
            Venue Type: {report.venue_type or ''}
            Security Staff Count: {report.security_staff_count or 0}
            Security Measures: {report.security_measures or ''}
            Incident Summary: {report.incident_summary or ''}
            Lessons Learned: {report.lessons_learned or ''}
            Recommendations: {report.recommendations or ''}
            Security Protocols: {report.security_protocols or ''}
            Emergency Response Plan: {report.emergency_response_plan or ''}
            Post Event Analysis: {report.post_event_analysis or ''}
            """

            metadata = {
                'report_id': report.id,
                'date': report.date.isoformat() if report.date else None,
                'risk_level': report.risk_level,
                'venue_type': report.venue_type,
                'doc_type': 'event_report'
            }

            # Split content into chunks
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=100,
                separators=["\n\n", "\n", " ", ""]
            )
            chunks = text_splitter.split_text(content)

            # Index each chunk
            for chunk in chunks:
                self.add_document(chunk, metadata)

            logger.info(f"Successfully indexed report {report.id}")
        except Exception as e:
            logger.error(f"Failed to index report {report.id}: {str(e)}", exc_info=True)
            raise

    def index_all_reports(self):
        """Index all existing event reports."""
        try:
            reports = EventReport.query.all()
            for report in reports:
                try:
                    self.index_event_report(report)
                except Exception as e:
                    logger.error(f"Failed to index report {report.id}: {str(e)}", exc_info=True)
                    continue
            logger.info("Completed indexing all reports")
        except Exception as e:
            logger.error(f"Failed to get reports for indexing: {str(e)}", exc_info=True)
            raise

# Create a singleton instance
vector_store = VectorStore()