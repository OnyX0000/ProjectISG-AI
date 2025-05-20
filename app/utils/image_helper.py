import torch
from app.models.models import caption_model, image_processor 
from PIL import Image
from fastapi import UploadFile
import os
import uuid
import datetime
import shutil

UPLOAD_DIR = "static/screenshot"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def run_captioning(image_path: str) -> str:
    """
    이미지 경로를 받아 캡션을 생성하는 함수 (GPU 사용)
    """
    raw_image = Image.open(image_path).convert("RGB")
    inputs = image_processor(raw_image, return_tensors="pt")
    
    # ✅ GPU로 전송
    caption_model.to('cuda:1')
    inputs = {k: v.to('cuda:1') for k, v in inputs.items()}

    with torch.no_grad():
        out = caption_model.generate(**inputs)

    caption = image_processor.decode(out[0], skip_special_tokens=True)
    return caption.strip()

def save_screenshot(file: UploadFile, user_id: str, session_id: str) -> str:
    """
    스크린샷 파일을 UUID 기반으로 저장합니다. 
    확장자는 .png로 고정됩니다.
    
    Args:
        file (UploadFile): 업로드된 파일 객체
        user_id (str): 사용자 ID
        session_id (str): 세션 ID
    
    Returns:
        str: 상대경로로 반환된 이미지 경로
    """
    # 디렉토리 생성
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    # 고유한 파일 이름 생성
    unique_name = f"screenshot_{user_id}_{session_id}_{uuid.uuid4().hex[:8]}.png"
    file_path = os.path.join(UPLOAD_DIR, unique_name)

    # 파일 저장
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # 상대 경로로 반환 (API에서 접근 가능하도록 처리)
    return os.path.relpath(file_path, ".").replace("\\", "/")