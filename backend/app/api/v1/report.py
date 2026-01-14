import json
import time
from uuid import UUID
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_user_email
from app.models.chat import Message
from app.schemas.vector_hit import VectorHit, Citation, PaperMeta

# Agent & Service
from app.agents.synthesizer.agent import SynthesizerAgentV2
from app.agents.synthesizer.renderer import render_dossier
from app.service.rag_service import rag_service
from app.core.llm import call_llm

router = APIRouter(prefix="/sessions", tags=["report"])
synthesizer_agent = SynthesizerAgentV2()

def analyze_report_intent(user_text: str) -> dict:
    """사용자 요청을 바탕으로 '보고서 작성' 전용 전략 수립"""
    prompt = f"""
    You are a Target Validation Report Planner.
    User Request: "{user_text}"
    
    Task:
    1. Define the focus of the final dossier (e.g., 'Target-Disease Linkage', 'Safety & Toxicity').
    2. Propose a brief outline for the report sections.
    3. Ensure you do NOT request new data extraction. Focus on synthesizing existing evidence.
    
    Output JSON ONLY:
    {{
        "report_focus": "...",
        "proposed_outline": ["...", "..."],
        "agent_type": "synthesizer"
    }}
    """
    try:
        response = call_llm(prompt, temperature=0)
        start, end = response.find("{"), response.rfind("}")
        return json.loads(response[start:end+1])
    except:
        return {
            "report_focus": "General Target Validation Dossier",
            "proposed_outline": ["Introduction", "Evidence Synthesis", "Conclusion"],
            "agent_type": "synthesizer"
        }

@router.post("/{session_id}/report")
def generate_report(
    session_id: UUID,
    payload: dict, # {"prompt": "...", "is_confirmed": bool}
    email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db)
):
    is_confirmed = payload.get("is_confirmed", False)
    user_prompt = payload.get("prompt", "최종 보고서 작성해줘.")

    # 사용자 요청 메시지 저장 (최초 요청 시만)
    if not is_confirmed:
        db.add(Message(session_id=session_id, user_email=email, role="user", content=user_prompt))
        db.commit()

    def event_generator():
        try:
            # ====================================================
            # 🛑 CASE 1: 분석 및 제안 (Proposal)
            # ====================================================
            if not is_confirmed:
                yield json.dumps({"type": "log", "content": "🤔 보고서 구성안을 기획하는 중입니다..."}, ensure_ascii=False) + "\n"
                analysis = analyze_report_intent(user_prompt)
                
                outline_str = "\n".join([f"- {item}" for item in analysis.get("proposed_outline", [])])
                proposal_msg = (
                    f"**[Target Dossier 작성 계획]**\n\n"
                    f"🎯 **보고서 초점**: {analysis.get('report_focus')}\n"
                    f"📋 **구성 목차**:\n{outline_str}\n\n"
                    f"이 구성으로 종합 보고서를 작성할까요?"
                )
                yield json.dumps({"type": "proposal", "content": proposal_msg, "analysis": analysis}, ensure_ascii=False) + "\n"
                return

            # ====================================================
            # 🚀 CASE 2: 실제 보고서 생성 (Execution)
            # ====================================================
            yield json.dumps({"type": "log", "content": "📂 데이터베이스에서 추출된 근거들을 수집 중입니다..."}, ensure_ascii=False) + "\n"
            print(f"[{time.strftime('%H:%M:%S')}] [REPORT] Start synthesis for {session_id}")

            # 1. 데이터 로드 (Extractor에 의해 이미 저장된 데이터만 조회)
            vector_db = rag_service.get_vector_db()
            docs = vector_db.get(where={"session_id": str(session_id)})
            
            if not docs or not docs["documents"]:
                yield json.dumps({"type": "error", "content": "분석할 근거 데이터가 없습니다. 먼저 'Extractor' 에이전트를 통해 지식을 추출해주세요."}, ensure_ascii=False) + "\n"
                return

            hits: List[VectorHit] = []
            for i, content in enumerate(docs["documents"]):
                meta = docs["metadatas"][i]
                claim_text = content.split("\n")[0].replace("Claim: ", "")
                hits.append(VectorHit(
                    claim_id=meta.get("chunk_id", f"C{i}"),
                    claim_text=claim_text,
                    relation_type="associates",
                    evidence_level=meta.get("evidence_level", "unknown"),
                    evidence=[Citation(pmid=meta.get("pmid", "0"), url=f"https://pubmed.ncbi.nlm.nih.gov/{meta.get('pmid', '0')}/", quote=claim_text)],
                    paper=PaperMeta(pmid=meta.get("pmid", "0"), title=meta.get("source", "Unknown"), year=None, url=f"https://pubmed.ncbi.nlm.nih.gov/{meta.get('pmid', '0')}/")
                ))

            # 2. 대화 문맥 로드
            recent_msgs = db.query(Message).filter(Message.session_id == session_id).order_by(Message.created_at.asc()).all()
            user_context = "\n".join([f"{m.role}: {m.content}" for m in recent_msgs])

            # 3. 에이전트 가동 (오직 hits 기반으로만 작성)
            yield json.dumps({"type": "log", "content": "🧠 지식 간 상관관계를 분석하여 전문 리포트 작성 중..."}, ensure_ascii=False) + "\n"
            dossier = synthesizer_agent.run(user_query=user_prompt, hits=hits, user_context=user_context)
            
            yield json.dumps({"type": "log", "content": "✍️ Dossier 형식으로 최종 렌더링 중..."}, ensure_ascii=False) + "\n"
            report_md = render_dossier(user_context=user_context, skeleton=dossier)

            # 4. 결과 저장
            db.add(Message(session_id=session_id, user_email=email, role="ai", content=report_md))
            db.commit()

            print(f"[{time.strftime('%H:%M:%S')}] [REPORT] Completed for session {session_id}")
            yield json.dumps({"type": "result", "data": {"content": report_md}}, ensure_ascii=False) + "\n"

        except Exception as e:
            print(f"[Report Error] {e}")
            yield json.dumps({"type": "error", "content": f"오류 발생: {str(e)}"}, ensure_ascii=False) + "\n"

    return StreamingResponse(
        event_generator(),
        media_type="application/x-ndjson",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache", "Connection": "keep-alive"}
    )