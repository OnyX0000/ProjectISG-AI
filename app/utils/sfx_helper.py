import os

# ✅ 파일명 중복 시 뒤에 숫자를 붙이는 함수
def get_unique_filename(file_path: str) -> str:
    """
    파일 경로가 이미 존재할 경우 뒤에 숫자를 붙여서 유니크한 파일명을 생성합니다.
    """
    base, ext = os.path.splitext(file_path)
    counter = 1
    new_path = file_path

    while os.path.exists(new_path):
        new_path = f"{base}_{counter}{ext}"
        counter += 1

    return new_path