import numpy as np
import gc
import pandas as pd
import matplotlib.pyplot as plt
from sentence_transformers import SentenceTransformer
from langchain_ollama import OllamaEmbeddings
from sklearn.metrics.pairwise import cosine_similarity
from scipy.stats import spearmanr, pearsonr

try:
    import torch
    has_torch = True
except ImportError:
    has_torch = False

# ✅ 테스트 데이터셋 정의
TEST_DATA = [
    {
        "query": "한글을 만든 사람은 누구인가?",
        "documents": [
            "한글은 세종대왕이 창제하였다.",
            "한글은 한국의 문자이다.",
            "세종대왕은 조선의 왕이다."
        ],
        "expected": "한글은 세종대왕이 창제하였다.",
        "label_scores": [1.0, 0.4, 0.7]
    },
    {
        "query": "대한민국의 수도는 어디인가?",
        "documents": [
            "대한민국의 수도는 서울이다.",
            "서울은 한국의 도시이다.",
            "부산은 대한민국의 도시이다."
        ],
        "expected": "대한민국의 수도는 서울이다.",
        "label_scores": [1.0, 0.8, 0.6]
    }
]

# ✅ 모델 목록 정의
HF_MODELS = {
    "snowflake-ko": "dragonkue/snowflake-arctic-embed-l-v2.0-ko",
    "bge-m3-ko": "dragonkue/BGE-m3-ko",
    "e5-small-ko": "dragonkue/multilingual-e5-small-ko",
    "kosimcse": "BM-K/KoSimCSE-roberta-multitask"
}

OLLAMA_MODELS = {
    "granite": "granite-embedding:278m",
    "nomic": "nomic-embed-text:latest"
}


def evaluate_similarity(model, is_ollama=False):
    all_corr_spearman = []
    all_corr_pearson = []

    for data in TEST_DATA:
        query = data["query"]
        docs = data["documents"]
        human_scores = data["label_scores"]

        if is_ollama:
            query_vec = model.embed_query(query)
            doc_vecs = model.embed_documents(docs)
        else:
            query_vec = model.encode([query])[0]
            doc_vecs = model.encode(docs)

        sims = cosine_similarity([query_vec], doc_vecs)[0]
        spearman_corr = spearmanr(sims, human_scores).correlation
        pearson_corr = pearsonr(sims, human_scores)[0]

        all_corr_spearman.append(spearman_corr)
        all_corr_pearson.append(pearson_corr)

    return np.mean(all_corr_spearman), np.mean(all_corr_pearson)


def evaluate_retrieval(model, is_ollama=False):
    correct = 0
    total = 0

    for data in TEST_DATA:
        query = data["query"]
        docs = data["documents"]
        expected = data["expected"]

        if is_ollama:
            query_vec = model.embed_query(query)
            doc_vecs = model.embed_documents(docs)
        else:
            query_vec = model.encode([query])[0]
            doc_vecs = model.encode(docs)

        sims = cosine_similarity([query_vec], doc_vecs)[0]
        retrieved = docs[np.argmax(sims)]

        if retrieved == expected:
            correct += 1
        total += 1

    return correct / total


def run_all_tests():
    results = []

    for name, path in HF_MODELS.items():
        print(f"🔍 HuggingFace: {name}")
        model = SentenceTransformer(path, device="cuda")

        acc = evaluate_retrieval(model)
        sp, pe = evaluate_similarity(model)
        results.append({"model": name, "rag_accuracy": acc, "spearman": sp, "pearson": pe})

        del model
        gc.collect()
        if has_torch:
            torch.cuda.empty_cache()

    for name, path in OLLAMA_MODELS.items():
        print(f"🔍 Ollama: {name}")
        model = OllamaEmbeddings(model=path)

        acc = evaluate_retrieval(model, is_ollama=True)
        sp, pe = evaluate_similarity(model, is_ollama=True)
        results.append({"model": name, "rag_accuracy": acc, "spearman": sp, "pearson": pe})

        del model
        gc.collect()
        if has_torch:
            torch.cuda.empty_cache()

    return pd.DataFrame(results)


def visualize_results(df: pd.DataFrame):
    metrics = ["rag_accuracy", "spearman", "pearson"]
    fig, axs = plt.subplots(len(metrics), 1, figsize=(10, 12))

    for i, metric in enumerate(metrics):
        axs[i].bar(df["model"], df[metric])
        axs[i].set_title(metric)
        axs[i].set_ylim(0, 1.05)
        axs[i].set_ylabel("Score")
        axs[i].grid(True)

    plt.tight_layout()
    plt.savefig("embedding_model_evaluation.png")
    print("✅ 저장 완료: embedding_model_evaluation.png")


if __name__ == "__main__":
    df_result = run_all_tests()
    visualize_results(df_result)
