print("STARTING TEST")
from agents.thesis_agent.models import ThesisInput
from agents.thesis_agent.thesis_agent import ThesisWriterAgent


agent = ThesisWriterAgent()

thesis_input = ThesisInput(
    company_name="Infosys Limited",
    financial_analysis="""
Revenue Growth: 4.57%
ROE: 31.44%
PE Ratio: 15.04
Operating Margin: 20.93%
""",
    news_analysis="""
Infosys secured multiple AI-related contracts.
Expanded partnerships with global enterprises.
""",
    peer_analysis="""
Infosys has a lower PE ratio than Tech Mahindra.
Infosys demonstrates stronger profitability than Wipro.
""",
)

report = agent.generate_report(thesis_input)

print("\n" + "=" * 60)
print("THESIS REPORT GENERATED")
print("=" * 60)

print("\nExecutive Summary:")
print(report.executive_summary)

print("\nBull Case:")
print(report.bull_case)

print("\nBear Case:")
print(report.bear_case)

print("\nKey Risks:")
print(report.key_risks)

print("\nPeer Positioning:")
print(report.peer_positioning)

print("\nInvestment Thesis:")
print(report.investment_thesis)

print("\nConclusion:")
print(report.conclusion)