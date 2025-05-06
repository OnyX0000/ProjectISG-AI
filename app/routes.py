from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Body
from pydantic import BaseModel, Field
from uuid import uuid4
from sqlalchemy.orm import Session as DbSession
from app.core.database import SessionLocal
from app.utils.action_enum import ActionType, ActionName
from typing import List, Optional
from datetime import datetime
import pandas as pd
import os
import shutil
from app.api.mbti.logic import generate_question, judge_response 
from app.utils.mbti_helper import init_mbti_state, update_score, get_session, get_mbti_profile, finalize_mbti
from app.models.models import UserLog, UserMBTI, Diary  
from app.utils.db_helper import get_mbti_by_user_id
from app.utils.log_helper import get_logs_by_user_and_date
from app.api.diary.diary_generator import run_diary_generation, format_diary_output, save_diary_to_db

# Routers
diary_router = APIRouter()
mbti_router = APIRouter()

UPLOAD_DIR = "static/screenshot"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class LogEntry(BaseModel):
    session_id: str
    user_id: str
    timestamp: str
    ingame_datetime: str
    location: str
    action_type: ActionType
    action_name: ActionName
    detail: str
    with_: Optional[str] = None
    screenshot: Optional[str] = None

@diary_router.post("/upload_with_screenshot")
async def upload_log_with_screenshot(
    session_id: str = Form(...),
    user_id: str = Form(...),
    timestamp: str = Form(...),
    ingame_datetime: str = Form(...),
    location: str = Form(...),
    action_type: str = Form(...),
    action_name: str = Form(...),
    detail: str = Form(...),
    with_: str = Form(None),
    file: UploadFile = File(None),
    db: DbSession = Depends(get_db)
):
    screenshot_path = None
    if file:
        ts = datetime.now().strftime("%Y%m%d%H%M%S")
        user_folder = os.path.join(UPLOAD_DIR, user_id)
        os.makedirs(user_folder, exist_ok=True)
        filename = f"screenshot_{session_id}_{ts}.png"
        file_path = os.path.join(user_folder, filename)
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        screenshot_path = os.path.relpath(file_path, ".").replace("\\", "/")

    log = UserLog(
        session_id=session_id,
        user_id=user_id,
        timestamp=timestamp,
        ingame_datetime=ingame_datetime,
        location=location,
        action_type=action_type,
        action_name=action_name,
        detail=detail,
        with_=with_,
        screenshot=screenshot_path
    )
    db.add(log)
    db.commit()
    return {"message": "로그 저장 완료", "screenshot": screenshot_path or "스크린샷 없음"}

@diary_router.post("/new_session")
async def generate_session_id():
    return {"session_id": str(uuid4())}

@diary_router.get("/logs")
async def get_all_logs(db: DbSession = Depends(get_db)):
    logs = db.query(UserLog).all()
    result = [{
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
    } for log in logs]
    return {"logs": result}

@diary_router.delete("/delete/{log_id}")
async def delete_log(log_id: int, db: DbSession = Depends(get_db)):
    log = db.query(UserLog).filter(UserLog.id == log_id).first()
    if not log:
        return {"error": f"ID {log_id}에 해당하는 로그가 없습니다."}
    db.delete(log)
    db.commit()
    return {"message": f"ID {log_id} 로그가 삭제되었습니다."}

@diary_router.put("/update/{log_id}")
async def update_log(log_id: int, updated: LogEntry, db: DbSession = Depends(get_db)):
    log = db.query(UserLog).filter(UserLog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="해당 로그를 찾을 수 없습니다.")
    for field in updated.dict():
        setattr(log, field, updated.dict()[field])
    db.commit()
    return {"message": f"ID {log_id} 로그가 수정되었습니다."}

class MBTIAskRequest(BaseModel):
    user_id: str
    session_id: str

@mbti_router.post("/ask")
def ask(input: MBTIAskRequest, db: DbSession = Depends(get_db)):
    session_state = get_session(input.user_id)
    if input.session_id:
        session_state["session_id"] = input.session_id
    if session_state.get("completed", False):
        return {"message": "이 사용자는 이미 MBTI 테스트를 완료했습니다.", "completed": True}
    if session_state["question_count"] >= 10:
        mbti = finalize_mbti(input.user_id, session_state, db)
        return {"message": f"MBTI 테스트가 완료되었습니다. 결과: {mbti}", "completed": True}
    history = "\n".join(session_state["conversation_history"])
    remain = [d for d in ["I-E", "S-N", "T-F", "J-P"] if d not in session_state["asked_dimensions"]]
    q, dim = generate_question(history, ", ".join(remain))
    session_state["current_question"] = q
    session_state["current_dimension"] = dim
    return {"question": q, "dimension": dim, "completed": False}

class MBTIAnswerRequest(BaseModel):
    user_id: str
    response: str

@mbti_router.post("/answer")
def answer(input: MBTIAnswerRequest, db: DbSession = Depends(get_db)):
    session_state = get_session(input.user_id)
    if session_state.get("completed", False):
        return {"message": "이미 MBTI 테스트를 완료했습니다.", "completed": True}
    session_state["conversation_history"].append(
        f"Q: {session_state['current_question']}\nA: {input.response}")
    session_state["current_response"] = input.response
    session_state["dimension_counts"][session_state["current_dimension"]] += 1
    session_state["asked_dimensions"].add(session_state["current_dimension"])
    judged = judge_response(input.response, session_state["current_dimension"])
    update_score(session_state, judged)
    session_state["question_count"] += 1
    if session_state["question_count"] >= 10:
        mbti_type = finalize_mbti(input.user_id, session_state, db)
        return {
            "message": "MBTI 테스트가 완료되었습니다.",
            "mbti": mbti_type,
            "name": session_state["mbti_name"],
            "summary": session_state["mbti_summary"],
            "content": session_state["mbti_content"],
            "completed": True
        }
    return {"message": "응답이 저장되었습니다. 다음 질문을 요청하세요.", "judged": judged, "completed": False}

@mbti_router.get("/result/{user_id}")
def get_final_mbti(user_id: str):
    session_state = get_session(user_id)
    if session_state["question_count"] < 10:
        raise HTTPException(status_code=400, detail="아직 질문이 완료되지 않았습니다.")
    scores = session_state["dimension_scores"]
    mbti = ""
    mbti += "I" if scores["I-E"] <= 0 else "E"
    mbti += "S" if scores["S-N"] <= 0 else "N"
    mbti += "T" if scores["T-F"] <= 0 else "F"
    mbti += "J" if scores["J-P"] <= 0 else "P"
    return {
        "mbti": mbti,
        "dimension_scores": scores,
        "conversation": session_state["conversation_history"],
        "match_accuracy": f"{sum(session_state['question_dimension_match'])} / {len(session_state['question_dimension_match'])}"
    }

@diary_router.post("/generate_diary")
async def generate_diary_endpoint(
    session_id: str = Body(...),
    user_id: str = Body(...),
    ingame_date: str = Body(...),
    db: DbSession = Depends(get_db)
):
    mbti = get_mbti_by_user_id(db, user_id)
    if not mbti:
        raise HTTPException(status_code=404, detail="해당 user_id의 MBTI 정보를 찾을 수 없습니다.")
    logs_df = get_logs_by_user_and_date(db, session_id, user_id, ingame_date)
    if logs_df.empty:
        raise HTTPException(status_code=404, detail="해당 날짜의 로그가 존재하지 않습니다.")
    result_state = run_diary_generation(session_id, user_id, ingame_date, logs_df, mbti, db, save_to_db=False)
    return format_diary_output(result_state)

@diary_router.post("/regenerate_emotion")
def regenerate_emotion(diary_text: str):
    from app.api.diary.diary_generator import regenerate_emotion_info
    return regenerate_emotion_info(diary_text)

@diary_router.post("/save_diary")
async def save_diary_endpoint(
    session_id: str = Body(...),
    user_id: str = Body(...),
    ingame_date: str = Body(...),
    diary_content: str = Body(...),
    best_screenshot_path: str = Body(None),
    db: DbSession = Depends(get_db)
):
    save_diary_to_db(db, session_id, user_id, ingame_date, diary_content, best_screenshot_path)
    return {"message": "Diary saved successfully."}

@diary_router.post("/get_all_diaries")
async def get_all_diaries_endpoint(
    user_id: str = Body(...),
    session_id: str = Body(...),
    db: DbSession = Depends(get_db)
):
    diaries = db.query(Diary).filter(
        Diary.user_id == user_id,
        Diary.session_id == session_id
    ).all()
    if not diaries:
        raise HTTPException(status_code=404, detail="해당 user_id와 session_id 조합으로 저장된 일지가 없습니다.")
    return {
        "user_id": user_id,
        "session_id": session_id,
        "diaries": [
            {
                "diary_id": d.id,
                "ingame_datetime": d.ingame_datetime,
                "content": d.content,
                "best_screenshot_path": d.best_screenshot_path
            } for d in diaries
        ]
    }
