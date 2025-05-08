import torch
from transformers import BlipProcessor, BlipForConditionalGeneration
from PIL import Image
from fastapi import UploadFile
import os
import datetime
import shutil

UPLOAD_DIR = "static/screenshot"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ✅ 모델 및 프로세서 로드 (최초 1회)
processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")

def run_captioning(image_path: str) -> str:
    """
    이미지 경로를 받아 캡션을 생성하는 함수
    """
    raw_image = Image.open(image_path).convert("RGB")
    inputs = processor(raw_image, return_tensors="pt")
    with torch.no_grad():
        out = model.generate(**inputs)
    caption = processor.decode(out[0], skip_special_tokens=True)
    return caption.strip()

def save_screenshot(file: UploadFile, user_id: str, session_id: str) -> str:
    """
    스크린샷 파일을 screenshot 폴더에 저장합니다. 
    클라이언트에서 전달된 파일명을 그대로 사용합니다.
    
    Args:
        file (UploadFile): 업로드된 파일 객체
        user_id (str): 사용자 ID
        session_id (str): 세션 ID
    
    Returns:
        str: 상대경로로 반환된 이미지 경로
    """
    # static/screenshot 디렉토리 생성
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    # 클라이언트에서 전달된 파일명 그대로 사용
    filename = file.filename
    file_path = os.path.join(UPLOAD_DIR, filename)

    # 동일한 이름이 있을 경우 기존 파일 삭제
    if os.path.exists(file_path):
        os.remove(file_path)

    # 파일 저장
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # 상대 경로로 반환 (API에서 접근 가능하도록 처리)
    return os.path.relpath(file_path, ".").replace("\\", "/")