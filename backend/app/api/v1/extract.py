# app/api/v1/extract.py
import json
import os
from uuid import UUID
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_user_email
from app.models.pipeline import StagedPaper, UploadedFile, Selection
from app.models.chat import Message
from app.agents.extractor.agent import ExtractorAgent
from app.schemas.retrieval import PaperCorpus, Paper, AbstractSentence
from app.schemas.knowledge import KnowledgeChunk
from app.schemas.extract import ExtractRequest
from app.service.rag_service import rag_service 
from langchain_upstage import UpstageDocumentParseLoader
from app.core.config import settings
from app.core.llm import call_llm

router = APIRouter(prefix="/sessions", tags=["extract"])
extractor_agent = ExtractorAgent(min_confidence=0.5)

def convert_file_to_paper(file_record: UploadedFile) -> Paper:
    try:
        loader = UpstageDocumentParseLoader(file_path=file_record.storage_path, api_key=settings.UPSTAGE_API_KEY, output_format="text")
        docs = loader.load()
        full_text = " ".join([d.page_content for d in docs])
        sentences = [s.strip() for s in full_text.split('.') if len(s.strip()) > 10]
        abstract_sentences = [AbstractSentence(sentence_id=f"{file_record.id}_s{i}", text=s) for i, s in enumerate(sentences)]
        return Paper(pmid=str(file_record.id), title=file_record.original_name, journal="Uploaded File", abstract_sentences=abstract_sentences, retrieval_reason="manual_upload", query_id="manual")
    except Exception as e:
        print(f"[File Conversion Error] {e}"); return None

def convert_staged_to_paper(staged: StagedPaper) -> Paper:
    text = staged.abstract or ""
    sentences = [s.strip() for s in text.split('.') if len(s.strip()) > 10]
    abstract_sentences = [AbstractSentence(sentence_id=f"{staged.id}_s{i}", text=s) for i, s in enumerate(sentences)]
    return Paper(pmid=str(staged.id), title=staged.title, year=staged.year, journal=staged.source, abstract_sentences=abstract_sentences, retrieval_reason="search_result", query_id="search")

def analyze_extraction_intent(user_text: str) -> dict:
    if not user_text or len(user_text) < 2: return {"is_specific": False, "instruction": "Extract all key scientific claims."}
    prompt = f"You are an Extraction Strategist. User Input: \"{user_text}\" Output JSON ONLY: {{ \"is_specific\": true/false, \"focus_summary\": \"...\", \"instruction\": \"...\" }}"
    try:
        response = call_llm(prompt, temperature=0); start = response.find("{"); end = response.rfind("}"); return json.loads(response[start:end+1])
    except: return {"is_specific": False, "instruction": "Extract all key scientific claims."}

@router.post("/{session_id}/extract")
def run_extract(session_id: UUID, payload: ExtractRequest, email: str = Depends(get_current_user_email), db: Session = Depends(get_db)):
    if not payload.is_confirmed:
        db.add(Message(session_id=session_id, user_email=email, role="user", content=payload.instruction or "선택된 문서 분석 시작해줘."))
        db.commit()

    def event_generator():
        try:
            if not payload.is_confirmed:
                yield json.dumps({"type": "log", "content": "🤔 추출 의도를 분석 중입니다..."}, ensure_ascii=False) + "\n"
                count = db.query(Selection).filter(Selection.session_id == session_id, Selection.user_email == email).count()
                if count == 0: yield json.dumps({"type": "error", "content": "선택된 파일이 없습니다."}, ensure_ascii=False) + "\n"; return
                analysis = analyze_extraction_intent(payload.instruction)
                proposal_msg = f"**[추출 전략 확인]**\n\n선택된 {count}개의 문서에서 " + (f"🎯 **초점**: {analysis.get('focus_summary')}" if analysis.get("is_specific") else "모든 주요 과학적 주장") + "을 추출하겠습니다. 진행할까요?"
                yield json.dumps({"type": "proposal", "content": proposal_msg, "analysis": analysis}, ensure_ascii=False) + "\n"; return

            final_instruction = payload.confirmed_instruction or "Extract all key claims."
            yield json.dumps({"type": "log", "content": f"🚀 추출 시작 (Focus: {final_instruction})"}, ensure_ascii=False) + "\n"
            
            selections = db.query(Selection).filter(Selection.session_id == session_id, Selection.user_email == email).all()
            target_papers = []
            for sel in selections:
                if sel.item_type == "uploaded_file":
                    uf = db.query(UploadedFile).filter(UploadedFile.id == sel.item_id).first()
                    if uf and os.path.exists(uf.storage_path):
                        yield json.dumps({"type": "log", "content": f"📖 파일 읽는 중: {uf.original_name}"}, ensure_ascii=False) + "\n"
                        paper = convert_file_to_paper(uf)
                        if paper: target_papers.append(paper); uf.status = "indexed"; db.add(uf)
                elif sel.item_type == "staged_paper":
                    sp = db.query(StagedPaper).filter(StagedPaper.id == sel.item_id).first()
                    if sp:
                        yield json.dumps({"type": "log", "content": f"📑 논문 로드 중: {sp.title[:30]}..."}, ensure_ascii=False) + "\n"
                        paper = convert_staged_to_paper(sp); 
                    if paper: target_papers.append(paper)
            db.commit()

            if not target_papers: yield json.dumps({"type": "error", "content": "유효한 문서가 없습니다."}, ensure_ascii=False) + "\n"; return
            
            yield json.dumps({"type": "log", "content": f"🧠 AI 정보 추출 중 ({len(target_papers)}개 문서)..."}, ensure_ascii=False) + "\n"
            corpus = PaperCorpus(query_id="manual_extract", papers=target_papers)
            extracted_chunks = extractor_agent.run(corpus) # ✅ 기존 run 사용
            yield json.dumps({"type": "log", "content": f"✅ 추출 완료! {len(extracted_chunks)}개의 정보를 발견했습니다."}, ensure_ascii=False) + "\n"

            if extracted_chunks:
                yield json.dumps({"type": "log", "content": "💾 데이터베이스 저장 중..."}, ensure_ascii=False) + "\n"
                # ✅ 터미널 로그 추가
                print(f"[RAG] Vector DB 저장 시작: {len(extracted_chunks)} chunks")
                docs_text, metadatas, ids = [], [], []
                for i, chunk in enumerate(extracted_chunks):
                    docs_text.append(f"Claim: {chunk.claim}\nTarget: {chunk.target or 'N/A'}\nConfidence: {chunk.confidence}")
                    metadatas.append({"chunk_id": chunk.chunk_id, "pmid": chunk.pmid, "source": chunk.metadata.get("paper_title", "Unknown"), "type": chunk.chunk_type, "session_id": str(session_id), "user_email": email})
                    ids.append(f"{session_id}_{chunk.pmid}_{i}")
                try:
                    vector_db = rag_service.get_vector_db()
                    vector_db.add_texts(texts=docs_text, metadatas=metadatas, ids=ids)
                    print(f"[RAG] Vector DB 저장 완료: {len(ids)}건") # ✅ 터미널 성공 로그
                except Exception as e:
                    print(f"[VectorDB Error] {e}"); yield json.dumps({"type": "log", "content": f"⚠️ 저장 중 오류: {str(e)}"}, ensure_ascii=False) + "\n"

            ai_content = f"✅ **분석 완료**: 총 {len(extracted_chunks)}개의 정보를 추출하여 데이터베이스에 저장했습니다."
            db.add(Message(session_id=session_id, user_email=email, role="ai", content=ai_content))
            db.commit()
            yield json.dumps({"type": "result", "data": {"count": len(extracted_chunks)}}, ensure_ascii=False) + "\n"
        except Exception as e:
            print(f"[Extract Error] {e}"); yield json.dumps({"type": "error", "content": str(e)}, ensure_ascii=False) + "\n"

    return StreamingResponse(event_generator(), media_type="application/x-ndjson", headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache", "Connection": "keep-alive"})