from sqlalchemy.orm import Session
from sqlalchemy import func, asc
import pandas as pd
import os
from pathlib import Path
from dotenv import load_dotenv
from app.models.models import UserLog

load_dotenv()
STATIC_BASE_URL = os.getenv("STATIC_BASE_URL")

def extract_date_only(ingame_datetime: str) -> str:
    """
    예시: '0001.01.01-13.17.29' -> '0001.01.01' 로 변환
    """
    if not ingame_datetime:
        return ""
    return ingame_datetime.split('-')[0]  # '-'를 기준으로 앞부분만 추출

def get_logs_by_user_and_date(db: Session, session_id: str, user_id: str, ingame_date: str) -> pd.DataFrame:
    """
    DB에서 session_id, user_id, ingame_date에 해당하는 로그를 조회합니다.
    
    Args:
        db (Session): SQLAlchemy 세션
        session_id (str): 세션 ID
        user_id (str): 사용자 ID
        ingame_date (str): 조회할 인게임 날짜 (0001.01.01-09.15.55 형식)

    Returns:
        pd.DataFrame: 조회된 로그 데이터프레임
    """
    
    # ✅ 날짜 포맷 변환 (extract_date_only 함수 활용)
    formatted_date = extract_date_only(ingame_date)

    # ✅ 쿼리 실행
    logs = db.query(UserLog).filter(
        UserLog.session_id == session_id,
        UserLog.user_id == user_id,
        func.substr(UserLog.ingame_datetime, 1, 10) == formatted_date
    ).order_by(asc(UserLog.ingame_datetime)).all()

    # ✅ 조회 결과 확인
    if not logs:
        return pd.DataFrame()

    # ✅ DataFrame 생성
    logs_df = pd.DataFrame([{
        "user_id": log.user_id,
        "timestamp": log.timestamp,
        "ingame_datetime": log.ingame_datetime,
        "location": log.location,
        "action_type": log.action_type,
        "action_name": log.action_name,
        "detail": log.detail,
        "with": log.with_,
        "screenshot": log.screenshot if log.screenshot else ""
    } for log in logs])

    return logs_df

def to_relative_screenshot_path(full_path: str) -> str:
    """
    스크린샷 파일의 절대 경로를 static/ 이하 상대 경로로 변환하는 함수
    """
    if full_path and "static" in full_path:
        static_index = full_path.index("static")
        return full_path[static_index:].replace("\\", "/")  # 윈도우 경로 \\ 를 /로 변환
    return full_path

# 기준 static 디렉토리
STATIC_ROOT = Path("static").resolve()

def convert_path_to_url(relative_path: str) -> str:
    """
    상대 경로를 보안적으로 안전한 URL로 변환 (디렉토리 이탈 방지 + BASE_URL 환경 설정)
    """
    # 절대 경로 계산
    full_path = (STATIC_ROOT / Path(relative_path)).resolve()

    # 디렉토리 이탈 여부 확인
    if not str(full_path).startswith(str(STATIC_ROOT)):
        raise ValueError(f"⚠️ Unsafe path detected: {relative_path}")

    # static 하위 경로만 추출
    relative_to_static = full_path.relative_to(STATIC_ROOT)
    url_path = f"{STATIC_BASE_URL}/{relative_to_static.as_posix()}"

    return url_path