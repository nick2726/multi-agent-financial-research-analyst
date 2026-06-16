THESIS_TEMPLATE = """
You are an expert equity research analyst.

Generate a professional investment research report for {company_name}.

Financial Analysis:
{financial_analysis}

News Analysis:
{news_analysis}

Filings Analysis:
{filings_analysis}

Peer Analysis:
{peer_analysis}

Produce the report using EXACTLY these headings:

Executive Summary

Bull Case

Bear Case

Key Risks

Peer Positioning

Investment Thesis

Conclusion

Requirements:
- Use only the supplied information.
- Do not hallucinate.
- Be concise and professional.
- Present balanced views.
- Clearly identify risks.
"""