# Cyber & Information Operations Intelligence — Phase 5

Phase 5 adds deterministic hybrid-threat fusion across cyber, information, military, diplomatic, economic, infrastructure, supply-chain, and political signals.

## Capabilities

- Cross-domain signal normalization
- Temporal convergence scoring
- Target convergence scoring
- Actor convergence scoring
- Geographic convergence scoring
- Cross-domain convergence scoring
- Infrastructure relevance scoring
- Hybrid campaign assessment

## Analytical safeguards

The engine measures convergence only. It does not treat temporal proximity, shared targets, repeated actors, or narrative similarity as proof of orchestration, attribution, hostile intent, or common control. Evidence status and confidence remain explicit. The hybrid score is an analytic prioritization measure, not a forecast probability.

## Formula

`hybrid_score = 0.20 temporal + 0.20 target + 0.15 actor + 0.15 geography + 0.20 cross-domain + 0.10 infrastructure`

The formula is versioned as `hybrid-fusion-v1` for later calibration.

## Phase boundary

Forecasting, escalation probabilities, persistence models, and scenario generation remain outside Phase 5.