from app.agents.validator.agent import ValidatorAgent

def test_validator_llm_result_smoke(sample_facts):
    agent = ValidatorAgent()
    validated = agent.run(sample_facts)

    assert validated is not None
    assert hasattr(validated, "claims")
    assert isinstance(validated.claims, list)

    for claim in validated.claims:
        assert claim.consistency in {"consistent", "conflicting", "insufficient"}
        assert isinstance(claim.evidence, list)
