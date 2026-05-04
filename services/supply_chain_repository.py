from services.supabase_client import get_supabase_client


def save_signal(signal: dict):
    supabase = get_supabase_client()
    response = supabase.table("supply_chain_signals").insert(signal).execute()
    return response.data


def save_agent_output(output: dict):
    supabase = get_supabase_client()
    response = supabase.table("supply_chain_agent_outputs").insert(output).execute()
    return response.data


def save_analysis(analysis: dict):
    supabase = get_supabase_client()
    response = supabase.table("supply_chain_saved_analysis").insert(analysis).execute()
    return response.data


def save_risk_score(risk_score: dict):
    supabase = get_supabase_client()
    response = supabase.table("supply_chain_risk_scores").insert(risk_score).execute()
    return response.data


def save_alert(alert: dict):
    supabase = get_supabase_client()
    response = supabase.table("supply_chain_alerts").insert(alert).execute()
    return response.data
