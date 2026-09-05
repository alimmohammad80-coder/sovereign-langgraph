from __future__ import annotations

from typing import Any

from .base import BaseCollector


class MitreAttackCollector(BaseCollector):
    source_name = "MITRE ATT&CK"
    enterprise_url = "https://raw.githubusercontent.com/mitre-attack/attack-stix-data/master/enterprise-attack/enterprise-attack.json"

    def _normalize(self, objects: list[dict[str, Any]]) -> list[dict[str, Any]]:
        collected_at = self.collected_at()
        records = []
        for obj in objects:
            external_refs = obj.get("external_references", [])
            attack_ref = next((r for r in external_refs if r.get("source_name") in {"mitre-attack", "capec"}), {})
            records.append({
                "source": "mitre_attack",
                "record_type": obj.get("type"),
                "source_record_id": obj.get("id"),
                "attack_id": attack_ref.get("external_id"),
                "name": obj.get("name"),
                "description": obj.get("description"),
                "created": obj.get("created"),
                "modified": obj.get("modified"),
                "revoked": obj.get("revoked", False),
                "deprecated": obj.get("x_mitre_deprecated", False),
                "kill_chain_phases": obj.get("kill_chain_phases", []),
                "external_references": external_refs,
                "raw_stix": obj,
                "provenance": {
                    "source_name": self.source_name,
                    "source_type": "stix_2_1_knowledge_base",
                    "source_url": self.enterprise_url,
                    "publisher": "MITRE",
                    "collected_at": collected_at.isoformat(),
                    "source_record_id": obj.get("id"),
                    "retrieval_method": "official_attack_stix_bundle",
                    "content_hash": self.stable_hash(obj),
                    "reliability_score": 0.98,
                },
            })
        return records

    async def collect(self, *, object_type: str | None = None, limit: int = 500) -> dict[str, Any]:
        bundle = await self.get_json(self.enterprise_url)
        objects = bundle.get("objects", [])
        if object_type:
            objects = [obj for obj in objects if obj.get("type") == object_type]
        objects = objects[: max(1, min(limit, 5000))]
        records = self._normalize(objects)
        return {"source": "mitre_attack", "count": len(records), "records": records}

    async def collect_intelligence_set(self) -> dict[str, Any]:
        """Fetch ATT&CK once and retain objects needed for technique and hypothesis correlation."""
        bundle = await self.get_json(self.enterprise_url)
        allowed = {"attack-pattern", "intrusion-set", "campaign", "relationship"}
        objects = [
            obj for obj in bundle.get("objects", [])
            if obj.get("type") in allowed and not obj.get("revoked") and not obj.get("x_mitre_deprecated")
        ]
        records = self._normalize(objects)
        return {"source": "mitre_attack", "count": len(records), "records": records}
