from fastapi import FastAPI
from app.routes import diary_router
from app.models.models import Base
from app.core.database import engine

app = FastAPI()

# ✅ 테이블 생성 (서버 실행 시 1회만 수행)
Base.metadata.create_all(bind=engine)

# ✅ API 라우터 등록
app.include_router(diary_router, prefix="/log", tags=["감성일지"])