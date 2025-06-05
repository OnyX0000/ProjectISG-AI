import random
from typing import List, Dict
import matplotlib.pyplot as plt
from langchain_ollama import ChatOllama
from rouge import Rouge
from evaluate import load as load_metric
from bert_score import score as bertscore
import pandas as pd
import gc

# 💡 용도별 프롬프트 테스트셋 정의
PROMPT_SETS = {
    "question": [
        {"input": "다음 대화 내용을 바탕으로 MBTI 질문을 생성해줘: 나는 혼자 있는 게 편해", "reference": "혼자 있는 것을 즐기시나요, 아니면 사람들과 함께 있을 때 더 편한가요?"},
    ],
    "evaluation": [
        {"input": "질문: 평소에 계획을 세우는 것을 좋아하시나요? 대답: 그때그때 달라요.", "reference": "해당 대답은 계획을 세우는 것을 선호하지 않는 경향으로 해석됩니다."},
    ],
    "diary": [
        {"input": "2024-05-27의 활동: 농장 물주기, 마을 산책, 꽃 수확", "reference": "오늘은 평화로운 하루였다. 꽃을 수확하고 마을을 거닐며 고요함을 느꼈다."},
    ],
    "emotion": [
        {"input": "오늘의 감성 일기: 햇살 가득한 밭에서 꽃을 돌보며 하루를 보냈다.", "reference": "고요함, 만족감"},
    ],
    "sfx": [
        {"input": "나뭇잎이 바람에 스치는 소리", "reference": "rustling leaves"},
    ],
    "comfy": [
        {"input": "밤하늘 아래 이세계 마을의 조용한 집", "reference": "fantasy village under the stars"},
    ]
}

TEMPERATURES = [0.2, 0.7, 1.0]

MODEL_MAPPING = {
    "question": "gemma3:12b",
    "evaluation": "gemma3:12b",
    "diary": "gemma3:12b",
    "emotion": "gemma3:12b",
    "sfx": "qwen3:8b",
    "comfy": "qwen3:8b"
}

def evaluate_outputs(references: List[str], predictions: List[str]) -> Dict[str, float]:
    rouge = Rouge()
    rouge_scores = rouge.get_scores(predictions, references, avg=True)["rouge-l"]

    # 💡 BLEU 예외 처리
    try:
        import evaluate
        bleu = evaluate.load("sacrebleu")
        bleu_result = bleu.compute(predictions=predictions, references=[[r] for r in references])
        bleu_score = bleu_result["score"]
    except Exception as e:
        print(f"❌ BLEU 계산 실패: {e}")
        bleu_score = 0.0

    # 💡 BERTScore
    bert_p, bert_r, bert_f = bertscore(predictions, references, lang="en")

    return {
        "ROUGE-L": rouge_scores["f"],
        "BLEU": bleu_score,
        "BERTScore-F1": float(bert_f.mean())
    }

def test_llm_outputs() -> pd.DataFrame:
    records = []
    model_cache = {}

    for use_case, prompts in PROMPT_SETS.items():
        references = [p["reference"] for p in prompts]
        input_texts = [p["input"] for p in prompts]

        for temp in TEMPERATURES:
            model_name = MODEL_MAPPING[use_case]
            model_key = f"{model_name}_{temp}"

            if model_key not in model_cache:
                model_cache[model_key] = ChatOllama(model=model_name, temperature=temp)
            llm = model_cache[model_key]

            predictions = [llm.invoke(p).content for p in input_texts]

            metrics = evaluate_outputs(references, predictions)
            metrics["use_case"] = use_case
            metrics["temperature"] = temp
            metrics["model"] = model_name
            records.append(metrics)

        gc.collect()  # GPU 메모리 정리

    return pd.DataFrame(records)

def plot_metrics(df: pd.DataFrame):
    metrics = ["ROUGE-L", "BLEU", "BERTScore-F1"]
    fig, axs = plt.subplots(len(metrics), 1, figsize=(10, 12))

    for i, metric in enumerate(metrics):
        for use_case in df["use_case"].unique():
            subset = df[df["use_case"] == use_case]
            axs[i].plot(subset["temperature"], subset[metric], marker='o', label=use_case)
        axs[i].set_title(metric)
        axs[i].set_xlabel("Temperature")
        axs[i].set_ylabel(metric)
        axs[i].legend()
        axs[i].grid(True)

    plt.tight_layout()
    plt.savefig("llm_evaluation_summary.png")
    print("✅ 평가 완료: llm_evaluation_summary.png 저장됨")

if __name__ == "__main__":
    df_result = test_llm_outputs()
    plot_metrics(df_result)
