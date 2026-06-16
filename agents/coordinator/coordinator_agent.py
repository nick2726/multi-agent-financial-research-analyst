        request = ResearchRequest(
            ticker=ticker,
            company_name=company_name,
            filing_path=Path(filing_path) if filing_path is not None else None,
            previous_filing_path=Path(previous_filing_path) if previous_filing_path is not None else None,
            peer_tickers=list(peer_tickers) if peer_tickers is not None else None,
            include_news=include_news,
            include_filings=include_filings,
            include_peers=include_peers,
        )
        logger.info("CoordinatorAgent started request=%s", request.model_dump(mode="json"))

        metadata: list[AgentExecutionMetadata] = []
        completed_agents: list[str] = []
        failed_agents: list[str] = []
        consolidated_data = ConsolidatedResearchData()

        financial_result = self._execute_agent(
            "financial_agent",
            lambda: self._financial_agent.analyze_company(request.ticker),
            metadata,
            completed_agents,
            failed_agents,
        )
        consolidated_data.financial_analysis = financial_result

        effective_company_name = request.company_name or self._derive_company_name(request, financial_result)
        if request.include_news:
            consolidated_data.news_analysis = self._execute_agent(
                "news_agent",
                lambda: self._news_agent.analyze_news(effective_company_name),
                metadata,
                completed_agents,
                failed_agents,
            )

        if request.include_filings and request.filing_path is not None:
            consolidated_data.filing_analysis = self._execute_agent(
                "filings_agent",
                lambda: self._filings_agent.analyze_filing(request.filing_path),
                metadata,
                completed_agents,
                failed_agents,
            )
            if request.previous_filing_path is not None:
                consolidated_data.filing_comparison = self._execute_agent(
                    "filings_comparison",
                    lambda: self._filings_agent.compare_filings(
                        request.previous_filing_path,
                        request.filing_path,
                    ),
                    metadata,
                    completed_agents,
                    failed_agents,
                )

        if request.include_peers:
            consolidated_data.peer_comparison = self._execute_agent(
                "peer_agent",
                lambda: self._peer_agent.compare_peers(request.ticker, request.peer_tickers),
                metadata,
                completed_agents,
                failed_agents,
            )

        response = CoordinatorResponse(
            request=request,
            consolidated_data=consolidated_data,
            execution_metadata=metadata,
            completed_agents=completed_agents,
            failed_agents=failed_agents,
        )
        logger.info(
            "CoordinatorAgent completed completed_agents=%s failed_agents=%s",
            completed_agents,
            failed_agents,
        )
        return response

    def _execute_agent(
        self,
        agent_name: str,
        operation: Callable[[], T],
        metadata: list[AgentExecutionMetadata],
        completed_agents: list[str],
        failed_agents: list[str],
    ) -> Optional[T]:
        """Execute one specialist agent and record success or failure metadata."""
        started_at = datetime.now(UTC)
        try:
            result = operation()
        except Exception as exc:
            completed_at = datetime.now(UTC)
            failed_agents.append(agent_name)
            metadata.append(
                self._build_metadata(
                    agent_name=agent_name,
                    status="failed",
                    started_at=started_at,
                    completed_at=completed_at,
                    error_type=exc.__class__.__name__,
                    error_message=str(exc),
                )
            )
            logger.exception("CoordinatorAgent specialist failed agent=%s", agent_name)
            return None

        completed_at = datetime.now(UTC)
        completed_agents.append(agent_name)
        metadata.append(
            self._build_metadata(
                agent_name=agent_name,
                status="completed",
                started_at=started_at,
                completed_at=completed_at,
            )
        )
        return result

    def _build_metadata(
        self,
        agent_name: str,
        status: str,
        started_at: datetime,
        completed_at: datetime,
        error_type: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> AgentExecutionMetadata:
        """Build execution metadata with duration in milliseconds."""
        duration_ms = (completed_at - started_at).total_seconds() * 1000
        return AgentExecutionMetadata(
            agent_name=agent_name,
            status=status,
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=duration_ms,
            error_type=error_type,
            error_message=error_message,
        )

    def _derive_company_name(
        self,
        request: ResearchRequest,
        financial_result: FinancialAnalysis | None,
    ) -> str:
        """Derive a news-search company name from financial data or ticker."""
        if request.company_name:
            return request.company_name
        if financial_result is not None:
            return financial_result.company.name
        return request.ticker


def generate_report(ticker: str) -> CoordinatorResponse:
    """Convenience function for running a coordinated research workflow."""
    return CoordinatorAgent().generate_report(ticker)