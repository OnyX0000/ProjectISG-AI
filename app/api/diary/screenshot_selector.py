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
        return None

    diary_embedding = model.encode([diary_text])[0]

    best_score = -1
    best_path = None

    for path in screenshot_paths:
        if not os.path.exists(path):
            continue

        try:
            caption = run_captioning(path)
            caption_embedding = model.encode([caption])[0]
            score = cosine_similarity([diary_embedding], [caption_embedding])[0][0]

            if score > best_score:
                best_score = score
                best_path = path
        except Exception:
            continue

    if best_path:
        return convert_path_to_url(best_path)
    else:
        return None
