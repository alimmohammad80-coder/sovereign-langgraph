# Cyber & Information Operations Intelligence — Phase 6

Phase 6 adds the first probabilistic forecasting and early-warning layer on top of the Phase 5 hybrid campaign assessment.

## Capabilities

- 7-day, 30-day, and 90-day escalation forecasts
- 7-day, 30-day, and 90-day persistence forecasts
- Explicit uncertainty intervals
- Forecast confidence assessment
- Versioned logistic baseline (`cyber-hybrid-logit-v1`)
- Early-warning score and level
- Cross-module handoff contract for Strategic Early Warning, Conflict Forecasting, Country Intelligence, Global Risk Map, Intelligence Stream, and Strategic AI Agents

## Inputs

The baseline uses Phase 5 hybrid convergence, temporal/target/infrastructure dimensions, cross-domain breadth, recent signal momentum, recent signal severity, and explicit prior rates.

## Calibration status

This implementation is deliberately labeled `baseline_requires_historical_calibration`. It creates auditable probabilistic outputs but must be calibrated and validated against historical labeled episodes before its probabilities are represented as fully calibrated operational forecasts.

## Phase boundary

Scenario generation, automated courses of action, frontend visualization, and LLM-generated probabilities are not part of Phase 6. AI may later explain these statistical outputs but should not replace the underlying probability model.
