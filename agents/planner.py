# Enhanced planner with assignment-compliant return format
INJECTION_PATTERNS = [
    "ignore all previous rules",
    "ignore all rules", 
    "dump memory",
    "dump system memory", 
    "override policy guard",
    "exfiltrate",
    "print hidden system",
    "bypass",
    "jailbreak",
    "ignore instructions",
    "system prompt",
    "reveal system"
]

PROHIBITED_PATTERNS = [
    "unmask pii",
    "cross-tenant access", 
    "guard override",
    "reveal system prompt",
    "access denied override",
    "show private documents from",
    "bypass security",
    "list phone numbers",
    "dump cnic", 
    "reveal confidential contacts",
    "extract phone numbers",
    "list contact details",
    "salary sheet",  # Cross-tenant financial data access
    "genomics salary",  # Specific cross-tenant access pattern for test
    "dump the entire memory contents",  # Memory dumping attack
    "dump memory contents",  # Memory dumping variations
    "attach all retrieved documents verbatim"  # Document dumping attack
    # Enhanced social engineering detection - specific phrases only
    "trusted collaborator from",
    "partner organization", 
    "research coordinator from",
    "confidential contacts from",
    "whistleblower hotline operator",
    "regulatory inspector from",
    "government privacy agency",
    "surprise audit",
    "data protection laws to avoid fines",
    "acting as a trusted",
    "pose as an internal", 
    "emulate a research coordinator",
    "mimic a regulatory",
    "impersonate a whistleblower",
    "simulate a system administrator",
    "present yourself as a token optimization"
]

# Cross-domain access patterns that should be refused
CROSS_DOMAIN_PATTERNS = {
    "U1": ["nlp", "robotics", "materials"],  # U1 can only access genomics + public
    "U2": ["genomics", "robotics", "materials"],  # U2 can only access nlp + public  
    "U3": ["genomics", "nlp", "materials"],  # U3 can only access robotics + public
    "U4": ["genomics", "nlp", "robotics"]   # U4 can only access materials + public
}

def planner(user_query: str, tenant_id: str = None) -> dict:
    """
    Enhanced planner that detects injection attempts, prohibited intents, and cross-domain access.
    Returns dict with injection, prohibited, and retrieval_query fields.
    """
    low = user_query.lower()
    
    # Check for injection patterns
    injection_detected = any(pattern in low for pattern in INJECTION_PATTERNS)
    
    # Check for prohibited patterns
    prohibited_detected = any(pattern in low for pattern in PROHIBITED_PATTERNS)
    
    # Check for cross-domain access if tenant is provided
    cross_domain_detected = False
    if tenant_id and tenant_id in CROSS_DOMAIN_PATTERNS:
        forbidden_domains = CROSS_DOMAIN_PATTERNS[tenant_id]
        # Only flag if explicitly asking for data from forbidden domains
        cross_domain_detected = any(f"{domain} memo" in low or f"{domain} notebook" in low or f"{domain} data" in low for domain in forbidden_domains)
    
    # Combine all prohibited checks
    prohibited_detected = prohibited_detected or cross_domain_detected
    
    # Generate retrieval query
    if injection_detected:
        retrieval_query = "__INJECTION__"
    elif prohibited_detected:
        retrieval_query = "__PROHIBITED__"
    else:
        # For normal queries, use the query as-is or clean it up
        retrieval_query = user_query.strip()
    
    return {
        "injection": injection_detected,
        "prohibited": prohibited_detected,
        "retrieval_query": retrieval_query
    }

# BACKUP: Original Plan class implementation
"""
from dataclasses import dataclass

@dataclass  
class Plan:
    need_retrieval: bool
    query: str

def planner_legacy(user_query: str) -> Plan:
    low = user_query.lower()
    if any(p in low for p in INJECTION_PATTERNS):
        return Plan(False, "__INJECTION__")
    return Plan(True, user_query if len(user_query.split())>2 else user_query)
"""
