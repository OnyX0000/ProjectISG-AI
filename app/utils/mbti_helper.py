from typing import Dict
import json
import os
from sqlalchemy.orm import Session
from threading import Lock
from app.models.models import UserMBTI
from langchain.memory import ConversationBufferMemory
from pydantic import Field

# ✅ MBTI 프로필이 저장된 JSON 파일 경로
MBTI_PROFILE_PATH = os.path.join("static", "JSON", "mbti_profile.json")

class CustomBufferMemory(ConversationBufferMemory):
    state_data: dict = Field(default_factory=dict)

    def save_context(self, inputs, outputs):
        """세션의 상태를 메모리에 저장합니다."""
        key = inputs.get("user_input")
        if key == "Update":
            # ✅ JSON 상태 저장
            state = outputs.get("state")
            # print(f"📝 [DEBUG] Saving state to CustomBufferMemory: {state}")
            self.state_data["state"] = state
        super().save_context(inputs, outputs)

    def load_memory_variables(self, inputs):
        """세션의 상태를 메모리에서 불러옵니다."""
        key = inputs.get("user_input")
        print(f"🔍 [DEBUG] Loading state from CustomBufferMemory for key: {key}")
        if "state" in self.state_data:
            # print(f"✅ [DEBUG] Found state: {self.state_data['state']}")
            return {"state": self.state_data["state"]}
        else:
            print("⚠️ [WARN] Memory에 'state'가 없습니다. 초기화 상태로 반환합니다.")
            return {}

# ✅ 사용자별 메모리 저장소
user_memories = {}

# ✅ 사용자별 메모리 가져오기
def get_user_memory(user_id: str, session_id: str) -> CustomBufferMemory:
    """
    사용자 ID와 세션 ID로 Custom Memory 객체를 생성하거나 가져옵니다.
    """
    key = (user_id, session_id)
    if key not in user_memories:
        print("⚠️ [WARN] Memory 객체가 CustomBufferMemory가 아닙니다. 초기화합니다.")
        user_memories[key] = CustomBufferMemory()
    return user_memories[key]

# ✅ MBTI 프로필 JSON 로드
def get_mbti_profile(mbti_type: str) -> dict:
    with open(MBTI_PROFILE_PATH, "r", encoding="utf-8") as f:
        mbti_profiles: Dict[str, Dict[str, str]] = json.load(f)
    return mbti_profiles.get(mbti_type, {
        "name": "알 수 없는 유형",
        "summary": "정의되지 않은 MBTI 유형입니다.",
        "content": "정확한 분석을 위해 더 많은 데이터가 필요합니다."
    })

# ✅ MBTI 대화 상태 초기화
def init_mbti_state() -> Dict:
    """
    초기화된 MBTI 상태를 반환합니다.
    """
    return {
        "question_count": 0,
        "conversation_history": [],
        "dimension_scores": {"I-E": 0, "S-N": 0, "T-F": 0, "J-P": 0},
        "dimension_counts": {"I-E": 0, "S-N": 0, "T-F": 0, "J-P": 0},
        "question_dimension_match": [],
        "asked_dimensions": [],
        "current_question": "",
        "current_response": "",
        "current_dimension": "",
        "completed": False
    }

# ✅ 세션 가져오기
def get_session(user_id: str, session_id: str, db: Session) -> dict:
    """
    사용자 ID와 세션 ID로 Memory에서 상태를 가져옵니다.
    상태가 없다면 초기화 후 저장합니다.
    """
    existing = db.query(UserMBTI).filter(UserMBTI.user_id == user_id, UserMBTI.session_id == session_id).first()
    if existing:
        return {"message": "이미 테스트가 완료된 사용자입니다.", "completed": True}
    
    memory = get_user_memory(user_id, session_id)

    # ✅ 메모리 상태 로딩 시도
    print(f"🔍 [DEBUG] Memory 상태 로드 시도: User ID = {user_id}, Session ID = {session_id}")
    session_data = memory.load_memory_variables({"user_input": "Update"})
    # print(f"🔍 [DEBUG] 로드된 Memory 데이터: {session_data}")

    if not session_data:
        state = init_mbti_state()
        print(f"🆕 [INFO] 메모리에 상태가 없어서 초기화합니다.")
        memory.save_context({"user_input": "Init"}, {"state": json.dumps(state)})
        return state
    else:
        if "state" in session_data:
            try:
                state = json.loads(session_data["state"])
                
                # ✅ List → Set 복원
                if isinstance(state.get("asked_dimensions"), list):
                    state["asked_dimensions"] = set(state["asked_dimensions"])
                
                # ✅ 질문 수가 7 이상이면 completed 표시
                if state.get("question_count", 0) >= 7:
                    state["completed"] = True

                # print(f"🔄 [DEBUG] 로딩된 세션 상태: {state}")
                return state
            except json.JSONDecodeError as e:
                print(f"❌ [ERROR] JSON 디코딩 실패: {e}")
                state = init_mbti_state()
                memory.save_context({"user_input": "ReInit"}, {"state": json.dumps(state)})
                return state
        else:
            state = init_mbti_state()
            memory.save_context({"user_input": "ReInit"}, {"state": json.dumps(state)})
            return state

# ✅ 세션 업데이트
def update_session(user_id: str, session_id: str, state: dict, db: Session):
    """
    업데이트된 세션 정보를 Memory에 반영합니다.
    질문이 7회 이상 진행되면 Memory에서 DB에 저장 후 제거합니다.
    """
    memory = get_user_memory(user_id, session_id)

    # ✅ JSON 문자열로 직렬화하기 전에 Set을 List로 변환
    if isinstance(state.get("asked_dimensions"), set):
        state["asked_dimensions"] = list(state["asked_dimensions"])

    # ✅ 직렬화 및 저장
    serialized_state = json.dumps(state)

    # ✅ 디버그 로그 추가
    # print(f"🔄 [DEBUG] 세션 업데이트: User ID = {user_id}, Session ID = {session_id}")
    # print(f"📝 업데이트할 세션 상태: {state}")

    memory.save_context({"user_input": "Update"}, {"state": serialized_state})

    # ✅ 업데이트 후 다시 불러와서 확인
    session_data = memory.load_memory_variables({"user_input": "Update"})
    # print(f"🔍 [DEBUG] 업데이트 후 메모리 상태: {session_data}")

    if state["question_count"] >= 7:
        print(f"✅ [INFO] ({user_id}, {session_id})의 메모리 릴리스 처리 및 DB 저장을 시작합니다.")
        
        # ✅ DB에 저장 처리
        try:
            mbti_type = finalize_mbti(user_id, session_id, state, db) 
            print(f"✅ [INFO] DB에 MBTI 결과 저장 완료: {mbti_type}")
            
            # ✅ 메모리 릴리스
            memory.clear()
            if (user_id, session_id) in user_memories:
                del user_memories[(user_id, session_id)]
            print(f"✅ [INFO] ({user_id}, {session_id})의 메모리 릴리스 완료")

            return mbti_type

        except Exception as e:
            print(f"❌ [ERROR] DB 저장 중 오류 발생: {e}")
    return None

# ✅ 응답 분석 결과에 따라 점수 갱신
def update_score(state: Dict, judged: Dict[str, str]):
    dim = judged["dimension"]
    side = judged["side"]

    # ✅ 디버그 메시지 추가
    # print(f"🔍 [DEBUG] Dimension: {dim}, Side: {side}")

    # ✅ Dimension이 올바르게 나뉘었는지 확인
    if "-" not in dim:
        print(f"⚠️ [WARN] Dimension이 올바르지 않습니다: {dim}")
        return  # 잘못된 Dimension은 스킵합니다.

    parts = dim.split("-")
    if len(parts) < 2:
        print(f"⚠️ [WARN] Dimension split 결과가 올바르지 않습니다: {parts}")
        return

    # ✅ 점수 갱신
    if side == parts[0]:
        state["dimension_scores"][dim] -= 1
    elif side == parts[1]:
        state["dimension_scores"][dim] += 1

# ✅ 최종 MBTI 유형 계산 및 DB 저장
def finalize_mbti(user_id: str, session_id: str, state: Dict, db: Session) -> str:
    scores = state["dimension_scores"]
    mbti = ""
    mbti += "I" if scores["I-E"] <= 0 else "E"
    mbti += "S" if scores["S-N"] <= 0 else "N"
    mbti += "T" if scores["T-F"] <= 0 else "F"
    mbti += "J" if scores["J-P"] <= 0 else "P"

    profile = get_mbti_profile(mbti)

    # ✅ 세션 상태에 프로필 정보 저장
    state["mbti_type"] = mbti
    state["mbti_name"] = profile["name"]
    state["mbti_summary"] = profile["summary"]
    state["mbti_content"] = profile["content"]
    state["completed"] = True

    # ✅ DB 저장
    existing = db.query(UserMBTI).filter(UserMBTI.user_id == user_id, UserMBTI.session_id == session_id).first()
    if existing:
        existing.mbti_type = mbti
        existing.name = profile["name"]
        existing.summary = profile["summary"]
        existing.content = profile["content"]
        print(f"✅ [INFO] 기존 레코드(user_id={user_id}, session_id={session_id}) 덮어쓰기 완료.")
    else:
        new_entry = UserMBTI(
            session_id=session_id,
            user_id=user_id,
            mbti_type=mbti,
            name=profile["name"],
            summary=profile["summary"],
            content=profile["content"]
        )
        db.add(new_entry)
        print(f"✅ [INFO] 새로운 레코드(user_id={user_id}, session_id={session_id}) 생성 완료.")
    db.commit()

    state["completed"] = True
    return mbti