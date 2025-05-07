from fastapi import FastAPI
from app.routes import diary_router, mbti_router
from fastapi.staticfiles import StaticFiles

app = FastAPI(root_path = "/service2")

app.mount("/service2/static", StaticFiles(directory="static"), name="static")

# 감성일지 관련 API 라우터 등록
app.include_router(diary_router, prefix="/log", tags=["감성일지"])

# mbti 관련 API 라우터 등록
app.include_router(mbti_router, prefix="/mbti", tags=["MBTI"])