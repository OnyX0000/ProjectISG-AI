import os
from langchain.chains import RetrievalQA
from langchain_community.vectorstores import FAISS, Chroma
from langchain_community.document_loaders import TextLoader
from app.models.models import diary_llm, embedding_model, c_embedding_model
from functools import lru_cache

CURRENT_FILE_DIR = os.path.dirname(os.path.abspath(__file__))
MBTI_STYLE_PATH = os.path.abspath(os.path.join(CURRENT_FILE_DIR, "../../../static/mbti_styles.txt"))
FAISS_DB_DIR = os.path.abspath(os.path.join(CURRENT_FILE_DIR, "../../../DB/faiss_store"))
CHROMA_DB_DIR = os.path.abspath(os.path.join(CURRENT_FILE_DIR, "../../../DB/chroma_store"))

# 🚨 존재 여부를 명시적으로 검사
if not os.path.exists(MBTI_STYLE_PATH):
    raise FileNotFoundError(f"MBTI 스타일 파일이 존재하지 않습니다: {MBTI_STYLE_PATH}")

# ✅ FAISS 저장 경로가 없다면 생성
os.makedirs(FAISS_DB_DIR, exist_ok=True)
os.makedirs(CHROMA_DB_DIR, exist_ok=True)

# 📦 FAISS 벡터스토어 로드 또는 새로 생성
index_file = os.path.join(FAISS_DB_DIR, "index.faiss")
store_file = os.path.join(FAISS_DB_DIR, "index.pkl")

# 🔄 문서 로딩 & 분리
if os.path.exists(index_file) and os.path.exists(store_file):
    vectorstore = FAISS.load_local(FAISS_DB_DIR, embedding_model, allow_dangerous_deserialization=True)
    chroma_store = Chroma(persist_directory=CHROMA_DB_DIR, embedding_function=c_embedding_model)
else:
    # 🔄 텍스트 파일 읽기
    with open(MBTI_STYLE_PATH, 'r', encoding='utf-8') as f:
        raw_text = f.read()

    # 🔄 MBTI별로 분리
    documents = []
    current_mbti = None
    current_text = ""

    for line in raw_text.split('\n'):
        if line.startswith("### "):
            if current_mbti and current_text:
                documents.append({
                    "text": current_text.strip(),
                    "metadata": {"mbti": current_mbti}
                })
            current_mbti = line[4:].split()[0]
            current_text = ""
        else:
            current_text += line + "\n"
    
    # 마지막 MBTI에 대한 문서 추가
    if current_mbti and current_text:
        documents.append({
            "text": current_text.strip(),
            "metadata": {"mbti": current_mbti}
        })
    
    # 🔄 FAISS에 임베딩
    vectorstore = FAISS.from_documents(documents, embedding_model)
    vectorstore.save_local(FAISS_DB_DIR)

        # 🔄 Chroma 저장 (✅ 추가됨)
    chroma_store = Chroma.from_documents(documents, c_embedding_model, persist_directory=CHROMA_DB_DIR)
    chroma_store.persist()

# 🔎 retriever 생성
retriever = vectorstore.as_retriever()
c_retriever = chroma_store.as_retriever()

# 🧠 RAG 체인 구성
rag_chain = RetrievalQA.from_chain_type(
    llm=diary_llm,
    retriever=c_retriever,
    return_source_documents=False
)

# ✅ RAG 체인 호출 함수 생성
def get_mbti_style(mbti: str) -> str:
    # 🔄 정확한 키워드로 검색
    query = f"{mbti} 스타일의 어투와 표현 방식"
    result = rag_chain.invoke(query)['result']
    
    # 🔄 결과가 없으면 기본값 반환
    if not result or len(result.strip()) == 0:
        return f"{mbti} 유형에 맞는 예시를 찾지 못했습니다."
    
    # 🔄 검색된 결과 반환
    return result

@lru_cache(maxsize=32)
def get_mbti_style_cached(mbti: str) -> str:
    """
    RAG 체인을 통해 MBTI 스타일을 검색하고, 캐시 처리합니다.
    """
    print(f"🔎 [Cache] {mbti} 스타일을 조회합니다.")
    return get_mbti_style(mbti)