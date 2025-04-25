from typing import Dict
import json
import os
from sqlalchemy.orm import Session
from app.models.models import UserMBTI

# MBTI 프로필이 저장된 JSON 파일 경로
MBTI_PROFILE_PATH = os.path.join("static", "JSON", "mbti_profile.json")


# MBTI 프로필 JSON 로드
def get_mbti_profile(mbti_type: str) -> dict:
    with open(MBTI_PROFILE_PATH, "r", encoding="utf-8") as f:
        mbti_profiles: Dict[str, Dict[str, str]] = json.load(f)
    return mbti_profiles.get(mbti_type, {
        "name": "알 수 없는 유형",
        "summary": "정의되지 않은 MBTI 유형입니다.",
        "content": "정확한 분석을 위해 더 많은 데이터가 필요합니다."
    })


# MBTI 대화 상태 초기화
def init_mbti_state() -> Dict:
    return {
        "question_count": 0,
        "conversation_history": [],
        "dimension_scores": {"I-E": 0, "S-N": 0, "T-F": 0, "J-P": 0},
        "dimension_counts": {"I-E": 0, "S-N": 0, "T-F": 0, "J-P": 0},
        "question_dimension_match": [],
        "asked_dimensions": set(),
        "current_question": "",
        "current_response": "",
        "current_dimension": "",
        "completed": False
    }


# 사용자별 세션 캐시 (메모리 기반)
user_sessions: dict[str, dict] = {}

def get_session(user_id: str) -> dict:
    if user_id not in user_sessions:
        user_sessions[user_id] = init_mbti_state()
    return user_sessions[user_id]


# 응답 분석 결과에 따라 점수 갱신
def update_score(state: Dict, judged: Dict[str, str]):
    dim = judged["dimension"]
    side = judged["side"]
    if side == dim.split("-")[0]:
        state["dimension_scores"][dim] -= 1
    elif side == dim.split("-")[1]:
        state["dimension_scores"][dim] += 1


# 최종 MBTI 유형 계산 및 DB 저장
def finalize_mbti(user_id: str, state: Dict, db: Session) -> str:
    scores = state["dimension_scores"]
    mbti = ""
    mbti += "I" if scores["I-E"] <= 0 else "E"
    mbti += "S" if scores["S-N"] <= 0 else "N"
    mbti += "T" if scores["T-F"] <= 0 else "F"
    mbti += "J" if scores["J-P"] <= 0 else "P"

    profile = get_mbti_profile(mbti)

    # 세션 상태에 프로필 정보 저장
    state["mbti_type"] = mbti
    state["mbti_name"] = profile["name"]
    state["mbti_summary"] = profile["summary"]
    state["mbti_content"] = profile["content"]
    state["completed"] = True

    session_id = state.get("session_id")

    # DB 저장
    existing = db.query(UserMBTI).filter(UserMBTI.user_id == user_id).first()
    if existing:
        existing.session_id = session_id 
        existing.mbti_type = mbti
        existing.name = profile["name"]
        existing.summary = profile["summary"]
        existing.content = profile["content"]
    else:
        new_entry = UserMBTI(
            session_id = session_id,
            user_id=user_id,
            mbti_type=mbti,
            name=profile["name"],
            summary=profile["summary"],
            content=profile["content"]
        )
        db.add(new_entry)
    db.commit()

    state["completed"] = True
    return mbti
