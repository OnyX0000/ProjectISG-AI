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

emotion_map = {
    "#고요함": ["안정", "차분"],
    "#성취감": ["상승", "보람"],
    "#그리움": ["회상", "감정 자극"],
    "#연결감": ["교류", "따뜻함"],
    "#외로움": ["고립", "저하"],
    "#따뜻함": ["치유", "회복"],
    "#불안정": ["혼란", "실패"],
    "#몰입": ["집중", "루틴"]
}

mbti_style_cache = {}

def prepare_log_node(state: DiaryState) -> DiaryState:
    sorted_group = state['group'].sort_values(by="timestamp")
    log_text = "\n".join([
        f"[{row['ingame_datetime']}] {row['action_type']} - {row['action_name']} @ {row['location']} | detail: {row['detail']}"
        + (f" (with: {row['with']})" if pd.notna(row['with']) and row['with'] else "")
        for _, row in sorted_group.iterrows()
    ])
    state['log_text'] = log_text
    state['date'] = sorted_group.iloc[0]['ingame_datetime'].split(' ')[0]
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
    selected = random.sample(list(emotion_map.items()), 3)
    state['emotion_tags'] = [tag for tag, _ in selected[:2]]
    state['emotion_keywords'] = [kw for _, kws in selected[:2] for kw in kws[:1]]
    return state

def generate_diary_node_factory(mbti: str):
    chain = prompt_template | llm | StrOutputParser()

    def node(state: DiaryState) -> DiaryState:
        diary = chain.invoke({
            "user_id": state["user_id"],
            "date": state["date"],
            "log_text": state["log_text"],
            "mbti": state["mbti"],
            "style_context": state["style_context"],
            "emotion_tags": ", ".join(state["emotion_tags"]),
            "emotion_keywords": ", ".join(state["emotion_keywords"])
        })
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
