-- SEWS Global Warning Registry seed
-- Idempotent: safe to run repeatedly.

insert into sews_warning_problems (
    problem_key,
    title,
    hypothesis,
    horizon_days,
    state,
    base_rate,
    severity_score,
    version,
    active,
    exposure_map,
    transition_rules
)
values (
    'WP-TWN-BLOCKADE',
    'Taiwan Blockade or Coercive Quarantine',
    'China initiates a blockade, coercive quarantine, or sustained maritime-air exclusion operation against Taiwan within 180 days.',
    180,
    'DORMANT',
    0.08,
    96.0,
    1,
    true,
    '{"region": "Indo-Pacific", "subregions": [], "countries": ["CHN", "TWN", "JPN", "USA"], "maritime_zones": ["Taiwan Strait", "East China Sea", "Philippine Sea"], "map_geometry": null, "classification": {"primary_domain": "Conflict and Military", "secondary_domains": ["Political Stability", "Energy and Supply Chain", "Humanitarian and Public Health"], "intelligence_priority": "TIER_1", "strategic_impact": "CATASTROPHIC", "forecast_horizon_days": 180}, "dependencies": {"related_warning_problems": ["WP-SEMICONDUCTOR-SHOCK", "WP-CRITICAL-MINERALS-RESTRICTION"], "parent_problem": null, "child_problems": [], "upstream_effects": [], "downstream_effects": [], "supply_chain_impacts": [], "financial_impacts": []}, "ai_configuration": {"required_agents": ["conflict_monitoring", "political_stability", "energy_security", "executive_briefing"], "required_data_sources": ["GDELT", "Google News RSS", "ReliefWeb", "ACLED", "UN", "Government and defense releases"], "required_indicator_classes": ["PRECURSOR", "ACCELERANT", "TRIGGER", "CONTRA"], "probability_model": "sews-logit-v1", "confidence_model": "sews-confidence-v1", "narrative_model_role": "EXPLANATION_ONLY", "deterministic_scoring_required": true, "contrary_evidence_required": true, "dark_feed_detection_required": true}, "outputs": {"bluf_template": "SEWS_BLUF_V1", "full_analysis_template": "SEWS_ANALYSIS_V1", "executive_summary_template": "SEWS_EXECUTIVE_V1", "dashboard_card_template": "SEWS_CARD_V1", "alert_template": "SEWS_ALERT_V1", "siam_briefing_template": "SEWS_SIAM_V1"}, "governance": {"analyst_review_required": false, "ledger_enabled": true, "forecast_verification_enabled": true, "brier_scoring_enabled": true, "immutable_assessment_versions": true}, "description": "China initiates a blockade, coercive quarantine, or sustained maritime-air exclusion operation against Taiwan within 180 days."}'::jsonb,
    '{"probability_model": "sews-logit-v1", "confidence_model": "sews-confidence-v1", "default_states": ["DORMANT", "WATCH", "ADVISORY", "WARNING", "CRITICAL"], "hysteresis_enabled": true, "analyst_override_enabled": true}'::jsonb
)
on conflict (problem_key)
do update set
    title = excluded.title,
    hypothesis = excluded.hypothesis,
    horizon_days = excluded.horizon_days,
    base_rate = excluded.base_rate,
    severity_score = excluded.severity_score,
    version = excluded.version,
    active = excluded.active,
    exposure_map = excluded.exposure_map,
    transition_rules = excluded.transition_rules,
    updated_at = now();

insert into sews_warning_problems (
    problem_key,
    title,
    hypothesis,
    horizon_days,
    state,
    base_rate,
    severity_score,
    version,
    active,
    exposure_map,
    transition_rules
)
values (
    'WP-IRN-ISR-ESCALATION',
    'Iran–Israel Regional Escalation',
    'Direct or proxy confrontation between Iran and Israel expands into sustained regional conflict within 90 days.',
    90,
    'DORMANT',
    0.18,
    95.0,
    1,
    true,
    '{"region": "Middle East and North Africa", "subregions": [], "countries": ["IRN", "ISR", "LBN", "SYR", "IRQ", "YEM"], "maritime_zones": ["Eastern Mediterranean", "Persian Gulf", "Red Sea"], "map_geometry": null, "classification": {"primary_domain": "Conflict and Military", "secondary_domains": ["Political Stability", "Energy and Supply Chain", "Humanitarian and Public Health"], "intelligence_priority": "TIER_1", "strategic_impact": "CATASTROPHIC", "forecast_horizon_days": 90}, "dependencies": {"related_warning_problems": ["WP-HORMUZ-CLOSURE", "WP-RED-SEA-SHIPPING", "WP-ENERGY-PRICE-SPIKE"], "parent_problem": null, "child_problems": [], "upstream_effects": [], "downstream_effects": [], "supply_chain_impacts": [], "financial_impacts": []}, "ai_configuration": {"required_agents": ["conflict_monitoring", "political_stability", "energy_security", "executive_briefing"], "required_data_sources": ["GDELT", "Google News RSS", "ReliefWeb", "ACLED", "UN", "Government and defense releases"], "required_indicator_classes": ["PRECURSOR", "ACCELERANT", "TRIGGER", "CONTRA"], "probability_model": "sews-logit-v1", "confidence_model": "sews-confidence-v1", "narrative_model_role": "EXPLANATION_ONLY", "deterministic_scoring_required": true, "contrary_evidence_required": true, "dark_feed_detection_required": true}, "outputs": {"bluf_template": "SEWS_BLUF_V1", "full_analysis_template": "SEWS_ANALYSIS_V1", "executive_summary_template": "SEWS_EXECUTIVE_V1", "dashboard_card_template": "SEWS_CARD_V1", "alert_template": "SEWS_ALERT_V1", "siam_briefing_template": "SEWS_SIAM_V1"}, "governance": {"analyst_review_required": false, "ledger_enabled": true, "forecast_verification_enabled": true, "brier_scoring_enabled": true, "immutable_assessment_versions": true}, "description": "Direct or proxy confrontation between Iran and Israel expands into sustained regional conflict within 90 days."}'::jsonb,
    '{"probability_model": "sews-logit-v1", "confidence_model": "sews-confidence-v1", "default_states": ["DORMANT", "WATCH", "ADVISORY", "WARNING", "CRITICAL"], "hysteresis_enabled": true, "analyst_override_enabled": true}'::jsonb
)
on conflict (problem_key)
do update set
    title = excluded.title,
    hypothesis = excluded.hypothesis,
    horizon_days = excluded.horizon_days,
    base_rate = excluded.base_rate,
    severity_score = excluded.severity_score,
    version = excluded.version,
    active = excluded.active,
    exposure_map = excluded.exposure_map,
    transition_rules = excluded.transition_rules,
    updated_at = now();

insert into sews_warning_problems (
    problem_key,
    title,
    hypothesis,
    horizon_days,
    state,
    base_rate,
    severity_score,
    version,
    active,
    exposure_map,
    transition_rules
)
values (
    'WP-RUS-NATO-SPILLOVER',
    'Russia–NATO Conflict Spillover',
    'The Russia–Ukraine war produces a direct military incident involving NATO territory or forces within 180 days.',
    180,
    'DORMANT',
    0.06,
    98.0,
    1,
    true,
    '{"region": "Europe", "subregions": [], "countries": ["RUS", "UKR", "POL", "LTU", "LVA", "EST", "ROU"], "maritime_zones": [], "map_geometry": null, "classification": {"primary_domain": "Conflict and Military", "secondary_domains": ["Political Stability", "Energy and Supply Chain", "Humanitarian and Public Health"], "intelligence_priority": "TIER_1", "strategic_impact": "CATASTROPHIC", "forecast_horizon_days": 180}, "dependencies": {"related_warning_problems": ["WP-UKR-FRONT-DETERIORATION", "WP-ENERGY-PRICE-SPIKE"], "parent_problem": null, "child_problems": [], "upstream_effects": [], "downstream_effects": [], "supply_chain_impacts": [], "financial_impacts": []}, "ai_configuration": {"required_agents": ["conflict_monitoring", "political_stability", "energy_security", "executive_briefing"], "required_data_sources": ["GDELT", "Google News RSS", "ReliefWeb", "ACLED", "UN", "Government and defense releases"], "required_indicator_classes": ["PRECURSOR", "ACCELERANT", "TRIGGER", "CONTRA"], "probability_model": "sews-logit-v1", "confidence_model": "sews-confidence-v1", "narrative_model_role": "EXPLANATION_ONLY", "deterministic_scoring_required": true, "contrary_evidence_required": true, "dark_feed_detection_required": true}, "outputs": {"bluf_template": "SEWS_BLUF_V1", "full_analysis_template": "SEWS_ANALYSIS_V1", "executive_summary_template": "SEWS_EXECUTIVE_V1", "dashboard_card_template": "SEWS_CARD_V1", "alert_template": "SEWS_ALERT_V1", "siam_briefing_template": "SEWS_SIAM_V1"}, "governance": {"analyst_review_required": false, "ledger_enabled": true, "forecast_verification_enabled": true, "brier_scoring_enabled": true, "immutable_assessment_versions": true}, "description": "The Russia–Ukraine war produces a direct military incident involving NATO territory or forces within 180 days."}'::jsonb,
    '{"probability_model": "sews-logit-v1", "confidence_model": "sews-confidence-v1", "default_states": ["DORMANT", "WATCH", "ADVISORY", "WARNING", "CRITICAL"], "hysteresis_enabled": true, "analyst_override_enabled": true}'::jsonb
)
on conflict (problem_key)
do update set
    title = excluded.title,
    hypothesis = excluded.hypothesis,
    horizon_days = excluded.horizon_days,
    base_rate = excluded.base_rate,
    severity_score = excluded.severity_score,
    version = excluded.version,
    active = excluded.active,
    exposure_map = excluded.exposure_map,
    transition_rules = excluded.transition_rules,
    updated_at = now();

insert into sews_warning_problems (
    problem_key,
    title,
    hypothesis,
    horizon_days,
    state,
    base_rate,
    severity_score,
    version,
    active,
    exposure_map,
    transition_rules
)
values (
    'WP-UKR-FRONT-DETERIORATION',
    'Major Ukrainian Front Deterioration',
    'Ukrainian defensive positions experience a strategically significant deterioration or territorial breakthrough within 90 days.',
    90,
    'DORMANT',
    0.22,
    88.0,
    1,
    true,
    '{"region": "Europe", "subregions": [], "countries": ["UKR", "RUS"], "maritime_zones": [], "map_geometry": null, "classification": {"primary_domain": "Conflict and Military", "secondary_domains": ["Political Stability", "Energy and Supply Chain", "Humanitarian and Public Health"], "intelligence_priority": "TIER_2", "strategic_impact": "SEVERE", "forecast_horizon_days": 90}, "dependencies": {"related_warning_problems": [], "parent_problem": null, "child_problems": [], "upstream_effects": [], "downstream_effects": [], "supply_chain_impacts": [], "financial_impacts": []}, "ai_configuration": {"required_agents": ["conflict_monitoring", "political_stability", "energy_security", "executive_briefing"], "required_data_sources": ["GDELT", "Google News RSS", "ReliefWeb", "ACLED", "UN", "Government and defense releases"], "required_indicator_classes": ["PRECURSOR", "ACCELERANT", "TRIGGER", "CONTRA"], "probability_model": "sews-logit-v1", "confidence_model": "sews-confidence-v1", "narrative_model_role": "EXPLANATION_ONLY", "deterministic_scoring_required": true, "contrary_evidence_required": true, "dark_feed_detection_required": true}, "outputs": {"bluf_template": "SEWS_BLUF_V1", "full_analysis_template": "SEWS_ANALYSIS_V1", "executive_summary_template": "SEWS_EXECUTIVE_V1", "dashboard_card_template": "SEWS_CARD_V1", "alert_template": "SEWS_ALERT_V1", "siam_briefing_template": "SEWS_SIAM_V1"}, "governance": {"analyst_review_required": false, "ledger_enabled": true, "forecast_verification_enabled": true, "brier_scoring_enabled": true, "immutable_assessment_versions": true}, "description": "Ukrainian defensive positions experience a strategically significant deterioration or territorial breakthrough within 90 days."}'::jsonb,
    '{"probability_model": "sews-logit-v1", "confidence_model": "sews-confidence-v1", "default_states": ["DORMANT", "WATCH", "ADVISORY", "WARNING", "CRITICAL"], "hysteresis_enabled": true, "analyst_override_enabled": true}'::jsonb
)
on conflict (problem_key)
do update set
    title = excluded.title,
    hypothesis = excluded.hypothesis,
    horizon_days = excluded.horizon_days,
    base_rate = excluded.base_rate,
    severity_score = excluded.severity_score,
    version = excluded.version,
    active = excluded.active,
    exposure_map = excluded.exposure_map,
    transition_rules = excluded.transition_rules,
    updated_at = now();

insert into sews_warning_problems (
    problem_key,
    title,
    hypothesis,
    horizon_days,
    state,
    base_rate,
    severity_score,
    version,
    active,
    exposure_map,
    transition_rules
)
values (
    'WP-PRK-STRATEGIC-PROVOCATION',
    'North Korean Strategic Provocation',
    'North Korea conducts a nuclear test, long-range missile launch, or major conventional provocation within 90 days.',
    90,
    'DORMANT',
    0.25,
    89.0,
    1,
    true,
    '{"region": "Indo-Pacific", "subregions": [], "countries": ["PRK", "KOR", "JPN", "CHN", "USA"], "maritime_zones": [], "map_geometry": null, "classification": {"primary_domain": "Conflict and Military", "secondary_domains": ["Political Stability", "Energy and Supply Chain", "Humanitarian and Public Health"], "intelligence_priority": "TIER_2", "strategic_impact": "SEVERE", "forecast_horizon_days": 90}, "dependencies": {"related_warning_problems": [], "parent_problem": null, "child_problems": [], "upstream_effects": [], "downstream_effects": [], "supply_chain_impacts": [], "financial_impacts": []}, "ai_configuration": {"required_agents": ["conflict_monitoring", "political_stability", "energy_security", "executive_briefing"], "required_data_sources": ["GDELT", "Google News RSS", "ReliefWeb", "ACLED", "UN", "Government and defense releases"], "required_indicator_classes": ["PRECURSOR", "ACCELERANT", "TRIGGER", "CONTRA"], "probability_model": "sews-logit-v1", "confidence_model": "sews-confidence-v1", "narrative_model_role": "EXPLANATION_ONLY", "deterministic_scoring_required": true, "contrary_evidence_required": true, "dark_feed_detection_required": true}, "outputs": {"bluf_template": "SEWS_BLUF_V1", "full_analysis_template": "SEWS_ANALYSIS_V1", "executive_summary_template": "SEWS_EXECUTIVE_V1", "dashboard_card_template": "SEWS_CARD_V1", "alert_template": "SEWS_ALERT_V1", "siam_briefing_template": "SEWS_SIAM_V1"}, "governance": {"analyst_review_required": false, "ledger_enabled": true, "forecast_verification_enabled": true, "brier_scoring_enabled": true, "immutable_assessment_versions": true}, "description": "North Korea conducts a nuclear test, long-range missile launch, or major conventional provocation within 90 days."}'::jsonb,
    '{"probability_model": "sews-logit-v1", "confidence_model": "sews-confidence-v1", "default_states": ["DORMANT", "WATCH", "ADVISORY", "WARNING", "CRITICAL"], "hysteresis_enabled": true, "analyst_override_enabled": true}'::jsonb
)
on conflict (problem_key)
do update set
    title = excluded.title,
    hypothesis = excluded.hypothesis,
    horizon_days = excluded.horizon_days,
    base_rate = excluded.base_rate,
    severity_score = excluded.severity_score,
    version = excluded.version,
    active = excluded.active,
    exposure_map = excluded.exposure_map,
    transition_rules = excluded.transition_rules,
    updated_at = now();

insert into sews_warning_problems (
    problem_key,
    title,
    hypothesis,
    horizon_days,
    state,
    base_rate,
    severity_score,
    version,
    active,
    exposure_map,
    transition_rules
)
values (
    'WP-PAK-POLITICAL-INSTABILITY',
    'Pakistan Political Instability',
    'Political confrontation in Pakistan produces sustained unrest, institutional paralysis, or an unconstitutional transfer of authority within 120 days.',
    120,
    'DORMANT',
    0.24,
    78.0,
    1,
    true,
    '{"region": "South Asia", "subregions": [], "countries": ["PAK"], "maritime_zones": [], "map_geometry": null, "classification": {"primary_domain": "Political Stability", "secondary_domains": ["Conflict and Military", "Economic and Financial", "Cyber and Information Operations"], "intelligence_priority": "TIER_2", "strategic_impact": "HIGH", "forecast_horizon_days": 120}, "dependencies": {"related_warning_problems": [], "parent_problem": null, "child_problems": [], "upstream_effects": [], "downstream_effects": [], "supply_chain_impacts": [], "financial_impacts": []}, "ai_configuration": {"required_agents": ["political_stability", "conflict_monitoring", "economic_risk", "executive_briefing"], "required_data_sources": ["World Bank", "IMF", "GDELT", "ACLED", "Election authorities", "Government releases"], "required_indicator_classes": ["PRECURSOR", "ACCELERANT", "TRIGGER", "CONTRA"], "probability_model": "sews-logit-v1", "confidence_model": "sews-confidence-v1", "narrative_model_role": "EXPLANATION_ONLY", "deterministic_scoring_required": true, "contrary_evidence_required": true, "dark_feed_detection_required": true}, "outputs": {"bluf_template": "SEWS_BLUF_V1", "full_analysis_template": "SEWS_ANALYSIS_V1", "executive_summary_template": "SEWS_EXECUTIVE_V1", "dashboard_card_template": "SEWS_CARD_V1", "alert_template": "SEWS_ALERT_V1", "siam_briefing_template": "SEWS_SIAM_V1"}, "governance": {"analyst_review_required": false, "ledger_enabled": true, "forecast_verification_enabled": true, "brier_scoring_enabled": true, "immutable_assessment_versions": true}, "description": "Political confrontation in Pakistan produces sustained unrest, institutional paralysis, or an unconstitutional transfer of authority within 120 days."}'::jsonb,
    '{"probability_model": "sews-logit-v1", "confidence_model": "sews-confidence-v1", "default_states": ["DORMANT", "WATCH", "ADVISORY", "WARNING", "CRITICAL"], "hysteresis_enabled": true, "analyst_override_enabled": true}'::jsonb
)
on conflict (problem_key)
do update set
    title = excluded.title,
    hypothesis = excluded.hypothesis,
    horizon_days = excluded.horizon_days,
    base_rate = excluded.base_rate,
    severity_score = excluded.severity_score,
    version = excluded.version,
    active = excluded.active,
    exposure_map = excluded.exposure_map,
    transition_rules = excluded.transition_rules,
    updated_at = now();

insert into sews_warning_problems (
    problem_key,
    title,
    hypothesis,
    horizon_days,
    state,
    base_rate,
    severity_score,
    version,
    active,
    exposure_map,
    transition_rules
)
values (
    'WP-AFG-CROSS-BORDER-MILITANCY',
    'Afghanistan–Pakistan Cross-Border Militancy',
    'Militant activity originating from or linked to Afghanistan causes a significant escalation in cross-border attacks or interstate tensions within 90 days.',
    90,
    'DORMANT',
    0.3,
    80.0,
    1,
    true,
    '{"region": "South and Central Asia", "subregions": [], "countries": ["AFG", "PAK"], "maritime_zones": [], "map_geometry": null, "classification": {"primary_domain": "Conflict and Military", "secondary_domains": ["Political Stability", "Energy and Supply Chain", "Humanitarian and Public Health"], "intelligence_priority": "TIER_2", "strategic_impact": "HIGH", "forecast_horizon_days": 90}, "dependencies": {"related_warning_problems": [], "parent_problem": null, "child_problems": [], "upstream_effects": [], "downstream_effects": [], "supply_chain_impacts": [], "financial_impacts": []}, "ai_configuration": {"required_agents": ["conflict_monitoring", "political_stability", "energy_security", "executive_briefing"], "required_data_sources": ["GDELT", "Google News RSS", "ReliefWeb", "ACLED", "UN", "Government and defense releases"], "required_indicator_classes": ["PRECURSOR", "ACCELERANT", "TRIGGER", "CONTRA"], "probability_model": "sews-logit-v1", "confidence_model": "sews-confidence-v1", "narrative_model_role": "EXPLANATION_ONLY", "deterministic_scoring_required": true, "contrary_evidence_required": true, "dark_feed_detection_required": true}, "outputs": {"bluf_template": "SEWS_BLUF_V1", "full_analysis_template": "SEWS_ANALYSIS_V1", "executive_summary_template": "SEWS_EXECUTIVE_V1", "dashboard_card_template": "SEWS_CARD_V1", "alert_template": "SEWS_ALERT_V1", "siam_briefing_template": "SEWS_SIAM_V1"}, "governance": {"analyst_review_required": false, "ledger_enabled": true, "forecast_verification_enabled": true, "brier_scoring_enabled": true, "immutable_assessment_versions": true}, "description": "Militant activity originating from or linked to Afghanistan causes a significant escalation in cross-border attacks or interstate tensions within 90 days."}'::jsonb,
    '{"probability_model": "sews-logit-v1", "confidence_model": "sews-confidence-v1", "default_states": ["DORMANT", "WATCH", "ADVISORY", "WARNING", "CRITICAL"], "hysteresis_enabled": true, "analyst_override_enabled": true}'::jsonb
)
on conflict (problem_key)
do update set
    title = excluded.title,
    hypothesis = excluded.hypothesis,
    horizon_days = excluded.horizon_days,
    base_rate = excluded.base_rate,
    severity_score = excluded.severity_score,
    version = excluded.version,
    active = excluded.active,
    exposure_map = excluded.exposure_map,
    transition_rules = excluded.transition_rules,
    updated_at = now();

insert into sews_warning_problems (
    problem_key,
    title,
    hypothesis,
    horizon_days,
    state,
    base_rate,
    severity_score,
    version,
    active,
    exposure_map,
    transition_rules
)
values (
    'WP-SAHEL-REGIME-FAILURE',
    'Sahel Regime Failure or Coup Escalation',
    'A Sahel state experiences a coup attempt, regime collapse, or major loss of territorial control within 180 days.',
    180,
    'DORMANT',
    0.28,
    82.0,
    1,
    true,
    '{"region": "Sub-Saharan Africa", "subregions": [], "countries": ["MLI", "NER", "BFA", "TCD", "SDN"], "maritime_zones": [], "map_geometry": null, "classification": {"primary_domain": "Political Stability", "secondary_domains": ["Conflict and Military", "Economic and Financial", "Cyber and Information Operations"], "intelligence_priority": "TIER_2", "strategic_impact": "HIGH", "forecast_horizon_days": 180}, "dependencies": {"related_warning_problems": [], "parent_problem": null, "child_problems": [], "upstream_effects": [], "downstream_effects": [], "supply_chain_impacts": [], "financial_impacts": []}, "ai_configuration": {"required_agents": ["political_stability", "conflict_monitoring", "economic_risk", "executive_briefing"], "required_data_sources": ["World Bank", "IMF", "GDELT", "ACLED", "Election authorities", "Government releases"], "required_indicator_classes": ["PRECURSOR", "ACCELERANT", "TRIGGER", "CONTRA"], "probability_model": "sews-logit-v1", "confidence_model": "sews-confidence-v1", "narrative_model_role": "EXPLANATION_ONLY", "deterministic_scoring_required": true, "contrary_evidence_required": true, "dark_feed_detection_required": true}, "outputs": {"bluf_template": "SEWS_BLUF_V1", "full_analysis_template": "SEWS_ANALYSIS_V1", "executive_summary_template": "SEWS_EXECUTIVE_V1", "dashboard_card_template": "SEWS_CARD_V1", "alert_template": "SEWS_ALERT_V1", "siam_briefing_template": "SEWS_SIAM_V1"}, "governance": {"analyst_review_required": false, "ledger_enabled": true, "forecast_verification_enabled": true, "brier_scoring_enabled": true, "immutable_assessment_versions": true}, "description": "A Sahel state experiences a coup attempt, regime collapse, or major loss of territorial control within 180 days."}'::jsonb,
    '{"probability_model": "sews-logit-v1", "confidence_model": "sews-confidence-v1", "default_states": ["DORMANT", "WATCH", "ADVISORY", "WARNING", "CRITICAL"], "hysteresis_enabled": true, "analyst_override_enabled": true}'::jsonb
)
on conflict (problem_key)
do update set
    title = excluded.title,
    hypothesis = excluded.hypothesis,
    horizon_days = excluded.horizon_days,
    base_rate = excluded.base_rate,
    severity_score = excluded.severity_score,
    version = excluded.version,
    active = excluded.active,
    exposure_map = excluded.exposure_map,
    transition_rules = excluded.transition_rules,
    updated_at = now();

insert into sews_warning_problems (
    problem_key,
    title,
    hypothesis,
    horizon_days,
    state,
    base_rate,
    severity_score,
    version,
    active,
    exposure_map,
    transition_rules
)
values (
    'WP-RED-SEA-SHIPPING',
    'Red Sea Shipping Disruption',
    'Hostile activity or military escalation produces a material deterioration in commercial shipping through the Red Sea and Bab el-Mandeb within 60 days.',
    60,
    'DORMANT',
    0.35,
    86.0,
    1,
    true,
    '{"region": "Middle East and North Africa", "subregions": [], "countries": ["YEM", "DJI", "ERI", "SAU", "EGY"], "maritime_zones": ["Red Sea", "Bab el-Mandeb", "Gulf of Aden"], "map_geometry": null, "classification": {"primary_domain": "Energy and Supply Chain", "secondary_domains": ["Economic and Financial", "Conflict and Military", "Corporate Exposure"], "intelligence_priority": "TIER_1", "strategic_impact": "SEVERE", "forecast_horizon_days": 60}, "dependencies": {"related_warning_problems": ["WP-SUEZ-DISRUPTION", "WP-ENERGY-PRICE-SPIKE"], "parent_problem": null, "child_problems": [], "upstream_effects": [], "downstream_effects": [], "supply_chain_impacts": [], "financial_impacts": []}, "ai_configuration": {"required_agents": ["energy_security", "trade_sanctions", "supply_chain", "corporate_exposure", "executive_briefing"], "required_data_sources": ["EIA", "UN Comtrade", "AIS and maritime data", "Port authorities", "World Bank", "Commodity markets"], "required_indicator_classes": ["PRECURSOR", "ACCELERANT", "TRIGGER", "CONTRA"], "probability_model": "sews-logit-v1", "confidence_model": "sews-confidence-v1", "narrative_model_role": "EXPLANATION_ONLY", "deterministic_scoring_required": true, "contrary_evidence_required": true, "dark_feed_detection_required": true}, "outputs": {"bluf_template": "SEWS_BLUF_V1", "full_analysis_template": "SEWS_ANALYSIS_V1", "executive_summary_template": "SEWS_EXECUTIVE_V1", "dashboard_card_template": "SEWS_CARD_V1", "alert_template": "SEWS_ALERT_V1", "siam_briefing_template": "SEWS_SIAM_V1"}, "governance": {"analyst_review_required": false, "ledger_enabled": true, "forecast_verification_enabled": true, "brier_scoring_enabled": true, "immutable_assessment_versions": true}, "description": "Hostile activity or military escalation produces a material deterioration in commercial shipping through the Red Sea and Bab el-Mandeb within 60 days."}'::jsonb,
    '{"probability_model": "sews-logit-v1", "confidence_model": "sews-confidence-v1", "default_states": ["DORMANT", "WATCH", "ADVISORY", "WARNING", "CRITICAL"], "hysteresis_enabled": true, "analyst_override_enabled": true}'::jsonb
)
on conflict (problem_key)
do update set
    title = excluded.title,
    hypothesis = excluded.hypothesis,
    horizon_days = excluded.horizon_days,
    base_rate = excluded.base_rate,
    severity_score = excluded.severity_score,
    version = excluded.version,
    active = excluded.active,
    exposure_map = excluded.exposure_map,
    transition_rules = excluded.transition_rules,
    updated_at = now();

insert into sews_warning_problems (
    problem_key,
    title,
    hypothesis,
    horizon_days,
    state,
    base_rate,
    severity_score,
    version,
    active,
    exposure_map,
    transition_rules
)
values (
    'WP-HORMUZ-CLOSURE',
    'Strait of Hormuz Closure or Severe Disruption',
    'Military action, interdiction, mining, or coercive restrictions materially disrupt transit through the Strait of Hormuz within 90 days.',
    90,
    'DORMANT',
    0.1,
    97.0,
    1,
    true,
    '{"region": "Middle East and North Africa", "subregions": [], "countries": ["IRN", "OMN", "ARE", "SAU", "QAT"], "maritime_zones": ["Strait of Hormuz", "Persian Gulf", "Gulf of Oman"], "map_geometry": null, "classification": {"primary_domain": "Energy and Supply Chain", "secondary_domains": ["Economic and Financial", "Conflict and Military", "Corporate Exposure"], "intelligence_priority": "TIER_1", "strategic_impact": "CATASTROPHIC", "forecast_horizon_days": 90}, "dependencies": {"related_warning_problems": ["WP-ENERGY-PRICE-SPIKE", "WP-EM-SOVEREIGN-DEBT"], "parent_problem": null, "child_problems": [], "upstream_effects": [], "downstream_effects": [], "supply_chain_impacts": [], "financial_impacts": []}, "ai_configuration": {"required_agents": ["energy_security", "trade_sanctions", "supply_chain", "corporate_exposure", "executive_briefing"], "required_data_sources": ["EIA", "UN Comtrade", "AIS and maritime data", "Port authorities", "World Bank", "Commodity markets"], "required_indicator_classes": ["PRECURSOR", "ACCELERANT", "TRIGGER", "CONTRA"], "probability_model": "sews-logit-v1", "confidence_model": "sews-confidence-v1", "narrative_model_role": "EXPLANATION_ONLY", "deterministic_scoring_required": true, "contrary_evidence_required": true, "dark_feed_detection_required": true}, "outputs": {"bluf_template": "SEWS_BLUF_V1", "full_analysis_template": "SEWS_ANALYSIS_V1", "executive_summary_template": "SEWS_EXECUTIVE_V1", "dashboard_card_template": "SEWS_CARD_V1", "alert_template": "SEWS_ALERT_V1", "siam_briefing_template": "SEWS_SIAM_V1"}, "governance": {"analyst_review_required": false, "ledger_enabled": true, "forecast_verification_enabled": true, "brier_scoring_enabled": true, "immutable_assessment_versions": true}, "description": "Military action, interdiction, mining, or coercive restrictions materially disrupt transit through the Strait of Hormuz within 90 days."}'::jsonb,
    '{"probability_model": "sews-logit-v1", "confidence_model": "sews-confidence-v1", "default_states": ["DORMANT", "WATCH", "ADVISORY", "WARNING", "CRITICAL"], "hysteresis_enabled": true, "analyst_override_enabled": true}'::jsonb
)
on conflict (problem_key)
do update set
    title = excluded.title,
    hypothesis = excluded.hypothesis,
    horizon_days = excluded.horizon_days,
    base_rate = excluded.base_rate,
    severity_score = excluded.severity_score,
    version = excluded.version,
    active = excluded.active,
    exposure_map = excluded.exposure_map,
    transition_rules = excluded.transition_rules,
    updated_at = now();

insert into sews_warning_problems (
    problem_key,
    title,
    hypothesis,
    horizon_days,
    state,
    base_rate,
    severity_score,
    version,
    active,
    exposure_map,
    transition_rules
)
values (
    'WP-SUEZ-DISRUPTION',
    'Suez Canal Operational Disruption',
    'Security, infrastructure, labor, or navigation conditions materially reduce Suez Canal throughput within 90 days.',
    90,
    'DORMANT',
    0.12,
    83.0,
    1,
    true,
    '{"region": "Middle East and North Africa", "subregions": [], "countries": ["EGY"], "maritime_zones": ["Suez Canal", "Red Sea", "Eastern Mediterranean"], "map_geometry": null, "classification": {"primary_domain": "Energy and Supply Chain", "secondary_domains": ["Economic and Financial", "Conflict and Military", "Corporate Exposure"], "intelligence_priority": "TIER_2", "strategic_impact": "HIGH", "forecast_horizon_days": 90}, "dependencies": {"related_warning_problems": [], "parent_problem": null, "child_problems": [], "upstream_effects": [], "downstream_effects": [], "supply_chain_impacts": [], "financial_impacts": []}, "ai_configuration": {"required_agents": ["energy_security", "trade_sanctions", "supply_chain", "corporate_exposure", "executive_briefing"], "required_data_sources": ["EIA", "UN Comtrade", "AIS and maritime data", "Port authorities", "World Bank", "Commodity markets"], "required_indicator_classes": ["PRECURSOR", "ACCELERANT", "TRIGGER", "CONTRA"], "probability_model": "sews-logit-v1", "confidence_model": "sews-confidence-v1", "narrative_model_role": "EXPLANATION_ONLY", "deterministic_scoring_required": true, "contrary_evidence_required": true, "dark_feed_detection_required": true}, "outputs": {"bluf_template": "SEWS_BLUF_V1", "full_analysis_template": "SEWS_ANALYSIS_V1", "executive_summary_template": "SEWS_EXECUTIVE_V1", "dashboard_card_template": "SEWS_CARD_V1", "alert_template": "SEWS_ALERT_V1", "siam_briefing_template": "SEWS_SIAM_V1"}, "governance": {"analyst_review_required": false, "ledger_enabled": true, "forecast_verification_enabled": true, "brier_scoring_enabled": true, "immutable_assessment_versions": true}, "description": "Security, infrastructure, labor, or navigation conditions materially reduce Suez Canal throughput within 90 days."}'::jsonb,
    '{"probability_model": "sews-logit-v1", "confidence_model": "sews-confidence-v1", "default_states": ["DORMANT", "WATCH", "ADVISORY", "WARNING", "CRITICAL"], "hysteresis_enabled": true, "analyst_override_enabled": true}'::jsonb
)
on conflict (problem_key)
do update set
    title = excluded.title,
    hypothesis = excluded.hypothesis,
    horizon_days = excluded.horizon_days,
    base_rate = excluded.base_rate,
    severity_score = excluded.severity_score,
    version = excluded.version,
    active = excluded.active,
    exposure_map = excluded.exposure_map,
    transition_rules = excluded.transition_rules,
    updated_at = now();

insert into sews_warning_problems (
    problem_key,
    title,
    hypothesis,
    horizon_days,
    state,
    base_rate,
    severity_score,
    version,
    active,
    exposure_map,
    transition_rules
)
values (
    'WP-SEMICONDUCTOR-SHOCK',
    'Global Semiconductor Supply Shock',
    'Geopolitical, industrial, environmental, or logistical disruption causes a material global semiconductor supply shock within 180 days.',
    180,
    'DORMANT',
    0.16,
    91.0,
    1,
    true,
    '{"region": "Global", "subregions": [], "countries": ["TWN", "CHN", "KOR", "JPN", "USA", "NLD"], "maritime_zones": ["Taiwan Strait", "South China Sea", "East China Sea"], "map_geometry": null, "classification": {"primary_domain": "Energy and Supply Chain", "secondary_domains": ["Economic and Financial", "Conflict and Military", "Corporate Exposure"], "intelligence_priority": "TIER_1", "strategic_impact": "SEVERE", "forecast_horizon_days": 180}, "dependencies": {"related_warning_problems": ["WP-TWN-BLOCKADE", "WP-CHN-FINANCIAL-STRESS"], "parent_problem": null, "child_problems": [], "upstream_effects": [], "downstream_effects": [], "supply_chain_impacts": [], "financial_impacts": []}, "ai_configuration": {"required_agents": ["energy_security", "trade_sanctions", "supply_chain", "corporate_exposure", "executive_briefing"], "required_data_sources": ["EIA", "UN Comtrade", "AIS and maritime data", "Port authorities", "World Bank", "Commodity markets"], "required_indicator_classes": ["PRECURSOR", "ACCELERANT", "TRIGGER", "CONTRA"], "probability_model": "sews-logit-v1", "confidence_model": "sews-confidence-v1", "narrative_model_role": "EXPLANATION_ONLY", "deterministic_scoring_required": true, "contrary_evidence_required": true, "dark_feed_detection_required": true}, "outputs": {"bluf_template": "SEWS_BLUF_V1", "full_analysis_template": "SEWS_ANALYSIS_V1", "executive_summary_template": "SEWS_EXECUTIVE_V1", "dashboard_card_template": "SEWS_CARD_V1", "alert_template": "SEWS_ALERT_V1", "siam_briefing_template": "SEWS_SIAM_V1"}, "governance": {"analyst_review_required": false, "ledger_enabled": true, "forecast_verification_enabled": true, "brier_scoring_enabled": true, "immutable_assessment_versions": true}, "description": "Geopolitical, industrial, environmental, or logistical disruption causes a material global semiconductor supply shock within 180 days."}'::jsonb,
    '{"probability_model": "sews-logit-v1", "confidence_model": "sews-confidence-v1", "default_states": ["DORMANT", "WATCH", "ADVISORY", "WARNING", "CRITICAL"], "hysteresis_enabled": true, "analyst_override_enabled": true}'::jsonb
)
on conflict (problem_key)
do update set
    title = excluded.title,
    hypothesis = excluded.hypothesis,
    horizon_days = excluded.horizon_days,
    base_rate = excluded.base_rate,
    severity_score = excluded.severity_score,
    version = excluded.version,
    active = excluded.active,
    exposure_map = excluded.exposure_map,
    transition_rules = excluded.transition_rules,
    updated_at = now();

insert into sews_warning_problems (
    problem_key,
    title,
    hypothesis,
    horizon_days,
    state,
    base_rate,
    severity_score,
    version,
    active,
    exposure_map,
    transition_rules
)
values (
    'WP-CRITICAL-MINERALS-RESTRICTION',
    'Critical Minerals Export Restrictions',
    'A major producer imposes new restrictions affecting global access to critical minerals or processing capacity within 180 days.',
    180,
    'DORMANT',
    0.22,
    80.0,
    1,
    true,
    '{"region": "Global", "subregions": [], "countries": ["CHN", "IDN", "COD", "CHL", "AUS"], "maritime_zones": [], "map_geometry": null, "classification": {"primary_domain": "Energy and Supply Chain", "secondary_domains": ["Economic and Financial", "Conflict and Military", "Corporate Exposure"], "intelligence_priority": "TIER_2", "strategic_impact": "HIGH", "forecast_horizon_days": 180}, "dependencies": {"related_warning_problems": [], "parent_problem": null, "child_problems": [], "upstream_effects": [], "downstream_effects": [], "supply_chain_impacts": [], "financial_impacts": []}, "ai_configuration": {"required_agents": ["energy_security", "trade_sanctions", "supply_chain", "corporate_exposure", "executive_briefing"], "required_data_sources": ["EIA", "UN Comtrade", "AIS and maritime data", "Port authorities", "World Bank", "Commodity markets"], "required_indicator_classes": ["PRECURSOR", "ACCELERANT", "TRIGGER", "CONTRA"], "probability_model": "sews-logit-v1", "confidence_model": "sews-confidence-v1", "narrative_model_role": "EXPLANATION_ONLY", "deterministic_scoring_required": true, "contrary_evidence_required": true, "dark_feed_detection_required": true}, "outputs": {"bluf_template": "SEWS_BLUF_V1", "full_analysis_template": "SEWS_ANALYSIS_V1", "executive_summary_template": "SEWS_EXECUTIVE_V1", "dashboard_card_template": "SEWS_CARD_V1", "alert_template": "SEWS_ALERT_V1", "siam_briefing_template": "SEWS_SIAM_V1"}, "governance": {"analyst_review_required": false, "ledger_enabled": true, "forecast_verification_enabled": true, "brier_scoring_enabled": true, "immutable_assessment_versions": true}, "description": "A major producer imposes new restrictions affecting global access to critical minerals or processing capacity within 180 days."}'::jsonb,
    '{"probability_model": "sews-logit-v1", "confidence_model": "sews-confidence-v1", "default_states": ["DORMANT", "WATCH", "ADVISORY", "WARNING", "CRITICAL"], "hysteresis_enabled": true, "analyst_override_enabled": true}'::jsonb
)
on conflict (problem_key)
do update set
    title = excluded.title,
    hypothesis = excluded.hypothesis,
    horizon_days = excluded.horizon_days,
    base_rate = excluded.base_rate,
    severity_score = excluded.severity_score,
    version = excluded.version,
    active = excluded.active,
    exposure_map = excluded.exposure_map,
    transition_rules = excluded.transition_rules,
    updated_at = now();

insert into sews_warning_problems (
    problem_key,
    title,
    hypothesis,
    horizon_days,
    state,
    base_rate,
    severity_score,
    version,
    active,
    exposure_map,
    transition_rules
)
values (
    'WP-ENERGY-PRICE-SPIKE',
    'Global Energy Price Spike',
    'A geopolitical or supply-side shock causes a sustained and material increase in global oil or natural-gas prices within 90 days.',
    90,
    'DORMANT',
    0.24,
    85.0,
    1,
    true,
    '{"region": "Global", "subregions": [], "countries": ["SAU", "IRN", "RUS", "QAT", "USA"], "maritime_zones": [], "map_geometry": null, "classification": {"primary_domain": "Economic and Financial", "secondary_domains": ["Political Stability", "Energy and Supply Chain", "Corporate Exposure"], "intelligence_priority": "TIER_2", "strategic_impact": "SEVERE", "forecast_horizon_days": 90}, "dependencies": {"related_warning_problems": [], "parent_problem": null, "child_problems": [], "upstream_effects": [], "downstream_effects": [], "supply_chain_impacts": [], "financial_impacts": []}, "ai_configuration": {"required_agents": ["economic_risk", "trade_sanctions", "financial_risk", "corporate_exposure", "executive_briefing"], "required_data_sources": ["IMF", "World Bank", "FRED", "OECD", "Central banks", "Market data"], "required_indicator_classes": ["PRECURSOR", "ACCELERANT", "TRIGGER", "CONTRA"], "probability_model": "sews-logit-v1", "confidence_model": "sews-confidence-v1", "narrative_model_role": "EXPLANATION_ONLY", "deterministic_scoring_required": true, "contrary_evidence_required": true, "dark_feed_detection_required": true}, "outputs": {"bluf_template": "SEWS_BLUF_V1", "full_analysis_template": "SEWS_ANALYSIS_V1", "executive_summary_template": "SEWS_EXECUTIVE_V1", "dashboard_card_template": "SEWS_CARD_V1", "alert_template": "SEWS_ALERT_V1", "siam_briefing_template": "SEWS_SIAM_V1"}, "governance": {"analyst_review_required": false, "ledger_enabled": true, "forecast_verification_enabled": true, "brier_scoring_enabled": true, "immutable_assessment_versions": true}, "description": "A geopolitical or supply-side shock causes a sustained and material increase in global oil or natural-gas prices within 90 days."}'::jsonb,
    '{"probability_model": "sews-logit-v1", "confidence_model": "sews-confidence-v1", "default_states": ["DORMANT", "WATCH", "ADVISORY", "WARNING", "CRITICAL"], "hysteresis_enabled": true, "analyst_override_enabled": true}'::jsonb
)
on conflict (problem_key)
do update set
    title = excluded.title,
    hypothesis = excluded.hypothesis,
    horizon_days = excluded.horizon_days,
    base_rate = excluded.base_rate,
    severity_score = excluded.severity_score,
    version = excluded.version,
    active = excluded.active,
    exposure_map = excluded.exposure_map,
    transition_rules = excluded.transition_rules,
    updated_at = now();

insert into sews_warning_problems (
    problem_key,
    title,
    hypothesis,
    horizon_days,
    state,
    base_rate,
    severity_score,
    version,
    active,
    exposure_map,
    transition_rules
)
values (
    'WP-EM-SOVEREIGN-DEBT',
    'Emerging-Market Sovereign Debt Distress',
    'One or more vulnerable emerging-market governments enter default, restructuring, or acute external-financing distress within 180 days.',
    180,
    'DORMANT',
    0.26,
    79.0,
    1,
    true,
    '{"region": "Global", "subregions": [], "countries": ["ARG", "EGY", "PAK", "GHA", "ZMB", "ETH"], "maritime_zones": [], "map_geometry": null, "classification": {"primary_domain": "Economic and Financial", "secondary_domains": ["Political Stability", "Energy and Supply Chain", "Corporate Exposure"], "intelligence_priority": "TIER_2", "strategic_impact": "HIGH", "forecast_horizon_days": 180}, "dependencies": {"related_warning_problems": [], "parent_problem": null, "child_problems": [], "upstream_effects": [], "downstream_effects": [], "supply_chain_impacts": [], "financial_impacts": []}, "ai_configuration": {"required_agents": ["economic_risk", "trade_sanctions", "financial_risk", "corporate_exposure", "executive_briefing"], "required_data_sources": ["IMF", "World Bank", "FRED", "OECD", "Central banks", "Market data"], "required_indicator_classes": ["PRECURSOR", "ACCELERANT", "TRIGGER", "CONTRA"], "probability_model": "sews-logit-v1", "confidence_model": "sews-confidence-v1", "narrative_model_role": "EXPLANATION_ONLY", "deterministic_scoring_required": true, "contrary_evidence_required": true, "dark_feed_detection_required": true}, "outputs": {"bluf_template": "SEWS_BLUF_V1", "full_analysis_template": "SEWS_ANALYSIS_V1", "executive_summary_template": "SEWS_EXECUTIVE_V1", "dashboard_card_template": "SEWS_CARD_V1", "alert_template": "SEWS_ALERT_V1", "siam_briefing_template": "SEWS_SIAM_V1"}, "governance": {"analyst_review_required": false, "ledger_enabled": true, "forecast_verification_enabled": true, "brier_scoring_enabled": true, "immutable_assessment_versions": true}, "description": "One or more vulnerable emerging-market governments enter default, restructuring, or acute external-financing distress within 180 days."}'::jsonb,
    '{"probability_model": "sews-logit-v1", "confidence_model": "sews-confidence-v1", "default_states": ["DORMANT", "WATCH", "ADVISORY", "WARNING", "CRITICAL"], "hysteresis_enabled": true, "analyst_override_enabled": true}'::jsonb
)
on conflict (problem_key)
do update set
    title = excluded.title,
    hypothesis = excluded.hypothesis,
    horizon_days = excluded.horizon_days,
    base_rate = excluded.base_rate,
    severity_score = excluded.severity_score,
    version = excluded.version,
    active = excluded.active,
    exposure_map = excluded.exposure_map,
    transition_rules = excluded.transition_rules,
    updated_at = now();

insert into sews_warning_problems (
    problem_key,
    title,
    hypothesis,
    horizon_days,
    state,
    base_rate,
    severity_score,
    version,
    active,
    exposure_map,
    transition_rules
)
values (
    'WP-CHN-FINANCIAL-STRESS',
    'China Financial and Property Stress',
    'Property-sector, local-government, or banking stress in China causes a material deterioration in domestic or regional financial conditions within 180 days.',
    180,
    'DORMANT',
    0.3,
    87.0,
    1,
    true,
    '{"region": "Indo-Pacific", "subregions": [], "countries": ["CHN", "HKG"], "maritime_zones": [], "map_geometry": null, "classification": {"primary_domain": "Economic and Financial", "secondary_domains": ["Political Stability", "Energy and Supply Chain", "Corporate Exposure"], "intelligence_priority": "TIER_2", "strategic_impact": "SEVERE", "forecast_horizon_days": 180}, "dependencies": {"related_warning_problems": [], "parent_problem": null, "child_problems": [], "upstream_effects": [], "downstream_effects": [], "supply_chain_impacts": [], "financial_impacts": []}, "ai_configuration": {"required_agents": ["economic_risk", "trade_sanctions", "financial_risk", "corporate_exposure", "executive_briefing"], "required_data_sources": ["IMF", "World Bank", "FRED", "OECD", "Central banks", "Market data"], "required_indicator_classes": ["PRECURSOR", "ACCELERANT", "TRIGGER", "CONTRA"], "probability_model": "sews-logit-v1", "confidence_model": "sews-confidence-v1", "narrative_model_role": "EXPLANATION_ONLY", "deterministic_scoring_required": true, "contrary_evidence_required": true, "dark_feed_detection_required": true}, "outputs": {"bluf_template": "SEWS_BLUF_V1", "full_analysis_template": "SEWS_ANALYSIS_V1", "executive_summary_template": "SEWS_EXECUTIVE_V1", "dashboard_card_template": "SEWS_CARD_V1", "alert_template": "SEWS_ALERT_V1", "siam_briefing_template": "SEWS_SIAM_V1"}, "governance": {"analyst_review_required": false, "ledger_enabled": true, "forecast_verification_enabled": true, "brier_scoring_enabled": true, "immutable_assessment_versions": true}, "description": "Property-sector, local-government, or banking stress in China causes a material deterioration in domestic or regional financial conditions within 180 days."}'::jsonb,
    '{"probability_model": "sews-logit-v1", "confidence_model": "sews-confidence-v1", "default_states": ["DORMANT", "WATCH", "ADVISORY", "WARNING", "CRITICAL"], "hysteresis_enabled": true, "analyst_override_enabled": true}'::jsonb
)
on conflict (problem_key)
do update set
    title = excluded.title,
    hypothesis = excluded.hypothesis,
    horizon_days = excluded.horizon_days,
    base_rate = excluded.base_rate,
    severity_score = excluded.severity_score,
    version = excluded.version,
    active = excluded.active,
    exposure_map = excluded.exposure_map,
    transition_rules = excluded.transition_rules,
    updated_at = now();

insert into sews_warning_problems (
    problem_key,
    title,
    hypothesis,
    horizon_days,
    state,
    base_rate,
    severity_score,
    version,
    active,
    exposure_map,
    transition_rules
)
values (
    'WP-CRITICAL-INFRA-CYBER',
    'Systemic Cyberattack on Critical Infrastructure',
    'A state-linked or sophisticated non-state actor causes a multi-sector critical-infrastructure disruption within 90 days.',
    90,
    'DORMANT',
    0.14,
    93.0,
    1,
    true,
    '{"region": "Global", "subregions": [], "countries": [], "maritime_zones": [], "map_geometry": null, "classification": {"primary_domain": "Cyber and Information Operations", "secondary_domains": ["Political Stability", "Conflict and Military", "Economic and Financial"], "intelligence_priority": "TIER_1", "strategic_impact": "CATASTROPHIC", "forecast_horizon_days": 90}, "dependencies": {"related_warning_problems": [], "parent_problem": null, "child_problems": [], "upstream_effects": [], "downstream_effects": [], "supply_chain_impacts": [], "financial_impacts": []}, "ai_configuration": {"required_agents": ["cyber_information_operations", "conflict_monitoring", "political_stability", "executive_briefing"], "required_data_sources": ["CISA", "National CERTs", "Vendor threat intelligence", "Government advisories", "GDELT", "Open-source reporting"], "required_indicator_classes": ["PRECURSOR", "ACCELERANT", "TRIGGER", "CONTRA"], "probability_model": "sews-logit-v1", "confidence_model": "sews-confidence-v1", "narrative_model_role": "EXPLANATION_ONLY", "deterministic_scoring_required": true, "contrary_evidence_required": true, "dark_feed_detection_required": true}, "outputs": {"bluf_template": "SEWS_BLUF_V1", "full_analysis_template": "SEWS_ANALYSIS_V1", "executive_summary_template": "SEWS_EXECUTIVE_V1", "dashboard_card_template": "SEWS_CARD_V1", "alert_template": "SEWS_ALERT_V1", "siam_briefing_template": "SEWS_SIAM_V1"}, "governance": {"analyst_review_required": false, "ledger_enabled": true, "forecast_verification_enabled": true, "brier_scoring_enabled": true, "immutable_assessment_versions": true}, "description": "A state-linked or sophisticated non-state actor causes a multi-sector critical-infrastructure disruption within 90 days."}'::jsonb,
    '{"probability_model": "sews-logit-v1", "confidence_model": "sews-confidence-v1", "default_states": ["DORMANT", "WATCH", "ADVISORY", "WARNING", "CRITICAL"], "hysteresis_enabled": true, "analyst_override_enabled": true}'::jsonb
)
on conflict (problem_key)
do update set
    title = excluded.title,
    hypothesis = excluded.hypothesis,
    horizon_days = excluded.horizon_days,
    base_rate = excluded.base_rate,
    severity_score = excluded.severity_score,
    version = excluded.version,
    active = excluded.active,
    exposure_map = excluded.exposure_map,
    transition_rules = excluded.transition_rules,
    updated_at = now();

insert into sews_warning_problems (
    problem_key,
    title,
    hypothesis,
    horizon_days,
    state,
    base_rate,
    severity_score,
    version,
    active,
    exposure_map,
    transition_rules
)
values (
    'WP-ELECTION-INTERFERENCE',
    'Major Election Interference Campaign',
    'A coordinated foreign or domestic information operation materially disrupts electoral confidence or administration within 120 days.',
    120,
    'DORMANT',
    0.32,
    75.0,
    1,
    true,
    '{"region": "Global", "subregions": [], "countries": [], "maritime_zones": [], "map_geometry": null, "classification": {"primary_domain": "Cyber and Information Operations", "secondary_domains": ["Political Stability", "Conflict and Military", "Economic and Financial"], "intelligence_priority": "TIER_2", "strategic_impact": "HIGH", "forecast_horizon_days": 120}, "dependencies": {"related_warning_problems": [], "parent_problem": null, "child_problems": [], "upstream_effects": [], "downstream_effects": [], "supply_chain_impacts": [], "financial_impacts": []}, "ai_configuration": {"required_agents": ["cyber_information_operations", "conflict_monitoring", "political_stability", "executive_briefing"], "required_data_sources": ["CISA", "National CERTs", "Vendor threat intelligence", "Government advisories", "GDELT", "Open-source reporting"], "required_indicator_classes": ["PRECURSOR", "ACCELERANT", "TRIGGER", "CONTRA"], "probability_model": "sews-logit-v1", "confidence_model": "sews-confidence-v1", "narrative_model_role": "EXPLANATION_ONLY", "deterministic_scoring_required": true, "contrary_evidence_required": true, "dark_feed_detection_required": true}, "outputs": {"bluf_template": "SEWS_BLUF_V1", "full_analysis_template": "SEWS_ANALYSIS_V1", "executive_summary_template": "SEWS_EXECUTIVE_V1", "dashboard_card_template": "SEWS_CARD_V1", "alert_template": "SEWS_ALERT_V1", "siam_briefing_template": "SEWS_SIAM_V1"}, "governance": {"analyst_review_required": false, "ledger_enabled": true, "forecast_verification_enabled": true, "brier_scoring_enabled": true, "immutable_assessment_versions": true}, "description": "A coordinated foreign or domestic information operation materially disrupts electoral confidence or administration within 120 days."}'::jsonb,
    '{"probability_model": "sews-logit-v1", "confidence_model": "sews-confidence-v1", "default_states": ["DORMANT", "WATCH", "ADVISORY", "WARNING", "CRITICAL"], "hysteresis_enabled": true, "analyst_override_enabled": true}'::jsonb
)
on conflict (problem_key)
do update set
    title = excluded.title,
    hypothesis = excluded.hypothesis,
    horizon_days = excluded.horizon_days,
    base_rate = excluded.base_rate,
    severity_score = excluded.severity_score,
    version = excluded.version,
    active = excluded.active,
    exposure_map = excluded.exposure_map,
    transition_rules = excluded.transition_rules,
    updated_at = now();

insert into sews_warning_problems (
    problem_key,
    title,
    hypothesis,
    horizon_days,
    state,
    base_rate,
    severity_score,
    version,
    active,
    exposure_map,
    transition_rules
)
values (
    'WP-FOOD-SECURITY-SHOCK',
    'Food-Security Shock in Fragile States',
    'Conflict, climate, trade restrictions, or price increases create acute food-security deterioration across one or more fragile states within 180 days.',
    180,
    'DORMANT',
    0.38,
    88.0,
    1,
    true,
    '{"region": "Global", "subregions": [], "countries": ["SDN", "SOM", "ETH", "YEM", "AFG", "HTI"], "maritime_zones": [], "map_geometry": null, "classification": {"primary_domain": "Humanitarian and Public Health", "secondary_domains": ["Political Stability", "Conflict and Military", "Economic and Financial"], "intelligence_priority": "TIER_2", "strategic_impact": "SEVERE", "forecast_horizon_days": 180}, "dependencies": {"related_warning_problems": ["WP-ENERGY-PRICE-SPIKE", "WP-EM-SOVEREIGN-DEBT"], "parent_problem": null, "child_problems": [], "upstream_effects": [], "downstream_effects": [], "supply_chain_impacts": [], "financial_impacts": []}, "ai_configuration": {"required_agents": ["humanitarian_monitoring", "political_stability", "economic_risk", "executive_briefing"], "required_data_sources": ["WHO", "ReliefWeb", "WFP", "FAO", "UNHCR", "World Bank"], "required_indicator_classes": ["PRECURSOR", "ACCELERANT", "TRIGGER", "CONTRA"], "probability_model": "sews-logit-v1", "confidence_model": "sews-confidence-v1", "narrative_model_role": "EXPLANATION_ONLY", "deterministic_scoring_required": true, "contrary_evidence_required": true, "dark_feed_detection_required": true}, "outputs": {"bluf_template": "SEWS_BLUF_V1", "full_analysis_template": "SEWS_ANALYSIS_V1", "executive_summary_template": "SEWS_EXECUTIVE_V1", "dashboard_card_template": "SEWS_CARD_V1", "alert_template": "SEWS_ALERT_V1", "siam_briefing_template": "SEWS_SIAM_V1"}, "governance": {"analyst_review_required": false, "ledger_enabled": true, "forecast_verification_enabled": true, "brier_scoring_enabled": true, "immutable_assessment_versions": true}, "description": "Conflict, climate, trade restrictions, or price increases create acute food-security deterioration across one or more fragile states within 180 days."}'::jsonb,
    '{"probability_model": "sews-logit-v1", "confidence_model": "sews-confidence-v1", "default_states": ["DORMANT", "WATCH", "ADVISORY", "WARNING", "CRITICAL"], "hysteresis_enabled": true, "analyst_override_enabled": true}'::jsonb
)
on conflict (problem_key)
do update set
    title = excluded.title,
    hypothesis = excluded.hypothesis,
    horizon_days = excluded.horizon_days,
    base_rate = excluded.base_rate,
    severity_score = excluded.severity_score,
    version = excluded.version,
    active = excluded.active,
    exposure_map = excluded.exposure_map,
    transition_rules = excluded.transition_rules,
    updated_at = now();

insert into sews_warning_problems (
    problem_key,
    title,
    hypothesis,
    horizon_days,
    state,
    base_rate,
    severity_score,
    version,
    active,
    exposure_map,
    transition_rules
)
values (
    'WP-OUTBREAK-CROSS-BORDER',
    'Cross-Border Infectious Disease Outbreak',
    'An infectious-disease event produces sustained cross-border transmission and significant public-health or economic disruption within 180 days.',
    180,
    'DORMANT',
    0.12,
    90.0,
    1,
    true,
    '{"region": "Global", "subregions": [], "countries": [], "maritime_zones": [], "map_geometry": null, "classification": {"primary_domain": "Humanitarian and Public Health", "secondary_domains": ["Political Stability", "Conflict and Military", "Economic and Financial"], "intelligence_priority": "TIER_2", "strategic_impact": "SEVERE", "forecast_horizon_days": 180}, "dependencies": {"related_warning_problems": [], "parent_problem": null, "child_problems": [], "upstream_effects": [], "downstream_effects": [], "supply_chain_impacts": [], "financial_impacts": []}, "ai_configuration": {"required_agents": ["humanitarian_monitoring", "political_stability", "economic_risk", "executive_briefing"], "required_data_sources": ["WHO", "ReliefWeb", "WFP", "FAO", "UNHCR", "World Bank"], "required_indicator_classes": ["PRECURSOR", "ACCELERANT", "TRIGGER", "CONTRA"], "probability_model": "sews-logit-v1", "confidence_model": "sews-confidence-v1", "narrative_model_role": "EXPLANATION_ONLY", "deterministic_scoring_required": true, "contrary_evidence_required": true, "dark_feed_detection_required": true}, "outputs": {"bluf_template": "SEWS_BLUF_V1", "full_analysis_template": "SEWS_ANALYSIS_V1", "executive_summary_template": "SEWS_EXECUTIVE_V1", "dashboard_card_template": "SEWS_CARD_V1", "alert_template": "SEWS_ALERT_V1", "siam_briefing_template": "SEWS_SIAM_V1"}, "governance": {"analyst_review_required": false, "ledger_enabled": true, "forecast_verification_enabled": true, "brier_scoring_enabled": true, "immutable_assessment_versions": true}, "description": "An infectious-disease event produces sustained cross-border transmission and significant public-health or economic disruption within 180 days."}'::jsonb,
    '{"probability_model": "sews-logit-v1", "confidence_model": "sews-confidence-v1", "default_states": ["DORMANT", "WATCH", "ADVISORY", "WARNING", "CRITICAL"], "hysteresis_enabled": true, "analyst_override_enabled": true}'::jsonb
)
on conflict (problem_key)
do update set
    title = excluded.title,
    hypothesis = excluded.hypothesis,
    horizon_days = excluded.horizon_days,
    base_rate = excluded.base_rate,
    severity_score = excluded.severity_score,
    version = excluded.version,
    active = excluded.active,
    exposure_map = excluded.exposure_map,
    transition_rules = excluded.transition_rules,
    updated_at = now();

