import os, json
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL = os.getenv("OPENAI_MODEL", "gpt-5.5")

def generate_fusion_report(country: str, signals: list, sources: list):
    prompt = f"""
You are Sovereign Intelligence's senior geopolitical intelligence analyst.

Produce a professional decision-support intelligence report for: {country}

Use ONLY the supplied signals and sources.
Do not invent facts.
Include Chicago author-date citations in the text.
Every major claim must cite supplied source metadata.

Signals:
{json.dumps(signals, ensure_ascii=False)}

Sources:
{json.dumps(sources, ensure_ascii=False)}
"""

    response = client.responses.create(
        model=MODEL,
        input=prompt,
        text={
            "format": {
                "type": "json_schema",
                "name": "sovereign_fusion_report",
                "schema": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "title": {"type": "string"},
                        "executive_judgment": {"type": "string"},
                        "risk_score": {"type": "integer"},
                        "confidence_score": {"type": "integer"},
                        "key_developments": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "strategic_assessment": {"type": "string"},
                        "early_warning_indicators": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "cascading_effects": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "decision_support": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "simulation_questions": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "references": {
                            "type": "array",
                            "items": {"type": "string"}
                        }
                    },
                    "required": [
                        "title",
                        "executive_judgment",
                        "risk_score",
                        "confidence_score",
                        "key_developments",
                        "strategic_assessment",
                        "early_warning_indicators",
                        "cascading_effects",
                        "decision_support",
                        "simulation_questions",
                        "references"
                    ]
                }
            }
        }
    )

    return json.loads(response.output_text)
