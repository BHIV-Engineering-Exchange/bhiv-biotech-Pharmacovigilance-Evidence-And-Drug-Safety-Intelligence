import re
import json
import hashlib


def normalize(value):
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value).strip().lower())


def content_fingerprint(record):
    """
    Compare substantive record content.
    Provenance timestamps and transformation metadata are excluded.
    """
    content = {
        "source": normalize(record.get("source")),
        "drug": normalize(record.get("drug_product_identifier")),
        "evidence_type": normalize(record.get("evidence_type")),
        "observation": normalize(record.get("observation")),
        "date": normalize(record.get("date")),
        "measurement_result": record.get("measurement_result"),
    }

    serialized = json.dumps(
        content,
        sort_keys=True,
        ensure_ascii=False,
        default=str
    )

    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def classify_records(records):
    """
    Classifies relationships without deleting or merging records.

    Exact duplicate:
        Same source identifier and same substantive content.

    Same identifier, different content:
        Potential conflict requiring human review.

    Same drug and observation:
        Potential duplicate requiring review.
    """

    results = {
        record.get("evidence_id"): {
            "duplicate_status": "NO_DUPLICATE_DETECTED",
            "conflict_status": (
                "SOURCE_REPORTED_CONFLICT"
                if normalize(record.get("validation_status")) == "conflicting"
                else "NO_PAIRWISE_CONFLICT_DETECTED"
            ),
            "related_evidence_ids": [],
            "human_review_required": bool(
                record.get("human_review_flag", False)
            ),
        }
        for record in records
    }

    for i in range(len(records)):
        first = records[i]
        first_id = first.get("evidence_id")
        first_provenance = first.get("evidence_provenance") or {}
        first_source_id = (
            first_provenance.get("original_evidence_id") or first_id
        )

        for j in range(i + 1, len(records)):
            second = records[j]
            second_id = second.get("evidence_id")
            second_provenance = second.get("evidence_provenance") or {}
            second_source_id = (
                second_provenance.get("original_evidence_id") or second_id
            )

            same_source = (
                normalize(first.get("source"))
                == normalize(second.get("source"))
            )

            same_identifier = (
                normalize(first_source_id)
                == normalize(second_source_id)
            )

            same_fingerprint = (
                content_fingerprint(first)
                == content_fingerprint(second)
            )

            same_drug_observation = (
                normalize(first.get("drug_product_identifier"))
                == normalize(second.get("drug_product_identifier"))
                and normalize(first.get("observation"))
                == normalize(second.get("observation"))
                and normalize(first.get("observation")) != ""
            )

            if same_source and same_identifier:
                if same_fingerprint:
                    relationship = "EXACT_DUPLICATE"
                    results[first_id]["duplicate_status"] = relationship
                    results[second_id]["duplicate_status"] = relationship
                else:
                    relationship = "SAME_SOURCE_ID_DIFFERENT_CONTENT"
                    results[first_id]["conflict_status"] = relationship
                    results[second_id]["conflict_status"] = relationship

                results[first_id]["related_evidence_ids"].append(second_id)
                results[second_id]["related_evidence_ids"].append(first_id)

                results[first_id]["human_review_required"] = True
                results[second_id]["human_review_required"] = True

            elif same_drug_observation:
                relationship = "POTENTIAL_DUPLICATE_REQUIRES_REVIEW"

                results[first_id]["duplicate_status"] = relationship
                results[second_id]["duplicate_status"] = relationship

                results[first_id]["related_evidence_ids"].append(second_id)
                results[second_id]["related_evidence_ids"].append(first_id)

                results[first_id]["human_review_required"] = True
                results[second_id]["human_review_required"] = True

    return results
