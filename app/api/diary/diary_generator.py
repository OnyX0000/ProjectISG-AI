from app.api.diary.graph import build_diary_graph, DiaryState
from app.utils.log_helper import extract_date_only
from app.models.models import Diary
from sqlalchemy.orm import Session
import pandas as pd

def save_diary_to_db(db: Session, user_id: str, date: str, content: str):
    diary = Diary(user_id=user_id, ingame_datetime=date, content=content)
    db.add(diary)
    db.commit()

def run_diary_generation(user_id: str, date: str, group: pd.DataFrame, mbti: str, db: Session, save_to_db: bool = True):
    graph = build_diary_graph()

    input_data = {
        "user_id": user_id,
        "date": date,
        "group": group,
        "mbti": mbti
    }

    state = graph.invoke(input_data)

    content = state["diary"]

    if save_to_db:
        save_diary_to_db(db, user_id, date, content)

    return state


def format_diary_output(state: DiaryState) -> dict:
    return {
        "user_id": state["user_id"],
        "date": state["date"],
        "mbti": state["mbti"],
        "emotion_tags": state["emotion_tags"],
        "emotion_keywords": state["emotion_keywords"],
        "diary": state["diary"]
    }
