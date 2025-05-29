import random
from typing import List, Dict
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import gc

from langchain_ollama import ChatOllama
from rouge import Rouge
from evaluate import load as load_metric
from bert_score import score as bertscore

PROMPT_SETS = {
    "question": [
        {"input": "다음 대화 내용을 바탕으로 MBTI 질문을 생성해줘: 나는 혼자 있는 게 편해", "reference": "혼자 있는 것을 즐기시나요, 아니면 사람들과 함께 있을 때 더 편한가요?"}
    ],
    "evaluation": [
        {"input": "질문: 평소에 계획을 세우는 것을 좋아하시나요? 대답: 그때그때 달라요.", "reference": "해당 대답은 계획을 세우는 것을 선호하지 않는 경향으로 해석됩니다."}
    ],
    "diary": [
        {"input": "2024-05-27의 활동: 농장 물주기, 마을 산책, 꽃 수확", "reference": "오늘은 평화로운 하루였다. 꽃을 수확하고 마을을 거닐며 고요함을 느꼈다."}
    ],
    "emotion": [
        {"input": "오늘의 감성 일기: 햇살 가득한 밭에서 꽃을 돌보며 하루를 보냈다.", "reference": "고요함, 만족감"}
    ],
    "sfx": [
        {"input": "나뭇잎이 바람에 스치는 소리", "reference": "rustling leaves"}
    ],
    "comfy": [
        {"input": "밤하늘 아래 이세계 마을의 조용한 집", "reference": "fantasy village under the stars"}
    ]
}

MODEL_LIST = ["gemma3:12b", "qwen3:8b", "phi4:14b", "EEVE-Korean-10.8b:latest"]
TEMPERATURE = 0.5


def evaluate_outputs(use_case: str, references: List[str], predictions: List[str]) -> Dict[str, float]:
    results = {}
    rouge = Rouge()
    try:
        rouge_scores = rouge.get_scores(predictions, references, avg=True)["rouge-l"]
        results["ROUGE-L"] = rouge_scores["f"]
    except:
        results["ROUGE-L"] = 0.0

    try:
        bleu = load_metric("sacrebleu")
        bleu_result = bleu.compute(predictions=predictions, references=[[r] for r in references], tokenize="none")
        results["BLEU"] = bleu_result["score"]
    except:
        results["BLEU"] = 0.0

    lang = "en" if use_case in ["sfx", "comfy"] else "ko"
    try:
        _, _, bert_f = bertscore(predictions, references, lang=lang)
        results["BERTScore-F1"] = float(bert_f.mean())
    except:
        results["BERTScore-F1"] = 0.0

    if use_case in ["emotion", "sfx", "comfy"]:
        exact_matches = [int(pred.strip() == ref.strip()) for pred, ref in zip(predictions, references)]
        results["ExactMatch"] = sum(exact_matches) / len(exact_matches)

        def jaccard(a, b):
            set_a, set_b = set(a.split(", ")), set(b.split(", "))
            return len(set_a & set_b) / len(set_a | set_b) if set_a | set_b else 0.0

        results["Jaccard"] = sum(jaccard(pred, ref) for pred, ref in zip(predictions, references)) / len(predictions)
    else:
        results["ExactMatch"] = None
        results["Jaccard"] = None

    return results


def test_llm_models() -> pd.DataFrame:
    records = []
    model_cache = {}

    for use_case, prompts in PROMPT_SETS.items():
        references = [p["reference"] for p in prompts]
        input_texts = [p["input"] for p in prompts]

        for model_name in MODEL_LIST:
            key = f"{model_name}_{TEMPERATURE}"
            if key not in model_cache:
                model_cache[key] = ChatOllama(model=model_name, temperature=TEMPERATURE)
            llm = model_cache[key]

            predictions = [llm.invoke(p).content if hasattr(llm.invoke(p), "content") else "" for p in input_texts]

            metrics = evaluate_outputs(use_case, references, predictions)
            metrics["use_case"] = use_case
            metrics["model"] = model_name
            records.append(metrics)

        gc.collect()

    return pd.DataFrame(records)


def plot_model_comparison(df: pd.DataFrame):
    use_cases = df["use_case"].unique()
    metrics = ["ROUGE-L", "BLEU", "BERTScore-F1", "ExactMatch", "Jaccard"]
    fig, axs = plt.subplots(len(use_cases), 1, figsize=(12, 5 * len(use_cases)))

    for i, use_case in enumerate(use_cases):
        subset = df[df["use_case"] == use_case]
        models = subset["model"].tolist()
        bar_width = 0.13
        x = np.arange(len(models))

        for j, metric in enumerate(metrics):
            if subset[metric].isnull().all():
                continue  # 해당 지표가 없는 경우 스킵
            scores = subset[metric].fillna(0).tolist()
            offset = (j - len(metrics) / 2) * bar_width + bar_width / 2
            axs[i].bar(x + offset, scores, width=bar_width, label=metric)

        axs[i].set_xticks(x)
        axs[i].set_xticklabels(models)
        axs[i].set_title(f"{use_case} performance")
        axs[i].set_ylabel("Score")
        axs[i].legend()
        axs[i].grid(True)

    plt.tight_layout()
    plt.savefig("llm_model_comparison.png")
    print("✅ 모델 비교 완료: llm_model_comparison.png 저장됨")


if __name__ == "__main__":
    df_result = test_llm_models()
    plot_model_comparison(df_result)
