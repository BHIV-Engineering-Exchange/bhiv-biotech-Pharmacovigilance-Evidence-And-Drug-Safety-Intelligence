"""Type stub exposing root-level evidence_store under the src package for static type checkers."""
from evidence_store import (
    EVIDENCE_FILE as EVIDENCE_FILE,
    load_evidence as load_evidence,
    save_evidence as save_evidence,
    add_evidence as add_evidence,
    add_evidence_with_audit as add_evidence_with_audit,
    detect_conflicts as detect_conflicts,
    _record_fingerprint as _record_fingerprint,
    _record_identity as _record_identity,
)

__all__ = [
    "EVIDENCE_FILE",
    "load_evidence",
    "save_evidence",
    "add_evidence",
    "add_evidence_with_audit",
    "detect_conflicts",
    "_record_fingerprint",
    "_record_identity",
]
