from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.repositories.conflict_intelligence_repository import (
    get_supabase_client,
)

from app.services.conflict_intelligence.conflict_forecast_ensemble import (
    ConflictForecastEnsemble,
)

from app.services.conflict_intelligence.conflict_forecast_calibrator import (
    ConflictForecastCalibrator,
)


CHANNELS_PATH = Path(
    "app/data/conflict_intelligence/"
    "rpe_channels.json"
)

MODEL_VERSION = "conflict-rpe-v1"


class RipplePropagationEngine:

    def __init__(self) -> None:
        self.db = get_supabase_client()

        self.channels = json.loads(
            CHANNELS_PATH.read_text()
        )["channels"]

        self.ensemble = (
            ConflictForecastEnsemble()
        )

        self.calibrator = (
            ConflictForecastCalibrator()
        )

    @staticmethod
    def _run_key(
        conflict_id: int,
        horizon_days: int,
        generated_at: str,
    ) -> str:

        raw = (
            f"{conflict_id}|"
            f"{horizon_days}|"
            f"{generated_at}|"
            f"{MODEL_VERSION}"
        )

        digest = hashlib.sha256(
            raw.encode()
        ).hexdigest()[:24].upper()

        return f"RPE-{digest}"

    def _episode(
        self,
        conflict_id: int,
    ) -> dict[str, Any]:

        rows = (
            self.db.table(
                "conflict_canonical_episodes"
            )
            .select(
                "id,"
                "conflict_id,"
                "state_participants,"
                "territories"
            )
            .eq(
                "conflict_id",
                conflict_id,
            )
            .limit(1)
            .execute()
            .data
            or []
        )

        if not rows:
            raise ValueError(
                f"Unknown conflict_id "
                f"{conflict_id}"
            )

        return rows[0]

    def _edges(
        self,
        source_node: str,
    ) -> list[dict[str, Any]]:

        return (
            self.db.table(
                "conflict_propagation_edges"
            )
            .select("*")
            .eq(
                "source_node",
                source_node,
            )
            .eq(
                "active",
                True,
            )
            .execute()
            .data
            or []
        )

    @staticmethod
    def _edge_effect(
        incoming: float,
        edge: dict[str, Any],
    ) -> float:

        weight = float(
            edge.get(
                "transmission_weight"
            )
            or 0.0
        )

        damping = float(
            edge.get(
                "damping_factor"
            )
            or 1.0
        )

        confidence = float(
            edge.get(
                "confidence"
            )
            or 50.0
        ) / 100.0

        return (
            incoming
            * weight
            * damping
            * confidence
        )

    def _propagate_from(
        self,
        source_node: str,
        initial_effect: float,
        max_depth: int = 2,
    ) -> tuple[
        list[dict[str, Any]],
        dict[str, float],
    ]:

        paths = []

        channel_totals = defaultdict(
            float
        )

        frontier = [
            {
                "node":
                    source_node,

                "effect":
                    initial_effect,

                "depth":
                    0,

                "path":
                    [source_node],
            }
        ]

        visited_edges = set()

        while frontier:

            current = frontier.pop(0)

            depth = int(
                current["depth"]
            )

            if depth >= max_depth:
                continue

            edges = self._edges(
                current["node"]
            )

            for edge in edges:

                relationship = str(
                    edge.get(
                        "relationship"
                    )
                    or ""
                )

                # Historical/reference links remain in the
                # knowledge graph but must not behave as
                # downstream causal transmission paths.
                if relationship in {
                    "participant_in_episode",
                    "territory_in_episode",
                }:
                    continue

                target = str(
                    edge[
                        "target_node"
                    ]
                )

                # Do not revisit a node already present
                # in the current path.
                if target in current[
                    "path"
                ]:
                    continue

                edge_signature = (
                    current[
                        "node"
                    ],
                    edge.get(
                        "relationship"
                    ),
                    target,
                    depth,
                )

                if (
                    edge_signature
                    in visited_edges
                ):
                    continue

                visited_edges.add(
                    edge_signature
                )

                channel = str(
                    edge[
                        "channel"
                    ]
                )

                base_effect = (
                    self._edge_effect(
                        float(
                            current[
                                "effect"
                            ]
                        ),
                        edge,
                    )
                )

                # Explicit graph-distance attenuation.
                #
                # depth 1 -> 1.00
                # depth 2 -> 0.65
                # future depth 3 -> 0.4225
                hop_attenuation = (
                    0.65 ** depth
                )

                effect = (
                    base_effect
                    * hop_attenuation
                )

                if effect <= 0:
                    continue

                new_path = (
                    current[
                        "path"
                    ]
                    + [
                        target
                    ]
                )

                record = {
                    "depth":
                        depth + 1,

                    "source_node":
                        current[
                            "node"
                        ],

                    "source_type":
                        edge.get(
                            "source_type"
                        ),

                    "target_node":
                        target,

                    "target_type":
                        edge.get(
                            "target_type"
                        ),

                    "relationship":
                        edge.get(
                            "relationship"
                        ),

                    "channel":
                        channel,

                    "effect":
                        round(
                            effect,
                            6,
                        ),

                    "edge_weight":
                        edge.get(
                            "transmission_weight"
                        ),

                    "damping_factor":
                        edge.get(
                            "damping_factor"
                        ),

                    "confidence":
                        edge.get(
                            "confidence"
                        ),

                    "path":
                        new_path,
                }

                paths.append(
                    record
                )

                channel_totals[
                    channel
                ] += effect

                frontier.append(
                    {
                        "node":
                            target,

                        "effect":
                            effect,

                        "depth":
                            depth + 1,

                        "path":
                            new_path,
                    }
                )

        return (
            paths,
            channel_totals,
        )

    def run(
        self,
        conflict_id: int,
        horizon_days: int = 30,
        lookback_days: int = 30,
        max_depth: int = 2,
        persist: bool = True,
    ) -> dict[str, Any]:

        if horizon_days not in {
            30,
            90,
            180,
            365,
        }:
            raise ValueError(
                "Supported horizons are "
                "30, 90, 180, and 365 days."
            )

        if max_depth not in {
            1,
            2,
            3,
            4,
        }:
            raise ValueError(
                "max_depth must be between 1 and 4."
            )

        episode = self._episode(
            conflict_id
        )

        forecast = (
            self.ensemble.forecast(
                conflict_id,
                horizon_days,
                lookback_days,
            )
        )

        calibration = (
            self.calibrator
            .calibrate_probability(
                forecast[
                    "ensemble_probability"
                ]
            )
        )

        raw_probability = float(
            forecast[
                "ensemble_probability"
            ]
        )

        calibrated_probability = float(
            calibration[
                "calibrated_probability"
            ]
        )

        # Use one causal root only.
        #
        # Starting independently from the episode, its countries,
        # and its territories double-counts the same originating
        # conflict shock. The graph itself must transmit the shock
        # from the episode into participants and territories.
        sources = [
            f"EPISODE-{conflict_id}"
        ]

        all_paths = []
        channel_totals = defaultdict(
            float
        )

        for source_node in sources:

            (
                paths,
                totals,
            ) = self._propagate_from(
                source_node,
                calibrated_probability,
                max_depth,
            )

            all_paths.extend(
                paths
            )

            for channel, value in (
                totals.items()
            ):
                channel_totals[
                    channel
                ] += value

        # Channel impact is derived from unique affected
        # nodes rather than summing every propagation path.
        #
        # Summing paths causes highly connected channels to
        # saturate at 100 even when individual effects are
        # moderate.

        channel_node_effects = defaultdict(dict)

        for path in all_paths:

            channel = str(
                path["channel"]
            )

            target = str(
                path["target_node"]
            )

            effect = float(
                path["effect"]
            )

            previous = (
                channel_node_effects[
                    channel
                ].get(
                    target,
                    0.0,
                )
            )

            if effect > previous:
                channel_node_effects[
                    channel
                ][
                    target
                ] = effect

        channel_impacts = {}

        for channel in self.channels:

            effects = sorted(
                channel_node_effects.get(
                    channel,
                    {}
                ).values(),
                reverse=True,
            )

            # Use the strongest five distinct nodes.
            # This preserves breadth without allowing
            # graph density to dominate the score.
            strongest = effects[:5]

            if strongest:
                channel_effect = (
                    sum(strongest)
                    / len(strongest)
                )
            else:
                channel_effect = 0.0

            channel_impacts[
                channel
            ] = {
                "impact_score":
                    round(
                        min(
                            channel_effect,
                            1.0,
                        )
                        * 100,
                        1,
                    ),

                "mean_top_node_effect":
                    round(
                        channel_effect,
                        6,
                    ),

                "affected_node_count":
                    len(effects),

                "channel_code":
                    self.channels[
                        channel
                    ][
                        "code"
                    ],
            }

        affected = {}

        for path in all_paths:

            target = path[
                "target_node"
            ]

            effect = float(
                path[
                    "effect"
                ]
            )

            if (
                target not in affected
                or effect
                > affected[
                    target
                ][
                    "maximum_effect"
                ]
            ):
                affected[target] = {
                    "node":
                        target,

                    "node_type":
                        path.get(
                            "target_type"
                        ),

                    "maximum_effect":
                        effect,

                    "channel":
                        path[
                            "channel"
                        ],
                }

        affected_nodes = sorted(
            affected.values(),
            key=lambda item:
                item[
                    "maximum_effect"
                ],
            reverse=True,
        )

        generated_at = (
            datetime.now(
                timezone.utc
            ).isoformat()
        )

        result = {
            "conflict_id":
                conflict_id,

            "canonical_episode_id":
                episode[
                    "id"
                ],

            "horizon_days":
                horizon_days,

            "current_state":
                forecast[
                    "current_state"
                ],

            "forecast_probability":
                raw_probability,

            "calibrated_probability":
                calibrated_probability,

            "propagation_depth":
                max_depth,

            "source_nodes":
                sources,

            "channel_impacts":
                channel_impacts,

            "affected_nodes":
                affected_nodes,

            "propagation_paths":
                all_paths,

            "path_count":
                len(
                    all_paths
                ),

            "model_version":
                MODEL_VERSION,

            "generated_at":
                generated_at,
        }

        if persist:

            run_key = self._run_key(
                conflict_id,
                horizon_days,
                generated_at,
            )

            (
                self.db.table(
                    "conflict_ripple_runs"
                )
                .insert(
                    {
                        "run_key":
                            run_key,

                        "conflict_id":
                            conflict_id,

                        "canonical_episode_id":
                            episode[
                                "id"
                            ],

                        "generated_at":
                            generated_at,

                        "horizon_days":
                            horizon_days,

                        "forecast_probability":
                            raw_probability,

                        "calibrated_probability":
                            calibrated_probability,

                        "propagation_depth":
                            max_depth,

                        "channel_impacts":
                            channel_impacts,

                        "affected_nodes":
                            affected_nodes,

                        "propagation_paths":
                            all_paths,

                        "model_version":
                            MODEL_VERSION,

                        "active":
                            True,

                        "review_status":
                            "validated",
                    }
                )
                .execute()
            )

            result[
                "run_key"
            ] = run_key

            result[
                "persisted"
            ] = True

        return result
