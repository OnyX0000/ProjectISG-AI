import os
from dotenv import load_dotenv

# ✅ .env 파일 로드
load_dotenv()

# ✅ PostgreSQL 연결 정보
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_DB = os.getenv("POSTGRES_DB")
POSTGRES_HOST = os.getenv("POSTGRES_HOST")
POSTGRES_PORT = os.getenv("POSTGRES_PORT")

# ✅ PostgreSQL URI 생성
POSTGRESQL_URI = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

# ✅ MongoDB DB 설정
MONGO_URI = os.getenv("MONGO_URI")

# ✅ ELEVENLABS 설정
ELEVENLABS_API_KEY = os.getenv("xi_API_KEY")

# ✅ DISCORD 설정
DISCORD_TOKEN = os.getenv("DISCORD_API_KEY")
FASTAPI_URL = "http://localhost:8016/service2/etc/sfx/generate"

# ✅ GPT 설정
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# ✅ SupertoneAI 설정
SUPERTONEAI_API_KEY = os.getenv("x-sup-api-key")

OUTPUT_DIR = os.getenv("OUTPUT_DIR")
OUTPUT_3D_DIR = os.path.join(OUTPUT_DIR, "3D")
MVADAPTER_SERVER = os.getenv("MVADAPTER_SERVER")
HY3D_SERVER = os.getenv("HY3D_SERVER")
PROMPT_CONVERT_API = os.getenv("PROMPT_CONVERT_API")