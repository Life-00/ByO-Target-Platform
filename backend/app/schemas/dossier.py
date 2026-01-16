from pydantic import BaseModel
from typing import List, Dict, Optional

class DossierSection(BaseModel):
    text: str
    citations: List[str] = []

class TargetDossier(BaseModel):
    dossier_id: str
    target: str
    sections: Dict[str, List[DossierSection]]
    format: str = "markdown"

