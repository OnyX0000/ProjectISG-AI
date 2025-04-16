# 👥 팀 협업 규칙 안내서

이 문서는 우리 팀이 하나의 GitHub 레포지토리에서 효율적으로 협업하기 위한 규칙을 정의한 문서입니다.  
Python 및 Jupyter Notebook 개발 환경에서 VSCode를 사용하는 기준으로 작성되었습니다.

---

## 📌 1. 커밋 메시지 규칙 (필수)

모든 커밋은 다음과 같은 **Conventional Commits** 형식을 따릅니다:

```
<타입>: <변경 요약>
```

### ✅ 타입 예시
| 타입 | 의미 |
|------|------|
| `feat` | 새로운 기능 추가 |
| `fix` | 버그 수정 |
| `docs` | 문서 수정 (README 등) |
| `style` | 코드 포맷 변경 (포맷터 적용 등) |
| `refactor` | 리팩토링 (기능 변화 없이 구조 개선) |
| `test` | 테스트 코드 추가 또는 수정 |
| `chore` | 설정 파일, 의존성, 기타 유지보수 작업 |
| `perf` | 성능 개선을 위한 코드 변경 |
| `ci` | CI/CD 설정 및 워크플로우 수정 |
| `build` | 빌드 시스템 또는 외부 종속성 관련 변경 (예: Dockerfile, setup.py 등) |
| `revert` | 이전 커밋 되돌리기 (git revert 작업 등) |
| `init` | 프로젝트 초기 세팅 작업 (초기화, 구조 설계 등) |
| `merge` | Git 병합 작업 (자동 생성 외 수동 병합 시 명시적으로 사용) |

### 🧾 커밋 메시지 예시
```
feat: LLM 응답 처리 API 추가
fix: 이미지 업로드 시 확장자 체크 오류 수정
docs: README에 프로젝트 구조 설명 추가
style: black 포맷 적용 및 공백 정리
refactor: 비동기 DB 처리 구조 개선
test: 영상 처리 모듈 테스트 코드 추가
chore: .gitignore에 .env 파일 추가
```

### 🔎 꿀팁
- 메시지는 **영어 또는 한국어로 요약되게 작성** (팀원 모두 이해 가능하게)
- 불필요하게 긴 메시지보다는 **핵심 기능 중심 요약** 권장
- 한 기능 단위로 커밋을 나눠 주세요 (기능별 커밋)

---

## 📌 2. VSCode + Python 코드 스타일 통일을 위한 설정

### 📁 `.editorconfig`
- 에디터 간 기본적인 들여쓰기, 개행, 문자 인코딩 등을 통일합니다.
- VSCode, PyCharm, Sublime 등 대부분의 에디터가 자동 인식합니다.

```ini
root = true

[*]
charset = utf-8
indent_style = space
indent_size = 4
end_of_line = lf
insert_final_newline = true
trim_trailing_whitespace = true
```

### 📁 `.vscode/settings.json`
- VSCode 환경에서 저장 시 자동 포맷, 린트, import 정리 등을 실행합니다.
- 프로젝트 루트에 `.vscode/` 폴더를 만들고 `settings.json`을 저장합니다.

```json
{
  "editor.formatOnSave": true,
  "python.formatting.provider": "black",
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  },
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "jupyter.formatOnSave.enabled": true
}
```

### 🛠 포맷터: `black`
- 팀 내 포맷 통일을 위해 Python 자동 포매터 `black`을 사용합니다.
- 모든 Python 코드는 저장 시 자동으로 `black` 스타일로 포맷됩니다.
- 예: 함수 선언, 문자열 따옴표, import 정렬 등은 black 기준으로 자동 적용

---

## 📌 3. 폴더 구조 및 역할 분담

```
app/
├── api/
│   └── diary/
│       ├── routes.py         # POST /log, /generate_diary, /edit
│       └── service.py        # 일지 생성 로직, LLM 호출
├── core/
│   ├── database.py           # SQLite 연결 및 세션 관리
│   └── config.py             # 환경 설정
├── models/
│   └── diary_log.py          # 감성일지용 로그 테이블 정의
├── utils/
│   └── log_parser.py         # 행동 로그 필터링 유틸 등
├── main.py                   # FastAPI 앱 엔트리
```

- 각자 맡은 디렉토리 외에는 Pull Request 리뷰 후 수정
- 팀원 간 협의 없이 타인의 코드 구조 변경 금지

---

## 📌 4. 가상 환경 및 의존성 관리

- Python 패키지는 `requirements.txt`에 명시 후 커밋합니다.
- 가상 환경은 `.venv` 사용 권장 (Git에 포함 X)
- `.env` 파일은 루트에 위치하되, **`.env.example`로 형식 공유**

---

## 📌 5. Git 사용 규칙

- `main` 브랜치는 항상 배포 가능 상태 유지
- 기능 개발 시 `feature/<기능명>` 브랜치 생성 후 작업
- 커밋 > 푸시 > Pull Request 생성 > 리뷰 후 병합

---

## 📌 6. 주피터 노트북 (.ipynb) 규칙

- 가능하면 `.py` 모듈화 후, `.ipynb`에서는 입출력 위주 사용
- 노트북도 저장 시 포맷 적용 (VSCode에서 설정 필요)
- `notebooks/` 디렉토리에 역할별 하위 폴더 구분 권장

---

## 📌 7. 기타

- README, API 명세 등은 최신 상태 유지
- PR 제목, 커밋 메시지는 규칙에 맞게 작성
- 정기적으로 Pull 받아 최신 코드 기준 작업
- Jupyter Notebook은 /Notebooks 폴더에 각자 이름 폴더에 넣어서 사용하기(JHL, JKL, SJL)

---

문의사항은 슬랙 또는 회의 시 논의 바랍니다. 👍
