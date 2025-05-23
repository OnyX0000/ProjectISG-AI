from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, ForeignKey
from langchain_ollama import ChatOllama, OllamaEmbeddings
from transformers import BlipProcessor, BlipForConditionalGeneration

Base = declarative_base()

class UserLog(Base):
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
    with_ = Column("with_", String)
    screenshot = Column(String)  

class UserMBTI(Base):
    __tablename__ = "users"

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
    session_id = Column(String, nullable=True)
    user_id = Column(String, ForeignKey("users.user_id"))
    ingame_datetime = Column(String)
    content = Column(String)
    best_screenshot_path = Column(String, nullable=True)
    emotion_tags = Column(String, nullable=True)         
    emotion_keywords = Column(String, nullable=True)  

# 모든 LLM 초기화는 이곳에서 관리
llm_question = ChatOllama(model="gemma3:12b", temperature=0.7)
llm_evaluator = ChatOllama(model="gemma3:12b", temperature=0.7)
diary_llm = ChatOllama(model="gemma3:12b", temperature=1.0)
emo_llm = ChatOllama(model="gemma3:12b", temperature=0.2)
sfx_llm = ChatOllama(model="qwen3:8b", temperature=0.2)
comfy_llm = ChatOllama(model="qwen3:8b", temperature=0.2)

# Ollama 기반 텍스트 임베딩
embedding_model = OllamaEmbeddings(model="nomic-embed-text")

# 이미지 처리 관련 모델
# 모델 및 프로세서 로드 (최초 1회)
image_processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base", use_fast=True)
caption_model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")

__all__ = ["llm_question", "llm_evaluator"]