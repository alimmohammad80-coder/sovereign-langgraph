from __future__ import annotations


class ConflictEventClassifier:

    RULES = {
        "missile_strike": [
            "missile strike",
            "missile strikes",
            "missile attack",
            "missile attacks",
            "missile barrage",
            "missile bombardment",
            "cruise missile",
            "ballistic missile attack",
            "rocket barrage",
        ],

        "airstrike": [
            "airstrike",
            "airstrikes",
            "air strike",
            "air strikes",
            "aerial attack",
            "aerial attacks",
            "aerial assault",
            "aerial assaults",
            "air bombardment",
            "bombards",
            "bombarded",
            "bombardment",
            "drone strike",
            "drone strikes",
            "drone attack",
            "drone attacks",
            "drone assault",
            "drone assaults",
            "drone barrage",
            "drone swarm",
        ],

        "armed_clash": [
            "armed clash",
            "armed clashes",
            "heavy fighting",
            "intense fighting",
            "ground fighting",
            "combat operations",
            "battle",
            "battles",
            "offensive operations",
            "counteroffensive",
        ],

        "border_incident": [
            "border clash",
            "border incident",
            "line of control",
            "cross-border fire",
            "exchange fire",
            "cross-border shelling",
        ],

        "military_activity": [
            "missile launch",
            "troop mobilization",
            "troop deployment",
            "military exercise",
            "naval exercise",
            "artillery fire",
            "shelling",
            "military operation",
            "military operations",
            "military buildup",
            "military build-up",
            "long-range strike",
            "long-range strikes",
            "deep strike",
            "deep strikes",
            "air war",
        ],

        "terrorism": [
            "terrorist attack",
            "terror attack",
            "suicide attack",
            "militant attack",
            "bombing",
        ],

        "political_instability": [
            "protest",
            "protests",
            "demonstration",
            "demonstrations",
            "unrest",
            "riots",
            "political crisis",
            "government collapse",
            "coup",
        ],

        "diplomatic_tension": [
            "diplomatic row",
            "diplomatic spat",
            "diplomatic firestorm",
            "summoned ambassador",
            "protested remarks",
            "protests remarks",
            "protest remarks",
            "protests kashmir remarks",
            "condemned remarks",
            "diplomatic protest",
        ],

        "diplomatic_engagement": [
            "peace talks",
            "negotiations",
            "dialogue",
            "summit",
            "mediation",
            "confidence-building",
            "confidence building",
        ],

        "ceasefire": [
            "ceasefire",
            "cease-fire",
            "truce",
            "cessation of hostilities",
        ],

        "sanctions": [
            "sanctions",
            "sanctioned",
            "asset freeze",
            "export controls",
            "embargo",
        ],
    }

    PRIORITY = [
        "missile_strike",
        "airstrike",
        "armed_clash",
        "border_incident",
        "terrorism",
        "military_activity",
        "diplomatic_tension",
        "political_instability",
        "ceasefire",
        "diplomatic_engagement",
        "sanctions",
    ]

    ESCALATORY = {
        "missile_strike",
        "airstrike",
        "armed_clash",
        "border_incident",
        "military_activity",
        "terrorism",
        "political_instability",
        "diplomatic_tension",
        "sanctions",
    }

    DEESCALATORY = {
        "ceasefire",
        "diplomatic_engagement",
    }

    @classmethod
    def classify(
        cls,
        *,
        title: str | None,
        summary: str | None,
    ) -> dict:

        text = (
            f"{title or ''} {summary or ''}"
            .lower()
        )

        # Contextual disambiguation:
        # "protest/protests" can mean a formal diplomatic objection,
        # not domestic political unrest.
        diplomatic_protest_patterns = (
            "protests remarks",
            "protested remarks",
            "protest remarks",
            "formally protested",
            "diplomatic protest",
            "summoned ambassador",
            "diplomatic row",
            "diplomatic spat",
            "diplomatic firestorm",
        )

        diplomatic_context = (
            (
                "envoy" in text
                or "ambassador" in text
            )
            and (
                "remarks" in text
                or "comment" in text
                or "visit" in text
            )
            and any(
                term in text
                for term in (
                    "row",
                    "spat",
                    "protest",
                    "firestorm",
                    "condemn",
                    "reignite",
                )
            )
        )

        if (
            any(
                pattern in text
                for pattern in diplomatic_protest_patterns
            )
            or "protests kashmir remarks" in text
            or diplomatic_context
        ):
            return {
                "event_type": "diplomatic_tension",
                "supports_escalation": True,
                "contradicts_escalation": False,
                "matches": [
                    {
                        "event_type": "diplomatic_tension",
                        "hits": [
                            pattern
                            for pattern in diplomatic_protest_patterns
                            if pattern in text
                        ],
                        "score": 1,
                        "priority": 0,
                    }
                ],
            }

        matches = []

        for event_type in cls.PRIORITY:
            keywords = cls.RULES[event_type]

            hits = [
                keyword
                for keyword in keywords
                if keyword in text
            ]

            if hits:
                matches.append(
                    {
                        "event_type": event_type,
                        "hits": hits,
                        "score": len(hits),
                        "priority":
                            cls.PRIORITY.index(
                                event_type
                            ),
                    }
                )

        matches.sort(
            key=lambda x: (
                -x["score"],
                x["priority"],
            )
        )

        primary = (
            matches[0]["event_type"]
            if matches
            else "other"
        )

        return {
            "event_type": primary,

            "supports_escalation":
                primary in cls.ESCALATORY,

            "contradicts_escalation":
                primary in cls.DEESCALATORY,

            "matches": matches,
        }
