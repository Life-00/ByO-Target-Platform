# app/api/v1/extract.py
import json
import os
from uuid import UUID
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db, SessionLocal
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

# -------------------------------------------------------------------------
# Helper Functions
# -------------------------------------------------------------------------

def convert_file_to_paper(file_record: UploadedFile) -> Optional[Paper]:
    """UploadedFile -> Paper 변환 (실물 PDF 우선)"""
    try:
        if not os.path.exists(file_record.storage_path):
            print(f"[Convert Error] File not found: {file_record.storage_path}")
            return None

        loader = UpstageDocumentParseLoader(
            file_path=file_record.storage_path,
            api_key=settings.UPSTAGE_API_KEY,
            output_format="text"
        )
        docs = loader.load()
        full_text = " ".join([(d.page_content or "") for d in docs])

        sentences = [s.strip() for s in full_text.split('.') if len(s.strip()) > 10]
        abstract_sentences = [
            AbstractSentence(sentence_id=f"{file_record.id}_s{i}", text=s)
            for i, s in enumerate(sentences)
        ]

        return Paper(
            pmid=str(file_record.id),
            title=file_record.original_name,
            journal="Uploaded File",
            abstract_sentences=abstract_sentences,
            retrieval_reason="manual_upload",
            query_id="manual"
        )
    except Exception as e:
        print(f"[File Conversion Error] {e}")
        return None


def convert_staged_to_paper(staged: StagedPaper) -> Paper:
    """PDF가 있으면 전문을, 없으면 초록을 분석하는 통합 함수"""
    
    # 1. 실물 PDF 확보 여부 확인 (null이 아니고 파일이 존재해야 함)
    if staged.pdf_storage_path and os.path.exists(staged.pdf_storage_path):
        try:
            print(f"📖 [Extract] 실물 PDF 전문 분석: {staged.title[:30]}...")
            loader = UpstageDocumentParseLoader(
                file_path=staged.pdf_storage_path,
                api_key=settings.UPSTAGE_API_KEY,
                output_format="text"
            )
            docs = loader.load()
            full_text = " ".join([(d.page_content or "") for d in docs])
            
            # 전문을 문장 단위로 분리 (Upstage 파싱 결과 활용)
            sentences = [s.strip() for s in full_text.split('.') if len(s.strip()) > 10]
            abstract_sentences = [
                AbstractSentence(sentence_id=f"{staged.id}_s{i}", text=s) 
                for i, s in enumerate(sentences)
            ]
            
            return Paper(
                pmid=str(staged.id),
                title=staged.title,
                year=staged.year,
                journal=staged.source,
                abstract_sentences=abstract_sentences,
                retrieval_reason="full_text_pdf", # 전문 분석 식별자
                query_id="search"
            )
        except Exception as e:
            print(f"⚠️ [Extract] PDF 파싱 에러: {e}")

    # 2. PDF가 없는 경우 (pdf_storage_path is null)
    print(f"📝 [Extract] 초록 데이터 분석: {staged.title[:30]}...")
    text = (staged.abstract or "").split("\n\n---SUMMARY_SECTION---\n")[0]
    sentences = [s.strip() for s in text.split('.') if len(s.strip()) > 10]
    abstract_sentences = [
        AbstractSentence(sentence_id=f"{staged.id}_s{i}", text=s) 
        for i, s in enumerate(sentences)
    ]
    
    return Paper(
        pmid=str(staged.id),
        title=staged.title,
        year=staged.year,
        journal=staged.source,
        abstract_sentences=abstract_sentences,
        retrieval_reason="search_result",
        query_id="search"
    )

def analyze_extraction_intent(user_text: str) -> dict:
    if not user_text or len(user_text) < 2:
        return {"is_specific": False, "instruction": "Extract all key scientific claims."}

    prompt = (
        'You are an Extraction Strategist. '
        f'User Input: "{user_text}" '
        'Output JSON ONLY: { "is_specific": true/false, "focus_summary": "...", "instruction": "..." }'
    )
    try:
        response = call_llm(prompt, temperature=0)
        start = response.find("{")
        end = response.rfind("}")
        return json.loads(response[start:end + 1])
    except:
        return {"is_specific": False, "instruction": "Extract all key scientific claims."}


def generate_korean_summary(full_text: str) -> str:
    """
    LLM을 사용하여 논문/문서의 전체 내용을 구조화된 국문 보고서로 요약합니다.
    """
    context_text = (full_text or "")[:30000]

    prompt = f"""
    You are an expert research analyst.
    Read the following document content and write a comprehensive **Executive Summary Report** in **Korean(한국어)**.

    [Format Requirements]
    1. **제목 (Title)**: Detect or summarize the title.
    2. **핵심 요약 (Executive Summary)**: 3-5 sentences summarizing the whole paper.
    3. **주요 발견 (Key Findings)**: Use bullet points.
    4. **방법론 (Methodology)**: Briefly explain how the study was conducted.
    5. **결론 및 제언 (Conclusion)**: Final thoughts.

    [Document Content]
    {context_text}

    Output in Markdown format.
    """
    try:
        return call_llm(prompt)
    except Exception as e:
        print(f"[Summary Error] {e}")
        return "요약 생성 중 오류가 발생했습니다."


# -------------------------------------------------------------------------
# [NEW] Auto-Extraction for Background Tasks
# -------------------------------------------------------------------------

def index_uploaded_file_pages_to_vector_db(
    uf: UploadedFile, session_id: UUID, user_email: str
) -> int:
    """
    ✅ PDF 본문(페이지 단위)을 Vector DB에 저장
    - RAG에서 '방법론/재료 및 방법' 같은 본문 질문을 답하려면 claim만 넣는 것으로 부족함
    - [[Page X]] prefix를 박아 retrieval 템플릿과 맞춤
    """
    if not uf or not os.path.exists(uf.storage_path):
        print(f"[Index Error] File missing: {getattr(uf, 'storage_path', None)}")
        return 0

    loader = UpstageDocumentParseLoader(
        file_path=uf.storage_path,
        api_key=settings.UPSTAGE_API_KEY,
        output_format="text",
    )
    docs = loader.load()

    texts, metadatas, ids = [], [], []
    for i, d in enumerate(docs):
        page_no = i + 1
        page_text = (getattr(d, "page_content", None) or "").strip()
        if not page_text:
            continue

        texts.append(f"[[Page {page_no}]]\n{page_text}")
        metadatas.append({
            "source": uf.original_name or "Unknown",
            "session_id": str(session_id),
            "user_email": user_email,
            "file_id": str(uf.id),
            "page": page_no,
            "kind": "pdf_page",
        })
        # ✅ 재인덱싱/세션 충돌 완화
        ids.append(f"s{session_id}_file_{uf.id}_p{page_no}")

    if not texts:
        print("[Index] No page text extracted; skip indexing.")
        return 0

    try:
        vector_db = rag_service.get_vector_db()
        vector_db.add_texts(texts=texts, metadatas=metadatas, ids=ids)
        return len(texts)
    except Exception as e:
        print(f"[VectorDB Error][pages] {e}")
        return 0


def auto_extract_file(session_id: UUID, file_id: UUID, user_email: str):
    """
    ✅ 자동 처리:
    1) 요약 저장
    2) (근본) 페이지 본문 인덱싱
    3) claim extraction(옵션/보조)
    """
    db = SessionLocal()
    try:
        print(f"🚀 [Auto-Process] Start processing File ID: {file_id}")

        uf = db.query(UploadedFile).filter(UploadedFile.id == file_id).first()
        if not uf:
            print(f"[Auto-Process] UploadedFile not found: {file_id}")
            return

        if not os.path.exists(uf.storage_path):
            print(f"[Auto-Process] File path missing: {uf.storage_path}")
            uf.status = "error"
            db.add(uf)
            db.commit()
            return

        # 1) 문서 파싱 (Full Text 확보)
        loader = UpstageDocumentParseLoader(
            file_path=uf.storage_path,
            api_key=settings.UPSTAGE_API_KEY,
            output_format="text"
        )
        docs = loader.load()
        # ✅ None-safe
        full_text = " ".join([(d.page_content or "") for d in docs])

        # -----------------------------------------------------
        # ✅ [Step 1] 구조화된 요약 보고서 생성 (Summary)
        # -----------------------------------------------------
        print(f"📝 [Auto-Process] Generating Summary for '{uf.original_name}'...")
        summary_text = generate_korean_summary(full_text)

        uf.summary = summary_text
        db.add(uf)
        db.commit()
        print("✅ [Auto-Process] Summary Saved!")

        # -----------------------------------------------------
        # ✅ [Step 1.5] (근본) PDF 본문 페이지 인덱싱
        # -----------------------------------------------------
        print(f"📚 [Auto-Process] Indexing PDF pages to Vector DB for '{uf.original_name}'...")
        pages_indexed = index_uploaded_file_pages_to_vector_db(uf, session_id, user_email)
        print(f"✅ [Auto-Process] Indexed {pages_indexed} page chunks")

        # -----------------------------------------------------
        # ✅ [Step 2] Claim Extraction (기존 로직 유지: 보조 지식)
        # -----------------------------------------------------
        indexed_ok = False

        try:
            sentences = [s.strip() for s in full_text.split('.') if len(s.strip()) > 10]
            abstract_sentences = [
                AbstractSentence(sentence_id=f"{uf.id}_s{i}", text=s)
                for i, s in enumerate(sentences)
            ]
            paper = Paper(
                pmid=str(uf.id),
                title=uf.original_name,
                journal="Uploaded File",
                abstract_sentences=abstract_sentences,
                retrieval_reason="manual_upload",
                query_id="manual"
            )

            print("🧠 [Auto-Process] Extracting claims...")
            corpus = PaperCorpus(query_id=f"auto_{file_id}", papers=[paper])
            instruction = "Extract all key scientific claims and quantitative results."
            extracted_chunks = extractor_agent.run(corpus, instruction=instruction)

            if extracted_chunks:
                print(f"[RAG] Vector DB 저장 시작(Claim): {len(extracted_chunks)} chunks")

                docs_text, metadatas, ids = [], [], []
                for i, chunk in enumerate(extracted_chunks):
                    docs_text.append(
                        f"Claim: {chunk.claim}\n"
                        f"Target: {chunk.target or 'N/A'}\n"
                        f"Confidence: {chunk.confidence}"
                    )
                    metadatas.append({
                        "chunk_id": chunk.chunk_id,
                        "pmid": chunk.pmid,
                        "source": uf.original_name or "Unknown",
                        "type": chunk.chunk_type,
                        "session_id": str(session_id),
                        "user_email": user_email,
                        "file_id": str(file_id),
                        "kind": "claim",
                    })
                    ids.append(f"auto_{session_id}_{chunk.pmid}_{i}")

                try:
                    vector_db = rag_service.get_vector_db()
                    vector_db.add_texts(texts=docs_text, metadatas=metadatas, ids=ids)
                    indexed_ok = True
                    print(f"[RAG] Vector DB 저장 완료(Claim): {len(ids)}건")
                except Exception as e:
                    print(f"[VectorDB Error][claims] {e}")
            else:
                print("[Auto-Process] No extracted chunks; skip claim vector db store.")
        except Exception as e:
            print(f"[Auto-Process] Claim extraction failed: {e}")

        # -----------------------------------------------------
        # ✅ 상태 업데이트: 페이지 or claim 중 하나라도 들어가면 indexed
        # -----------------------------------------------------
        uf.status = "indexed" if (pages_indexed > 0 or indexed_ok) else "analyzed"
        db.add(uf)
        db.commit()

        print(f"🎉 [Auto-Process] All Done for '{uf.original_name}' (pages={pages_indexed}, claims_ok={indexed_ok})")

    except Exception as e:
        print(f"❌ [Auto-Process] Error: {e}")
        db.rollback()
        try:
            uf = db.query(UploadedFile).filter(UploadedFile.id == file_id).first()
            if uf:
                uf.status = "error"
                db.add(uf)
                db.commit()
        except Exception as e2:
            print(f"[Auto-Process] Failed to set error status: {e2}")
    finally:
        db.close()


# -------------------------------------------------------------------------
# API Endpoints
# -------------------------------------------------------------------------

@router.post("/{session_id}/extract")
def run_extract(
    session_id: UUID,
    payload: ExtractRequest,
    email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db)
):
    """
    사용자가 채팅창에서 명시적으로 추출을 요청할 때 사용하는 스트리밍 엔드포인트
    """
    if not payload.is_confirmed:
        db.add(Message(
            session_id=session_id,
            user_email=email,
            role="user",
            content=payload.instruction or "선택된 문서 분석 시작해줘."
        ))
        db.commit()

    def event_generator():
        try:
            # 1. 의도 분석 및 제안 (Proposal)
            if not payload.is_confirmed:
                yield json.dumps({"type": "log", "content": "🤔 추출 의도를 분석 중입니다..."}, ensure_ascii=False) + "\n"
                count = db.query(Selection).filter(Selection.session_id == session_id, Selection.user_email == email).count()
                if count == 0:
                    yield json.dumps({"type": "error", "content": "선택된 파일이 없습니다."}, ensure_ascii=False) + "\n"
                    return

                analysis = analyze_extraction_intent(payload.instruction)
                proposal_msg = (
                    f"**[추출 전략 확인]**\n\n선택된 {count}개의 문서에서 "
                    + (f"🎯 **초점**: {analysis.get('focus_summary')}" if analysis.get("is_specific") else "모든 주요 과학적 주장")
                    + "을 추출하겠습니다. 진행할까요?"
                )
                yield json.dumps({"type": "proposal", "content": proposal_msg, "analysis": analysis}, ensure_ascii=False) + "\n"
                return

            # 2. 실행 (Execution)
            final_instruction = payload.confirmed_instruction or "Extract all key claims."
            yield json.dumps({"type": "log", "content": f"🚀 추출 시작 (Focus: {final_instruction})"}, ensure_ascii=False) + "\n"

            selections = db.query(Selection).filter(Selection.session_id == session_id, Selection.user_email == email).all()
            target_papers = []

            # 선택된 아이템 로드
            for sel in selections:
                if sel.item_type == "uploaded_file":
                    uf = db.query(UploadedFile).filter(UploadedFile.id == sel.item_id).first()
                    if uf and os.path.exists(uf.storage_path):
                        yield json.dumps({"type": "log", "content": f"📖 파일 읽는 중: {uf.original_name}"}, ensure_ascii=False) + "\n"
                        paper = convert_file_to_paper(uf)
                        if paper:
                            target_papers.append(paper)
                            uf.status = "indexed"  # 상태 업데이트(기존 로직 유지)
                            db.add(uf)
                elif sel.item_type == "staged_paper":
                    sp = db.query(StagedPaper).filter(StagedPaper.id == sel.item_id).first()
                    if sp:
                        yield json.dumps({"type": "log", "content": f"📑 논문 로드 중: {sp.title[:30]}..."}, ensure_ascii=False) + "\n"
                        paper = convert_staged_to_paper(sp)
                        if paper:
                            target_papers.append(paper)

            db.commit()

            if not target_papers:
                yield json.dumps({"type": "error", "content": "유효한 문서가 없습니다."}, ensure_ascii=False) + "\n"
                return

            # 에이전트 실행
            yield json.dumps({"type": "log", "content": f"🧠 AI 정보 추출 중 ({len(target_papers)}개 문서)..."}, ensure_ascii=False) + "\n"
            corpus = PaperCorpus(query_id="manual_extract", papers=target_papers)
            extracted_chunks = extractor_agent.run(corpus, instruction=final_instruction)
            yield json.dumps({"type": "log", "content": f"✅ 추출 완료! {len(extracted_chunks)}개의 정보를 발견했습니다."}, ensure_ascii=False) + "\n"

            # DB 저장
            if extracted_chunks:
                yield json.dumps({"type": "log", "content": "💾 데이터베이스 저장 중..."}, ensure_ascii=False) + "\n"
                print(f"[RAG] Vector DB 저장 시작: {len(extracted_chunks)} chunks")

                docs_text, metadatas, ids = [], [], []
                for i, chunk in enumerate(extracted_chunks):
                    docs_text.append(
                        f"Claim: {chunk.claim}\n"
                        f"Target: {chunk.target or 'N/A'}\n"
                        f"Confidence: {chunk.confidence}"
                    )
                    metadatas.append({
                        "chunk_id": chunk.chunk_id,
                        "pmid": chunk.pmid,
                        "source": chunk.metadata.get("paper_title", "Unknown"),
                        "type": chunk.chunk_type,
                        "session_id": str(session_id),
                        "user_email": email,
                        "kind": "claim",
                    })
                    ids.append(f"{session_id}_{chunk.pmid}_{i}")

                try:
                    vector_db = rag_service.get_vector_db()
                    vector_db.add_texts(texts=docs_text, metadatas=metadatas, ids=ids)
                    print(f"[RAG] Vector DB 저장 완료: {len(ids)}건")
                except Exception as e:
                    print(f"[VectorDB Error] {e}")
                    yield json.dumps({"type": "log", "content": f"⚠️ 저장 중 오류: {str(e)}"}, ensure_ascii=False) + "\n"

            ai_content = f"✅ **분석 완료**: 총 {len(extracted_chunks)}개의 정보를 추출하여 데이터베이스에 저장했습니다."
            db.add(Message(session_id=session_id, user_email=email, role="ai", content=ai_content))
            db.commit()

            yield json.dumps({"type": "result", "data": {"count": len(extracted_chunks)}}, ensure_ascii=False) + "\n"

        except Exception as e:
            print(f"[Extract Error] {e}")
            yield json.dumps({"type": "error", "content": str(e)}, ensure_ascii=False) + "\n"

    return StreamingResponse(
        event_generator(),
        media_type="application/x-ndjson",
        headers={
            "X-Accel-Buffering": "no",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
