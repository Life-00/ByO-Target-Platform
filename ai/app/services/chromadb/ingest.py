from app.schemas.paper import PaperCorpus
from app.core.chromadb import papers_collection


def add_papers_to_chromadb(corpus: PaperCorpus) -> None:
    """
    Store paper abstract sentences into vector DB (Chroma)

    - One document per abstract sentence
    - Metadata preserved for traceability
    """
    ids = []
    documents = []
    metadatas = []

    for paper in corpus.papers:
        for sent in paper.abstract_sentences:
            doc_id = f"{paper.pmid}_{sent.sentence_id}"

            ids.append(doc_id)
            documents.append(sent.text)
            metadatas.append({
                "pmid": paper.pmid,
                "title": paper.title,
                "journal": paper.journal,
                "year": paper.year,
                "sentence_id": sent.sentence_id,
                "retrieval_reason": paper.retrieval_reason,
                "source": "pubmed",
            })

    if ids:
        papers_collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
        )