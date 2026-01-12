from __future__ import annotations

from typing import Optional, TypedDict

from app.schemas.user_query import UserQuery
from app.schemas.paper import PaperCorpus


class RetrieverState(TypedDict, total=False):
    # input
    user_query: UserQuery

    # output
    paper_corpus: PaperCorpus

    # meta / errors
    error: Optional[str]
