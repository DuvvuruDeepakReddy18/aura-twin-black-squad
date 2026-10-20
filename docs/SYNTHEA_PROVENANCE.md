# Synthea context: authentic synthetic records, unmatched identities

AURA imports 16 adult profiles from the official Synthea sample CSV archive. These are records produced by Synthea, not hand-written patient biographies. They provide a synthetic EHR view beside a separate participant's open research wearable record.

**The two records do not describe the same person.** The interface must call the result a **Composite Research Twin**. The association demonstrates ingestion, provenance, missing-data handling and presentation; it cannot establish a physiological benefit from combining these unmatched records.

## Source and reproducibility

| Item | Value |
|---|---|
| Official source | [Synthea sample downloads](https://synthetichealth.github.io/downloads.html) |
| Pinned sample repository commit | `2c7d489eb4c8bc967dbfab3499a0f573818880dc` |
| Archive SHA-256 | `a7f6f24d3ebd96bbf0b5ef29a16ca6bd6d7ca68db65537ca6ccab6adc20ec609` |
| Actual archive patient count | 102 |
| Chosen historical cutoff | 2019-01-01 |
| Eligible adults alive at cutoff | 69 |
| Exported profiles | 16 |
| Importer version | `aura-synthea-import-1.0.0` |
| Generator version and seed | Not supplied by this sample archive; recorded as unavailable |

The official download page describes unrestricted use of the synthetic sample data and requests citation of [Walonoski et al., 2018](https://doi.org/10.1093/jamia/ocx079). Field meanings follow the [official CSV data dictionary](https://github.com/synthetichealth/synthea/wiki/CSV-File-Data-Dictionary).

The cutoff is an application choice for a historical EHR snapshot. It is **not** the archive's generation date, and the source medical dates have not been shifted to manufacture a match with the wearable timeline.

```powershell
python -X utf8 scripts/ingest_synthea.py --download --as-of 2019-01-01
python -m unittest ml/test_synthea_ingestion.py
```

The importer downloads the immutable commit URL, validates the archive hash before parsing and records hashes, sizes and row counts for the source CSV files. Raw CSV data stay in the ignored `work/` directory.

## Deterministic assignment

Eligible profiles are sorted by source UUID, and the first 16 are assigned in order to research participant identifiers `001` through `016`. Selection uses no wearable readings, outcomes, model scores, demographic similarity or target prevalence. The published assignment manifest contains a SHA-256 digest of the source patient identifier rather than the UUID itself.

This arbitrary assignment is documented in [the assignment manifest](../data/research/synthea-assignment.json). Unmatched Synthea-only and Synthea-plus-wearable model families are negative controls. They are excluded from primary model-family selection. Matched source HbA1c and sex, when evaluated, come from the wearable study's own metadata and are a separate evidence source.

## Chronology, missingness and minimization

- Age is calculated from the source birth date at the historical cutoff. The source birth date itself is not exported.
- BMI, HbA1c and LDL are the latest available source observations on or before that cutoff, with observation time, code, unit and source row retained.
- Diagnoses and medications use source records that started by the cutoff. Resolution dates after the cutoff are withheld.
- The export retains up to 30 diagnoses, 30 medications and 40 recent observations per profile, with available and retained counts disclosed.
- Absent labs remain `null`. There is no imputation in the EHR display. Among these 16 profiles, BMI is absent for 1, HbA1c for 9 and LDL for 6.
- Genetic context is unavailable. No genotype was invented.
- Names, addresses, contact details, direct source identifiers, birth dates, government identifiers, income and coordinates are excluded.

Unusual values are not silently rewritten to plausible values. The original sample is synthetic and may contain clinically implausible values; any modelling treatment must be visible and reproducible.

The importer rejected 15,138 post-cutoff observation rows, 442 post-cutoff condition rows and 1,333 post-cutoff medication rows among the selected profiles. These counts demonstrate chronological filtering; they do not demonstrate clinical validity.

## Machine-readable evidence

- [Imported profiles](../data/research/synthea.json)
- [Source and transformation manifest](../data/research/synthea-provenance.json)
- [Target-blind assignment manifest](../data/research/synthea-assignment.json)
- [Importer](../scripts/ingest_synthea.py)
- [Chronology, minimization and checksum tests](../ml/test_synthea_ingestion.py)

The three importer tests cover future observation/resolution exclusion, missing-field and identity-field handling, and checksum rejection. They use explicit test fixtures rather than adding invented records to the demonstration data.
