# app/tests/extractor/test_extractor_pdf_only.py

import uuid
from pathlib import Path
from typing import List, Tuple

import nltk
from pypdf import PdfReader

nltk.download("punkt")
from nltk.tokenize import sent_tokenize

from app.schemas.retrieval import (
    Paper,
    PaperCorpus,
    AbstractSentence,
    SectionSentence,
)
from app.agents.extractor.agent import ExtractorAgent
from app.core.chromadb import knowledge_collection

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

def parse_pdf_to_sentences(pdf_path: str) -> List[Tuple[str, str]]:
    """
    PDF → [(section, sentence)] 변환
    section: abstract | body | unknown
    """

    reader = PdfReader(pdf_path)
    raw_text = []

    for page in reader.pages:
        text = page.extract_text()
        if text:
            raw_text.append(text)

    full_text = "\n".join(raw_text)
    lower = full_text.lower()

    abstract_text = ""
    body_text = full_text

    if "abstract" in lower:
        idx = lower.find("abstract")
        abstract_text = full_text[idx : idx + 2000]  # 앞부분 일부
        body_text = full_text[idx + 2000 :]

    sentences = []

    for s in sent_tokenize(abstract_text):
        sentences.append(("abstract", s))

    for s in sent_tokenize(body_text):
        sentences.append(("results", s))

    return sentences

def build_paper_from_pdf(pdf_path: str, query_id: str) -> Paper:
    parsed = parse_pdf_to_sentences(pdf_path)

    fulltext_sentences = []
    abstract_sentences = []

    for idx, (section, text) in enumerate(parsed):
        sid = f"s_{idx}"

        fulltext_sentences.append(
            SectionSentence(
                sentence_id=sid,
                text=text,
                section=section,
            )
        )

        if section == "abstract":
            abstract_sentences.append(
                AbstractSentence(
                    sentence_id=sid,
                    text=text,
                )
            )

    return Paper(
        source="manual",
        source_id=Path(pdf_path).stem,
        pmid=None, # 39587458
        title="Sarcopenia’s Role in Neoadjuvant Chemotherapy Outcomes for Locally Advanced Breast Cancer: A Retrospective Analysis",
        year=2024,
        journal=None,
        authors=[],
        has_fulltext=True,
        abstract_sentences=abstract_sentences,
        fulltext_sentences=fulltext_sentences,
        retrieval_reason="manual_pdf_test",
        query_id=query_id,
    )

def test_extractor_pdf_only_end_to_end():
    # ---------- 준비 ----------
    pdf_path = DATA_DIR / "Sarcopenia’s Role in Neoadjuvant Chemotherapy Outcomes for Locally Advanced Breast Cancer - A Retrospective Analysis.pdf"  # 실제 PDF 경로
    assert pdf_path.exists(), f"PDF not found: {pdf_path}"

    query_id = f"pdf-test-{uuid.uuid4()}"

    paper = build_paper_from_pdf(pdf_path, query_id)

    corpus = PaperCorpus(
        query_id=query_id,
        papers=[paper],
    )

    extractor = ExtractorAgent()

    # ---------- STEP 1: Extract ----------
    chunks = extractor.run(corpus)
    # print(f"\n[TEST] Extracted chunks: {len(chunks)}")
    assert isinstance(chunks, list)
    print(f"[TEST] Outcome claims extracted: {len(chunks)}")

    # Claim / Evidence 출력 (사람이 눈으로 확인)
    for i, c in enumerate(chunks):
        print(f"\n--- CHUNK {i} ---")
        print("CLAIM:", c.claim)
        print("CONFIDENCE:", c.confidence)
        print("EVIDENCE:")
        for ev in c.metadata.get("evidence_spans", []):
            print("  ", ev)

    # ---------- STEP 2: ChromaDB 적재 ----------
    extractor.run_and_store(corpus)

    # ---------- STEP 3: ChromaDB 검증 ----------
    count = knowledge_collection.count()
    print(f"\n[CHROMA] total stored chunks: {count}")

    if count == 0:
        print("[TEST RESULT] No outcome claims passed filtering (EXPECTED)")
    else:
        print("[TEST RESULT] Outcome claims stored in ChromaDB")


    # ---------- STEP 4: Retrieval 테스트 ----------
    results = knowledge_collection.query(
        query_texts=[
            "Does sarcopenia increase chemotherapy-related toxicity in breast cancer?"
        ],
        n_results=3,
    )

    docs = results["documents"][0]

    print("\n[CHROMA QUERY RESULT]")

    if count == 0:
        # 지금 단계에서는 이게 정답
        assert len(docs) == 0
        print("[EXPECTED] No retrieval results because no outcome claims were stored.")
    else:
        assert len(docs) > 0
        for doc in docs:
            print("-", doc)


if __name__ == "__main__":
    test_extractor_pdf_only_end_to_end()