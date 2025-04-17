from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, Field
from uuid import uuid4
from sqlalchemy.orm import Session as DbSession
from app.core.database import SessionLocal
from app.models.models import DiaryLog
from app.utils.action_enum import ActionType, ActionName
from typing import List, Optional
from datetime import datetime
import os
import shutil

diary_router = APIRouter()

UPLOAD_DIR = "C:/Wanted/Final/ProjectISG-AI/static/screenshot"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# DB 세션 의존성 주입
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 로그 수신용 모델
class LogEntry(BaseModel):
    session_id: str = Field(..., example="", description="세션 고유 식별자 (UUID)")
    user_id: str = Field(..., example="", description="유저 고유 식별자")
    timestamp: str = Field(..., example="", description="행동 발생 시간 (실제 시스템 시간)")
    ingame_datetime: str = Field(..., example="", description="인게임 내 시간/날짜 (예: 1일차 오전 10시)")
    location: str = Field(..., example="", description="행동이 발생한 장소 (예: 농장, 주방 등)")
    action_type: ActionType = Field(..., example="", description="행동의 대분류 (예: COOKING, FARMING)")
    action_name: ActionName = Field(..., example="", description="행동의 세부 명칭 (예: start_cooking)")
    detail: str = Field(..., example="", description="행동에 대한 상세 설명")
    with_: Optional[str] = Field(None, example="", description="상호작용 대상자 닉네임 (선택)" )
    screenshot: Optional[str] = Field(None, example="", description="스크린샷 이미지 파일 경로 (선택)")

# 스크린샷 + 로그 통합 업로드 API
@diary_router.post("/upload_with_screenshot")
async def upload_log_with_screenshot(
    session_id: str = Form(..., example="", description="세션 고유 식별자 (UUID)"),
    user_id: str = Form(..., example="", description="유저 고유 식별자"),
    timestamp: str = Form(..., example="", description="행동 발생 시간 (실제 시스템 시간)"),
    ingame_datetime: str = Form(..., example="", description="인게임 내 시간/날짜 (예: 1일차 오전 10시)"),
    location: str = Form(..., example="", description="행동이 발생한 장소 (예: 농장, 주방 등)"),
    action_type: ActionType = Form(..., example="", description="행동의 대분류 (예: COOKING, FARMING)"),
    action_name: ActionName = Form(..., example="", description="행동의 세부 명칭 (예: start_cooking)"),
    detail: str = Form(..., example="", description="행동에 대한 상세 설명"),
    with_: str = Form(None, example="", description="상호작용 대상자 닉네임 (선택)"),
    file: Optional[UploadFile] = File(None, description="스크린샷 이미지 파일 (선택)"),
    db: DbSession = Depends(get_db)
):
    screenshot_path = None

    if file:
        ts = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"screenshot_{session_id}_{ts}.png"
        file_path = os.path.join(UPLOAD_DIR, filename)

        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        screenshot_path = file_path

    log = DiaryLog(
        session_id=session_id,
        user_id=user_id,
        timestamp=timestamp,
        ingame_datetime=ingame_datetime,
        location=location,
        action_type=action_type.value,
        action_name=action_name.value,
        detail=detail,
        with_=with_,
        screenshot=screenshot_path
    )

    db.add(log)
    db.commit()

    return {
        "message": "스크린샷 포함 여부와 관계없이 로그 저장 완료",
        "screenshot": screenshot_path or "이미지 없음"
    }

# UUID 세션 ID 발급 API
@diary_router.post("/new_session")
async def generate_session_id():
    session_id = str(uuid4())
    return {"session_id": session_id}

# 모든 로그 조회 API
@diary_router.get("/logs")
async def get_all_logs(db: DbSession = Depends(get_db)):
    logs = db.query(DiaryLog).all()
    result = []
    for log in logs:
        result.append({
            "id": log.id,
            "session_id": log.session_id,
            "user_id": log.user_id,
            "timestamp": log.timestamp,
            "ingame_datetime": log.ingame_datetime,
            "location": log.location,
            "action_type": log.action_type,
            "action_name": log.action_name,
            "detail": log.detail,
            "with": log.with_,
            "screenshot": log.screenshot
        })
    return {"logs": result}

# 개별 로그 삭제 API
@diary_router.delete("/delete/{log_id}")
async def delete_log(log_id: int, db: DbSession = Depends(get_db)):
    log = db.query(DiaryLog).filter(DiaryLog.id == log_id).first()
    if not log:
        return {"error": f"ID {log_id}에 해당하는 로그가 없습니다."}
    db.delete(log)
    db.commit()
    return {"message": f"ID {log_id} 로그가 삭제되었습니다."}

# 로그 수정 API
@diary_router.put("/update/{log_id}")
async def update_log(log_id: int, updated: LogEntry, db: DbSession = Depends(get_db)):
    log = db.query(DiaryLog).filter(DiaryLog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="해당 로그를 찾을 수 없습니다.")

    log.session_id = updated.session_id
    log.user_id = updated.user_id
    log.timestamp = updated.timestamp
    log.ingame_datetime = updated.ingame_datetime
    log.location = updated.location
    log.action_type = updated.action_type.value
    log.action_name = updated.action_name.value
    log.detail = updated.detail
    log.with_ = updated.with_
    log.screenshot = updated.screenshot

    db.commit()
    return {"message": f"ID {log_id} 로그가 수정되었습니다."}
