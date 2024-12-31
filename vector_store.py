import os
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
        self.embeddings = OpenAIEmbeddings()
        self.engine = create_engine(os.environ['DATABASE_URL'])
    
    def create_embedding(self, text: str) -> List[float]:
        """Create an embedding for a given text."""
        return self.embeddings.embed_query(text)
    
    def add_document(self, content: str, metadata: Dict[str, Any] = None):
        """Add a document to the vector store."""
        embedding = self.create_embedding(content)
        
        with self.engine.connect() as conn:
            query = text("""
                INSERT INTO document_embeddings (content, embedding, metadata)
                VALUES (:content, :embedding, :metadata)
            """)
            conn.execute(query, {
                'content': content,
                'embedding': embedding,
                'metadata': metadata or {}
            })
            conn.commit()
    
    def search_similar(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search for similar documents using cosine similarity."""
        query_embedding = self.create_embedding(query)
        
        with self.engine.connect() as conn:
            query = text("""
                SELECT content, metadata, 
                       1 - (embedding <=> :query_embedding) as similarity
                FROM document_embeddings
                ORDER BY similarity DESC
                LIMIT :limit
            """)
            result = conn.execute(query, {
                'query_embedding': query_embedding,
                'limit': limit
            })
            
            return [{
                'content': row.content,
                'metadata': row.metadata,
                'similarity': float(row.similarity)
            } for row in result]

    def index_event_report(self, report: EventReport):
        """Index an event report's content in the vector store."""
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
            'date': report.date.isoformat(),
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

    def index_all_reports(self):
        """Index all existing event reports."""
        reports = EventReport.query.all()
        for report in reports:
            self.index_event_report(report)

vector_store = VectorStore()
