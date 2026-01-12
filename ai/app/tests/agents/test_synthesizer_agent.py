from app.agents.synthesizer.agent import SynthesizerAgent

def test_synthesizer_outputs_dossier(sample_validated_claims):

    agent = SynthesizerAgent()
    dossier = agent.run(sample_validated_claims, target="EGFR")

    assert dossier.target == "EGFR"
    assert "key_claims" in dossier.sections
