"""Type stub exposing root-level evidence_schema under the src package for static type checkers."""
from evidence_schema import (
    EvidenceRecord as EvidenceRecord,
    validate_evidence as validate_evidence,
    generate_evidence_id as generate_evidence_id,
    ALLOWED_DATA_ORIGINS as ALLOWED_DATA_ORIGINS,
    SCHEMA_VERSION as SCHEMA_VERSION,
    ORIGIN_REAL_WORLD as ORIGIN_REAL_WORLD,
    ORIGIN_SYNTHETIC as ORIGIN_SYNTHETIC,
    ORIGIN_TEST as ORIGIN_TEST,
    ORIGIN_BENCHMARK as ORIGIN_BENCHMARK,
    REPORTED_ASSOCIATION as REPORTED_ASSOCIATION,
    MATCHED as MATCHED,
    AMBIGUOUS as AMBIGUOUS,
    UNRESOLVED as UNRESOLVED,
)

__all__ = [
    "EvidenceRecord",
    "validate_evidence",
    "generate_evidence_id",
    "ALLOWED_DATA_ORIGINS",
    "SCHEMA_VERSION",
    "ORIGIN_REAL_WORLD",
    "ORIGIN_SYNTHETIC",
    "ORIGIN_TEST",
    "ORIGIN_BENCHMARK",
    "REPORTED_ASSOCIATION",
    "MATCHED",
    "AMBIGUOUS",
    "UNRESOLVED",
]
