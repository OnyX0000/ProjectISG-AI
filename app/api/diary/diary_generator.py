from app.api.diary.graph import build_diary_graph, DiaryState
from app.models.models import Diary
from sqlalchemy.orm import Session

def save_diary_to_db(db: Session, user_id: str, date: str, content: str):
    diary = Diary(user_id=user_id, ingame_datetime=date, content=content)
    db.add(diary)
    db.commit()

def run_diary_generation(user_id: str, date: str, group, mbti: str, db: Session):
    graph = build_diary_graph()
    state = graph.invoke({
        "user_id": user_id,
        "date": date,
        "group": group,
        "mbti": mbti
    })

    content = state["diary"]
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
