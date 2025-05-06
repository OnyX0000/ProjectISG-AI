from app.api.diary.graph import build_diary_graph, DiaryState
from app.api.diary.prompt_diary import emotion_tag_chain
from app.api.diary.screenshot_selector import select_best_screenshot
from app.utils.log_helper import to_relative_screenshot_path
from app.models.models import Diary
from sqlalchemy.orm import Session
import pandas as pd

def save_diary_to_db(
    db: Session,
    session_id: str,
    user_id: str,
    date: str,
    content: str,
    best_screenshot_path: str = None,
    emotion_tags: list[str] = None,
    emotion_keywords: list[str] = None
):
    diary = Diary(
        session_id=session_id,
        user_id=user_id,
        ingame_datetime=date,
        content=content,
        best_screenshot_path=best_screenshot_path,
        emotion_tags=",".join(emotion_tags or []),
        emotion_keywords=",".join(emotion_keywords or [])
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

    # 감정 키워드/태그 별도 체인 호출
    emotion_result = emotion_tag_chain.invoke({"diary": diary_content})
    emotion_keywords = emotion_result.get("keywords", [])
    emotion_tags = emotion_result.get("emotion_tags", [])

    # 스크린샷 경로 추출
    screenshot_paths = group['screenshot'].dropna().unique().tolist()
    screenshot_paths = [to_relative_screenshot_path(path) for path in screenshot_paths if path]

    # 대표 이미지 선택
    best_screenshot_path = select_best_screenshot(diary_content, screenshot_paths)

    # 저장
    if save_to_db:
        save_diary_to_db(
            db=db,
            session_id=session_id,
            user_id=user_id,
            date=date,
            content=diary_content,
            best_screenshot_path=best_screenshot_path,
            emotion_tags=emotion_tags,
            emotion_keywords=emotion_keywords
        )

    return {
        "user_id": user_id,
        "date": date,
        "mbti": mbti,
        "diary": diary_content,
        "emotion_tags": emotion_tags,
        "emotion_keywords": emotion_keywords,
        "session_id": session_id,
        "best_screenshot_path": best_screenshot_path
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

def regenerate_emotion_info(diary_text: str) -> dict:
    result = emotion_tag_chain.invoke({"diary": diary_text})
    return {
        "keywords": result["keywords"],
        "emotion_tags": result["emotion_tags"]
    }
