from datetime import datetime, timezone


VALID_STATES = {
    "PENDING",
    "IN_REVIEW",
    "COMPLETED",
    "ESCALATED",
}

ALLOWED_TRANSITIONS = {
    "PENDING": {"IN_REVIEW", "ESCALATED"},
    "IN_REVIEW": {"COMPLETED", "ESCALATED"},
    "ESCALATED": {"IN_REVIEW"},
    "COMPLETED": set(),
}


def create_review_item(evidence_id, reason):
    return {
        "evidence_id": evidence_id,
        "review_status": "PENDING",
        "review_reason": reason,
        "review_history": [],
        "reviewer_id": None,
        "workflow_completed": False,
        "safety_confirmed": False,
        "causality_confirmed": False,
    }


def transition_review(item, new_status, reviewer_id, note=""):
    current = item["review_status"]

    if new_status not in VALID_STATES:
        raise ValueError("Invalid review status: " + str(new_status))

    if not reviewer_id or not str(reviewer_id).strip():
        raise ValueError("A reviewer ID is required.")

    if new_status not in ALLOWED_TRANSITIONS[current]:
        raise ValueError(
            "Transition not allowed: "
            + current + " -> " + new_status
        )

    event = {
        "from_status": current,
        "to_status": new_status,
        "reviewer_id": str(reviewer_id).strip(),
        "note": note,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }

    item["review_history"].append(event)
    item["review_status"] = new_status
    item["reviewer_id"] = str(reviewer_id).strip()

    if new_status == "COMPLETED":
        item["workflow_completed"] = True

    return item
