# Drug Safety Record-Level Provenance Audit

Audit date: 2026-11-23
Dataset: evidence_records.csv
Total records: 10

## 1. Record-level findings

| Evidence ID | Source category | Source-level finding | Status |
|---|---|---|---|
| EV001 | FAERS/AEMS | Original report ID and source URL unavailable | INCOMPLETE |
| EV002 | FAERS/AEMS | Original report ID and source URL unavailable | INCOMPLETE |
| EV003 | PubMed | PMID, article title and source URL unavailable | INCOMPLETE |
| EV004 | DailyMed | Product identifier, SETID and label URL unavailable | INCOMPLETE |
| EV005 | ClinicalTrials.gov | Explicitly fictional demonstration record; no NCT ID | SYNTHETIC |
| EV006 | Laboratory QC | Fictional sample; original worksheet and specification unavailable | SYNTHETIC |
| EV007 | Drug Quality Complaint | Fictional complaint; original complaint identifier unavailable | SYNTHETIC |
| EV008 | Medication Error Report | Source information requires verification; original incident ID unavailable | UNVERIFIED |
| EV009 | PubMed | PMID and article URL unavailable; conflict requires human review | INCOMPLETE |
| EV010 | Laboratory QC | Fictional sample; raw supporting information insufficient | SYNTHETIC |

## 2. Common provenance field assessment

| Required field | Finding |
|---|---|
| Original source category | Present for all 10 records |
| Original source URL | Not present |
| Original source record identifier | Not present |
| Underlying dataset identifier | Not present |
| Retrieval method | Not present |
| Source retrieval timestamp | Not present |
| Source-level transformation evidence | Not present |
| Local normalization transformation | Documented in normalizer code |
| Source version | Hardcoded as existing_test1_csv |
| Ingestion timestamp | Generated during normalization |

## 3. Transformation limitation

The producer normalizer declares the following transformation path:

existing_csv -> field_mapping -> canonical_normalization

The normalizer also assigns source_version as existing_test1_csv.

These values document the local normalization process. They do not independently establish the original external source artifact, source retrieval process or source-level transformation history.

## 4. Required follow-up evidence

1. EV001 and EV002: Original FAERS/AEMS report identifiers and source records.
2. EV003 and EV009: PubMed identifiers, article titles and source URLs.
3. EV004: DailyMed product identifier and label reference.
4. EV005: Retain as explicitly fictional demonstration data unless an authentic trial record is supplied.
5. EV006 and EV010: Original laboratory worksheets, batch identifiers and applicable specifications, if genuine records exist.
6. EV007: Original complaint documentation, if available.
7. EV008: Verified medication-error source and incident identifier.
8. All records: Document actual retrieval method and source-level transformation where evidence exists.

## 5. Conclusion

The 10-record CSV has identifiable source-category labels, but its source-level provenance is insufficient for independent verification.

No missing source URLs, identifiers or retrieval details have been invented.

Records with fictional, incomplete or unverified provenance must remain distinguishable and subject to the appropriate human review.

This audit does not establish that the records were retrieved from the external databases named in the CSV.
