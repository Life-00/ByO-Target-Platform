import uuid
from app.schemas.paper import PaperCorpus, Paper, AbstractSentence
from app.schemas.user_query import UserQuery

class RetrieverAgent:
    def run(self, user_query: UserQuery) -> PaperCorpus:
        print(f"[Retriever] Searching papers for: {user_query.target}")
        
        # Mock 데이터 생성 (스키마 준수)
        return PaperCorpus(
            query_id=user_query.query_id,
            papers=[
                Paper(
                    pmid="12345678",
                    title=f"Effect of {user_query.target} on Cell Growth",
                    year=2024,
                    journal="Nature Fake",
                    abstract_sentences=[
                        AbstractSentence(sentence_id="s1", text=f"{user_query.target} significantly inhibited growth."),
                        AbstractSentence(sentence_id="s2", text="The mechanism was related to apoptosis.")
                    ],
                    retrieval_reason="keyword"
                ),
                Paper(
                    pmid="87654321",
                    title=f"Clinical study of {user_query.target}",
                    year=2023,
                    journal="Medical Fake",
                    abstract_sentences=[
                        AbstractSentence(sentence_id="s1", text=f"We observed no side effects for {user_query.target}."),
                    ],
                    retrieval_reason="update"
                )
            ]
        )