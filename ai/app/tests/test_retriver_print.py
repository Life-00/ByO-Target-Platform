# scripts/run_retriever_print.py
from app.agents.retriever.agent import RetrieverAgent
from app.schemas.query import UserQuery

def main():
    uq = UserQuery(
        query_id="debug-q-001",
        target_hint="EGFR",
        disease="lung cancer",
        organ="lung",
        intent="Does EGFR inhibition show efficacy in lung cancer?",
        hypothesis=None,
        constraints=None,
    )

    agent = RetrieverAgent(
        use_llm_expand=False,
        use_llm_filter=False,   # ✅ 먼저 출력 확인만
        default_retmax=10,
        semantic_top_n=20,
        llm_keep_eval_n=0,
    )

    corpus = agent.run(uq)

    print("query_id:", corpus.query_id)
    print("num_papers:", len(corpus.papers))

    for i, p in enumerate(corpus.papers[:5]):
        print(f"\n[{i}] PMID={p.pmid} year={p.year} journal={p.journal}")
        print("title:", p.title[:200])

if __name__ == "__main__":
    main()


'''
기전 검증
{
  "query_id": "R1",
  "target": "EGFR",
  "disease": "lung cancer",
  "target_organ": "lung",
  "intent": "Evaluate EGFR as a therapeutic target for lung cancer"
}

동물 모델 검증
{
  "query_id": "R1",
  "target": "EGFR",
  "disease": "lung cancer",
  "target_organ": "lung",
  "intent": "Evaluate EGFR as a therapeutic target for lung cancer"
}

환자 샘플 근거
{
  "query_id": "R4",
  "target": "EGFR",
  "disease": "lung cancer",
  "target_organ": "lung",
  "intent": "Is EGFR overexpressed in lung cancer patient samples?"
}

치료 개입 근거
{
  "query_id": "R5",
  "target": "EGFR",
  "disease": "lung cancer",
  "target_organ": "lung",
  "intent": "Does EGFR inhibition improve lung cancer outcomes?"
}

조직 특이성
{
  "query_id": "R6",
  "target": "EGFR",
  "disease": "lung cancer",
  "target_organ": "lung",
  "intent": "Is EGFR activity specific to lung tissue in cancer?"
}

질병 하위군
{
  "query_id": "R7",
  "target": "EGFR",
  "disease": "non-small cell lung cancer",
  "target_organ": "lung",
  "intent": "Is EGFR relevant in specific lung cancer subtypes?"
}

경쟁 타깃 비교용
{
  "query_id": "R8",
  "target": "EGFR",
  "disease": "lung cancer",
  "target_organ": "lung",
  "intent": "Is EGFR a well-established target compared to other lung cancer targets?"
}

부정적/한계 근거 포함
{
  "query_id": "R9",
  "target": "EGFR",
  "disease": "lung cancer",
  "target_organ": "lung",
  "intent": "Are there limitations or resistance issues when targeting EGFR?"
}

적응중 확장 가능성
{
  "query_id": "R10",
  "target": "EGFR",
  "disease": "lung cancer",
  "target_organ": "lung",
  "intent": "Could EGFR targeting be extended beyond lung cancer?"
}

'''