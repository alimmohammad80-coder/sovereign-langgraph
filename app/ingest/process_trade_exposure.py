import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
)


def score_exposure(value):
    if value is None:
        return 50, "Guarded"

    value = float(value)

    if value >= 10_000_000_000:
        return 85, "Critical"
    if value >= 1_000_000_000:
        return 72, "High"
    if value >= 100_000_000:
        return 60, "Elevated"
    return 45, "Guarded"


def decision_support(commodity_name, score):
    if score >= 80:
        return f"Critical exposure in {commodity_name}. Assess alternative suppliers, rerouting options, inventory buffers, and sanctions/chokepoint risk."
    if score >= 70:
        return f"High exposure in {commodity_name}. Monitor disruption signals and identify backup trade routes."
    if score >= 60:
        return f"Elevated exposure in {commodity_name}. Maintain watchlist and review supplier concentration."
    return f"Guarded exposure in {commodity_name}. Continue baseline monitoring."


def run_processor(limit=500):
    rows = (
        supabase
        .table("sc_raw_trade_flows")
        .select("*")
        .limit(limit)
        .execute()
        .data or []
    )

    output = []

    for row in rows:
        score, level = score_exposure(row.get("trade_value_usd"))

        output.append({
            "commodity_code": row.get("commodity_code"),
            "commodity_name": row.get("commodity_name"),
            "reporter_country": row.get("reporter_country"),
            "partner_country": row.get("partner_country"),
            "reporter_iso3": row.get("reporter_iso3"),
            "partner_iso3": row.get("partner_iso3"),
            "trade_flow": row.get("trade_flow"),
            "total_trade_value_usd": row.get("trade_value_usd"),
            "total_weight_kg": row.get("net_weight_kg"),
            "period": row.get("period"),
            "exposure_score": score,
            "exposure_level": level,
            "decision_support": decision_support(row.get("commodity_name"), score)
        })

    if output:
        supabase.table("sc_trade_exposure_summary").insert(output).execute()

    print({
        "status": "success",
        "records_processed": len(output)
    })


if __name__ == "__main__":
    run_processor()
