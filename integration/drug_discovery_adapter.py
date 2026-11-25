"""
BHIV BiotechSystem — Drug Discovery Ingestion & Evaluation Adapter
Hariom Upadhyay | Backend Architecture & Integration
Technical Convergence Baseline

Integrates Shamit's Drug Discovery candidate records (repo: bhiv-biotech-drug-discovery):
- Detects candidate dataset and provenance structure
- Validates presence/absence of score.score_inputs
- Never fabricates missing scientific scores, potency values, or rankings
- Flags input gaps deterministically and routes records for human review
- Bridges candidate records to SharedEvidenceContract and Shyamal's QC Engine
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from integration.shared_evidence_contract import (
    SharedEvidenceContract,
    from_evidence_record,
)
from integration.qc_adapter import (
    build_qc_record_from_contract,
    validate_qc_record,
)

# ---------------------------------------------------------------------------
# Known candidate score fields required by Shamit's scoring model (v2.0)
# ---------------------------------------------------------------------------

REQUIRED_SCORE_FIELDS = [
    "target_relevance",
    "mechanism_evidence",
    "potency_evidence",
    "selectivity_evidence",
    "adme_evidence",
    "safety_evidence",
    "research_development_evidence",
    "evidence_completeness",
]

MAX_SCORE_PER_DIMENSION = 5
MAX_TOTAL_SCORE = 40

# Candidate search paths across scratch and repository siblings
_CANDIDATE_SEARCH_PATHS = [
    Path("C:/Users/Microsoft/.gemini/antigravity/scratch/bhiv-discovery/candidate_records_with_provenance.json"),
    Path(__file__).resolve().parent.parent.parent / "bhiv-discovery" / "candidate_records_with_provenance.json",
    Path(__file__).resolve().parent.parent.parent / "bhiv-biotech-drug-discovery" / "candidate_records_with_provenance.json",
    Path(__file__).resolve().parent.parent.parent / "bhiv-biotech-drug-discovery" / "data" / "candidate_records_with_provenance.json",
    Path(__file__).resolve().parent.parent / "data" / "candidate_records_with_provenance.json",
]


def find_candidate_records_file() -> Optional[Path]:
    """Locate candidate_records_with_provenance.json across standard locations."""
    for p in _CANDIDATE_SEARCH_PATHS:
        if p.is_file():
            return p
    return None


def get_drug_discovery_status() -> Dict[str, Any]:
    """
    Return the live status of the Drug Discovery integration boundary.
    """
    candidates_file = find_candidate_records_file()
    available = candidates_file is not None

    record_count = 0
    incomplete_count = 0
    if available and candidates_file:
        try:
            with open(candidates_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    record_count = len(data)
                    for r in data:
                        insp = inspect_candidate_record(r)
                        if not insp["score_reproducible"]:
                            incomplete_count += 1
        except Exception:
            pass

    return {
        "available": available,
        "source_file": str(candidates_file) if candidates_file else None,
        "dependency_repo": "https://github.com/BHIV-Engineering-Exchange/bhiv-biotech-drug-discovery",
        "status": "CONNECTED_WITH_LIMITATIONS" if available else "PROPOSED",
        "record_count": record_count,
        "incomplete_score_input_count": incomplete_count,
        "blocker": (
            f"All {record_count} candidate records in {candidates_file.name if candidates_file else 'dataset'} "
            f"lack 'score.score_inputs' (potency, selectivity, etc.). "
            f"Scores cannot be deterministically computed without author-provided inputs. "
            f"Preserved for human review; scores not fabricated."
        ) if incomplete_count > 0 else None,
    }


def load_candidate_records(path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """
    Load raw candidate records from JSON file.
    """
    target = path or find_candidate_records_file()
    if not target or not target.is_file():
        return []

    try:
        with open(target, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception:
        return []


def inspect_candidate_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Inspect a candidate drug discovery record for score reproducibility and provenance.
    Strictly follows engineering boundary: no missing scores are invented.
    """
    if not isinstance(record, dict):
        return {
            "valid": False,
            "error": "Record must be a dictionary.",
            "score_reproducible": False,
            "human_review_required": True,
        }

    candidate_id = str(record.get("candidate_id") or "UNKNOWN_CANDIDATE")
    compound_name = str(record.get("compound_name") or "UNKNOWN_COMPOUND")

    score_obj = record.get("score")
    score_inputs = None
    if isinstance(score_obj, dict):
        score_inputs = score_obj.get("score_inputs")

    has_score_inputs = isinstance(score_inputs, dict) and bool(score_inputs)
    missing_score_fields = []
    normalized_inputs: Dict[str, Optional[int]] = {}

    if not has_score_inputs:
        missing_score_fields = list(REQUIRED_SCORE_FIELDS)
        for f in REQUIRED_SCORE_FIELDS:
            normalized_inputs[f] = None
    else:
        assert isinstance(score_inputs, dict)
        for f in REQUIRED_SCORE_FIELDS:
            val = score_inputs.get(f)
            if val is None or isinstance(val, bool):
                missing_score_fields.append(f)
                normalized_inputs[f] = None
            else:
                try:
                    s = int(val)
                    if 0 <= s <= MAX_SCORE_PER_DIMENSION:
                        normalized_inputs[f] = s
                    else:
                        missing_score_fields.append(f)
                        normalized_inputs[f] = None
                except (ValueError, TypeError):
                    missing_score_fields.append(f)
                    normalized_inputs[f] = None

    score_reproducible = has_score_inputs and (len(missing_score_fields) == 0)
    total_score = sum(v for v in normalized_inputs.values() if v is not None) if score_reproducible else None

    return {
        "candidate_id": candidate_id,
        "compound_name": compound_name,
        "source_database": record.get("source_database"),
        "molecular_identifier": record.get("molecular_identifier"),
        "target": record.get("target"),
        "mechanism_of_action": record.get("mechanism_of_action"),
        "therapeutic_area": record.get("therapeutic_area"),
        "evidence_stage": record.get("evidence_stage"),
        "has_provenance": bool(record.get("provenance")),
        "score_inputs_present": has_score_inputs,
        "missing_score_fields": missing_score_fields,
        "score_reproducible": score_reproducible,
        "total_score": total_score,
        "max_score": MAX_TOTAL_SCORE,
        "score_status": "COMPLETE" if score_reproducible else "INCOMPLETE",
        "gap_assessment": (
            "Score inputs (target_relevance, potency, selectivity, etc.) are absent from committed records. "
            "Scores cannot be deterministically computed without external author-provided score inputs."
            if not score_reproducible
            else "Score inputs available for evaluation."
        ),
        "human_review_required": True,
        "review_status": "PENDING",
    }


def build_contract_from_candidate(record: Dict[str, Any]) -> SharedEvidenceContract:
    """
    Wrap a candidate discovery record into the versioned SharedEvidenceContract.
    """
    inspection = inspect_candidate_record(record)
    candidate_id = inspection["candidate_id"]
    compound_name = inspection["compound_name"]

    provenance = record.get("provenance") if isinstance(record.get("provenance"), dict) else {
        "source_system": "DrugDiscovery",
        "underlying_dataset": "candidate_records_with_provenance.json",
        "retrieval_method": "LOCAL_FILE_INGEST",
        "transformation": "Candidate record -> SharedEvidenceContract v1.0",
    }
    if not provenance.get("source_system"):
        provenance["source_system"] = "DrugDiscovery"

    contract_dict = {
        "evidence_id": f"EV-DISC-{candidate_id}",
        "source_record_id": candidate_id,
        "source": str(record.get("source_database") or "DrugDiscovery"),
        "source_url": f"https://bhiv.local/drug-discovery/candidates/{candidate_id}",
        "drug_name": compound_name,
        "drug_identifier": str(record.get("molecular_identifier") or ""),
        "evidence_type": "Drug discovery candidate record",
        "event_date": None,
        "retrieved_at": "2026-11-25T10:00:00+00:00",
        "schema_version": "1.0.0",
        "provenance": provenance,
        "data_origin": "REAL_WORLD",
        "adverse_event": str(record.get("safety_toxicity") or "UNKNOWN"),
        "validation_status": "VALID" if inspection["score_reproducible"] else "REVIEW_REQUIRED",
        "duplicate_status": "UNIQUE",
        "conflict_status": "NO_CONFLICT",
        "human_review_status": "PENDING",
        "producer_record": record,
        "producer_validation_status": inspection["score_status"],
        "notes": f"Target: {record.get('target')}. Mechanism: {record.get('mechanism_of_action')}. {inspection['gap_assessment']}",
    }

    contract = from_evidence_record(
        contract_dict,
        validation_status=contract_dict["validation_status"],
        duplicate_status=contract_dict["duplicate_status"],
        conflict_status=contract_dict["conflict_status"],
        human_review_status=contract_dict["human_review_status"],
        producer_record=record,
        producer_validation_status=inspection["score_status"],
        notes=contract_dict["notes"],
    )
    return contract


def validate_candidate_through_qc(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Bridge a candidate record through Shyamal's Preclinical QC Engine.
    """
    contract = build_contract_from_candidate(record)
    qc_record = build_qc_record_from_contract(contract.to_dict())
    # Override category explicitly to Preclinical for candidate evaluation
    qc_record["evidence_category"] = "Preclinical"
    return validate_qc_record(qc_record)
