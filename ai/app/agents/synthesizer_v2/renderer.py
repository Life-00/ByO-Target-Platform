from __future__ import annotations

from app.schemas.dossier import TargetDossier
from .renderer_markdown import render_dossier_markdown
from .renderer_pdf import render_dossier_pdf


def render_dossier(user_context: str, skeleton: TargetDossier):
    """
    표현 계층 진입점
    - 기본: markdown (str)
    - format == "pdf": PDF bytes
    """
    fmt = getattr(skeleton, "format", "markdown")

    if fmt == "pdf":
        return render_dossier_pdf(skeleton)

    return render_dossier_markdown(user_context=user_context, dossier=skeleton)
