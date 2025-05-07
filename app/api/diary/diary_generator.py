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
    # ✅ None 체크 및 경로 수정
    if best_screenshot_path and best_screenshot_path.startswith("None"):
        best_screenshot_path = best_screenshot_path.replace("None", "")
    
    # ✅ 기본값 설정: None일 경우에도 "없음"으로 명시
    emotion_tags_str = ",".join(emotion_tags) if emotion_tags else None
    emotion_keywords_str = ",".join(emotion_keywords) if emotion_keywords else None

    # 🔍 디버그 로그 추가
    print("📝 Saving to DB")
    print(f"Session ID: {session_id}")
    print(f"User ID: {user_id}")
    print(f"Ingame Date: {date}")
    print(f"Content: {content}")
    print(f"Best Screenshot Path: {best_screenshot_path}")
    print(f"Emotion Tags: {emotion_tags_str}")
    print(f"Emotion Keywords: {emotion_keywords_str}")

    # ✅ DB 객체 생성
    try:
        diary = Diary(
            session_id=session_id,
            user_id=user_id,
            ingame_datetime=date,
            content=content,
            best_screenshot_path=best_screenshot_path if best_screenshot_path else None,
            emotion_tags=emotion_tags_str if emotion_tags_str else None,
            emotion_keywords=emotion_keywords_str if emotion_keywords_str else None
        )
        db.add(diary)
        db.commit()
        print("✅ DB Commit 성공")
    except Exception as e:
        print(f"❌ DB Commit 실패: {e}")
        db.rollback()

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
    
    # 💡 여기서 None 처리 추가
    emotion_keywords = emotion_result.get("keywords", [])
    emotion_tags = emotion_result.get("emotion_tags", [])

    if not emotion_keywords:
        print("⚠️ 감정 키워드 생성에 실패했습니다.")
    if not emotion_tags:
        print("⚠️ 감정 태그 생성에 실패했습니다.")

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
