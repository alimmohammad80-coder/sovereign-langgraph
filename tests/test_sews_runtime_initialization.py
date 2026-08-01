import json
from pathlib import Path
from app.services.sews_runtime_initialization_service import SEWSRuntimeInitializationService

def test_mapping_aggregation_matches_reference_count():
    data = json.loads(Path('app/data/sews_global_analytic_frameworks.json').read_text())
    rows, refs = SEWSRuntimeInitializationService._mapping_rows(data)
    assert refs == data['mapped_indicator_reference_count']
    assert len({(x['problem_key'], x['indicator_key']) for x in rows}) == len(rows)
    assert all(x['polarity'] == (-1.0 if x['indicator_class'] == 'CONTRA' else 1.0) for x in rows)

def test_indicator_library_conversion():
    data = json.loads(Path('app/data/sews_global_indicator_library.json').read_text())
    rows = SEWSRuntimeInitializationService._indicator_rows(data)
    assert len(rows) == data['indicator_count']
    assert len({x['indicator_key'] for x in rows}) == len(rows)
