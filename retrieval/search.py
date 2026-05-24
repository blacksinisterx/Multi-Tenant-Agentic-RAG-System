from __future__ import annotations
import re
from typing import List
from .index import Hit

PII_PATTERNS = [
    re.compile(r"\b\d{5}-\d{7}-\d\b"),
    re.compile(r"\+?92-?\d{3}-?\d{7}"),
]

def mask_pii(text: str) -> str:
    out = text
    for pat in PII_PATTERNS:
        out = pat.sub("[REDACTED]", out)
    return out

def policy_guard(hits: List[Hit], active_tenant: str) -> List[Hit] | dict:
    safe = []
    for h in hits:
        if h.tenant == "public" or h.visibility == "public":
            safe.append(h); continue
        
        # Allow access if document tenant starts with active tenant (U2 can access U2_nlp, U2_robotics, etc.)
        if h.tenant.startswith(active_tenant + "_") or h.tenant == active_tenant:
            masked = mask_pii(h.text)
            h.pii_masked = (masked != h.text)
            h.text = masked
            safe.append(h)
        # Otherwise, cross-tenant access denied - skip this document
        
    if not safe:
        return {"refusal":"AccessDenied","reason":"No retrievable documents under current ACL."}
    return safe
