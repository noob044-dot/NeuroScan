from pathlib import Path
import sqlite3

from sqlalchemy import Column, Float, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "roadwatch.db"
DATABASE_URL = f"sqlite:///{DATABASE_PATH.as_posix()}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True)
    password = Column(String)
    role = Column(String)
    full_name = Column(String)
    contact_number = Column(String)
    sms_opt_in = Column(Integer, default=1)
    credit_points = Column(Integer, default=0)
    total_points_earned = Column(Integer, default=0)


class Complaint(Base):
    __tablename__ = "complaints"

    id = Column(Integer, primary_key=True)
    issue_type = Column(String)
    image_path = Column(String)
    confidence = Column(Float)
    latitude = Column(Float)
    longitude = Column(Float)
    comment = Column(String)
    status = Column(String, default="Pending")
    user_name = Column(String)
    user_contact = Column(String)
    reference_code = Column(String)
    created_at = Column(String)
    user_id = Column(Integer)
    issue_key = Column(String)
    detection_mode = Column(String)
    model_key = Column(String)
    severity = Column(String)
    last_updated_at = Column(String)
    reward_points = Column(Integer, default=0)
    priority_requested = Column(Integer, default=0)


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    complaint_id = Column(Integer)
    title = Column(String)
    message = Column(String)
    channel = Column(String)
    status_snapshot = Column(String)
    created_at = Column(String)
    read_at = Column(String)


def _ensure_column(cursor: sqlite3.Cursor, table_name: str, column_name: str, definition: str) -> None:
    cursor.execute(f"PRAGMA table_info({table_name})")
    existing_columns = {row[1] for row in cursor.fetchall()}
    if column_name not in existing_columns:
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")


def init_db() -> None:
    Base.metadata.create_all(bind=engine)

    with sqlite3.connect(DATABASE_PATH) as connection:
        cursor = connection.cursor()
        _ensure_column(cursor, "complaints", "reference_code", "VARCHAR")
        _ensure_column(cursor, "complaints", "created_at", "VARCHAR")
        _ensure_column(cursor, "complaints", "user_id", "INTEGER")
        _ensure_column(cursor, "complaints", "issue_key", "VARCHAR")
        _ensure_column(cursor, "complaints", "detection_mode", "VARCHAR")
        _ensure_column(cursor, "complaints", "model_key", "VARCHAR")
        _ensure_column(cursor, "complaints", "severity", "VARCHAR")
        _ensure_column(cursor, "complaints", "last_updated_at", "VARCHAR")
        _ensure_column(cursor, "complaints", "reward_points", "INTEGER DEFAULT 0")
        _ensure_column(cursor, "complaints", "priority_requested", "INTEGER DEFAULT 0")
        _ensure_column(cursor, "users", "sms_opt_in", "INTEGER DEFAULT 1")
        _ensure_column(cursor, "users", "credit_points", "INTEGER DEFAULT 0")
        _ensure_column(cursor, "users", "total_points_earned", "INTEGER DEFAULT 0")
        connection.commit()


init_db()
