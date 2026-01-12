from app.agents.synthesizer.agent import SynthesizerAgent
from app.schemas.claim import ValidatedClaims

def test_synthesizer_outputs_dossier(sample_validated_claims):

    agent = SynthesizerAgent()
    validated = ValidatedClaims(claims=sample_validated_claims)
    dossier = agent.run(validated, target="EGFR")

    assert dossier.target == "EGFR"
    assert "key_claims" in dossier.sections
