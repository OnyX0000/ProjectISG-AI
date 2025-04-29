from app.api.diary.graph import build_diary_graph, DiaryState
from app.api.diary.screenshot_selector import select_best_screenshot
from app.utils.log_helper import to_relative_screenshot_path
from app.utils.log_helper import extract_date_only
from app.models.models import Diary
from sqlalchemy.orm import Session
import pandas as pd

def save_diary_to_db(
    db: Session,
    session_id: str,
    user_id: str,
    date: str,
    content: str,
    best_screenshot_path: str = None
):
    diary = Diary(
        session_id=session_id,
        user_id=user_id,
        ingame_datetime=date,
        content=content,
        best_screenshot_path=best_screenshot_path
    )
    db.add(diary)
    db.commit()


def run_diary_generation(
    session_id: str,
    user_id: str,
    date: str,
    group: pd.DataFrame,
    mbti: str,
    db: Session,
    save_to_db: bool = True
):
    graph = build_diary_graph()

    input_data = {
        "user_id": user_id,
        "date": date,
        "group": group,
        "mbti": mbti,
    }

    state = graph.invoke(input_data)

    diary_content = state["diary"]

    # 스크린샷 경로 추출
    screenshot_paths = group['screenshot'].dropna().unique().tolist()
    screenshot_paths = [to_relative_screenshot_path(path) for path in screenshot_paths if path]

    # best screenshot 선택
    best_screenshot_path = select_best_screenshot(diary_content, screenshot_paths)

    if save_to_db:
        save_diary_to_db(db, session_id, user_id, date, diary_content, best_screenshot_path)

    return {
        "user_id": state["user_id"],            # ✅ state 기준
        "date": state["date"],                  # ✅ date
        "mbti": state["mbti"],                  # ✅ mbti
        "emotion_tags": state["emotion_tags"],  # ✅ emotion_tags
        "emotion_keywords": state["emotion_keywords"],  # ✅ emotion_keywords
        "diary": state["diary"],                 # ✅ diary
        "session_id": session_id,                # 추가 정보 (저장용)
        "best_screenshot_path": best_screenshot_path  # 추가 정보 (저장용)
    }

def format_diary_output(state: DiaryState) -> dict:
    return {
        "user_id": state["user_id"],
        "date": state["date"],
        "mbti": state["mbti"],
        "emotion_tags": state["emotion_tags"],
        "emotion_keywords": state["emotion_keywords"],
        "diary": state["diary"]
    }
