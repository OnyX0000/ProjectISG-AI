import torch
from transformers import BlipProcessor, BlipForConditionalGeneration
from PIL import Image

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
