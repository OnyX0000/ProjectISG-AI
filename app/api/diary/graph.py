from typing import TypedDict
import pandas as pd
import random
from concurrent.futures import ThreadPoolExecutor
from langgraph.graph import StateGraph
from langchain_core.runnables import RunnableLambda
from langchain_core.output_parsers import StrOutputParser
from app.models.models import diary_llm as llm
from app.api.diary.rag import rag_chain, get_mbti_style, get_mbti_style_cached
from app.utils.agent_tools import retrieve_mbti_style_from_web
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
        # ✅ 병렬 처리로 RAG와 DuckDuckGo 호출
        with ThreadPoolExecutor(max_workers=2) as executor:
            rag_future = executor.submit(get_mbti_style, mbti)
            agent_future = executor.submit(retrieve_mbti_style_from_web, mbti)
            
            rag_result = rag_future.result()
            agent_result = agent_future.result()
        
        # 🔄 결과 결합
        combined_result = f"{rag_result}\n\n🔎 [Web Search Result]\n{agent_result}"
        mbti_style_cache[mbti] = combined_result
        state['style_context'] = combined_result
    
    return state

def assign_emotion_node(state: DiaryState) -> DiaryState:
    selected_emotion = random.choice(emotion_list)
    state['emotion_keywords'] = [selected_emotion]

    # ✅ 해시태그 매핑 최적화
    state['emotion_tags'] = emotion_tag_mapping.get(selected_emotion, ["#감정", "#일상"])
    return state

def generate_diary_node_factory(mbti: str):
    chain = prompt_template | llm | StrOutputParser()

    # 🔄 캐시된 프롬프트 생성
    prompt_cache = {}

    def node(state: DiaryState) -> DiaryState:
        try:
            # 🔄 캐시된 스타일 검색
            if mbti in prompt_cache:
                style_context = prompt_cache[mbti]
            else:
                style_context = get_mbti_style_cached(mbti)
                prompt_cache[mbti] = style_context

            # ✅ 프롬프트 생성 최적화 (캐시된 경우 사용)
            if mbti not in prompt_cache:
                prompt = f"""
                너는 감성 일지 생성자야. 유저의 MBTI는 {mbti}이고, 어투는 다음과 같아:
                {style_context}
                
                활동 로그:
                {state["log_text"]}

                [생성 규칙]
                1. {mbti} 성향에 맞춰 어투를 유지해.
                2. 감정 상태에 맞춰 자연스러운 표현을 사용해.
                3. 감성적이거나 논리적인 표현을 강화해.
                4. 단순한 문장이 아닌, 깊이 있는 서술로 작성해.
                """
                prompt_cache[mbti] = prompt
            else:
                prompt = prompt_cache[mbti]

            # 🔄 LLM 호출
            diary = chain.invoke({
                "user_id": state["user_id"],
                "date": state["date"],
                "log_text": state["log_text"],
                "mbti": state["mbti"],
                "style_context": style_context,
                "emotion_tags": ", ".join(state.get("emotion_tags", [])),
                "emotion_keywords": ", ".join(state.get("emotion_keywords", []))
            })
        except Exception as e:
            print(f"❌ [ERROR] LLM 호출 중 오류 발생: {e}")
            diary = "Diary Content"
        
        state['diary'] = diary
        return state

    return node

def output_node(state: DiaryState) -> DiaryState:
    if "diary" not in state or not state["diary"]:
        state["diary"] = "❌ 감성 일지 생성 중 오류가 발생했습니다."
    if "emotion_tags" not in state or not state["emotion_tags"]:
        state["emotion_tags"] = ["#오류", "#생성실패"]
    if "emotion_keywords" not in state or not state["emotion_keywords"]:
        state["emotion_keywords"] = ["오류"]
    return state

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
    builder.add_node("output", RunnableLambda(output_node))

    builder.set_entry_point("prepare_log")
    builder.add_edge("prepare_log", "retrieve_mbti", on_error = "output")
    builder.add_edge("retrieve_mbti", "assign_emotion", on_error = "output")

    def route_by_mbti(state: DiaryState) -> str:
        node_key = f"generate_diary_{state.get('mbti', 'INTP')}"
        return node_key if node_key in builder.nodes else "generate_diary_default"

    route_map = {f"generate_diary_{mbti}": f"generate_diary_{mbti}" for mbti in mbti_list}
    route_map["generate_diary_default"] = "generate_diary_default"

    builder.add_conditional_edges("assign_emotion", route_by_mbti, route_map)

    for node in route_map.values():
        builder.add_edge(node, "generate_emotion_info", on_error = "output")
    builder.add_edge("generate_emotion_info", "output", on_error = "output")

    builder.set_finish_point("output")
    return builder.compile()