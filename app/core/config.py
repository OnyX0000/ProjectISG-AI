from dotenv import load_dotenv
import os

# .env 파일 로드
load_dotenv()

# 환경변수에서 DB URL 읽기
DATABASE_URL = os.getenv("DATABASE_URL")