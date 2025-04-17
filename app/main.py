from fastapi import FastAPI
from app.routes import diary_router

app = FastAPI()

# 감성일지 관련 API 라우터 등록
app.include_router(diary_router, prefix="/log", tags=["감성일지"])
