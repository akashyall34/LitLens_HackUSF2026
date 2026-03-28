from google.adk.agents import Agent

gap_detection_agent = Agent(
    name="gap_detection_agent",
    model="gemini-2.5-flash",
    instruction="Handle gap detection requests for LitLens.",
    tools=[],
)
