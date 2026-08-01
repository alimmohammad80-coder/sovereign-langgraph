import importlib
from dataclasses import dataclass
from typing import Any, Callable
from app.sews_bridge.schemas import SourceBridgeStatus
from app.sews_bridge.source_registry import SOURCE_DEFINITIONS, SourceDefinition

@dataclass(slots=True)
class ResolvedSource:
    definition: SourceDefinition
    callable: Callable[..., Any]
    import_path: str

def import_callable(import_path: str):
    module_name, attr = import_path.split(":", 1)
    module = importlib.import_module(module_name)
    value = getattr(module, attr)
    if not callable(value):
        raise TypeError(f"{import_path} is not callable")
    return value

def resolve_source(definition):
    errors = []
    for candidate in definition.candidates:
        try:
            func = import_callable(candidate)
            return ResolvedSource(definition, func, candidate), SourceBridgeStatus(
                source_key=definition.source_key,
                available=True,
                selected_callable=candidate,
                candidates_checked=list(definition.candidates),
            )
        except Exception as exc:
            errors.append(f"{candidate}: {type(exc).__name__}: {exc}")
    return None, SourceBridgeStatus(
        source_key=definition.source_key,
        available=False,
        candidates_checked=list(definition.candidates),
        error=" | ".join(errors),
    )

def discover_sources():
    resolved, statuses = {}, []
    for definition in SOURCE_DEFINITIONS:
        source, status = resolve_source(definition)
        statuses.append(status)
        if source:
            resolved[definition.source_key] = source
    return resolved, statuses
