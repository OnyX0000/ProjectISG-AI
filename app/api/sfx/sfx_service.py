import requests
import os
from fastapi import HTTPException
from fastapi.responses import FileResponse
from app.api.sfx.sfx_translation import translate_to_english
from app.core.config import ELEVENLABS_API_KEY
from app.utils.sfx_helper import get_unique_filename

class ElevenLabsSFX:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.endpoint = "https://api.elevenlabs.io/v1/sfx/generate"

    def generate_sfx(self, prompt: str, duration: float = None, prompt_influence: float = 0.3):
        endpoint = "https://api.elevenlabs.io/v1/sound-generation"
        headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json"
        }
        data = {
            "text": prompt,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.5
            }
        }
        if duration:
            data["duration"] = duration
        if prompt_influence:
            data["prompt_influence"] = prompt_influence

        response = requests.post(endpoint, headers=headers, json=data)

        if response.status_code == 200:
            return response.content
        else:
            raise Exception(f"Failed to generate SFX: {response.text}")


def generate_sfx_with_translation(prompt: str, duration: float = None, prompt_influence: float = 0.3):
    """
    한글로 입력된 프롬프트를 영어로 번역하고 효과음을 생성합니다.
    """
    # ✅ SFX 클라이언트 초기화
    sfx_client = ElevenLabsSFX(api_key=ELEVENLABS_API_KEY)

    try:
        # ✅ 1️⃣ 한글 → 영어 번역
        english_prompt = translate_to_english(prompt)
        print(f"🔄 [DEBUG] 번역된 프롬프트: {english_prompt}")

        # ✅ 2️⃣ 효과음 생성
        audio_data = sfx_client.generate_sfx(english_prompt, duration, prompt_influence)

        # ✅ 3️⃣ 파일 저장
        file_name = f"{prompt.replace(' ', '_')}.mp3"
        file_path = f"static/sfx/{file_name}"
        unique_file_path = get_unique_filename(file_path)

        # ✅ 디렉토리 생성 (없으면 생성)
        os.makedirs(os.path.dirname(unique_file_path), exist_ok=True)

        with open(unique_file_path, "wb") as f:
            f.write(audio_data)

        print(f"🔊 [INFO] SFX 생성 완료: {unique_file_path}")
        return {
            "message": "SFX 생성 성공",
            "file_path": unique_file_path,
            "filename": os.path.basename(unique_file_path)  
        }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
