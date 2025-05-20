from app.api.comfy.comfyui_translator import format_comfyui_prompt
from fastapi import HTTPException

def generate_comfyui_prompt(prompt: str) -> dict:
    """
    ComfyUI에 전달할 수 있는 포맷으로 프롬프트 생성
    """
    try:
        formatted_prompts = format_comfyui_prompt(prompt)
        return {
            "message": "ComfyUI 프롬프트 생성 성공",
            "prompts": formatted_prompts
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
