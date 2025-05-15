from typing import TypedDict
import pandas as pd
import random
from langgraph.graph import StateGraph
from langchain_core.runnables import RunnableLambda
from langchain_core.output_parsers import StrOutputParser

from app.models.models import diary_llm as llm
from app.api.diary.rag import rag_chain
from app.api.diary.prompt_diary import prompt_template, emotion_tag_chain

class DiaryState(TypedDict, total=False):
    user_id: str
    date: str
    group: pd.DataFrame
    log_text: str
    diary: str
    mbti: str
    style_context: str
    emotion_tags: list[str]
    emotion_keywords: list[str]

emotion_list = ["고요함", "성취감", "그리움", "연결감", "불안정", "몰입"]

# ✅ 감정 키워드에 따른 연관 해시태그
emotion_tag_mapping = {
    "고요함": ["#평온", "#명상", "#안정", "#조용한시간"],
    "성취감": ["#성장", "#목표달성", "#보람", "#자부심"],
    "그리움": ["#추억", "#회상", "#기억", "#감정"],
    "연결감": ["#연대", "#따뜻함", "#교감", "#소속감"],
    "불안정": ["#불안", "#혼란", "#불확실", "#고민"],
    "몰입": ["#집중", "#몰두", "#시간가속", "#경험"]
}

mbti_style_cache = {}

def prepare_log_node(state: DiaryState) -> DiaryState:
    sorted_group = state['group'].sort_values(by="timestamp")
    log_text = "\n".join([
        f"[{row['ingame_datetime'].strftime('%Y-%m-%d')}] {row['action_type']} - {row['action_name']} @ {row['location']} | detail: {row['detail']}"
        + (f" (with: {row['with']})" if pd.notna(row['with']) and row['with'] else "")
        for _, row in sorted_group.iterrows()
    ])
    state['log_text'] = log_text
    state['date'] = sorted_group.iloc[0]['ingame_datetime'].strftime('%Y-%m-%d')
    return state

def retrieve_mbti_style_node(state: DiaryState) -> DiaryState:
    mbti = state.get("mbti", "INFP")
    if mbti in mbti_style_cache:
        state['style_context'] = mbti_style_cache[mbti]
    else:
        result = rag_chain.invoke(f"MBTI {mbti} 말투 스타일을 알려줘")
        mbti_style_cache[mbti] = result
        state['style_context'] = result
    return state

def assign_emotion_node(state: DiaryState) -> DiaryState:
    # ✅ 감정 키워드를 무작위로 하나만 선택
    selected_emotion = random.choice(emotion_list)
    state['emotion_keywords'] = [selected_emotion]

    # ✅ 감정 키워드에 맞는 태그를 랜덤으로 2개 생성
    possible_tags = emotion_tag_mapping.get(selected_emotion, ["#감정", "#일상"])
    state['emotion_tags'] = random.sample(possible_tags, 2)
    
    return state

def generate_diary_node_factory(mbti: str):
    chain = prompt_template | llm | StrOutputParser()

    def node(state: DiaryState) -> DiaryState:
        # 🛠️ LLM 호출
        try:
            diary = chain.invoke({
                "user_id": state["user_id"],
                "date": state["date"],
                "log_text": state["log_text"],
                "mbti": state["mbti"],
                "style_context": state["style_context"],
                "emotion_tags": ", ".join(state["emotion_tags"]),
                "emotion_keywords": ", ".join(state["emotion_keywords"])
            })
        except Exception as e:
            print(f"❌ [ERROR] LLM 호출 중 오류 발생: {e}")
            diary = "Diary Content"
        
        state['diary'] = diary
        return state

    return node

def generate_emotion_info(state: DiaryState) -> DiaryState:
    result = emotion_tag_chain.invoke({"diary": state["diary"]})
    state["emotion_keywords"] = result.get("keywords", [])
    state["emotion_tags"] = result.get("emotion_tags", [])
    return state

default_diary_node = generate_diary_node_factory("INTP")

def build_diary_graph() -> StateGraph:
    mbti_list = ["INTP", "ENTP", "INFJ", "ESFJ", "INFP", "ISFP", "ISTJ", "ENFP", "ESTJ", "ISTP", "ESTP", "ISFJ", "ENTJ", "ENFJ", "INTJ", "ESFP"]

    builder = StateGraph(DiaryState)
    builder.add_node("prepare_log", RunnableLambda(prepare_log_node))
    builder.add_node("retrieve_mbti", RunnableLambda(retrieve_mbti_style_node))
    builder.add_node("assign_emotion", RunnableLambda(assign_emotion_node))

    for mbti in mbti_list:
        builder.add_node(f"generate_diary_{mbti}", RunnableLambda(generate_diary_node_factory(mbti)))
    builder.add_node("generate_diary_default", RunnableLambda(default_diary_node))

    builder.add_node("generate_emotion_info", RunnableLambda(generate_emotion_info))
    builder.add_node("output", lambda state: state)

    builder.set_entry_point("prepare_log")
    builder.add_edge("prepare_log", "retrieve_mbti")
    builder.add_edge("retrieve_mbti", "assign_emotion")

    def route_by_mbti(state: DiaryState) -> str:
        node_key = f"generate_diary_{state.get('mbti', 'INTP')}"
        return node_key if node_key in builder.nodes else "generate_diary_default"

    route_map = {f"generate_diary_{mbti}": f"generate_diary_{mbti}" for mbti in mbti_list}
    route_map["generate_diary_default"] = "generate_diary_default"

    builder.add_conditional_edges("assign_emotion", route_by_mbti, route_map)

    for node in route_map.values():
        builder.add_edge(node, "generate_emotion_info")
    builder.add_edge("generate_emotion_info", "output")

    builder.set_finish_point("output")
    return builder.compile()
