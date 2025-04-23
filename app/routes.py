from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Body
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
from app.api.mbti.logic import generate_question, judge_response
from app.utils.mbti_helper import init_mbti_state, update_score, get_session, get_mbti_profile, finalize_mbti
from app.models.models import UserMBTI

diary_router = APIRouter()

mbti_router = APIRouter()

UPLOAD_DIR = "../static/screenshot"
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

# request 모델 정의
class MBTIAskRequest(BaseModel):
    user_id: str

@mbti_router.post("/ask")
def ask(input: MBTIAskRequest, db: DbSession = Depends(get_db)):
    session_state = get_session(input.user_id)

    # ✅ 이미 완료된 경우 메시지 반환
    if session_state.get("completed", False):
        return {
            "message": "이 사용자는 이미 MBTI 테스트를 완료했습니다.",
            "completed": True
        }

    # ✅ 질문이 10개 이상인 경우 MBTI 최종화
    if session_state["question_count"] >= 10:
        mbti = finalize_mbti(input.user_id, session_state, db)
        return {
            "message": f"MBTI 테스트가 완료되었습니다. 결과: {mbti}",
            "completed": True
        }

    # ✅ 계속 진행
    history = "\n".join(session_state["conversation_history"])
    remain = [d for d in ["I-E", "S-N", "T-F", "J-P"] if d not in session_state["asked_dimensions"]]
    q, dim = generate_question(history, ", ".join(remain))
    session_state["current_question"] = q
    session_state["current_dimension"] = dim
    session_state["question_count"] += 1

    return {
        "question": q,
        "dimension": dim,
        "completed": False
    }

class MBTIAnswerRequest(BaseModel):
    user_id: str
    response: str

@mbti_router.post("/answer")
def answer(input: MBTIAnswerRequest, db: DbSession = Depends(get_db)):
    session_state = get_session(input.user_id)

    if session_state.get("completed", False):
        return {"message": "이미 MBTI 테스트를 완료했습니다.", "completed": True}

    # 대화 기록 추가
    session_state["conversation_history"].append(
        f"Q: {session_state['current_question']}\nA: {input.response}"
    )
    session_state["current_response"] = input.response
    session_state["dimension_counts"][session_state["current_dimension"]] += 1
    session_state["asked_dimensions"].add(session_state["current_dimension"])

    # 판단 및 점수 갱신
    judged = judge_response(input.response, session_state["current_dimension"])
    update_score(session_state, judged)

    # 질문 카운트 갱신
    session_state["question_count"] += 1

    # ✅ 10번째 질문이면 MBTI 최종 판단 및 DB 저장
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

    return {
        "message": "응답이 저장되었습니다. 다음 질문을 요청하세요.",
        "judged": judged,
        "completed": False
    }

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