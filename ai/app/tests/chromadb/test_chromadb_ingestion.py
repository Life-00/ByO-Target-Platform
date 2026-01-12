import uuid
from app.core.chromadb import papers_collection


def seed_chromadb():
    """
    테스트용 문서 1개를 ChromaDB에 적재
    """
    if papers_collection.count() > 0:
        return  # 이미 적재되어 있으면 중복 방지

    papers_collection.add(
        ids=[str(uuid.uuid4())],
        documents=[
            "EGFR inhibition shows efficacy in lung cancer models."
        ],
        metadatas=[
            {
                "pmid": "123",
                "title": "EGFR inhibition in lung cancer",
                "journal": "Nature",
                "year": 2020,
            }
        ],
    )


def test_chromadb_has_documents():
    seed_chromadb()

    count = papers_collection.count()
    assert count > 0, "ChromaDB papers_collection is empty"


def test_chromadb_document_structure():
    seed_chromadb()

    res = papers_collection.get(
        include=["documents", "metadatas"],
        limit=3,
    )

    documents = res["documents"]
    metadatas = res["metadatas"]

    assert documents, "No documents returned from ChromaDB"
    assert metadatas, "No metadatas returned from ChromaDB"

    md = metadatas[0]
    assert "pmid" in md
    assert "title" in md
