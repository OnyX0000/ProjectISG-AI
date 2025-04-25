import os
from langchain.chains import RetrievalQA
from langchain.vectorstores import FAISS
from langchain_community.document_loaders import TextLoader
from app.models.models import diary_llm, embedding_model

CURRENT_FILE_DIR = os.path.dirname(os.path.abspath(__file__))
MBTI_STYLE_PATH = os.path.abspath(os.path.join(CURRENT_FILE_DIR, "../../../static/mbti_styles.txt"))

# 🚨 존재 여부를 명시적으로 검사
if not os.path.exists(MBTI_STYLE_PATH):
    raise FileNotFoundError(f"MBTI 스타일 파일이 존재하지 않습니다: {MBTI_STYLE_PATH}")

# 📄 텍스트 문서 로드
docs = TextLoader(MBTI_STYLE_PATH, encoding='utf-8').load()

# 🧠 FAISS 벡터스토어 및 RAG 체인 구성
vectorstore = FAISS.from_documents(docs, embedding_model)
retriever = vectorstore.as_retriever()

rag_chain = RetrievalQA.from_chain_type(
    llm=diary_llm,
    retriever=retriever,
    return_source_documents=False
)