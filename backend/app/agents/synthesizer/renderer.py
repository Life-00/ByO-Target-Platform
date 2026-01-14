# app/agents/synthesizer/renderer.py
from __future__ import annotations
from app.schemas.dossier import TargetDossier
from .renderer_markdown import render_dossier_markdown

def render_dossier(user_context: str, skeleton: TargetDossier):
    """
    Dossier 객체를 지정된 포맷으로 변환합니다.
    """
    fmt = getattr(skeleton, "format", "markdown")
    
    # 현재는 Markdown만 기본 지원
    print(f"[Renderer] Rendering dossier in {fmt} format...")
    return render_dossier_markdown(user_context=user_context, dossier=skeleton)