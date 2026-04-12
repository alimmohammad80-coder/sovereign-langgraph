from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from openai import OpenAI

client = OpenAI()

class State(TypedDict, total=False):
    query: str
    geo: str
    energy: str
    security: str
    score: str
    final: str

# --- Geopolitical Agent ---
def geopolitical_agent(state: State) -> State:
    response = client.responses.create(
        model="gpt-4.1-mini",
        input=f"Geopolitical risk analysis: {state['query']}"
    )
    return {"geo": response.output_text}

# --- Energy Agent ---
def energy_agent(state: State) -> State:
    response = client.responses.create(
        model="gpt-4.1-mini",
        input=f"Energy risk analysis: {state['query']}"
    )
    return {"energy": response.output_text}

# --- Security Agent ---
def security_agent(state: State) -> State:
    response = client.responses.create(
        model="gpt-4.1-mini",
        input=f"Security and terrorism threat analysis: {state['query']}"
    )
    return {"security": response.output_text}

# --- Scoring Engine ---
def scoring_engine(state: State) -> State:
    combined = f"""
Geopolitical:
{state.get('geo','')}

Energy:
{state.get('energy','')}

Security:
{state.get('security','')}
"""

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=f"""
Based on the analysis below, assign risk scores from 0–100:

Geopolitical Risk:
Energy Risk:
Security Risk:
Overall Risk:

Also briefly justify each score.

{combined}
"""
    )

    return {"score": response.output_text}

# --- Final Briefing ---
def final_briefing(state: State) -> State:
    response = client.responses.create(
        model="gpt-4.1-mini",
        input=f"""
Create a professional intelligence briefing using:

Analysis:
{state.get('geo','')}
{state.get('energy','')}
{state.get('security','')}

Scores:
{state.get('score','')}
"""
    )

    return {"final": response.output_text}

# --- Build Graph ---
builder = StateGraph(State)

builder.add_node("geo", geopolitical_agent)
builder.add_node("energy", energy_agent)
builder.add_node("security", security_agent)
builder.add_node("score", scoring_engine)
builder.add_node("final", final_briefing)

# Parallel agents
builder.add_edge(START, "geo")
builder.add_edge(START, "energy")
builder.add_edge(START, "security")

# Then scoring
builder.add_edge("geo", "score")
builder.add_edge("energy", "score")
builder.add_edge("security", "score")

# Then final briefing
builder.add_edge("score", "final")

builder.add_edge("final", END)

graph = builder.compile()

# --- Run ---
if __name__ == "__main__":
    output = graph.invoke({
        "query": "Assess Pakistan political, security and energy risks"
    })
    print(output["final"])
