from app.agents.extractor.agent import ExtractorAgent
from app.schemas.retrieval import PaperCorpus, Paper, AbstractSentence
from app.core.chromadb import knowledge_collection


def main():
    print("[TEST] start Extractor → ChromaDB integration")

    # ---- 1. Retriever 출력 가정 (정상 스키마만 충족) ----
    paper = Paper(
        pmid="TEST_PMID_001",
        title="Test Paper Title",
        journal="Test Journal",
        year=2024,
        retrieval_reason="manual",   # Literal 허용값
        query_id="TEST_QUERY_001",
        abstract_sentences=[
            AbstractSentence(
                sentence_id="abs_1",
                text="CGRP monoclonal antibodies reduce migraine frequency."
            )
        ],
    )

    corpus = PaperCorpus(
        query_id="TEST_QUERY_001",
        papers=[paper]
    )

    # 2️. 실행
    agent = ExtractorAgent(min_confidence=0.0)
    chunks = agent.run_and_store(corpus)
    print(f"[TEST] extracted chunks: {len(chunks)}")

    # 3️. KnowledgeChunk 생성 확인
    assert len(chunks) > 0

    # 4. DB 저장 확인
    count = knowledge_collection.count()
    print(f"[TEST] DB chunk count: {count}")

    assert len(chunks) > 0, "❌ No KnowledgeChunk extracted"
    assert count > 0, "❌ No KnowledgeChunk stored in ChromaDB"

    # 5. 실제 retrieval 확인
    results = knowledge_collection.query(
        query_texts=["CGRP migraine"],
        n_results=3,
        where={"query_id": "TEST_QUERY_001"},
    )
    print(f"[TEST] retrieval results: {len(results["documents"][0])}")
    print(f"[TEST] retrieval results contents: {results["documents"][0]}")


    assert len(results["documents"][0]) > 0, "❌ Retrieval failed"

    print("[TEST] ✅ Extractor DB integration test PASSED")

if __name__ == "__main__":
    main()