# ByO Agents (Retriever + Synthesizer)

## 1) 환경 준비

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Architecture

- retriever / synthesizer: agent logic
- central / graph: orchestration (LangGraph)
- outputs: generated dossiers (evaluation)
