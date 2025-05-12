from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Body
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from uuid import uuid4
from sqlalchemy.orm import Session as DbSession
from app.core.database import SessionLocal
from app.utils.action_enum import ActionType, ActionName
from typing import List, Optional
from datetime import datetime
from pathlib import Path
import pandas as pd
import os
import shutil
from app.api.mbti.logic import generate_question, judge_response 
from app.utils.mbti_helper import init_mbti_state, update_score, get_session, get_mbti_profile, finalize_mbti
from app.models.models import UserLog, UserMBTI, Diary  
from app.utils.db_helper import get_mbti_by_user_id
from app.utils.log_helper import get_logs_by_user_and_date, convert_path_to_url, extract_date_only
from app.api.diary.diary_generator import run_diary_generation, format_diary_output, save_diary_to_db
from app.utils.image_helper import save_screenshot

# Routers
diary_router = APIRouter()
mbti_router = APIRouter()
log_router = APIRouter()

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

@log_router.post("/upload_with_screenshot")
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
    """
    로그와 스크린샷을 동시에 업로드하고 DB에 저장합니다.
    """
    screenshot_path = None
    if file:
        screenshot_path = save_screenshot(file, user_id, session_id)

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

    return {
        "message": "로그 저장 완료",
        "screenshot": screenshot_path or "스크린샷 없음"
    }

@diary_router.post("/new_session")
async def generate_session_id():
    return {"session_id": str(uuid4())}

@log_router.get("/logs")
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

@log_router.delete("/delete/{log_id}")
async def delete_log(log_id: int, db: DbSession = Depends(get_db)):
    log = db.query(UserLog).filter(UserLog.id == log_id).first()
    if not log:
        return {"error": f"ID {log_id}에 해당하는 로그가 없습니다."}
    db.delete(log)
    db.commit()
    return {"message": f"ID {log_id} 로그가 삭제되었습니다."}

@log_router.put("/update/{log_id}")
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
async def ask(input: MBTIAskRequest, db: DbSession = Depends(get_db)):
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
async def answer(input: MBTIAnswerRequest, db: DbSession = Depends(get_db)):
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
async def get_final_mbti(user_id: str):
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
    # 1️⃣ MBTI 정보 가져오기
    mbti = get_mbti_by_user_id(db, user_id)
    if not mbti:
        raise HTTPException(status_code=404, detail="해당 user_id의 MBTI 정보를 찾을 수 없습니다.")

    # 2️⃣ 로그 정보 가져오기
    logs_df = get_logs_by_user_and_date(db, session_id, user_id, ingame_date)

    if logs_df.empty:
        print("⚠️ 로그가 존재하지 않습니다. 404 에러를 반환합니다.")
        raise HTTPException(status_code=404, detail="해당 날짜의 로그가 존재하지 않습니다.")

    # # ✅ 'screenshot' 컬럼 존재 여부 확인
    # if 'screenshot' not in logs_df.columns:
    #     print("⚠️ 'screenshot' 컬럼이 DataFrame에 없습니다.")
    # else:
    #     print("✅ 'screenshot' 컬럼이 존재합니다.")
    #     print("=== screenshot 컬럼 내용 ===")
    #     print(logs_df['screenshot'].head())
    #     print("=== 모든 데이터 ===")
    #     print(logs_df.head())

    # 3️⃣ 다이어리 생성 및 대표 이미지 선택
    result_state = run_diary_generation(session_id, user_id, ingame_date, logs_df, mbti, db, save_to_db=False)
    
    # ✅ 대표 이미지 파일명만 추출
    best_screenshot_filename = None
    if result_state.get("best_screenshot_path"):
        best_screenshot_filename = Path(result_state["best_screenshot_path"]).name

    # ✅ 최종 응답 생성
    response = format_diary_output(result_state)
    response["best_screenshot_filename"] = best_screenshot_filename

    if "ingame_datetime" in response:
        # ingame_datetime을 YYYY.MM.DD 형식으로 변경
        response["ingame_datetime"] = extract_date_only(response["ingame_datetime"])

    return response

@diary_router.post("/regenerate_emotion")
async def regenerate_emotion(diary_text: str):
    from app.api.diary.diary_generator import regenerate_emotion_info
    return regenerate_emotion_info(diary_text)

@diary_router.post("/save_diary")
async def save_diary_endpoint(
    session_id: str = Body(...),
    user_id: str = Body(...),
    ingame_date: str = Body(...),
    diary_content: str = Body(...),
    db: DbSession = Depends(get_db)
):
    # 1️⃣ 로그 정보 가져오기
    logs_df = get_logs_by_user_and_date(db, session_id, user_id, ingame_date)

    # ✅ 컬럼이 없을 경우 강제로 생성
    if 'screenshot' not in logs_df.columns:
        print("⚠️ 'screenshot' 컬럼이 누락되어 강제로 생성합니다.")
        logs_df['screenshot'] = ""

    # 2️⃣ 대표 이미지 다시 찾기
    from app.api.diary.screenshot_selector import select_best_screenshot

    try:
        screenshot_paths = logs_df['screenshot'].dropna().unique().tolist()
    except KeyError:
        print("⚠️ 'screenshot' 컬럼이 존재하지 않아서 기본 이미지로 대체합니다.")
        screenshot_paths = ["static/screenshot/default.png"]

    # ✅ 기본 이미지 설정
    if not screenshot_paths:
        print("⚠️ 대표 이미지가 없어서 기본 이미지로 대체합니다.")
        best_screenshot_path = "static/screenshot/default.png"
    else:
        best_screenshot_path = select_best_screenshot(diary_content, screenshot_paths)

    # ✅ 3️⃣ 감정 태그/키워드 생성
    from app.api.diary.prompt_diary import emotion_tag_chain
    emotion_result = emotion_tag_chain.invoke({"diary": diary_content})
    
    emotion_keywords = emotion_result.get("keywords", [])
    emotion_tags = emotion_result.get("emotion_tags", [])

    if not emotion_keywords:
        emotion_keywords = ["미정"]
        print("⚠️ 감정 키워드 생성에 실패하여 기본값 '미정'으로 설정되었습니다.")
    
    if not emotion_tags:
        emotion_tags = ["없음"]
        print("⚠️ 감정 태그 생성에 실패하여 기본값 '없음'으로 설정되었습니다.")

    # ✅ 인게임 날짜를 연월일까지만 추출
    formatted_ingame_date = extract_date_only(ingame_date)

    # 4️⃣ DB에 저장
    save_diary_to_db(
        db, 
        session_id, 
        user_id, 
        formatted_ingame_date, 
        diary_content, 
        best_screenshot_path,
        emotion_tags, 
        emotion_keywords
    )
    
    # ✅ 파일명만 반환
    best_screenshot_filename = None
    if best_screenshot_path:
        best_screenshot_filename = Path(best_screenshot_path).name

    return {
        "message": "Diary saved successfully.",
        "best_screenshot_filename": best_screenshot_filename,
        "emotion_tags": emotion_tags,
        "emotion_keywords": emotion_keywords
    }

# ✅ FileResponse로 반환할 파일 기본 경로 설정
BASE_IMAGE_PATH = Path("static/screenshot")

@diary_router.post("/get_all_diaries")
async def get_all_diaries_endpoint(
    user_id: str = Body(...),
    session_id: str = Body(...),
    db: DbSession = Depends(get_db)
):
    # DB에서 일지 조회
    diaries = db.query(Diary).filter(
        Diary.user_id == user_id,
        Diary.session_id == session_id
    ).all()

    if not diaries:
        raise HTTPException(status_code=404, detail="해당 user_id와 session_id 조합으로 저장된 일지가 없습니다.")

    # ✅ 결과 생성
    result = {
        "user_id": user_id,
        "session_id": session_id,
        "diaries": []
    }

    for diary in diaries:
        # 파일명만 추출
        screenshot_name = Path(diary.best_screenshot_path).name if diary.best_screenshot_path else None

        # ✅ 날짜 형식 변경 (extract_date_only 사용)
        formatted_date = extract_date_only(diary.ingame_datetime)

        # ✅ 파일명만 반환
        result["diaries"].append({
            "diary_id": diary.id,
            "ingame_datetime": formatted_date,
            "content": diary.content,
            "best_screenshot_filename": screenshot_name
        })

    return result

# ✅ 파일을 다운로드가 아닌 화면에 바로 렌더링
@diary_router.get("/render_image/{image_name}")
async def render_image(image_name: str):
    file_path = BASE_IMAGE_PATH / image_name
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="파일이 존재하지 않습니다.")
    
    # ✅ 다운로드가 아닌 브라우저에 바로 렌더링하도록 설정
    headers = {"Content-Disposition": "inline"}
    return FileResponse(file_path, media_type='image/png', headers=headers)

@log_router.delete("/diary/delete")
async def delete_diary(session_id: str, user_id: str, db: DbSession = Depends(get_db)):
    """
    특정 session_id와 user_id에 해당하는 Diary 데이터를 삭제합니다.
    """
    diaries = db.query(Diary).filter(Diary.session_id == session_id, Diary.user_id == user_id).all()
    
    if not diaries:
        raise HTTPException(status_code=404, detail="삭제할 Diary 데이터가 존재하지 않습니다.")
    
    for diary in diaries:
        db.delete(diary)
    
    db.commit()
    return {"message": f"{len(diaries)}개의 일지가 삭제되었습니다."}