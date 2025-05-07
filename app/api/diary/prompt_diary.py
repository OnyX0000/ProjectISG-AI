from langchain_core.prompts import ChatPromptTemplate
from app.models.models import diary_llm
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

prompt_template = ChatPromptTemplate.from_template("""
너는 감성 일지 생성자야. 유저의 MBTI는 {mbti}이고, 어투는 다음과 같아:
{style_context}

활동 로그:
{log_text}

위 정보를 바탕으로 서정적인 감성 일지를 다음 형식으로 생성해줘.

날짜: 로그 기반 날짜

# 일지 내용

# 오늘의 감정 기록:
(시적인 감정 회고)

지침:
1. 위 포맷을 꼭 유지하면서, 사용자 시점에서 활동 기반 감정적 일지를 작성해.
2. 일지내용은 가능한 한 자세히 작성해.
3. 로그 내용이나 프롬프트 정보는 출력하지마.
""")

emotion_tag_chain = (
    ChatPromptTemplate.from_template(
        """
        아래는 사용자가 작성한 감성 일지입니다:

        {diary}

        이 일지에서 유추할 수 있는 감정 키워드 3~5개와 감정 태그 2~3개를 생성해주세요.

        출력 형식:
        키워드: 키워드1, 키워드2, 키워드3
        태그: 태그1, 태그2
        """
    )
    | diary_llm
    | StrOutputParser()
    | (lambda x: {
        "keywords": [k.strip() for k in x.split("키워드:")[1].split("태그:")[0].split(",")],
        "emotion_tags": [t.strip() for t in x.split("태그:")[1].split(",")]
    })
)
