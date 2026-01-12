# Synthesizer Agent 최종 산출물

from pydantic import BaseModel
from typing import List, Dict


class DossierSection(BaseModel):
    text: str
    citations: List[str]  # PMID list


class TargetDossier(BaseModel):
    dossier_id: str
    target: str

    sections: Dict[str, List[DossierSection]]
    format: str  # markdown | pdf
