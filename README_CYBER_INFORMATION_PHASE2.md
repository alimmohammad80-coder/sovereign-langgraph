# Cyber & Information Operations Intelligence — Phase 2

Phase 2 establishes the live-source ingestion layer for Sovereign Intelligence AI.

## Sources

- CISA Known Exploited Vulnerabilities
- CISA Cybersecurity Advisories
- NVD CVE 2.0
- MITRE ATT&CK
- GDELT DOC 2.0
- URLhaus
- AbuseIPDB
- UK National Cyber Security Centre threat reports
- Canadian Centre for Cyber Security alerts and advisories
- MISP-compatible threat intelligence platforms

## Standards

- STIX 2.x bundle normalization
- TAXII 2.x collection ingestion
- MISP event and attribute normalization
- RSS/Atom CERT/CSIRT ingestion

## Controls

Collectors use bounded request sizes, explicit source provenance, collection timestamps, stable SHA-256 content hashes, and normalized source records. API-key based sources read credentials from environment variables. Phase 2 does not persist observations or perform attribution, clustering, fusion, forecasting, or frontend rendering; those remain later phases.
