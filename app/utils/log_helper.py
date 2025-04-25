from sqlalchemy.orm import Session
import pandas as pd
from app.models.models import DiaryLog

def get_logs_by_user_and_date(db: Session, user_id: str, ingame_date: str) -> pd.DataFrame:
    logs = db.query(DiaryLog).filter(
        DiaryLog.user_id == user_id,
        DiaryLog.ingame_datetime.like(f"{ingame_date}%")
    ).all()

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
