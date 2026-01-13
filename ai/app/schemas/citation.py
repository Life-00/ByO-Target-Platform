from pydantic import BaseModel

class Citation(BaseModel):
    pmid: str
    url: str
    quote: str
    section: str | None = None
