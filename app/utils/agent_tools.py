from langchain.agents import initialize_agent, AgentExecutor
from langchain.tools import Tool
from langchain_community.tools import DuckDuckGoSearchRun

# 🔄 DuckDuckGo Tool 등록
ddg_search = DuckDuckGoSearchRun()

# 🔎 LangChain Tool 정의
search_tool = Tool(
    name="duckduckgo_search",
    func=ddg_search.run,
    description="사용자의 질문과 관련된 정보를 웹에서 검색할 수 있는 도구입니다."
)

def retrieve_mbti_style_from_web(mbti: str) -> str:
    """
    DuckDuckGo Tool을 사용하여 웹에서 MBTI 스타일 정보를 검색합니다.
    """
    # query = f"{mbti} 유형의 MZ 말투 스타일 설명"
    # print(f"🔎 [Agent] DuckDuckGo로 '{query}' 검색 중...")

    # # ✅ Tool 실행
    # result = search_tool.func(query)

    # if not result or len(result.strip()) == 0:
    #     print("🔎 [Agent] 검색 결과가 없습니다.")
    #     return "검색 결과를 찾을 수 없습니다."
    
    # print(f"🔎 [Agent] 검색 결과:\n{result}")
    # return result
    return ''

