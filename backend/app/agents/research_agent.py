from google.adk.agents import Agent

research_agent = Agent(
    name="research_agent",
    model="gemini-2.5-flash",
    instruction="Handle research queries for LitLens.",
    tools=[],
)
