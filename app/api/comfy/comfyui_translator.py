from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from app.models.models import comfy_llm

# ✅ 프롬프트 템플릿 설정
translate_prompt = PromptTemplate.from_template(
    """
    /no_think
    너는 텍스트를 ComfyUI에서 사용할 수 있도록 변환하는 전문가야.
    
    [예시]
    Input: "밝고 행복한 장면, 아이들이 뛰어노는 공원"
    Output:
    Positive: "bright, happy scene, children playing in the park"
    Negative: "dark, lonely, sad"

    [예시]
    Input: "어두운 방 안에서 혼자 책을 읽는 사람"
    Output:
    Positive: "person reading a book alone in a dark room"
    Negative: "bright, crowded, noisy"

    [변환할 텍스트]
    Input: "{prompt}"
    Output:
    """
)

# ✅ 체인 생성
translate_chain = translate_prompt | comfy_llm | StrOutputParser()

# ✅ 체인 실행 함수
def format_comfyui_prompt(prompt: str) -> dict:
    """
    한글 프롬프트를 영어로 번역하고 ComfyUI 형식에 맞게 변환합니다.
    """

    # 🔄 LLM 체인 실행
    response = translate_chain.invoke({"prompt": prompt})
    
    # ✅ <think>...</think> 태그 제거 처리
    while "<think>" in response and "</think>" in response:
        start_idx = response.index("<think>")
        end_idx = response.index("</think>") + len("</think>")
        print(f"🛠️ <think> 태그 발견: {response[start_idx:end_idx]} → 삭제 처리합니다.")
        response = response[:start_idx] + response[end_idx:]

    # ✅ Positive/Negative 구분
    if "Positive:" in response and "Negative:" in response:
        positive = response.split("Positive:")[1].split("Negative:")[0].strip()
        negative = response.split("Negative:")[1].strip()
    else:
        raise ValueError("⚠️ [ERROR] 변환 실패: LLM의 출력 형식이 올바르지 않습니다.")

    # ✅ ComfyUI 포맷에 맞춰 반환 (리스트 형태, 양 끝에 " 제거)
    positive_list = [phrase.strip().strip('"') for phrase in positive.split(",") if phrase.strip()]
    negative_list = [phrase.strip().strip('"') for phrase in negative.split(",") if phrase.strip()]

    return {
        "positive": positive_list,
        "negative": negative_list
    }