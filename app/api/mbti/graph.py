# ✅ app/api/mbti/graph.py
from langgraph.graph import StateGraph
from langchain_core.runnables import RunnableLambda
from app.api.mbti.logic import (
    question_chain, judge_chain, update_score
)

def build_langgraph():
    builder = StateGraph(dict)

    def ask_node(state: dict) -> dict:
        if state["completed"]:
            state["current_question"] = "이미 테스트가 완료되었습니다."
            return state
        history = "\n".join(state["conversation_history"])
        remain = [d for d in ["I-E", "S-N", "T-F", "J-P"] if d not in state["asked_dimensions"]]
        result = question_chain.invoke({"history": history, "remaining_dimensions": ", ".join(remain)})
        lines = result.strip().splitlines()
        question_line = next(line for line in lines if line.lower().startswith("질문"))
        dimension_line = next(line for line in lines if line.lower().startswith("dimension"))
        state["current_question"] = question_line.split(":", 1)[1].strip()
        state["current_dimension"] = dimension_line.split(":", 1)[1].strip()
        return state

    def classify_node(state: dict) -> dict:
        state["dimension_counts"][state["current_dimension"]] += 1
        state["asked_dimensions"].add(state["current_dimension"])
        return state

    def analyze_node(state: dict) -> dict:
        result = judge_chain.invoke({"response": state["current_response"], "target_dimension": state["current_dimension"]})
        lines = result.strip().splitlines()
        dim_line = next(line for line in lines if line.lower().startswith("dimension"))
        side_line = next(line for line in lines if line.lower().startswith("side"))
        dim = dim_line.split(":")[1].strip()
        side = side_line.split(":")[1].strip()
        update_score(state, {"dimension": dim, "side": side})
        return state

    def count_node(state: dict) -> dict:
        state["question_count"] += 1
        return state

    def should_continue(state: dict) -> str:
        return "ask" if state["question_count"] < 10 else "done"

    builder.add_node("ask", RunnableLambda(ask_node))
    builder.add_node("classify", RunnableLambda(classify_node))
    builder.add_node("analyze", RunnableLambda(analyze_node))
    builder.add_node("count", RunnableLambda(count_node))
    builder.set_entry_point("ask")
    builder.add_edge("ask", "classify")
    builder.add_edge("classify", "analyze")
    builder.add_edge("analyze", "count")
    builder.add_conditional_edges("count", should_continue, {"ask": "ask", "done": "ask"})

    return builder.compile()
