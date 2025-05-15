from app.core.database import get_pg_session, get_mongo_collection
from app.models.models import UserMBTI, UserLog

def get_mbti_by_user_id(db, user_id: str) -> str | None:
    """
    PostgreSQL에서 UserMBTI 정보를 조회합니다.

    :param db: FastAPI에서 전달받은 DB 세션
    :param user_id: 조회할 사용자의 ID
    :return: 사용자의 MBTI 타입 문자열 (없으면 None 반환)
    """
    user = db.query(UserMBTI).filter(UserMBTI.user_id == user_id).first()
    return user.mbti_type if user else None

def get_diary_from_mongo(user_id: str, date: str):
    """
    MongoDB에서 특정 user_id와 date에 해당하는 Diary를 조회합니다.

    :param user_id: 조회할 사용자의 ID
    :param date: 조회할 일지 날짜 (YYYY.MM.DD 형식)
    :return: 일지 데이터 (없으면 None 반환)
    """
    diary_collection = get_mongo_collection("diary")
    
    # 날짜 형식이 맞는지 확인하고 조회
    formatted_date = date if "." in date else date.replace("-", ".")
    
    diary = diary_collection.find_one({"user_id": user_id, "date": formatted_date})
    if not diary:
        print("❌ 일지를 찾을 수 없습니다.")
    return diary

def get_game_logs_by_user_id(db, user_id: str):
    """
    PostgreSQL에서 UserLog 정보를 조회합니다.

    :param db: FastAPI에서 전달받은 DB 세션
    :param user_id: 조회할 사용자의 ID
    :return: 사용자의 모든 게임 로그 리스트
    """
    logs = db.query(UserLog).filter(UserLog.user_id == user_id).all()
    return logs
    
def save_diary_to_mongo(session_id, user_id, date, content, emotion_tags, emotion_keywords, screenshot_path):
    """
    MongoDB에 Diary를 저장합니다.
    """
    # MongoDB의 diary 컬렉션 가져오기
    diary_collection = get_mongo_collection("diary")

    # MongoDB Document 생성
    diary_data = {
        "session_id": session_id,
        "user_id": user_id,
        "date": date,
        "content": content,
        "emotion_tags": emotion_tags,
        "emotion_keywords": emotion_keywords,
        "screenshot_path": screenshot_path
    }

    # MongoDB에 삽입
    diary_collection.insert_one(diary_data)