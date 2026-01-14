import uuid
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_user_email
from app.schemas.research import ResearchRequest, StagedPaperResponse
from app.models.pipeline import StagedPaper

# Agent & Schema
from app.agents.retriever.agent import RetrieverAgent
from app.schemas.query import UserQuery
from app.core.llm import call_llm  # ✅ LLM 호출 함수 임포트

router = APIRouter(prefix="/sessions", tags=["research"])

retriever_agent = RetrieverAgent(
    use_llm_expand=True,
    use_llm_filter=True,
    default_retmax=50,
    semantic_top_n=50,
    llm_keep_eval_n=10 
)

# ----------------------------------------------------------------
# ✅ [추가] 사용자의 자연어를 분석하는 함수
# ----------------------------------------------------------------
# app/api/v1/research.py 수정

def analyze_user_input(user_text: str) -> dict:
    prompt = f"""
    You are a specialized Query Analyst for a Biomedical Research Agent.
    
    User Input: "{user_text}"
    
    Task:
    1. Analyze if the user's intent is clear enough to perform a PubMed search.
    2. Extract structured information if possible.
    3. Translate Korean query to English biomedical terms.
    
    Output JSON format ONLY:
    {{
        "is_clear": true/false,
        "missing_info": "...",
        "intent": "...",
        "target": "...",
        "disease": "..."
    }}
    """
    
    try:
        response = call_llm(prompt, temperature=0)
        
        # ✅ [수정] JSON 추출 로직 강화 (앞뒤 군더더기 제거)
        start_idx = response.find("{")
        end_idx = response.rfind("}")
        
        if start_idx != -1 and end_idx != -1:
            json_str = response[start_idx : end_idx + 1]
            return json.loads(json_str)
        else:
            # JSON 구조를 못 찾은 경우
            print(f"[Query Analysis Fail] No JSON found in: {response}")
            return {"is_clear": True, "intent": user_text}
            
    except Exception as e:
        print(f"[Query Analysis Error] {e}")
        return {"is_clear": True, "intent": user_text}
    
# ----------------------------------------------------------------

@router.post("/{session_id}/research", response_model=list[StagedPaperResponse])
async def research(
    session_id: str, 
    payload: ResearchRequest, 
    email: str = Depends(get_current_user_email), 
    db: Session = Depends(get_db)
):
    print(f"[Research] Original Query: {payload.query}")

    # 1. LLM을 통해 사용자 의도 분석
    analysis = analyze_user_input(payload.query)
    
    # 2. 정보가 불충분할 경우 처리
    if not analysis.get("is_clear", True):
        # ⚠️ 중요: 현재 프론트엔드는 논문 리스트 반환을 기대하므로, 
        # 에러를 내서 메시지를 보여주거나, 빈 리스트를 주고 Chat으로 유도해야 함.
        # 여기서는 400 Bad Request로 '추가 정보 요청' 메시지를 보냅니다.
        question = analysis.get("missing_info", "더 구체적인 연구 주제나 키워드를 알려주세요.")
        raise HTTPException(status_code=400, detail=f"[추가 정보 필요] {question}")

    # 3. 구조화된 쿼리 생성
    # 분석된 intent가 있으면 그걸 쓰고, 없으면 원문 사용
    refined_intent = analysis.get("intent") or payload.query
    
    print(f"[Research] Refined Intent: {refined_intent}")

    user_query = UserQuery(
        query_id=str(uuid.uuid4()),
        intent=refined_intent,
        target_hint=analysis.get("target"), 
        disease=analysis.get("disease"),
        organ=None
    )

    # 4. 에이전트 실행
    try:
        corpus = retriever_agent.run(user_query)
    except Exception as e:
        print(f"[Research Error] {e}")
        raise HTTPException(status_code=500, detail=str(e))

    if not corpus.papers:
        return []

    # 5. 결과 저장 (기존 로직 동일)
    final_papers = corpus.papers[:payload.top_k]
    saved_models = []
    
    for p in final_papers:
        if hasattr(p, "abstract_sentences") and p.abstract_sentences:
            abstract_text = " ".join([s.text for s in p.abstract_sentences])
        else:
            abstract_text = ""

        staged = StagedPaper(
            session_id=session_id,
            user_email=email,
            source="pubmed",
            title=p.title,
            authors=", ".join(p.authors) if p.authors else "",
            year=p.year,
            url=p.url if hasattr(p, "url") else f"https://pubmed.ncbi.nlm.nih.gov/{p.pmid}/",
            abstract=abstract_text,
            score=p.score if hasattr(p, "score") else 0.0
        )
        db.add(staged)
        saved_models.append(staged)

    db.commit()
    return saved_models

# ... (list_candidates는 그대로)

@router.get("/{session_id}/research/candidates", response_model=list[StagedPaperResponse])
async def list_candidates(session_id: str, email: str = Depends(get_current_user_email), db: Session = Depends(get_db)):
    return db.query(StagedPaper).filter(StagedPaper.session_id == session_id, StagedPaper.user_email == email).order_by(StagedPaper.created_at.desc()).all()