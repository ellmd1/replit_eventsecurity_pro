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
from models import EventReport

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class VectorStore:
    def __init__(self):
        self.embeddings = OpenAIEmbeddings(openai_api_key=os.environ.get('OPENAI_API_KEY'))
        self.engine = create_engine(os.environ['DATABASE_URL'])
        logger.info("Vector store instance created")

    def initialize_store(self):
        """Initialize vector store tables and indices"""
        try:
            logger.info("Initializing vector store...")
            with self.engine.connect() as conn:
                # Create vector extension
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                conn.commit()

                # Create embeddings table with vector support
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS document_embeddings (
                        id SERIAL PRIMARY KEY,
                        content TEXT NOT NULL,
                        embedding vector(1536),
                        metadata JSONB DEFAULT '{}'::jsonb,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                conn.commit()

                # Create similarity search index
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS embeddings_vector_idx 
                    ON document_embeddings 
                    USING ivfflat (embedding vector_cosine_ops)
                    WITH (lists = 100)
                """))
                conn.commit()

                logger.info("Vector store tables and indices created successfully")

        except Exception as e:
            logger.error(f"Failed to initialize vector store: {str(e)}", exc_info=True)
            raise

    def add_document(self, content: str, metadata: Dict[str, Any] = None):
        """Add a document to the vector store"""
        if metadata is None:
            metadata = {}

        try:
            # Generate embedding
            embedding = self.create_embedding(content)
            embedding_array = np.array(embedding).astype(float)

            # Format embedding for PostgreSQL
            embedding_list = [float(x) for x in embedding_array]

            # Use SQLAlchemy style parameter binding
            with self.engine.connect() as conn:
                stmt = text("""
                    INSERT INTO document_embeddings (content, embedding, metadata)
                    VALUES (:content, :embedding::vector, :metadata::jsonb)
                """)

                params = {
                    'content': content,
                    'embedding': f"[{','.join(str(x) for x in embedding_list)}]",
                    'metadata': json.dumps(metadata)
                }

                conn.execute(stmt, params)
                conn.commit()

            logger.info(f"Document added successfully: {metadata.get('id', 'unknown')}")

        except Exception as e:
            logger.error(f"Failed to add document: {str(e)}", exc_info=True)
            raise

    def search_similar(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search for similar documents"""
        try:
            # Generate query embedding
            query_embedding = self.create_embedding(query)
            query_array = np.array(query_embedding).astype(float)

            # Format query embedding for PostgreSQL
            query_list = [float(x) for x in query_array]

            # Execute similarity search with SQLAlchemy style parameter binding
            with self.engine.connect() as conn:
                stmt = text("""
                    SELECT 
                        content,
                        metadata,
                        1 - (embedding <=> :embedding::vector) as similarity
                    FROM document_embeddings
                    WHERE embedding IS NOT NULL
                    ORDER BY embedding <=> :embedding::vector
                    LIMIT :limit
                """)

                result = conn.execute(stmt, {
                    'embedding': f"[{','.join(str(x) for x in query_list)}]",
                    'limit': limit
                })

                return [{
                    'content': row.content,
                    'metadata': json.loads(row.metadata) if isinstance(row.metadata, str) else row.metadata,
                    'similarity': float(row.similarity)
                } for row in result]

        except Exception as e:
            logger.error(f"Failed to search similar documents: {str(e)}", exc_info=True)
            return []

    def create_embedding(self, text: str) -> List[float]:
        """Create an embedding vector for text"""
        try:
            logger.debug(f"Generating embedding for text: {text[:100]}...")
            return self.embeddings.embed_query(text)
        except Exception as e:
            logger.error(f"Failed to create embedding: {str(e)}", exc_info=True)
            raise

    def index_event_report(self, report: EventReport):
        """Index a single event report"""
        try:
            # Prepare document content
            content = f"""
Title: {report.title or ''}
Description: {report.description or ''}
Location: {report.location or ''}
Risk Level: {report.risk_level or ''}
Venue Type: {report.venue_type or ''}
Security Measures: {report.security_measures or ''}
Incident Summary: {report.incident_summary or ''}
Lessons Learned: {report.lessons_learned or ''}
Recommendations: {report.recommendations or ''}
            """.strip()

            # Prepare metadata
            metadata = {
                'id': report.id,
                'date': report.date.isoformat() if report.date else None,
                'risk_level': report.risk_level,
                'type': 'event_report'
            }

            # Split into chunks for better semantic search
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200,
                separators=["\n\n", "\n", ". ", " ", ""]
            )
            chunks = splitter.split_text(content)

            # Index each chunk
            for i, chunk in enumerate(chunks):
                chunk_metadata = {
                    **metadata,
                    'chunk': i,
                    'total_chunks': len(chunks)
                }
                self.add_document(chunk, chunk_metadata)

            logger.info(f"Successfully indexed report {report.id}")

        except Exception as e:
            logger.error(f"Failed to index report {report.id}: {str(e)}", exc_info=True)
            raise

    def index_all_reports(self):
        """Index all event reports"""
        try:
            reports = EventReport.query.all()
            total = len(reports)
            success = 0
            failed = 0

            logger.info(f"Starting indexing of {total} reports...")

            for report in reports:
                try:
                    self.index_event_report(report)
                    success += 1
                except Exception as e:
                    failed += 1
                    logger.error(f"Failed to index report {report.id}: {str(e)}")
                    continue

            logger.info(f"Completed indexing. Success: {success}, Failed: {failed}")

        except Exception as e:
            logger.error(f"Failed to index reports: {str(e)}", exc_info=True)
            raise

# Create singleton instance
vector_store = VectorStore()