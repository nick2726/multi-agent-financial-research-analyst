from agents.thesis_agent.models import (
    ThesisInput,
)

from agents.thesis_agent.thesis_agent import (
    ThesisWriterAgent,
)


agent = ThesisWriterAgent()

thesis_input = ThesisInput(
    company_name="Infosys Limited",
    financial_analysis="""
Revenue Growth: 4.57%
ROE: 31.44%
PE Ratio: 15.04
""",
    news_analysis="""
Infosys secured multiple AI-related contracts.
""",
    peer_analysis="""
Infosys has lower PE compared to Tech Mahindra.
""",
)

report = agent.generate_report(
    thesis_input
)

print(report.model_dump_json(indent=2))