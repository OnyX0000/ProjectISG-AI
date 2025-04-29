from langchain_core.prompts import ChatPromptTemplate

prompt_template = ChatPromptTemplate.from_template("""
너는 감성 일지 생성자야. 유저의 MBTI는 {mbti}이고, 어투는 다음과 같아:
{style_context}

활동 로그:
{log_text}

감정 키워드: {emotion_keywords}
감정 태그: {emotion_tags}

위 정보를 바탕으로 서정적인 감성 일지를 다음 형식으로 생성해줘.

날짜: 로그 기반 날짜

# 일지 내용:
                                                   
# 대표 이모지:  

# 오늘의 감정 기록:
(짧고 시적인 감정 회고 한 줄)

지침:
1. 위 포맷을 꼭 유지하면서, 사용자 시점에서 활동 기반 감정적 일지를 작성해.
2. 감정태그와 키워드는 일지에서 자연스럽게 느껴지는 감정에 맞게 위 리스트에서만 각각 2-3개씩 택해서 작성해.
3. 로그 내용이나 프롬프트 정보는 출력하지마.
4. 일지의 내용을 대표하는 감정의 이모지를 1개만 작성해서 출력해.
""")
