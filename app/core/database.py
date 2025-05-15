from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from pymongo import MongoClient
from app.core.config import POSTGRESQL_URI, MONGO_URI

# PostgreSQL 엔진 설정
pg_engine = create_engine(
    POSTGRESQL_URI,
    pool_pre_ping=True
)
PGSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=pg_engine)

# MongoDB 클라이언트 설정
mongo_client = MongoClient(MONGO_URI)
mongo_db = mongo_client['isg']

def get_pg_session():
    """
    PostgreSQL 세션을 생성하여 반환합니다.
    """
    return PGSessionLocal()

def get_mongo_collection(collection_name):
    """
    MongoDB 컬렉션을 반환합니다.
    """
    return mongo_db[collection_name]
