from langchain_core.prompts import ChatPromptTemplate
from app.models.models import diary_llm, emo_llm
from langchain_core.output_parsers import StrOutputParser

# llm을 qwen3:8b를 쓴다면 처음에 /no_think나 /think라고 붙여서 switch mode
prompt_template = ChatPromptTemplate.from_template("""

너는 감성 일지 생성자야. 유저의 MBTI는 {mbti}이고, 어투는 다음과 같아:
{style_context}

활동 로그:
{log_text}

위 정보를 바탕으로 서정적인 감성 일지를 다음 형식으로 생성해줘.

# 일지 내용

# 오늘의 감정 기록:
(짧고 간결한 시적인 감정 회고)
                                                   
# 감정 키워드 :
# 감정 태그 :

지침:
1. 위 포맷을 꼭 유지하면서, 사용자 시점에서 실제 행한 활동 기반 감정적 일지를 작성해.
2. 일지내용은 실제로 행동로그가 생성된 활동만 가능한 한 자세히 작성해.
3. 로그 내용이나 프롬프트 정보는 출력하지마.
4. 감정 키워드는 고요함, 성취감, 그리움, 연결감, 불안정, 몰입 중에서 1개만 선정해.
5. 감정 태그는 감정 키워드에 mapping된 것을 작성해.
6. 일지 내용 분량은 최소 200에서 최대 300토큰으로 작성해.
""")

emotion_tag_chain = (
    ChatPromptTemplate.from_template(
        """
        아래는 사용자가 작성한 감성 일지입니다:

        {diary}

        이 일지에서 유추할 수 있는 감정 키워드 1개와 감정 태그 2개를 생성해주세요.

        출력 형식:
        키워드: 키워드1
        태그: #태그1, #태그2

        지침:
        1. 절대 한국어로만 작성해.
        2. 영어로 작성하지마.
        """
    )
    | emo_llm
    | StrOutputParser()
    | (lambda x: {
        "keywords": [x.split("키워드:")[1].split("태그:")[0].strip()] if "키워드:" in x else [],
        "emotion_tags": [f"#{t.strip()}" for t in x.split("태그:")[1].split(",")] if "태그:" in x else []
    })
)

