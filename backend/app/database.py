from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from app.config import settings

DATABASE_URL = f"postgresql://{settings.postgres_user}:{settings.postgres_password}@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class AgentSession(Base):
    __tablename__ = "agent_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    agent_name = Column(String, nullable=False)
    status = Column(String, default="running")
    created_at = Column(DateTime, default=datetime.utcnow)
    stopped_at = Column(DateTime, nullable=True)
    last_heartbeat = Column(DateTime, nullable=True)
    
    messages = relationship("ChatMessage", back_populates="session")


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("agent_sessions.id"))
    role = Column(String, nullable=False)  # user, agent, system
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    session = relationship("AgentSession", back_populates="messages")


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
