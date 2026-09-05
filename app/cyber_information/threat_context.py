from __future__ import annotations

import re
from typing import Any


_PRODUCT_CONTEXT = (
    (("sonicwall", "vpn", "gateway", "remote access", "sma"), {
        "asset_role": "internet-facing remote-access infrastructure",
        "likely_targets": ["enterprise remote-access gateways", "administrator accounts", "internal networks behind the appliance"],
        "attacker_objectives": ["gain initial access", "establish persistence", "steal credentials", "prepare lateral movement or ransomware deployment"],
        "why_targeted": "Remote-access appliances sit at the boundary between the internet and internal networks. Compromising one can give an attacker a high-value entry point without first compromising an employee workstation.",
    }),
    (("sharepoint", "collaboration", "document management"), {
        "asset_role": "enterprise collaboration and document infrastructure",
        "likely_targets": ["organizations running exposed or reachable SharePoint servers", "document repositories", "authenticated enterprise users"],
        "attacker_objectives": ["execute code on a server", "steal documents or credentials", "move deeper into an enterprise network", "establish persistence"],
        "why_targeted": "SharePoint often contains sensitive documents and trusted enterprise identities. Server compromise can provide both valuable information and a path into adjacent systems.",
    }),
    (("peoplesoft", "peopletools", "oracle"), {
        "asset_role": "enterprise business and human-resources application infrastructure",
        "likely_targets": ["organizations using PeopleSoft", "HR and administrative systems", "privileged business application accounts"],
        "attacker_objectives": ["bypass authentication", "take control of business applications", "access sensitive personnel or administrative data", "use the application as a foothold"],
        "why_targeted": "Enterprise business applications hold sensitive operational and personnel data and often connect to other internal systems. Authentication bypass can turn an exposed application into a privileged foothold.",
    }),
    (("chromium", "chrome", "edge", "browser"), {
        "asset_role": "end-user web browser infrastructure",
        "likely_targets": ["users visiting malicious or compromised web content", "organizations using Chromium-based browsers"],
        "attacker_objectives": ["execute attacker-controlled code in the browser context", "chain the flaw with additional vulnerabilities", "compromise endpoints through crafted web content"],
        "why_targeted": "Browsers process untrusted internet content continuously. A reliable browser exploit can provide a scalable route to many users and can be combined with sandbox-escape or privilege-escalation flaws for deeper compromise.",
    }),
)


def _text(record: dict[str, Any]) -> str:
    return " ".join(str(record.get(key) or "") for key in ("title", "description", "vendor", "product", "required_action")).lower()


def _context_for_product(text: str) -> dict[str, Any]:
    for terms, context in _PRODUCT_CONTEXT:
        if any(term in text for term in terms):
            return context
    return {
        "asset_role": "enterprise technology infrastructure",
        "likely_targets": ["organizations running the affected product", "systems exposed to the vulnerable component"],
        "attacker_objectives": ["gain unauthorized access", "execute code or manipulate the affected system", "establish a foothold for follow-on activity"],
        "why_targeted": "Attackers tend to prioritize exploitable software that provides access to valuable systems, privileged functions, sensitive data, or a path into a broader network.",
    }


def _access_profile(text: str) -> dict[str, Any]:
    unauth = bool(re.search(r"unauthenticated|without authentication|missing authentication|authentication bypass", text))
    remote = bool(re.search(r"remote|over a network|network", text))
    code_exec = bool(re.search(r"arbitrary code|execute code|code injection|os commands|command execution", text))
    data_access = bool(re.search(r"data|information disclosure|read files|documents", text))
    return {
        "remote_exploitation_indicated": remote,
        "authentication_required": False if unauth else None,
        "code_execution_indicated": code_exec,
        "data_access_indicated": data_access,
    }


def build_threat_context(record: dict[str, Any]) -> dict[str, Any]:
    text = _text(record)
    product_context = _context_for_product(text)
    access = _access_profile(text)

    observed_actor = record.get("threat_actor") or record.get("actor") or record.get("attributed_actor")
    ransomware = str(record.get("known_ransomware_use") or "").lower() in {"known", "yes", "true"}
    known_exploited = record.get("record_type") == "known_exploited_vulnerability"

    if observed_actor:
        attribution_status = "source_reported"
        associated_actors = [{"name": str(observed_actor), "relationship": "source-reported association"}]
        attribution_summary = f"The source record associates this activity with {observed_actor}. Independent corroboration should still be checked before treating attribution as definitive."
        attribution_confidence = "moderate"
    elif ransomware:
        attribution_status = "actor_unspecified_ransomware_use"
        associated_actors = [{"name": "Ransomware operators", "relationship": "actor class; specific group not identified"}]
        attribution_summary = "CISA reports known ransomware campaign use, but the available record does not identify a specific ransomware group or state sponsor."
        attribution_confidence = "moderate"
    else:
        attribution_status = "unattributed"
        associated_actors = []
        attribution_summary = "No specific threat actor is identified in the available source evidence. The platform should not infer a named actor from vulnerability exploitation alone."
        attribution_confidence = "low"

    exploitation_summary = (
        "Observed exploitation in the wild is confirmed by inclusion in CISA's Known Exploited Vulnerabilities catalog."
        if known_exploited
        else "This record describes a vulnerability, but this source alone does not establish active exploitation in the wild."
    )

    objectives = list(product_context["attacker_objectives"])
    if ransomware and "deploy or enable ransomware" not in objectives:
        objectives.append("deploy or enable ransomware")

    return {
        "attribution_status": attribution_status,
        "attribution_confidence": attribution_confidence,
        "associated_actors": associated_actors,
        "attribution_summary": attribution_summary,
        "exploitation_summary": exploitation_summary,
        "asset_role": product_context["asset_role"],
        "likely_targets": product_context["likely_targets"],
        "likely_attacker_objectives": objectives,
        "why_targeted": product_context["why_targeted"],
        "access_profile": access,
        "plain_language_assessment": f"This affects {product_context['asset_role']}. {product_context['why_targeted']} {attribution_summary}",
        "evidence_basis": [
            "CISA KEV or source-record exploitation status" if known_exploited else "source vulnerability record",
            "affected product and vulnerability description",
            "deterministic product-role and access-pattern analysis",
        ],
        "analytic_caveat": "Likely targets and attacker objectives are analytic context, not evidence of a specific attacker's identity or motive unless directly supported by cited source reporting.",
    }
