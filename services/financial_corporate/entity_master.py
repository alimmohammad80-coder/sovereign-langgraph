from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional


@dataclass(frozen=True)
class CorporateEntity:
    entity_id: str
    legal_name: str
    common_name: str
    country_iso3: str
    sector: str
    industry: str
    tier: int
    tickers: List[str] = field(default_factory=list)
    exchanges: List[str] = field(default_factory=list)
    identifiers: Dict[str, str] = field(default_factory=dict)
    strategic_tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


class CorporateEntityMaster:
    """Canonical company registry used across financial and supply-chain modules.

    This first version intentionally keeps the registry in code so the API contract
    can stabilize before persistence/provider ingestion is added. External IDs are
    optional and must only be populated when verified by a provider.
    """

    def __init__(self) -> None:
        self._entities: Dict[str, CorporateEntity] = {
            entity.entity_id: entity for entity in self._seed_entities()
        }

    @staticmethod
    def _seed_entities() -> List[CorporateEntity]:
        return [
            CorporateEntity(
                entity_id="corp_tsmc",
                legal_name="Taiwan Semiconductor Manufacturing Company Limited",
                common_name="TSMC",
                country_iso3="TWN",
                sector="Information Technology",
                industry="Semiconductors",
                tier=1,
                tickers=["TSM", "2330"],
                exchanges=["NYSE", "TWSE"],
                strategic_tags=["advanced_semiconductors", "taiwan", "foundry", "critical_supply_chain"],
            ),
            CorporateEntity(
                entity_id="corp_nvidia",
                legal_name="NVIDIA Corporation",
                common_name="NVIDIA",
                country_iso3="USA",
                sector="Information Technology",
                industry="Semiconductors",
                tier=1,
                tickers=["NVDA"],
                exchanges=["NASDAQ"],
                strategic_tags=["ai_compute", "semiconductors", "data_centers"],
            ),
            CorporateEntity(
                entity_id="corp_apple",
                legal_name="Apple Inc.",
                common_name="Apple",
                country_iso3="USA",
                sector="Information Technology",
                industry="Technology Hardware",
                tier=1,
                tickers=["AAPL"],
                exchanges=["NASDAQ"],
                strategic_tags=["consumer_electronics", "china_exposure", "semiconductor_demand"],
            ),
            CorporateEntity(
                entity_id="corp_asml",
                legal_name="ASML Holding N.V.",
                common_name="ASML",
                country_iso3="NLD",
                sector="Information Technology",
                industry="Semiconductor Equipment",
                tier=1,
                tickers=["ASML"],
                exchanges=["NASDAQ", "EURONEXT"],
                strategic_tags=["euv", "semiconductor_equipment", "export_controls", "critical_supply_chain"],
            ),
            CorporateEntity(
                entity_id="corp_samsung_electronics",
                legal_name="Samsung Electronics Co., Ltd.",
                common_name="Samsung Electronics",
                country_iso3="KOR",
                sector="Information Technology",
                industry="Semiconductors and Electronics",
                tier=1,
                tickers=["005930"],
                exchanges=["KRX"],
                strategic_tags=["memory", "semiconductors", "consumer_electronics"],
            ),
            CorporateEntity(
                entity_id="corp_microsoft",
                legal_name="Microsoft Corporation",
                common_name="Microsoft",
                country_iso3="USA",
                sector="Information Technology",
                industry="Software and Cloud",
                tier=1,
                tickers=["MSFT"],
                exchanges=["NASDAQ"],
                strategic_tags=["cloud", "ai_compute", "enterprise_software"],
            ),
            CorporateEntity(
                entity_id="corp_amazon",
                legal_name="Amazon.com, Inc.",
                common_name="Amazon",
                country_iso3="USA",
                sector="Consumer Discretionary",
                industry="E-Commerce and Cloud",
                tier=1,
                tickers=["AMZN"],
                exchanges=["NASDAQ"],
                strategic_tags=["cloud", "logistics", "ecommerce"],
            ),
            CorporateEntity(
                entity_id="corp_aramco",
                legal_name="Saudi Arabian Oil Company",
                common_name="Saudi Aramco",
                country_iso3="SAU",
                sector="Energy",
                industry="Integrated Oil and Gas",
                tier=1,
                tickers=["2222"],
                exchanges=["TADAWUL"],
                strategic_tags=["oil", "energy_security", "middle_east", "critical_infrastructure"],
            ),
        ]

    def list_entities(
        self,
        query: Optional[str] = None,
        country_iso3: Optional[str] = None,
        sector: Optional[str] = None,
        tier: Optional[int] = None,
        limit: int = 50,
    ) -> List[Dict[str, object]]:
        entities = list(self._entities.values())

        if query:
            needle = query.strip().lower()
            entities = [
                entity for entity in entities
                if needle in entity.legal_name.lower()
                or needle in entity.common_name.lower()
                or any(needle in ticker.lower() for ticker in entity.tickers)
                or any(needle in tag.lower() for tag in entity.strategic_tags)
            ]

        if country_iso3:
            iso3 = country_iso3.strip().upper()
            entities = [entity for entity in entities if entity.country_iso3 == iso3]

        if sector:
            sector_key = sector.strip().lower()
            entities = [entity for entity in entities if sector_key in entity.sector.lower()]

        if tier is not None:
            entities = [entity for entity in entities if entity.tier == tier]

        entities.sort(key=lambda entity: (entity.tier, entity.common_name))
        return [entity.to_dict() for entity in entities[:limit]]

    def get_entity(self, entity_id: str) -> Optional[Dict[str, object]]:
        entity = self._entities.get(entity_id)
        return entity.to_dict() if entity else None

    def resolve(self, reference: str) -> Optional[Dict[str, object]]:
        needle = reference.strip().lower()
        if not needle:
            return None

        if needle in self._entities:
            return self._entities[needle].to_dict()

        exact_matches: List[CorporateEntity] = []
        partial_matches: List[CorporateEntity] = []

        for entity in self._entities.values():
            aliases = [entity.legal_name, entity.common_name, *entity.tickers]
            normalized_aliases = [alias.lower() for alias in aliases]
            if needle in normalized_aliases:
                exact_matches.append(entity)
            elif any(needle in alias for alias in normalized_aliases):
                partial_matches.append(entity)

        candidates = exact_matches or partial_matches
        if not candidates:
            return None

        candidates.sort(key=lambda entity: (entity.tier, len(entity.common_name)))
        return candidates[0].to_dict()
