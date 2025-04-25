from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, ForeignKey
from langchain_community.chat_models import ChatOllama
from langchain.embeddings import OllamaEmbeddings

Base = declarative_base()

class DiaryLog(Base):
    __tablename__ = "game_logs"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String)
    user_id = Column(String)
    timestamp = Column(String)
    ingame_datetime = Column(String)
    location = Column(String)
    action_type = Column(String)
    action_name = Column(String)
    detail = Column(String)
    with_ = Column("with", String)
    screenshot = Column(String)  

class UserMBTI(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, unique=True, index=True, nullable=False)
    session_id = Column(String, nullable=True)  
    mbti_type = Column(String, nullable=True)
    name = Column(String, nullable=True)
    summary = Column(String, nullable=True)
    content = Column(String, nullable=True)

class Diary(Base):
    __tablename__ = "diary"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("user.user_id"))
    ingame_datetime = Column(String)
    content = Column(String)

# 모든 LLM 초기화는 이곳에서 관리
llm_question = ChatOllama(model="gemma3:12b", temperature=0.7)
llm_evaluator = ChatOllama(model="gemma3:12b", temperature=0.7)
diary_llm = ChatOllama(model="gemma3:12b", temperature=0.7)

# Ollama 기반 텍스트 임베딩
embedding_model = OllamaEmbeddings(model="nomic-embed-text")

__all__ = ["llm_question", "llm_evaluator"]