from typing import Dict, Tuple
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from app.models.models import llm_question, llm_evaluator

# 질문 생성을 위한 프롬프트
question_prompt = ChatPromptTemplate.from_template(
    """너는 MBTI 분석가야. 지금까지의 대화:
{history}
아직 질문하지 않은 dimension은 다음과 같아: {remaining_dimensions}
이 중 하나를 골라 다음과 같은 형식으로 질문을 생성해줘:

질문: [질문 내용]
dimension: [I-E / S-N / T-F / J-P 중 하나]
"""
)

# 응답 판단을 위한 프롬프트
judge_prompt = PromptTemplate.from_template(
    """다음 사용자의 응답을 읽고, 주어진 MBTI 성향 dimension의 관점에서 어느 방향에 가까운지를 판단해줘.

응답:
"{response}"

분석 대상 dimension: {target_dimension}

아래 중 하나의 방향을 선택:
- I vs E
- S vs N
- T vs F
- J vs P

출력 예시 형식:
dimension: T-F
side: F
이유: 판단 근거를 한 문장으로 기술
"""
)

question_chain = question_prompt | llm_question | StrOutputParser()
judge_chain = judge_prompt | llm_evaluator | StrOutputParser()

# 질문 생성 함수
def generate_question(history: str, remaining_dimensions: str) -> tuple[str, str]:
    if not remaining_dimensions:
        print("⚠️ [WARN] 남은 Dimension이 없습니다. 기본값으로 대체합니다.")
        remaining_dimensions = "I-E, S-N, T-F, J-P"
    
    result = question_chain.invoke({
        "history": history,
        "remaining_dimensions": remaining_dimensions
    })
    lines = result.strip().splitlines()
    
    # ✅ 올바른 형식의 질문이 생성되었는지 확인
    question_line = next((line for line in lines if line.lower().startswith("질문")), None)
    dimension_line = next((line for line in lines if line.lower().startswith("dimension")), None)
    
    if not question_line or not dimension_line:
        print("⚠️ [WARN] 질문 생성 실패. 기본값으로 대체합니다.")
        return "기본 질문: 당신은 혼자 있을 때 에너지를 얻나요?", "I-E"

    question = question_line.split(":", 1)[1].strip()
    dimension = dimension_line.split(":", 1)[1].strip()

    # ✅ 만약 dimension이 비어 있다면 기본값으로 대체
    if not dimension or dimension not in ["I-E", "S-N", "T-F", "J-P"]:
        print(f"⚠️ [WARN] Dimension이 유효하지 않습니다. 기본값으로 대체합니다. (dimension={dimension})")
        dimension = "I-E"
    
    return question, dimension

# 응답 평가 함수
def judge_response(response: str, target_dimension: str) -> dict:
    result = judge_chain.invoke({
        "response": response,
        "target_dimension": target_dimension
    })
    lines = result.strip().splitlines()
    dim_line = next(line for line in lines if line.lower().startswith("dimension"))
    side_line = next(line for line in lines if line.lower().startswith("side"))
    reason_line = next((line for line in lines if line.lower().startswith("이유")), "")
    dim = dim_line.split(":")[1].strip()
    side = side_line.split(":")[1].strip()
    reason = reason_line.split(":", 1)[1].strip() if ":" in reason_line else "(근거 없음)"
    return {
        "dimension": dim,
        "side": side,
        "reason": reason
    }
