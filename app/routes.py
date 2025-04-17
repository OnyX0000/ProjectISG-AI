from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from uuid import uuid4
from sqlalchemy.orm import Session as DbSession
from app.core.database import SessionLocal
from app.models.models import DiaryLog
from typing import List

diary_router = APIRouter()

# DB 세션 의존성 주입
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 1. 클라이언트 로그 수신용 모델
class LogEntry(BaseModel):
    session_id: str
    user_id: str
    timestamp: str
    ingame_datetime: str
    location: str
    action_type: str
    action_name: str
    detail: str
    with_: str | None = None

# 1-1. 로그 업로드 API
@diary_router.post("/upload")
async def receive_logs(logs: List[LogEntry], db: DbSession = Depends(get_db)):
    for log in logs:
        log_data = DiaryLog(
            session_id=log.session_id,
            user_id=log.user_id,
            timestamp=log.timestamp,
            ingame_datetime=log.ingame_datetime,
            location=log.location,
            action_type=log.action_type,
            action_name=log.action_name,
            detail=log.detail,
            with_=log.with_
        )
        db.add(log_data)
    db.commit()
    return {"message": f"{len(logs)}개의 로그 저장 완료"}

# 2. UUID 세션 ID 발급 API
@diary_router.post("/new_session")
async def generate_session_id():
    session_id = str(uuid4())
    return {"session_id": session_id}

# 3. 모든 로그 조회 API
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
            "with": log.with_
        })
    return {"logs": result}

# 4. 개별 로그 삭제 API
@diary_router.delete("/delete/{log_id}")
async def delete_log(log_id: int, db: DbSession = Depends(get_db)):
    log = db.query(DiaryLog).filter(DiaryLog.id == log_id).first()
    if not log:
        return {"error": f"ID {log_id}에 해당하는 로그가 없습니다."}
    db.delete(log)
    db.commit()
    return {"message": f"ID {log_id} 로그가 삭제되었습니다."}

# 5. 로그 수정 API
@diary_router.put("/update/{log_id}")
async def update_log(log_id: int, updated: LogEntry, db: DbSession = Depends(get_db)):
    log = db.query(DiaryLog).filter(DiaryLog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="해당 로그를 찾을 수 없습니다.")

    # 로그 필드 업데이트
    log.session_id = updated.session_id
    log.user_id = updated.user_id
    log.timestamp = updated.timestamp
    log.ingame_datetime = updated.ingame_datetime
    log.location = updated.location
    log.action_type = updated.action_type
    log.action_name = updated.action_name
    log.detail = updated.detail
    log.with_ = updated.with_

    db.commit()
    return {"message": f"ID {log_id} 로그가 수정되었습니다."}