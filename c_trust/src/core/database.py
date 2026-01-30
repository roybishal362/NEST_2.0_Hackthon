"""
Database management and schema initialization for C-TRUST system
"""
import sqlite3
from pathlib import Path
from typing import Optional
from sqlalchemy import create_engine, MetaData, Table, Column, String, Float, DateTime, JSON, Boolean, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import logging

from .config import config_manager

logger = logging.getLogger(__name__)

Base = declarative_base()


class ClinicalSnapshotTable(Base):
    """Clinical snapshot database table"""
    __tablename__ = "snapshots"
    
    snapshot_id = Column(String, primary_key=True)
    study_id = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.now)
    processing_status = Column(String, default="PENDING")
    data_sources = Column(JSON)
    snapshot_metadata = Column(JSON)


class AgentSignalTable(Base):
    """Agent signal database table"""
    __tablename__ = "agent_signals"
    
    signal_id = Column(String, primary_key=True)
    snapshot_id = Column(String, nullable=False)
    agent_name = Column(String, nullable=False)
    entity_id = Column(String, nullable=False)
    entity_type = Column(String, nullable=False)
    signal_type = Column(String, nullable=False)
    severity = Column(String, nullable=False)
    confidence = Column(Float, nullable=False)
    evidence = Column(JSON)
    can_abstain = Column(Boolean, default=True)
    timestamp = Column(DateTime, default=datetime.now)


class ConsensusDecisionTable(Base):
    """Consensus decision database table"""
    __tablename__ = "consensus_decisions"
    
    decision_id = Column(String, primary_key=True)
    snapshot_id = Column(String, nullable=False)
    entity_id = Column(String, nullable=False)
    entity_type = Column(String, nullable=False)
    risk_level = Column(String, nullable=False)
    confidence = Column(Float, nullable=False)
    contributing_agents = Column(JSON)
    recommended_actions = Column(JSON)
    dqi_score = Column(Float)
    timestamp = Column(DateTime, default=datetime.now)


class DQIScoreTable(Base):
    """DQI score database table"""
    __tablename__ = "dqi_scores"
    
    score_id = Column(String, primary_key=True)
    entity_id = Column(String, nullable=False)
    snapshot_id = Column(String, nullable=False)
    overall_score = Column(Float, nullable=False)
    dimensions = Column(JSON)
    band = Column(String, nullable=False)
    trend = Column(String)
    timestamp = Column(DateTime, default=datetime.now)


class GuardianEventTable(Base):
    """Guardian event database table"""
    __tablename__ = "guardian_events"
    
    event_id = Column(String, primary_key=True)
    snapshot_id = Column(String, nullable=False)
    event_type = Column(String, nullable=False)
    severity = Column(String, nullable=False)
    entity_id = Column(String)
    data_delta_summary = Column(String)
    expected_behavior = Column(String)
    actual_behavior = Column(String)
    recommendation = Column(String)
    timestamp = Column(DateTime, default=datetime.now)


class AuditEventTable(Base):
    """Audit event database table"""
    __tablename__ = "audit_events"
    
    event_id = Column(String, primary_key=True)
    timestamp = Column(DateTime, default=datetime.now)
    event_type = Column(String, nullable=False)
    entity_id = Column(String)
    user_id = Column(String)
    component_name = Column(String, nullable=False)
    action_taken = Column(String, nullable=False)
    details = Column(JSON)


class DatabaseManager:
    """Manages database connections and operations"""
    
    def __init__(self, database_url: Optional[str] = None):
        """Initialize database manager"""
        self.database_url = database_url or config_manager.get_config().database_url
        self.engine = None
        self.SessionLocal = None
        self._initialize_engine()
    
    def _initialize_engine(self):
        """Initialize SQLAlchemy engine and session factory"""
        try:
            self.engine = create_engine(
                self.database_url,
                echo=False,  # Set to True for SQL debugging
                pool_pre_ping=True
            )
            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )
            logger.info(f"Database engine initialized: {self.database_url}")
        except Exception as e:
            logger.error(f"Failed to initialize database engine: {e}")
            raise
    
    def create_tables(self):
        """Create all database tables"""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create database tables: {e}")
            raise
    
    def get_session(self):
        """Get database session"""
        if not self.SessionLocal:
            raise RuntimeError("Database not initialized")
        return self.SessionLocal()
    
    def health_check(self) -> bool:
        """Check database connectivity"""
        try:
            from sqlalchemy import text
            with self.get_session() as session:
                session.execute(text("SELECT 1"))
                return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    def initialize_schema(self):
        """Initialize database schema with default data"""
        try:
            self.create_tables()
            
            # Add any default configuration or seed data here
            with self.get_session() as session:
                # Example: Insert default system configuration
                logger.info("Database schema initialized successfully")
                session.commit()
                
        except Exception as e:
            logger.error(f"Failed to initialize database schema: {e}")
            raise


# Global database manager instance
db_manager = DatabaseManager()


def get_database():
    """Dependency injection for database sessions"""
    session = db_manager.get_session()
    try:
        yield session
    finally:
        session.close()


def init_database():
    """Initialize database for the application"""
    try:
        db_manager.initialize_schema()
        logger.info("Database initialization completed")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise