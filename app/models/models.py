from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String
from langchain_community.chat_models import ChatOllama

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
    screenshot = Column(String)  # ✅ 스크린샷 경로 추가

class UserMBTI(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, unique=True, index=True)
    mbti_type = Column(String)
    name = Column(String)
    summary = Column(String)
    content = Column(String)

# 모든 LLM 초기화는 이곳에서 관리
llm_question = ChatOllama(model="gemma3:12b", temperature=0.7)
llm_evaluator = ChatOllama(model="gemma3:12b", temperature=0.7)

__all__ = ["llm_question", "llm_evaluator"]