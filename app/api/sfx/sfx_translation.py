from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from app.models.models import sfx_llm
import re

# ✅ 프롬프트 템플릿 정의
translate_prompt = PromptTemplate.from_template("""
/no_think
Translate the following Korean sentence to English: 

Korean: {korean_text}
English:
                                                
Rule:
1. Result must include only translated text.
""")

# ✅ LangChain을 이용한 번역 체인 생성
translate_chain = translate_prompt | sfx_llm | StrOutputParser()

def translate_to_english(korean_text: str) -> str:
    """
    한글 텍스트를 영어로 번역합니다.
    """
    # ✅ 1️⃣ 번역 실행
    result = translate_chain.invoke({
        "korean_text": korean_text
    })

    # ✅ 2️⃣ 번역된 결과에서 <think> 태그가 있을 경우 내부 내용 전부 제거
    if "<think>" in result and "</think>" in result:
        print(f"🛠️ <think> 태그 발견: 내용 제거 처리합니다.")
        result = re.sub(r"<think>.*?</think>", "", result, flags=re.DOTALL)

    return result.strip()
