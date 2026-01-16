# app/agents/retriever/prompt_loader.py 수정안
import json

def load_prompt(path: str) -> str:
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if isinstance(data, dict) and "system_prompt" in data:
        return data["system_prompt"]
    
    return json.dumps(data, ensure_ascii=False)