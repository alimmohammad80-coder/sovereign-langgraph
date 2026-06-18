import os
import uuid
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

COMTRADE_BASE_URL = "https://comtradeapi.un.org/data/v1/get/C/A/HS"


STARTER_COMMODITIES = [
    {"code": "2709", "name": "Crude petroleum oils"},
    {"code": "2711", "name": "Petroleum gases and LNG"},
    {"code": "8542", "name": "Electronic integrated circuits / semiconductors"},
    {"code": "1001", "name": "Wheat and meslin"},
    {"code": "2603", "name": "Copper ores and concentrates"},
    {"code": "8507", "name": "Electric accumulators / lithium-ion batteries"},
]


def create_pipeline_run():
    run_id = str(uuid.uuid4())

    supabase.table("sc_pipeline_runs").insert({
        "id": run_id,
        "pipeline_name": "un_comtrade_trade_flows",
        "status": "running",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "records_processed": 0,
        "errors": []
    }).execute()

    return run_id


def complete_pipeline_run(run_id, status, records_processed, errors=None):
    supabase.table("sc_pipeline_runs").update({
        "status": status,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "records_processed": records_processed,
        "errors": errors or []
    }).eq("id", run_id).execute()


def fetch_comtrade_data(commodity_code, period="2023", reporter="all", partner="all"):
    params = {
        "cmdCode": commodity_code,
        "period": period,
        "reporterCode": reporter,
        "partnerCode": partner,
        "flowCode": "X,M",
        "includeDesc": "true"
    }

    response = requests.get(COMTRADE_BASE_URL, params=params, timeout=45)
    response.raise_for_status()
    return response.json()


def normalize_record(record, commodity_code, commodity_name, run_id):
    return {
        "source_id": "un_comtrade",
        "pipeline_run_id": run_id,
        "reporter_country": record.get("reporterDesc"),
        "partner_country": record.get("partnerDesc"),
        "reporter_iso3": record.get("reporterISO"),
        "partner_iso3": record.get("partnerISO"),
        "commodity_code": commodity_code,
        "commodity_name": commodity_name,
        "trade_flow": record.get("flowDesc"),
        "trade_value_usd": record.get("primaryValue"),
        "net_weight_kg": record.get("netWgt"),
        "quantity": record.get("qty"),
        "period": str(record.get("period")),
        "raw_payload": record,
        "ingested_at": datetime.now(timezone.utc).isoformat()
    }


def run_comtrade_ingestion(period="2023"):
    run_id = create_pipeline_run()
    total_records = 0
    errors = []

    for commodity in STARTER_COMMODITIES:
        try:
            payload = fetch_comtrade_data(
                commodity_code=commodity["code"],
                period=period
            )

            records = payload.get("data", [])

            rows = [
                normalize_record(
                    record=record,
                    commodity_code=commodity["code"],
                    commodity_name=commodity["name"],
                    run_id=run_id
                )
                for record in records
            ]

            if rows:
                supabase.table("sc_raw_trade_flows").insert(rows[:500]).execute()
                total_records += len(rows[:500])

        except Exception as e:
            errors.append({
                "commodity_code": commodity["code"],
                "error": str(e)
            })

    final_status = "completed" if not errors else "completed_with_errors"
    complete_pipeline_run(run_id, final_status, total_records, errors)

    return {
        "status": final_status,
        "run_id": run_id,
        "records_processed": total_records,
        "errors": errors
    }


if __name__ == "__main__":
    result = run_comtrade_ingestion(period="2023")
    print(result)
