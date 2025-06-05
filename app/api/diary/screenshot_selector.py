import hashlib
import json
import os
from app.utils.image_helper import run_captioning
from app.utils.log_helper import convert_path_to_url, to_relative_screenshot_path
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from app.models.models import embedding_model

# 캐시 디렉토리
CACHE_DIR = "cache/embeddings"
os.makedirs(CACHE_DIR, exist_ok=True)

model = embedding_model

def get_cached_embedding(path: str):
    key = hashlib.md5(path.encode()).hexdigest()
    cache_path = os.path.join(CACHE_DIR, f"{key}.json")

    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data["caption"], data["embedding"]
        except Exception as e:
            print(f"⚠️ 캐시 로딩 실패 ({cache_path}): {e}")
            return None, None
    return None, None

def save_embedding_to_cache(path: str, caption: str, embedding: list):
    key = hashlib.md5(path.encode()).hexdigest()
    cache_path = os.path.join(CACHE_DIR, f"{key}.json")
    try:
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump({"caption": caption, "embedding": embedding}, f)
    except Exception as e:
        print(f"⚠️ 캐시 저장 실패: {e}")

def select_best_screenshot(diary_text: str, screenshot_paths: list[str]) -> str:
    if not screenshot_paths:
        return to_relative_screenshot_path("static/screenshot/default.png")

    valid_paths = [p for p in screenshot_paths if os.path.exists(p)]
    if not valid_paths:
        return to_relative_screenshot_path("static/screenshot/default.png")

    diary_embedding = model.embed_query(diary_text)

    best_score = -1
    best_path = None

    for path in valid_paths:
        caption, cached_embedding = get_cached_embedding(path)

        if not caption or not cached_embedding:
            try:
                caption = run_captioning(path)
                caption_embedding = model.embed_query(caption)
                save_embedding_to_cache(path, caption, caption_embedding)
            except Exception as e:
                print(f"⚠️ 임베딩 생성 실패 for {path}: {e}")
                continue
        else:
            caption_embedding = cached_embedding

        try:
            score = cosine_similarity([diary_embedding], [caption_embedding])[0][0]
        except Exception as e:
            print(f"⚠️ Similarity 계산 실패 for {path}: {e}")
            continue

        if score > best_score:
            best_score = score
            best_path = path

    if best_path:
        return convert_path_to_url(best_path)
    else:
        return to_relative_screenshot_path("static/screenshot/default.png")
