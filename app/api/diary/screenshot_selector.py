from app.utils.image_helper import run_captioning
from app.utils.log_helper import convert_path_to_url
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from app.models.models import embedding_model
import os

# ✅ 문장 임베딩 모델 로드 (한글 포함)
model = embedding_model

from app.utils.log_helper import to_relative_screenshot_path
import os
from sklearn.metrics.pairwise import cosine_similarity

def select_best_screenshot(diary_text: str, screenshot_paths: list[str]) -> str:
    """
    일지 내용과 가장 유사한 스크린샷을 선택하여 URL로 반환
    """
    if not screenshot_paths:
        print("⚠️ No screenshot paths provided. 기본 이미지로 대체합니다.")
        return to_relative_screenshot_path("static/screenshot/default.png")

    # ✅ 유효한 경로만 필터링
    valid_paths = [path for path in screenshot_paths if os.path.exists(path)]
    if not valid_paths:
        print("⚠️ All paths are invalid. 기본 이미지로 대체합니다.")
        return to_relative_screenshot_path("static/screenshot/default.png")

    # ✅ 일지 임베딩 생성
    diary_embedding = model.embed_query(diary_text)
    if not diary_embedding:
        print("⚠️ Diary Embedding 생성 실패!")
        return to_relative_screenshot_path("static/screenshot/default.png")
    print(f"📝 Diary Embedding 생성 성공: {diary_embedding}")

    # ✅ 초기화
    best_score = -1
    best_path = None

    for path in valid_paths:
        print(f"🔍 Checking path: {path}")
        try:
            caption = run_captioning(path)
            print(f"📝 Caption generated: {caption}")
        except Exception as e:
            print(f"⚠️ Caption 생성 실패 for {path}: {e}")
            continue

        try:
            caption_embedding = model.embed_query(caption)
            if not caption_embedding:
                print(f"⚠️ Caption Embedding 생성 실패 for {path}")
                continue
        except Exception as e:
            print(f"⚠️ Embedding 생성 실패 for {path}: {e}")
            continue

        try:
            score = cosine_similarity([diary_embedding], [caption_embedding])[0][0]
            print(f"🔄 Similarity score for {path}: {score}")
        except Exception as e:
            print(f"⚠️ Similarity 계산 실패 for {path}: {e}")
            continue

        # ✅ 무조건 가장 높은 유사도를 가진 경로를 선택
        if score > best_score or best_score == -1:
            best_score = score
            best_path = path

    if best_path:
        print(f"✅ Best screenshot path selected: {best_path} with score {best_score}")
        return convert_path_to_url(best_path)
    else:
        print("⚠️ No suitable screenshot found. 기본 이미지로 대체합니다.")
        return to_relative_screenshot_path("static/screenshot/default.png")