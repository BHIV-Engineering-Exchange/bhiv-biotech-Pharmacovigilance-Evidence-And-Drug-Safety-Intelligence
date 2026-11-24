"""Type stub exposing root-level entity_resolution under the src package for static type checkers."""
from entity_resolution import (
    EntityCandidate as EntityCandidate,
    ResolutionResult as ResolutionResult,
    resolve_entity as resolve_entity,
    normalize_entity_name as normalize_entity_name,
    MATCHED as MATCHED,
    AMBIGUOUS as AMBIGUOUS,
    UNRESOLVED as UNRESOLVED,
)

__all__ = [
    "EntityCandidate",
    "ResolutionResult",
    "resolve_entity",
    "normalize_entity_name",
    "MATCHED",
    "AMBIGUOUS",
    "UNRESOLVED",
]
