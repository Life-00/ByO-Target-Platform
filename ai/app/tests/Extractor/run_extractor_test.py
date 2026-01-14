import os
from pathlib import Path
from typing import List
from collections import Counter

from pypdf import PdfReader
import nltk
from nltk.tokenize import sent_tokenize

from app.schemas.retrieval import Paper, AbstractSentence, PaperCorpus
from app.agents.extractor.agent import ExtractorAgent


# --------------------------------------------------
# 0. NLTK 준비 (최초 1회)
# --------------------------------------------------
try:
    nltk.data.find("tokenizers/punkt")
except LookupError:
    nltk.download("punkt")


# --------------------------------------------------
# 1. PDF → Abstract 추출
# --------------------------------------------------

def extract_abstract(pdf_path: str) -> str:
    reader = PdfReader(pdf_path)
    text = "\n".join(
        page.extract_text() or "" for page in reader.pages[:2]
    )

    lower = text.lower()
    start = lower.find("abstract")
    end = lower.find("introduction")

    if start != -1 and end != -1 and end > start:
        return text[start:end].strip()

    return text[:2000]  # fallback (테스트용)


# --------------------------------------------------
# 2. PDF 목록
# --------------------------------------------------

PDF_FILES = [
    "Calcitonin gene-related peptide-targeted therapy in migraine.pdf",
    "CGRP and CGRP-Receptor as Targets of Migraine Therapy.pdf",
    "CGRP as the target of new migraine therapies.pdf",
    "CGRP-targeted_medication_in_chronic_migraine_-_sys.pdf",
    "Future_targets_for_migraine_treatment_beyond_CGRP.pdf",
]

BASE_DIR = Path(__file__).resolve().parent
PDF_DIR = BASE_DIR / "extractor_test"   # 여기에 PDF 위치


# --------------------------------------------------
# 3. PaperCorpus 생성
# --------------------------------------------------

def build_corpus() -> PaperCorpus:
    papers = []

    for idx, fname in enumerate(PDF_FILES):
        path = PDF_DIR / fname

        abstract = extract_abstract(str(path))
        sentences = sent_tokenize(abstract)

        abstract_sents = [
            AbstractSentence(
                sentence_id=str(i),
                text=s
            )
            for i, s in enumerate(sentences)
            if s.strip()
        ]

        paper = Paper(
            pmid=f"TEST_PMID_{idx}",
            title=fname.replace(".pdf", ""),
            year=2023,
            journal="TestJournal",
            abstract_sentences=abstract_sents,
            retrieval_reason="manual",
            query_id="extractor_local_test",
        )

        papers.append(paper)

    return PaperCorpus(
        query_id="extractor_local_test",
        papers=papers
    )


# --------------------------------------------------
# 4. 분포 리포트 (1순위 품질 점검)
# --------------------------------------------------

def print_distribution_report(chunks):
    from collections import Counter

    effect_counter = Counter()
    stance_counter = Counter()
    salience_counter = Counter()

    for c in chunks:
        # effect.direction
        if c.effect:
            effect_counter[c.effect.get("direction", "UNKNOWN")] += 1
        else:
            effect_counter["NONE"] += 1

        # stance.polarity
        if c.stance:
            stance_counter[c.stance.get("polarity", "UNKNOWN")] += 1
        else:
            stance_counter["NONE"] += 1

        # salience는 metadata에서
        sal = c.metadata.get("salience")
        if sal and isinstance(sal, dict):
            level = sal.get("level", "NONE")
        else:
            level = "NONE"
        salience_counter[level] += 1

    print("\n" + "=" * 80)
    print("EXTRACTOR DISTRIBUTION REPORT (QUALITY CHECK)")
    print("=" * 80)

    print("\n[Effect.direction]")
    for k, v in effect_counter.items():
        print(f"{k:>12s} : {v}")

    print("\n[Stance.polarity]")
    for k, v in stance_counter.items():
        print(f"{k:>12s} : {v}")

    print("\n[Salience.level]")
    for k, v in salience_counter.items():
        print(f"{k:>12s} : {v}")

    print("=" * 80)


# --------------------------------------------------
# 5. Extractor 실행
# --------------------------------------------------

def run_extractor():
    corpus = build_corpus()

    extractor = ExtractorAgent(
        min_confidence=0.0   # 테스트에서는 필터 OFF
    )

    chunks = extractor.run(corpus)

    # 1️⃣ 품질 점검 리포트
    print_distribution_report(chunks)

    # 2️⃣ 전체 개수 요약
    print("\n" + "=" * 80)
    print(f"TOTAL CHUNKS EXTRACTED: {len(chunks)}")
    print("=" * 80)

    # 3️⃣ 개별 출력 (디버깅/검증용)
    for idx, c in enumerate(chunks, 1):
        print(f"\n[{idx}] -------------------------------------------")
        print("PMID:", c.pmid)
        print("TITLE:", c.metadata.get("paper_title"))
        print("CLAIM:", c.claim)

        print("\nEFFECT:")
        for k, v in (c.effect or {}).items():
            print(f"  - {k}: {v}")

        print("\nSTANCE:")
        for k, v in (c.stance or {}).items():
            print(f"  - {k}: {v}")

        print("SALIENCE:")
        sal = c.metadata.get("salience")
        if sal:
            for k, v in sal.items():
                print(f"  - {k}: {v}")
        else:
            print("  - NONE")

        print(f"\nEVIDENCE_LEVEL: {c.evidence_level}")
        print(f"CONFIDENCE: {c.confidence}")
        print(f"NOTES: {c.metadata.get('notes')}")


if __name__ == "__main__":
    run_extractor()
