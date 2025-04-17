from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import DATABASE_URL

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}  # SQLite에 필요
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
