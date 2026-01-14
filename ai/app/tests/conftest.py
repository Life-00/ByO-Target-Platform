# import pytest
# from app.schemas.paper import Paper, AbstractSentence
# from app.schemas.fact import Fact, RelationInfo, EntitySet, ExperimentInfo
# from app.schemas.claim import ValidatedClaim
# from app.schemas.dossier import TargetDossier
#
#
# @pytest.fixture
# def sample_paper_corpus():
#     return [
#         Paper(
#             pmid="123",
#             title="EGFR inhibition in lung cancer",
#             abstract="EGFR inhibition shows efficacy in lung cancer models.",
#             abstract_sentences=[
#                 AbstractSentence(
#                     sentence_id="s0",
#                     text="EGFR inhibition shows efficacy in lung cancer models."
#                 )
#             ],
#             journal="Nature",
#             year="2020",
#             retrieval_reason="test_fixture"
#         )
#     ]
#
#
<<<<<<< HEAD
# @pytest.fixture(params=[
#     # CASE 1: consistent (모두 증가)
#     [
#                 Fact(
#                     fact_id="f1",
#                     pmid="111",
#                     sentence_id="s1",
#                     text="EGFR activation promotes lung cancer growth",
#                     entities=EntitySet(
#                         target=["EGFR"], disease=["lung cancer"], organ=[], compound=[]
#                     ),
#                     relation=RelationInfo(type="increase", object="tumor growth"),
#                     experiment=ExperimentInfo(model="cell", species="unknown"),
#                 ),
#         Fact(
#             fact_id="f2",
#             pmid="112",
#             sentence_id="s2",
#             text="EGFR overexpression enhances tumor progression",
#             entities=EntitySet(
#                 target=["EGFR"], disease=["lung cancer"], organ=[], compound=[]
#             ),
#             relation=RelationInfo(type="increase", object="tumor growth"),
#             experiment=ExperimentInfo(model="animal", species="mouse"),
#         ),
#     ],
#
#     # CASE 2: conflicting (증가 vs 감소)
#     [
#         Fact(
#             fact_id="f3",
#             pmid="113",
#             sentence_id="s3",
#             text="EGFR inhibition reduces tumor growth",
#             entities=EntitySet(
#                 target=["EGFR"], disease=["lung cancer"], organ=[], compound=[]
#             ),
#             relation=RelationInfo(type="decrease", object="tumor growth"),
#             experiment=ExperimentInfo(model="animal", species="mouse"),
#         ),
#         Fact(
#             fact_id="f4",
#             pmid="114",
#             sentence_id="s4",
#             text="EGFR activation promotes tumor growth",
#             entities=EntitySet(
#                 target=["EGFR"], disease=["lung cancer"], organ=[], compound=[]
#             ),
#             relation=RelationInfo(type="increase", object="tumor growth"),
#             experiment=ExperimentInfo(model="cell", species="Unknown"),
#         ),
#     ],
#
#     # CASE 3: insufficient (관계가 애매)
#     [
#         Fact(
#             fact_id="f5",
#             pmid="115",
#             sentence_id="s5",
#             text="EGFR expression was observed in lung cancer samples",
#             entities=EntitySet(
#                 target=["EGFR"], disease=["lung cancer"], organ=[], compound=[]
#             ),
#             relation=RelationInfo(type="association", object="lung cancer"),
#             experiment=ExperimentInfo(model="clinical", species="human"),
#         ),
#     ],
# ])
# def sample_facts(request):
#     return request.param

# @pytest.fixture
# def sample_facts():
#     return [
#         Fact(
#             fact_id="f1",
#             pmid="123",
#             sentence_id="s0",
#             text="EGFR inhibition reduces tumor growth",
#             entities=EntitySet(
#                 target=["EGFR"],
#                 disease=["lung cancer"],
#                 organ=[],
#                 compound=[]
#             ),
#             relation=RelationInfo(
#                 type="decrease",
#                 object="tumor growth"
#             ),
#             experiment=ExperimentInfo(
#                 model="animal",
#                 species="mouse"
#             )
#         )
#     ]
>>>>>>> 9224b6f7e57a72ad1f6b5088fc3432d00220090a
#
#
# @pytest.fixture
# def sample_validated_claims():
#     return [
#         ValidatedClaim(
#             claim_id="c1",
#             normalized_claim="EGFR inhibits tumor growth",
#             evidence=[],
#             evidence_summary={},
#             consistency="consistent",
#             risk_signals=[]
#         )
#     ]
