from sqlalchemy.orm import Session
from app.models.models import UserMBTI

def get_mbti_by_user_id(db: Session, user_id: str) -> str | None:
    user = db.query(UserMBTI).filter(UserMBTI.user_id == user_id).first()
    return user.mbti_type if user else None
