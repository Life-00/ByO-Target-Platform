from app.agents.validator.agent import ValidatorAgent

def test_validator_outputs_validated_claims(sample_facts):

    agent = ValidatorAgent()
    validated = agent.run(sample_facts)

    assert validated is not None
    assert hasattr(validated, "claims")

    for claim in validated.claims:
        assert claim.consistency in {"consistent", "conflicting", "insufficient"}
        assert isinstance(claim.evidence, list)