from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, ForeignKey
from langchain_ollama import ChatOllama, OllamaEmbeddings
from transformers import BlipProcessor, BlipForConditionalGeneration
from functools import lru_cache
from app.utils.embedding_wrapper import LangchainEmbeddingWrapper # 허깅페이스 임베딩모델로 수정할때 사용 
import torch

Base = declarative_base()

# ✅ DB 모델 정의
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

# ✅ 필요 시 캐싱된 LLM 접근 (동일 모델 호출 최적화용, 사용자가 원하는 경우에만 사용)
@lru_cache(maxsize=10)
def get_llm(model_name: str, temperature: float = 0.7) -> ChatOllama:
    return ChatOllama(model=model_name, temperature=temperature)

# ✅ 메모리 절약 + 기존 코드 호환
llm_question = get_llm("EEVE-Korean-10.8b", temperature=0.7)
llm_evaluator = get_llm("phi4:14b", temperature=0.7)
diary_llm = get_llm("gemma3:12b", temperature=1.0)
emo_llm = get_llm("gemma3:12b", temperature=0.2)
sfx_llm = get_llm("qwen3:8b", temperature=0.2)
comfy_llm = get_llm("qwen3:8b", temperature=0.2)

# ✅ 텍스트 임베딩
# embedding_model = LangchainEmbeddingWrapper("dragonkue/BGE-m3-ko") 이거 쓰려면 벡터DB 다시 만들어야 함
embedding_model = OllamaEmbeddings(model = "nomic-embed-text:latest")

# ✅ 이미지 처리 모델 (지연 로딩 + CPU에 올림)
image_processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base", use_fast=True)
caption_model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base").to("cuda" if torch.cuda.is_available() else "cpu")

# ✅ 외부 import 제한
__all__ = [
    "llm_question", "llm_evaluator", "diary_llm", "emo_llm", "sfx_llm", "comfy_llm",
    "embedding_model", "get_llm", "image_processor", "caption_model",
    "UserLog", "UserMBTI", "Diary"
]
