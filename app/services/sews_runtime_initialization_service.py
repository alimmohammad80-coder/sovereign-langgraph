from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from supabase import Client

FRAMEWORK_PATH = Path('app/data/sews_global_analytic_frameworks.json')
LIBRARY_PATH = Path('app/data/sews_global_indicator_library.json')


class SEWSRuntimeInitializationService:
    def __init__(self, db: Client):
        self.db = db

    @staticmethod
    def _load(path: Path) -> dict[str, Any]:
        return json.loads(path.read_text())

    @staticmethod
    def _indicator_rows(library: dict[str, Any]) -> list[dict[str, Any]]:
        indicators = library.get('indicators') or library.get('indicator_definitions') or []
        rows = []
        for item in indicators:
            key = item.get('indicator_key')
            if not key:
                continue
            sources = item.get('source_keys') or item.get('preferred_source_keys') or item.get('sources') or []
            if sources and isinstance(sources[0], dict):
                sources = [str(x.get('source_key') or x.get('key') or x.get('name')) for x in sources if x]
            rows.append({
                'indicator_key': key,
                'name': item.get('name') or item.get('indicator_name') or key.replace('_', ' ').title(),
                'description': item.get('description') or f'Canonical SEWS indicator for {key}.',
                'primary_domain': item.get('primary_domain') or item.get('domain') or 'Unknown',
                'secondary_domains': item.get('secondary_domains') or [],
                'default_class': item.get('default_class') or item.get('indicator_class') or 'PRECURSOR',
                'status': item.get('status') or 'ACTIVE',
                'measurement_unit': item.get('measurement_unit'),
                'measurement_type': item.get('measurement_type') or 'EVENT_COUNT',
                'expected_direction': item.get('expected_direction') or 'INCREASE',
                'geographic_scope': item.get('geographic_scope') or {},
                'sector_scope': item.get('sector_scope') or item.get('sectors') or [],
                'collection_method': item.get('collection_method') or 'API',
                'source_keys': sources,
                'source_requirements': item.get('source_requirements') or {},
                'refresh_interval_minutes': int(item.get('refresh_interval_minutes', 1440)),
                'stale_after_minutes': int(item.get('stale_after_minutes', 4320)),
                'default_source_reliability': float(item.get('default_source_reliability', 70)),
                'default_relevance': float(item.get('default_relevance', 70)),
                'default_weight': float(item.get('default_weight', 1.0)),
                'normalization_config': item.get('normalization_config') or {},
                'threshold_config': item.get('threshold_config') or {},
                'owner_agent': item.get('owner_agent') or 'sews-indicator-agent',
                'tags': item.get('tags') or [],
                'version': int(item.get('version', 1)),
                'active': bool(item.get('active', True)),
            })
        return rows

    @staticmethod
    def _mapping_rows(frameworks: dict[str, Any]) -> tuple[list[dict[str, Any]], int]:
        aggregated: dict[tuple[str, str], dict[str, Any]] = {}
        refs = 0
        priorities = {'TRIGGER': 1, 'ACCELERANT': 2, 'CONTRA': 2, 'PRECURSOR': 3}
        for problem in frameworks.get('warning_problems', []):
            problem_key = problem['warning_problem_key']
            for framework in problem.get('frameworks', []):
                if framework.get('status', 'ACTIVE') != 'ACTIVE':
                    continue
                fw = float(framework.get('weight', 1.0))
                for group in framework.get('indicator_groups', []):
                    gw = float(group.get('weight', 1.0))
                    rationale = f"{framework.get('name')}: {group.get('name')}. {group.get('analytic_purpose') or ''}".strip()
                    for mapped in group.get('mapped_indicators', []):
                        refs += 1
                        pair = (problem_key, mapped['indicator_key'])
                        cls = mapped['indicator_class']
                        if pair not in aggregated:
                            aggregated[pair] = {
                                'problem_key': problem_key,
                                'indicator_key': mapped['indicator_key'],
                                'indicator_class': cls,
                                'weight': fw * gw,
                                'polarity': -1.0 if cls == 'CONTRA' else 1.0,
                                'minimum_relevance': 40.0,
                                'minimum_reliability': 40.0,
                                'activation_threshold': None,
                                'critical_threshold': None,
                                'lead_time_min_days': None,
                                'lead_time_max_days': None,
                                'rationales': {rationale},
                                'collection_priority': priorities.get(cls, 3),
                                'required': True,
                                'active': True,
                                'mapping_version': 1,
                            }
                        else:
                            aggregated[pair]['weight'] += fw * gw
                            aggregated[pair]['rationales'].add(rationale)
                            aggregated[pair]['collection_priority'] = min(aggregated[pair]['collection_priority'], priorities.get(cls, 3))
        rows = []
        for row in aggregated.values():
            row['weight'] = round(row['weight'], 4)
            row['rationale'] = ' | '.join(sorted(row.pop('rationales')))[:4000]
            rows.append(row)
        rows.sort(key=lambda x: (x['problem_key'], x['indicator_key']))
        return rows, refs

    @staticmethod
    def _chunks(rows: list[dict[str, Any]], size: int = 250):
        for i in range(0, len(rows), size):
            yield rows[i:i+size]

    def status(self) -> dict[str, Any]:
        def fetch_all(
            table_name: str,
            columns: str,
            *,
            active_only: bool = True,
            page_size: int = 500,
        ) -> list[dict[str, Any]]:
            rows: list[dict[str, Any]] = []
            start = 0

            while True:
                query = (
                    self.db.table(table_name)
                    .select(columns)
                )

                if active_only:
                    query = query.eq("active", True)

                result = (
                    query
                    .range(start, start + page_size - 1)
                    .execute()
                )

                batch = result.data or []
                rows.extend(batch)

                if len(batch) < page_size:
                    break

                start += page_size

            return rows

        warning_rows = fetch_all(
            "sews_warning_problems",
            "problem_key",
        )

        definition_rows = fetch_all(
            "sews_indicator_definitions",
            "indicator_key",
        )

        mapping_rows = fetch_all(
            "sews_warning_problem_indicators",
            "problem_key,indicator_key",
        )

        warning_keys = {
            row["problem_key"]
            for row in warning_rows
        }

        mapped_keys = {
            row["problem_key"]
            for row in mapping_rows
        }

        unmapped = sorted(warning_keys - mapped_keys)

        warning_count = len(warning_rows)
        definition_count = len(definition_rows)
        mapping_count = len(mapping_rows)

        return {
            "warning_problems": warning_count,
            "indicator_definitions": definition_count,
            "warning_indicator_mappings": mapping_count,
            "mapped_warning_problems": len(
                warning_keys & mapped_keys
            ),
            "unmapped_warning_problems": unmapped,
            "mapping_ready": (
                warning_count == 20
                and definition_count >= 1224
                and mapping_count >= 1436
                and not unmapped
            ),
            "metadata": {
                "expected_framework_references": 1920,
                "expected_unique_mappings": 1436,
                "expected_indicator_definitions": 1224,
                "expected_warning_problems": 20,
            },
        }

    def initialize(self, *, dry_run: bool = False) -> dict[str, Any]:
        library = self._load(LIBRARY_PATH)
        frameworks = self._load(FRAMEWORK_PATH)
        definitions = self._indicator_rows(library)
        mappings, refs = self._mapping_rows(frameworks)
        warning_keys = {x['problem_key'] for x in (self.db.table('sews_warning_problems').select('problem_key').execute().data or [])}
        framework_keys = {x['warning_problem_key'] for x in frameworks.get('warning_problems', [])}
        missing_warnings = sorted(framework_keys - warning_keys)
        payload = {
            'status': 'preview' if dry_run else 'success',
            'dry_run': dry_run,
            'indicator_definitions_in_library': len(definitions),
            'mapping_references_in_frameworks': refs,
            'unique_warning_indicator_pairs': len(mappings),
            'missing_warning_problems': missing_warnings,
            'indicator_definitions_upserted': 0,
            'mappings_upserted': 0,
        }
        if dry_run or missing_warnings:
            if missing_warnings:
                payload['status'] = 'blocked'
            return payload
        for chunk in self._chunks(definitions):
            self.db.table('sews_indicator_definitions').upsert(chunk, on_conflict='indicator_key').execute()
            payload['indicator_definitions_upserted'] += len(chunk)
        for chunk in self._chunks(mappings):
            self.db.table('sews_warning_problem_indicators').upsert(chunk, on_conflict='problem_key,indicator_key').execute()
            payload['mappings_upserted'] += len(chunk)
        return payload
