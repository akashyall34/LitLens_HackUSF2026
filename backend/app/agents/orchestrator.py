from google.adk.agents import Agent
from app.agents.ingestion_agent import ingestion_agent
from app.agents.gap_detection_agent import gap_detection_agent
from app.agents.research_agent import research_agent

orchestrator = Agent(
    name="litlens_orchestrator",
    model="gemini-2.5-flash",
    instruction=(
        "You are the LitLens orchestrator. Route user requests to the correct specialist: "
        "ingestion, gap detection, or research. Delegate immediately and do not answer directly."
    ),
    sub_agents=[ingestion_agent, gap_detection_agent, research_agent],
)
