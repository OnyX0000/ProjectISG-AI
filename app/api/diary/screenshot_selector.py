from app.utils.image_helper import run_captioning
from app.utils.log_helper import convert_path_to_url
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from app.models.models import embedding_model
import os

# ✅ 문장 임베딩 모델 로드 (한글 포함)
model = embedding_model

def select_best_screenshot(diary_text: str, screenshot_paths: list[str]) -> str:
    """
    일지 내용과 가장 유사한 스크린샷을 선택하여 URL로 반환
    """
    if not screenshot_paths:
        print("⚠️ No screenshot paths provided.")
        return None

    diary_embedding = model.embed_query(diary_text)
    if diary_embedding is None or not len(diary_embedding):
        print("⚠️ Diary Embedding 생성 실패!")
        return None
    print(f"📝 Diary Embedding 생성 성공: {diary_embedding}")

    best_score = -1
    best_path = None

    for path in screenshot_paths:
        print(f"🔍 Checking path: {path} - Exists: {os.path.exists(path)}")

        if not os.path.exists(path):
            continue

        try:
            caption = run_captioning(path)
            print(f"📝 Caption generated: {caption}")
            
            caption_embedding = model.embed_query(caption)
            if caption_embedding is None or not len(caption_embedding):
                print(f"⚠️ Caption Embedding 생성 실패 for {path}")
                continue

            score = cosine_similarity([diary_embedding], [caption_embedding])[0][0]
            print(f"🔄 Similarity score for {path}: {score}")

            # ✅ 무조건 가장 높은 유사도를 가진 경로를 선택
            if score > best_score or best_score == -1:
                best_score = score
                best_path = path
        except Exception as e:
            print(f"⚠️ Error during processing of {path}: {e}")
            continue

    if best_path:
        print(f"✅ Best screenshot path selected: {best_path} with score {best_score}")
        return convert_path_to_url(best_path)
    else:
        print("⚠️ No suitable screenshot found.")
        return None
