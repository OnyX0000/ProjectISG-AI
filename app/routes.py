from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Body, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from uuid import uuid4
from datetime import datetime
from sqlalchemy.orm import Session as DbSession
from app.core.database import get_pg_session, get_mongo_collection
from app.utils.action_enum import ActionType, ActionName
from typing import List, Optional
from datetime import datetime
from pathlib import Path
import pandas as pd
import os
import shutil
from app.api.mbti.logic import generate_question, judge_response 
from app.utils.mbti_helper import init_mbti_state, update_score, get_session, update_session, get_mbti_profile, finalize_mbti
from app.models.models import UserLog, UserMBTI
from app.utils.db_helper import (
    get_mbti_by_user_id,
    get_game_logs_by_user_id,
    save_diary_to_mongo,
    get_diary_from_mongo
)
from app.utils.log_helper import get_logs_by_user_and_date, convert_path_to_url, extract_date_only
from app.api.diary.diary_generator import run_diary_generation, format_diary_output, regenerate_emotion_info
from app.utils.image_helper import save_screenshot
from app.api.diary.screenshot_selector import select_best_screenshot
from app.api.diary.prompt_diary import emotion_tag_chain

# Routers
diary_router = APIRouter()
mbti_router = APIRouter()
log_router = APIRouter()

UPLOAD_DIR = "static/screenshot"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# PostgreSQL DB 세션 생성 함수
def get_db():
    db = get_pg_session()
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

    # ✅ 날짜 형식 변환
    try:
        timestamp = datetime.strptime(timestamp, "%Y.%m.%d-%H.%M.%S")
        ingame_datetime = datetime.strptime(ingame_datetime, "%Y.%m.%d-%H.%M.%S")
    except ValueError as e:
        return {
            "message": "날짜 형식이 잘못되었습니다. 'YYYY.MM.DD-HH.MM.SS' 형식을 맞춰주세요.",
            "error": str(e)
        }

    # ✅ SQLAlchemy 모델 생성
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

    # ✅ DB 저장
    try:
        db.add(log)
        db.commit()
    except Exception as e:
        db.rollback()
        return {"message": "DB 저장 중 오류가 발생했습니다.", "error": str(e)}

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
        "with_": log.with_,
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
    """
    사용자별 세션에 질문을 생성하여 반환합니다.
    """
    session_state = get_session(input.user_id, input.session_id, db)

    # 이미 완료된 상태라면 반환
    if session_state.get("completed", False):
        return {"message": "이미 MBTI 테스트가 완료되었습니다.", "completed": True}

    # Dimension 생성
    history = "\n".join(session_state["conversation_history"])
    remain = [d for d in ["I-E", "S-N", "T-F", "J-P"] if d not in session_state["asked_dimensions"]]
    q, dim = generate_question(history, ", ".join(remain))

    # ✅ 만약 dimension이 비어 있거나 유효하지 않다면 기본값으로 대체
    if not dim or dim not in ["I-E", "S-N", "T-F", "J-P"]:
        print(f"⚠️ [WARN] Dimension이 유효하지 않음. 기본값 'I-E'로 대체합니다.")
        dim = "I-E"

    session_state["current_question"] = q
    session_state["current_dimension"] = dim
    update_session(input.user_id, input.session_id, session_state, db)

    return {"question": q, "dimension": dim, "completed": False}

class MBTIAnswerRequest(BaseModel):
    user_id: str
    session_id: str
    response: str

@mbti_router.post("/answer")
async def answer(input: MBTIAnswerRequest, db: DbSession = Depends(get_db)):
    """
    사용자 응답을 저장하고 분석하여 세션에 반영합니다.
    """
    session_state = get_session(input.user_id, input.session_id, db)
    if session_state.get("completed", False):
        return {"message": "이미 MBTI 테스트가 완료되었습니다.", "completed": True}

    # ✅ List를 Set으로 변환 후 추가 (중복 방지)
    current_dimension = session_state["current_dimension"]
    asked_set = set(session_state["asked_dimensions"])
    asked_set.add(current_dimension)
    session_state["asked_dimensions"] = list(asked_set)  

    session_state["conversation_history"].append(
        f"Q: {session_state['current_question']}\nA: {input.response}"
    )
    session_state["current_response"] = input.response
    session_state["dimension_counts"][session_state["current_dimension"]] += 1

    judged = judge_response(input.response, session_state["current_dimension"])
    update_score(session_state, judged)

    # ✅ 5회 QA가 끝나면 자동으로 메모리 릴리스 및 DB 저장
    session_state["question_count"] += 1
    update_session(input.user_id, input.session_id, session_state, db)  # ✅ db 전달

    if session_state["question_count"] >= 5:
        print(f"✅ [INFO] ({input.user_id}, {input.session_id})의 세션 종료 및 메모리 릴리스")
        return {"message": "MBTI 테스트가 완료되었습니다. 세션이 종료되었습니다.", "completed": True}

    return {"message": "응답이 저장되었습니다. 다음 질문을 요청하세요.", "judged": judged, "completed": False}

@mbti_router.get("/users")
async def get_users(limit: int = Query(default=3, description="조회할 사용자 수"), db: DbSession = Depends(get_db)):
    """
    사용자의 MBTI 정보를 지정된 개수만큼 조회하고, 전체 행 개수도 함께 반환합니다.
    """
    # ✅ 전체 행 개수 조회
    total_count = db.query(UserMBTI).count()

    if total_count == 0:
        raise HTTPException(status_code=404, detail="데이터가 존재하지 않습니다.")
    
    # ✅ 지정된 개수만큼 조회
    users = db.query(UserMBTI).limit(limit).all()

    # ✅ 결과 포맷
    result = {
        "total_count": total_count,
        "users": [
            {
                "user_id": user.user_id,
                "session_id": user.session_id,
                "mbti_type": user.mbti_type,
                "name": user.name,
                "summary": user.summary,
                "content": user.content
            }
            for user in users
        ]
    }

    return result

@diary_router.post("/generate_diary")
async def generate_diary_endpoint(
    session_id: str = Body(...),
    user_id: str = Body(...),
    ingame_date: str = Body(...),
    db: DbSession = Depends(get_db)
):
    """
    PostgreSQL에서 로그 정보를 가져오고 Diary를 생성한 뒤, 클라이언트에 반환합니다.
    DB에 저장하지 않습니다.
    """

    # 1️⃣ MBTI 정보 가져오기
    mbti = get_mbti_by_user_id(db, user_id)
    if not mbti:
        print("❌ [ERROR] MBTI 정보가 없습니다.")
        raise HTTPException(status_code=404, detail="해당 user_id의 MBTI 정보를 찾을 수 없습니다.")

    # 2️⃣ 로그 정보 가져오기 (PostgreSQL)
    logs_df = get_logs_by_user_and_date(db, session_id, user_id, ingame_date)

    if logs_df.empty:
        print("⚠️ [ERROR] 로그가 존재하지 않습니다. 404 에러를 반환합니다.")
        raise HTTPException(status_code=404, detail="해당 날짜의 로그가 존재하지 않습니다.")

    # 3️⃣ 일지 생성
    print("📝 [DEBUG] 일지 생성 중...")
    result_state = run_diary_generation(
        session_id=session_id,
        user_id=user_id,
        date=ingame_date,
        group=logs_df,
        mbti=mbti,
        save_to_db=False
    )

    # ✅ 대표 이미지 찾기
    screenshot_paths = logs_df['screenshot'].dropna().unique().tolist()
    best_screenshot_path = select_best_screenshot(result_state["diary"], screenshot_paths)

    # ✅ 날짜 포맷 변환
    formatted_ingame_date = extract_date_only(ingame_date)

    # ✅ 파일명만 반환
    best_screenshot_filename = (
        Path(best_screenshot_path).name if best_screenshot_path else "default.png"
    )

    # ✅ 최종 결과 반환 (format_diary_output 사용)
    formatted_response = format_diary_output(result_state)
    formatted_response.update({
        "message": "Diary generated successfully.",
        "best_screenshot_filename": best_screenshot_filename,
        "formatted_date": formatted_ingame_date
    })

    return formatted_response

@diary_router.post("/regenerate_emotion")
async def regenerate_emotion(diary_text: str):
    return regenerate_emotion_info(diary_text)

@diary_router.post("/save_diary")
async def save_diary_endpoint(
    session_id: str = Body(...),
    user_id: str = Body(...),
    ingame_date: str = Body(...),
    diary_content: str = Body(...),
    db: DbSession = Depends(get_db)  # ✅ PostgreSQL 세션 유지
):
    """
    로그를 조회하여 대표 이미지를 선택하고 MongoDB에 일지 저장
    """
    # 1️⃣ PostgreSQL에서 로그 정보 가져오기
    logs_df = get_logs_by_user_and_date(db, session_id, user_id, ingame_date)

    # ✅ 컬럼이 없을 경우 강제로 생성
    if 'screenshot' not in logs_df.columns:
        print("⚠️ 'screenshot' 컬럼이 누락되어 강제로 생성합니다.")
        logs_df['screenshot'] = ""

    # 2️⃣ 대표 이미지 다시 찾기
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

    # ✅ 4️⃣ MongoDB에 저장
    from app.utils.db_helper import save_diary_to_mongo
    save_diary_to_mongo(
        session_id=session_id,
        user_id=user_id,
        date=formatted_ingame_date,
        content=diary_content,
        emotion_tags=emotion_tags,
        emotion_keywords=emotion_keywords,
        screenshot_path=best_screenshot_path
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
    session_id: str = Body(...)
):
    """
    MongoDB에서 특정 user_id와 session_id에 해당하는 모든 일지를 조회합니다.
    """
    # ✅ MongoDB 컬렉션 가져오기
    diary_collection = get_mongo_collection("diary")

    # ✅ MongoDB 쿼리 실행 (모든 일지 조회)
    diaries = list(diary_collection.find({
        "user_id": user_id,
        "session_id": session_id
    }))

    # ✅ 결과가 없으면 404 에러
    if not diaries:
        raise HTTPException(status_code=404, detail="해당 user_id와 session_id 조합으로 저장된 일지가 없습니다.")

    # ✅ 결과 생성
    result = {
        "user_id": user_id,
        "session_id": session_id,
        "diaries": []
    }

    # ✅ Diary 문서 순회하며 결과 생성
    for diary in diaries:
        screenshot_name = Path(diary.get("screenshot_path")).name if diary.get("screenshot_path") else None
        # ✅ 날짜 포맷 변환
        formatted_date = extract_date_only(diary.get("date"))
        result["diaries"].append({
            "diary_id": str(diary.get("_id")),  # ObjectId를 문자열로 변환
            "ingame_datetime": formatted_date,
            "content": diary.get("content"),
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
async def delete_diary(session_id: str, user_id: str):
    """
    특정 session_id와 user_id에 해당하는 Diary 데이터를 MongoDB에서 삭제합니다.
    """
    diary_collection = get_mongo_collection("diary")
    result = diary_collection.delete_many({
        "session_id": str(session_id),
        "user_id": str(user_id)
    })
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="삭제할 Diary 데이터가 존재하지 않습니다.")
    
    return {"message": f"{result.deleted_count}개의 일지가 삭제되었습니다."}
