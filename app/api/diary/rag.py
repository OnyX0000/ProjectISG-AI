import os
from langchain.chains import RetrievalQA
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import TextLoader
from app.models.models import diary_llm, embedding_model

CURRENT_FILE_DIR = os.path.dirname(os.path.abspath(__file__))
MBTI_STYLE_PATH = os.path.abspath(os.path.join(CURRENT_FILE_DIR, "../../../static/mbti_styles.txt"))
FAISS_DB_DIR = os.path.abspath(os.path.join(CURRENT_FILE_DIR, "../../../DB/faiss_store"))

# 🚨 존재 여부를 명시적으로 검사
if not os.path.exists(MBTI_STYLE_PATH):
    raise FileNotFoundError(f"MBTI 스타일 파일이 존재하지 않습니다: {MBTI_STYLE_PATH}")

# ✅ FAISS 저장 경로가 없다면 생성
os.makedirs(FAISS_DB_DIR, exist_ok=True)

# 📦 FAISS 벡터스토어 로드 또는 새로 생성
index_file = os.path.join(FAISS_DB_DIR, "index.faiss")
store_file = os.path.join(FAISS_DB_DIR, "index.pkl")

if os.path.exists(index_file) and os.path.exists(store_file):
    # 저장된 벡터스토어가 있으면 불러오기
    vectorstore = FAISS.load_local(FAISS_DB_DIR, embedding_model, allow_dangerous_deserialization=True)
else:
    # 없으면 새로 생성하고 저장
    docs = TextLoader(MBTI_STYLE_PATH, encoding='utf-8').load()
    vectorstore = FAISS.from_documents(docs, embedding_model)
    vectorstore.save_local(FAISS_DB_DIR)

# 🔎 retriever 생성
retriever = vectorstore.as_retriever()

# 🧠 RAG 체인 구성
rag_chain = RetrievalQA.from_chain_type(
    llm=diary_llm,
    retriever=retriever,
    return_source_documents=False
)
