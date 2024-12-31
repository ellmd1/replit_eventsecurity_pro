import os
import logging
import json
from datetime import datetime
from typing import List, Dict, Any
import numpy as np
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from sqlalchemy import create_engine, text
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
                # First ensure vector extension is installed
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                conn.commit()
                logger.info("Vector extension initialized")

                # Drop existing table if exists
                conn.execute(text("DROP TABLE IF EXISTS document_embeddings"))
                conn.commit()

                # Create table with vector extension support
                create_table_sql = """
                    CREATE TABLE document_embeddings (
                        id SERIAL PRIMARY KEY,
                        content TEXT NOT NULL,
                        embedding vector(1536),
                        metadata JSONB,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    )
                """
                conn.execute(text(create_table_sql))
                conn.commit()
                logger.info("Created document_embeddings table")

                # Create vector similarity index
                create_index_sql = """
                    CREATE INDEX ON document_embeddings 
                    USING ivfflat (embedding vector_cosine_ops)
                    WITH (lists = 100)
                """
                conn.execute(text(create_index_sql))
                conn.commit()
                logger.info("Created vector similarity index")

                return True

        except Exception as e:
            logger.error(f"Failed to initialize vector store: {str(e)}", exc_info=True)
            return False

    def add_document(self, content: str, metadata: Dict[str, Any] = None):
        """Add a document to the vector store"""
        if metadata is None:
            metadata = {}

        try:
            # Generate embedding
            embedding = self.create_embedding(content)
            embedding_arr = np.array(embedding).astype(float).tolist()

            # Insert using parameterized query
            with self.engine.connect() as conn:
                # Create the vector literal directly in SQL
                sql = text("""
                    INSERT INTO document_embeddings (content, embedding, metadata)
                    VALUES (:content, array_to_vector(:embedding), :metadata)
                """)

                # Create vector conversion function if it doesn't exist
                conn.execute(text("""
                    CREATE OR REPLACE FUNCTION array_to_vector(float8[])
                    RETURNS vector
                    AS $$ SELECT $1::vector $$
                    LANGUAGE SQL
                    IMMUTABLE
                    PARALLEL SAFE;
                """))
                conn.commit()

                # Execute insert with parameters
                conn.execute(sql, {
                    'content': content,
                    'embedding': embedding_arr,
                    'metadata': json.dumps(metadata)
                })
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
            query_arr = np.array(query_embedding).astype(float).tolist()

            # Execute search
            with self.engine.connect() as conn:
                sql = text("""
                    SELECT 
                        content,
                        metadata,
                        1 - (embedding <=> array_to_vector(:embedding)) as similarity
                    FROM document_embeddings
                    WHERE embedding IS NOT NULL
                    ORDER BY embedding <=> array_to_vector(:embedding)
                    LIMIT :limit
                """)

                result = conn.execute(sql, {
                    'embedding': query_arr,
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
            embeddings = self.embeddings.embed_query(text)
            return embeddings
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