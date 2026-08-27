from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def migrate_sqlite() -> None:
    if not settings.database_url.startswith("sqlite"):
        return
    statements = [
        ("datasets", "source_type", "ALTER TABLE datasets ADD COLUMN source_type VARCHAR(32) DEFAULT 'file'"),
        ("dashboards", "layout_json", "ALTER TABLE dashboards ADD COLUMN layout_json TEXT DEFAULT '[]'"),
        ("dashboards", "share_token", "ALTER TABLE dashboards ADD COLUMN share_token VARCHAR(64) DEFAULT ''"),
        ("dashboards", "summary_json", "ALTER TABLE dashboards ADD COLUMN summary_json TEXT DEFAULT '{}'"),
    ]
    with engine.begin() as conn:
        for table, column, ddl in statements:
            rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
            names = {row[1] for row in rows}
            if names and column not in names:
                conn.execute(text(ddl))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
