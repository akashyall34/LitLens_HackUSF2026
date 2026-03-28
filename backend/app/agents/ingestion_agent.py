from google.adk.agents import Agent

ingestion_agent = Agent(
    name="ingestion_agent",
    model="gemini-2.5-flash",
    instruction="Handle ingestion requests for LitLens.",
    tools=[],
)
