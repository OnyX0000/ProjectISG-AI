from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from app.models.models import UserLog

# 스크린샷 선택용 프롬프트
select_screenshot_prompt = ChatPromptTemplate.from_template(
"""
다음은 유저의 감성 일지야:

{diary}

아래는 여러 스크린샷 경로야:

{screenshots}

일지 내용과 가장 어울리는 스크린샷 경로 하나만 골라줘.
경로만 그대로 출력해. (설명 추가하지 마.)
""")

def select_best_screenshot(diary: str, screenshot_paths: list[str]) -> str:
    from app.models.models import llm_question  # 사용할 LLM 객체 가져오기
    chain = select_screenshot_prompt | llm_question | StrOutputParser()
    screenshots_text = "\n".join(screenshot_paths)
    best_screenshot = chain.invoke({
        "diary": diary,
        "screenshots": screenshots_text
    })
    return best_screenshot.strip()