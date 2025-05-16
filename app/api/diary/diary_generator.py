from app.api.diary.graph import build_diary_graph, DiaryState
from app.api.diary.prompt_diary import emotion_tag_chain
from app.api.diary.screenshot_selector import select_best_screenshot
from app.utils.log_helper import to_relative_screenshot_path
from app.utils.db_helper import save_diary_to_mongo, get_diary_from_mongo
import pandas as pd

def save_diary_to_mongo_db(
    session_id: str,
    user_id: str,
    date: str,
    content: str,
    best_screenshot_path: str = None,
    emotion_tags: list[str] = None,
    emotion_keywords: list[str] = None
):
    """
    MongoDB에 Diary를 저장하는 함수
    """
    try:
        save_diary_to_mongo(
            session_id=session_id,
            user_id=user_id,
            date=date,
            content=content,
            emotion_tags=emotion_tags,
            emotion_keywords=emotion_keywords,
            screenshot_path=best_screenshot_path
        )
        print("✅ MongoDB에 저장 성공")
    except Exception as e:
        print(f"❌ MongoDB 저장 실패: {e}")

def run_diary_generation(
    session_id: str,
    user_id: str,
    date: str,
    group: pd.DataFrame,
    mbti: str,
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

    # "qwen3" 모델을 LLM으로 사용시 처리 필요한 부분
    if "<think>" in diary_content and "</think>" in diary_content:
        start_idx = diary_content.index("<think>")
        end_idx = diary_content.index("</think>") + len("</think>")
        print(f"🛠️ <think> 태그 발견: {diary_content[start_idx:end_idx]} → 삭제 처리합니다.")
        diary_content = diary_content[:start_idx] + diary_content[end_idx:]

    # 감정 키워드/태그 별도 체인 호출
    emotion_result = emotion_tag_chain.invoke({"diary": diary_content})
    
    # 💡 여기서 None 처리 추가
    emotion_keywords = emotion_result.get("keywords", [])
    emotion_tags = emotion_result.get("emotion_tags", [])

    if not emotion_keywords:
        print("⚠️ 감정 키워드 생성에 실패했습니다.")
    else:
        print(emotion_keywords)
        
    if not emotion_tags:
        print("⚠️ 감정 태그 생성에 실패했습니다.")
    else:
        print(emotion_tags)


    # 스크린샷 경로 추출
    screenshot_paths = group['screenshot'].dropna().unique().tolist()
    screenshot_paths = [to_relative_screenshot_path(path) for path in screenshot_paths if path]

    # 대표 이미지 선택
    best_screenshot_path = select_best_screenshot(diary_content, screenshot_paths)

    # ✅ 날짜 포맷 수정 (시간 제거)
    formatted_date = date.split('-')[0] if '-' in date else date

    # ✅ DB에 저장
    if save_to_db:
        save_diary_to_mongo_db(
            session_id=session_id,
            user_id=user_id,
            date=formatted_date,  
            content=diary_content,
            best_screenshot_path=best_screenshot_path,
            emotion_tags=emotion_tags,
            emotion_keywords=emotion_keywords
        )

    return {
        "user_id": user_id,
        "date": formatted_date,
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
        "diary": state["diary"],  
        "best_screenshot_filename": state.get("best_screenshot_path", "default.png"),  
        "formatted_date": state.get("date") 
    }

def regenerate_emotion_info(diary_text: str) -> dict:
    """
    일지 내용을 바탕으로 감정 키워드와 태그를 재생성합니다.
    """
    result = emotion_tag_chain.invoke({"diary": diary_text})
    return {
        "keywords": result["keywords"],
        "emotion_tags": result["emotion_tags"]
    }
