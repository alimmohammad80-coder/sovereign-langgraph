from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from typing import Dict, List


@dataclass(frozen=True)
class ProviderCapability:
    provider_id: str
    name: str
    role: str
    enabled: bool
    requires_key: bool
    authoritative_for: List[str]

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


class FinancialCorporateProviderRegistry:
    """Registry describing evidence providers and their intended authority.

    Provider adapters should normalize their output before it reaches the entity
    master or scoring engine. This prevents provider-specific schemas from leaking
    into core intelligence contracts.
    """

    def capabilities(self) -> List[Dict[str, object]]:
        sec_user_agent = os.getenv("SEC_USER_AGENT")
        alpha_vantage_key = os.getenv("ALPHA_VANTAGE_API_KEY")
        capabilities = [
            ProviderCapability(
                provider_id="sec_edgar",
                name="SEC EDGAR / XBRL",
                role="Public-company filings, fundamentals, material events and issuer identifiers",
                enabled=bool(sec_user_agent),
                requires_key=False,
                authoritative_for=["US_public_filings", "financial_statements", "CIK", "8-K", "10-K", "10-Q"],
            ),
            ProviderCapability(
                provider_id="gleif",
                name="GLEIF",
                role="Legal-entity identity, LEI records and relationship resolution",
                enabled=True,
                requires_key=False,
                authoritative_for=["LEI", "legal_entity_identity", "entity_relationships"],
            ),
            ProviderCapability(
                provider_id="fred_credit_conditions",
                name="Federal Reserve Bank of St. Louis FRED",
                role="Interest rates, Treasury curve and system credit/funding conditions",
                enabled=True,
                requires_key=False,
                authoritative_for=["interest_rates", "treasury_curve", "credit_spreads", "funding_conditions"],
            ),
            ProviderCapability(
                provider_id="alpha_vantage_market",
                name="Alpha Vantage",
                role="Optional global equity price history for company-specific market stress",
                enabled=bool(alpha_vantage_key),
                requires_key=True,
                authoritative_for=["equity_prices", "OHLCV", "market_history"],
            ),
            ProviderCapability(
                provider_id="ofac",
                name="U.S. Treasury OFAC",
                role="Sanctions and restricted counterparty evidence",
                enabled=True,
                requires_key=False,
                authoritative_for=["sanctions", "restricted_entities"],
            ),
            ProviderCapability(
                provider_id="supply_chain_bridge",
                name="Sovereign Supply Chain Intelligence",
                role="Facilities, suppliers, ports, commodities, chokepoints and disruption exposure",
                enabled=True,
                requires_key=False,
                authoritative_for=["supplier_exposure", "facility_exposure", "logistics_exposure", "commodity_exposure"],
            ),
        ]
        return [capability.to_dict() for capability in capabilities]

    def architecture(self) -> Dict[str, object]:
        return {
            "normalization_contract": {
                "entity_identity": ["entity_id", "legal_name", "country_iso3", "identifiers", "source", "observed_at"],
                "financial_observation": ["entity_id", "metric", "value", "unit", "period_end", "source", "observed_at"],
                "market_observation": ["entity_id", "symbol", "date", "close", "volume", "source", "observed_at"],
                "credit_observation": ["series_id", "date", "value", "source", "observed_at"],
                "risk_evidence": ["entity_id", "dimension", "signal", "severity", "confidence", "source", "observed_at"],
                "exposure_edge": ["source_entity_id", "target_id", "relationship_type", "weight", "source", "observed_at"],
            },
            "provider_rule": "Providers supply evidence and identity; they do not assign the final corporate risk score.",
        }
