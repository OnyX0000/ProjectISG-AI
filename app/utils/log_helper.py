from sqlalchemy.orm import Session
from sqlalchemy import func, asc
import pandas as pd
from app.models.models import UserLog

def get_logs_by_user_and_date(db: Session, user_id: str, ingame_date: str) -> pd.DataFrame:
    logs = db.query(UserLog).filter(
        UserLog.user_id == user_id,
        func.substr(UserLog.ingame_datetime, 1, 10) == ingame_date  
    ).order_by(asc(UserLog.ingame_datetime))
    logs = logs.all()

    if not logs:
        return pd.DataFrame()

    return pd.DataFrame([{
        "user_id": log.user_id,
        "timestamp": log.timestamp,
        "ingame_datetime": log.ingame_datetime,
        "location": log.location,
        "action_type": log.action_type,
        "action_name": log.action_name,
        "detail": log.detail,
        "with": log.with_
    } for log in logs])

def extract_date_only(ingame_datetime: str) -> str:
    """
    예시: '0001.01.01-13.17.29' -> '0001.01.01' 로 변환
    """
    if not ingame_datetime:
        return ""
    return ingame_datetime.split('-')[0]  # '-'를 기준으로 앞부분만 추출
