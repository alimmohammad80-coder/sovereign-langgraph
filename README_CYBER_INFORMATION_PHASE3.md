# Cyber & Information Operations Intelligence — Phase 3

Phase 3 converts normalized collector records into operational cyber intelligence objects.

## Implemented

- Cyber incident normalization from Phase 2 collector records
- Deterministic vulnerability exposure assessment
- Actor/campaign relationship extraction from STIX relationships
- Infrastructure target profiling
- Graph-ready entity and relationship generation using the Phase 1 ontology
- FastAPI endpoints under `/api/cyber-information/engine/*`
- Network-independent engine tests

## Analytical rules

- Severity, confidence, and exposure are separate values.
- Confirmed source observations remain distinguishable from assessed attribution.
- Vulnerability exposure scoring is deterministic and explainable.
- Actor/campaign links are not inferred when the source relationship is missing.
- Graph attribution relationships use assessed evidence status.

## Phase boundary

Phase 3 does not implement narrative clustering, information-operation analysis, coordinated behavior detection, hybrid fusion, or forecasting. Those remain subsequent phases.