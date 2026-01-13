from typing import Dict, Any

def _fmt_citation(e: Dict[str, Any]) -> str:
    quote = e.get("quote", "").strip()
    pmid = e.get("pmid", "").strip()
    url = e.get("url", "").strip()
    return f'- Quote: "{quote}"\n    Source: PMID: {pmid}, URL: {url}'

def render_dossier(user_context: str, skeleton: dict) -> str:
    tp = skeleton.get("target_profile", {})
    kc = skeleton.get("key_claims", [])
    el = skeleton.get("evidence_level", {})
    rs = skeleton.get("risk_signals", [])
    ns = skeleton.get("next_validation_steps", [])

    lines = []
    lines.append("# Target Dossier\n")

    # 1) Target Profile
    lines.append("## 1) Target Profile")
    lines.append(f"- Query: {tp.get('query', '')}")
    cov = tp.get("coverage", {})
    lines.append(f"- Coverage: papers={cov.get('papers')}, claims={cov.get('claims')}, years={cov.get('years')}")
    if user_context:
        lines.append(f"- Notes: user_context provided")
    else:
        lines.append(f"- Notes: (none)")
    lines.append("")

    # 2) Key Claims
    lines.append("## 2) Key Claims (Evidence-linked)")
    if not kc:
        lines.append("- (No claims available)\n")
    else:
        for item in kc:
            cid = item.get("claim_id", "UNKNOWN")
            lines.append(f"### Claim {cid}")
            lines.append(f"- Claim: {item.get('claim_text','')}")
            lines.append(f"- Evidence:")
            ev_list = item.get("evidence", [])
            for ev in ev_list:
                lines.append(_fmt_citation(ev))
            lines.append("")  # blank line between claims

    # 3) Evidence Level
    lines.append("## 3) Evidence Level Summary")
    lines.append(f"- In vitro: {len(el.get('in_vitro', []))} claim(s)")
    lines.append(f"- In vivo: {len(el.get('in_vivo', []))} claim(s)")
    lines.append(f"- Clinical: {len(el.get('clinical', []))} claim(s)")
    lines.append("")

    # 4) Risk Signals
    lines.append("## 4) Risk Signals (Evidence-linked)")
    if not rs:
        lines.append("- (No risk signals found)\n")
    else:
        for r in rs:
            cid = r.get("claim_id", "UNKNOWN")
            lines.append(f"### Risk for Claim {cid}")
            lines.append(f"- Risk type: {r.get('risk_type','')}")
            ev = r.get("evidence", {})
            lines.append(f"- Evidence:")
            lines.append(_fmt_citation(ev))
            lines.append("")

    # 5) Next Steps
    lines.append("## 5) Next Validation Steps (Evidence-gap only)")
    if not ns:
        lines.append("- (No suggested steps)\n")
    else:
        for step in ns:
            lines.append(f"- Step: {step.get('proposal','')}")
            lines.append(f"  - Why (gap): {step.get('supported_by','')}")
        lines.append("")

    return "\n".join(lines)
