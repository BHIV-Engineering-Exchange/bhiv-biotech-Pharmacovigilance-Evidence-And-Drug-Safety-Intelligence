import hashlib
import json
import os
from typing import List, Dict, Any, Optional

try:
    from src.monitoring import log_event
except ImportError:
    try:
        from monitoring import log_event
    except ImportError:
        def log_event(event_name, level="INFO", **kwargs):
            pass


EVIDENCE_FILE = "evidence_output.json"


def load_evidence(filepath: Optional[str] = None):
    """Load existing evidence records."""

    target_file = filepath or EVIDENCE_FILE

    if not os.path.exists(target_file):
        return []

    try:
        with open(target_file, "r", encoding="utf-8") as file:
            data = json.load(file)

        if isinstance(data, list):
            return data

        return []

    except (json.JSONDecodeError, OSError):
        return []


def save_evidence(records, filepath: Optional[str] = None):
    """Save evidence records."""

    target_file = filepath or EVIDENCE_FILE

    with open(target_file, "w", encoding="utf-8") as file:
        json.dump(records, file, indent=4)


def _record_fingerprint(record: Dict[str, Any]) -> str:
    """
    Create a deterministic fingerprint for an evidence record.

    The fingerprint is used to compare payload contents for duplicate
    and conflict detection.
    """

    fingerprint_data = {
        "drug_name": record.get("drug_name"),
        "drug_identifier": record.get("drug_identifier"),
        "adverse_event": record.get("adverse_event"),
        "source": record.get("source"),
        "evidence_type": record.get("evidence_type"),
        "event_date": record.get("event_date"),
        "association_type": record.get("association_type"),
        "data_origin": record.get("data_origin"),
    }

    canonical_data = json.dumps(
        fingerprint_data,
        sort_keys=True,
        separators=(",", ":")
    )

    return hashlib.sha256(
        canonical_data.encode("utf-8")
    ).hexdigest()


def _record_identity(record: Dict[str, Any]):
    """
    Return the deterministic identity of an evidence record.

    Source record ID is preferred because it represents the original
    source identity.

    If unavailable, a deterministic content fingerprint is used.
    """

    source_id = record.get("source_record_id")

    if source_id:
        return ("source_record_id", str(source_id).strip())

    return ("fingerprint", _record_fingerprint(record))


def detect_conflicts(
    new_records: List[Dict[str, Any]],
    existing_records: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """
    Detect payload conflicts between new records and stored records sharing a source_record_id.

    A conflict occurs when two records have the same source_record_id but
    different content fingerprints.
    """

    if existing_records is None:
        existing_records = load_evidence()

    existing_by_source_id: Dict[str, Dict[str, Any]] = {}
    for r in existing_records:
        if isinstance(r, dict) and r.get("source_record_id"):
            sid = str(r["source_record_id"]).strip()
            existing_by_source_id[sid] = r

    conflicts = []

    for record in new_records:
        if not isinstance(record, dict):
            continue

        sid = record.get("source_record_id")
        if not sid:
            continue

        clean_sid = str(sid).strip()
        if clean_sid in existing_by_source_id:
            existing_rec = existing_by_source_id[clean_sid]
            existing_fp = _record_fingerprint(existing_rec)
            new_fp = _record_fingerprint(record)

            if existing_fp != new_fp:
                # Find differing fields
                differing_fields = []
                for key in ["drug_name", "drug_identifier", "adverse_event", "event_date", "association_type", "data_origin"]:
                    if existing_rec.get(key) != record.get(key):
                        differing_fields.append({
                            "field": key,
                            "existing_value": existing_rec.get(key),
                            "new_value": record.get(key),
                        })

                conflicts.append({
                    "source_record_id": clean_sid,
                    "existing_fingerprint": existing_fp,
                    "new_fingerprint": new_fp,
                    "differences": differing_fields,
                    "conflicting_record": record,
                })

    return conflicts


def add_evidence(new_records: List[Dict[str, Any]]) -> int:
    """
    Add only evidence records that are not already stored.

    Duplicate detection uses:
    1. source_record_id when available;
    2. deterministic content fingerprint otherwise.

    When a record with an existing source_record_id arrives with conflicting
    content, the conflict is explicitly logged rather than silently dropped.
    """

    audit = add_evidence_with_audit(new_records)
    return audit["added"]


def add_evidence_with_audit(new_records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Add evidence records with complete audit accounting of added, duplicates, and conflicts.
    """

    existing_records = load_evidence()

    existing_by_source_id: Dict[str, Dict[str, Any]] = {}
    existing_fingerprints = set()

    for r in existing_records:
        if isinstance(r, dict):
            sid = r.get("source_record_id")
            if sid:
                existing_by_source_id[str(sid).strip()] = r
            existing_fingerprints.add(_record_fingerprint(r))

    added = 0
    duplicates = 0
    conflicts = 0
    conflict_records = []

    for record in new_records:
        if not isinstance(record, dict):
            continue

        sid = record.get("source_record_id")
        rec_fp = _record_fingerprint(record)

        if sid:
            clean_sid = str(sid).strip()
            if clean_sid in existing_by_source_id:
                existing_rec = existing_by_source_id[clean_sid]
                existing_fp = _record_fingerprint(existing_rec)

                if existing_fp == rec_fp:
                    duplicates += 1
                    continue
                else:
                    conflicts += 1
                    conflict_info = {
                        "source_record_id": clean_sid,
                        "existing_fingerprint": existing_fp,
                        "new_fingerprint": rec_fp,
                    }
                    conflict_records.append(conflict_info)
                    log_event(
                        "EVIDENCE_RECORD_CONFLICT",
                        level="WARNING",
                        source_record_id=clean_sid,
                        existing_fingerprint=existing_fp,
                        new_fingerprint=rec_fp,
                    )
                    continue

            # Check if an identical payload exists under fingerprint
            if rec_fp in existing_fingerprints:
                duplicates += 1
                continue

            existing_records.append(record)
            existing_by_source_id[clean_sid] = record
            existing_fingerprints.add(rec_fp)
            added += 1

        else:
            if rec_fp in existing_fingerprints:
                duplicates += 1
                continue

            existing_records.append(record)
            existing_fingerprints.add(rec_fp)
            added += 1

    save_evidence(existing_records)

    return {
        "added": added,
        "duplicates": duplicates,
        "conflicts": conflicts,
        "conflict_records": conflict_records,
    }
