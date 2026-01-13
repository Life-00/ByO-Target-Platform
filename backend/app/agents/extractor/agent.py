import uuid
from app.schemas.paper import PaperCorpus
from app.schemas.fact import FactSet, Fact, EntitySet, ExperimentInfo, RelationInfo

class ExtractorAgent:
    def run(self, corpus: PaperCorpus) -> FactSet:
        print(f"[Extractor] Extracting facts from {len(corpus.papers)} papers")
        
        facts_list = []
        for paper in corpus.papers:
            # 각 논문의 첫 번째 문장을 팩트로 변환하는 척 함
            if paper.abstract_sentences:
                sent = paper.abstract_sentences[0]
                facts_list.append(
                    Fact(
                        fact_id=uuid.uuid4().hex,
                        pmid=paper.pmid,
                        sentence_id=sent.sentence_id,
                        text=sent.text,
                        entities=EntitySet(
                            target=["Sample Drug"],
                            disease=["Cancer"],
                            organ=["Liver"],
                            compound=[]
                        ),
                        experiment=ExperimentInfo(
                            model="cell",      # 필수 필드
                            species="human",   # 필수 필드
                            assay="MTT assay"
                        ),
                        relation=RelationInfo(
                            type="decrease",   # 필수 필드
                            object="Cell viability"
                        )
                    )
                )
                
        return FactSet(facts=facts_list)