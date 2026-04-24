import logging
import os
from contextlib import contextmanager
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool
from urllib.parse import quote_plus

from app.core.config import DB_FILE

logger = logging.getLogger("dsa.db.session")

class DatabaseManager:
    """Centralized database engine and session management."""
    
    def __init__(self, sql_server_url: str = None):
        self.sql_server_url = sql_server_url or os.getenv("SQL_SERVER_URL")
        self.is_sql_server = bool(self.sql_server_url)
        self.engine = self._create_engine()
        self.SessionLocal = sessionmaker(bind=self.engine)
        logger.info("Database manager initialized (%s)", "SQL Server" if self.is_sql_server else "SQLite")

    def _create_engine(self):
        if self.is_sql_server:
            try:
                encoded_conn = quote_plus(self.sql_server_url)
                engine = create_engine(
                    f"mssql+pyodbc:///?odbc_connect={encoded_conn}",
                    pool_pre_ping=True, pool_size=10, max_overflow=20, echo=False
                )
                self._run_migrations(engine)
                return engine
            except Exception as exc:
                logger.warning(
                    "SQL Server unavailable, falling back to SQLite local database: %s",
                    exc,
                )
                self.is_sql_server = False

        engine = create_engine(
            f"sqlite:///{DB_FILE}",
            connect_args={"check_same_thread": False},
            poolclass=QueuePool, pool_size=10, max_overflow=20, echo=False
        )

        # Run auto-migrations
        self._run_migrations(engine)
        return engine

    def _run_migrations(self, engine):
        """Automatically add missing columns for new features."""
        columns = [
            ("is_manual_grade", "BIT" if self.is_sql_server else "BOOLEAN DEFAULT 0"),
            ("rubric_file_path", "NVARCHAR(500)" if self.is_sql_server else "VARCHAR(500)"),
            ("score_proof", "NVARCHAR(MAX)" if self.is_sql_server else "TEXT"),
            ("rubric_snapshot", "NVARCHAR(MAX)" if self.is_sql_server else "TEXT")
        ]
        from sqlalchemy import text
        prefix = "ADD" if self.is_sql_server else "ADD COLUMN"
        
        with engine.connect() as conn:
            for col_name, col_type in columns:
                try:
                    conn.execute(text(f"ALTER TABLE grading_history {prefix} {col_name} {col_type}"))
                    conn.commit()
                    logger.info("Database Migration: Added %s", col_name)
                except Exception:
                    pass
            
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def close(self):
        if self.engine:
            self.engine.dispose()
