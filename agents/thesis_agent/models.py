from typing import Optional

from pydantic import BaseModel


class ThesisInput(BaseModel):
    company_name: str
    financial_analysis: str
    news_analysis: Optional[str] = None
    filings_analysis: Optional[str] = None
    peer_analysis: Optional[str] = None


class InvestmentReport(BaseModel):
    executive_summary: str
    bull_case: str
    bear_case: str
    key_risks: str
    peer_positioning: str
    investment_thesis: str
    conclusion: str