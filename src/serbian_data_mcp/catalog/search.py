"""Semantic search engine for datasets."""

from __future__ import annotations

import logging
from typing import Any

from .cache import DatasetCatalog
from .models import CachedDataset, SearchResult
from ..intelligence.query_expander import QueryExpander

logger = logging.getLogger(__name__)


class SearchEngine:
    """Semantic search with relevance scoring.

    Example:
        catalog = DatasetCatalog()
        await catalog.initialize()

        engine = SearchEngine(catalog)
        results = await engine.search("population by age")
    """

    def __init__(self, catalog: DatasetCatalog) -> None:
        """Initialize search engine.

        Args:
            catalog: Dataset catalog to search
        """
        self.catalog = catalog
        self.query_expander = QueryExpander()

    async def search(
        self,
        query: str,
        max_results: int = 10,
        min_score: float = 0.3
    ) -> list[SearchResult]:
        """Search catalog with semantic understanding.

        Args:
            query: Search query
            max_results: Maximum number of results to return
            min_score: Minimum relevance score (0.0-1.0)

        Returns:
            List of search results sorted by relevance

        Example:
            results = await engine.search("stanovništvo")
            for result in results:
                print(f"{result.dataset.title} ({result.relevance_score:.2f})")
        """
        if not self.catalog.datasets:
            logger.warning("Catalog is empty")
            return []

        # Expand query with synonyms and translations
        expanded_terms = await self.query_expander.expand(query)
        logger.info(f"Query expanded: {query} → {expanded_terms}")

        # Score all datasets
        scored_results: list[SearchResult] = []
        for dataset in self.catalog.get_all():
            score, matched_keywords = self._calculate_relevance(dataset, expanded_terms)

            if score >= min_score:
                result = SearchResult(
                    dataset=dataset,
                    relevance_score=score,
                    matched_keywords=matched_keywords,
                    match_reason=self._explain_match(score, matched_keywords)
                )
                scored_results.append(result)

        # Sort by relevance score descending
        scored_results.sort(key=lambda r: r.relevance_score, reverse=True)

        # Return top N results
        return scored_results[:max_results]

    def _calculate_relevance(
        self,
        dataset: CachedDataset,
        terms: list[str]
    ) -> tuple[float, list[str]]:
        """Calculate relevance score for dataset.

        Args:
            dataset: Dataset to score
            terms: Search terms (expanded)

        Returns:
            Tuple of (score, matched_keywords)
        """
        score = 0.0
        matched_keywords: list[str] = []

        title_lower = dataset.title.lower()
        desc_lower = dataset.description.lower()
        tags_lower = [tag.lower() for tag in dataset.tags]

        for term in terms:
            term_lower = term.lower()

            # Title match: highest weight (0.5)
            if term_lower in title_lower:
                score += 0.5
                matched_keywords.append(term)

            # Description match: medium weight (0.3)
            if term_lower in desc_lower:
                score += 0.3
                if term not in matched_keywords:
                    matched_keywords.append(term)

            # Tags match: lower weight (0.2)
            for tag in tags_lower:
                if term_lower in tag:
                    score += 0.2
                    if term not in matched_keywords:
                        matched_keywords.append(term)
                    break  # Only score once per term

        # Cap score at 1.0
        score = min(score, 1.0)

        return score, matched_keywords

    def _explain_match(self, score: float, matched_keywords: list[str]) -> str:
        """Generate explanation for why a dataset matched.

        Args:
            score: Relevance score
            matched_keywords: Keywords that matched

        Returns:
            Human-readable explanation
        """
        if score >= 0.8:
            strength = "strong match"
        elif score >= 0.5:
            strength = "good match"
        elif score >= 0.3:
            strength = "partial match"
        else:
            strength = "weak match"

        if matched_keywords:
            keywords_str = ", ".join(matched_keywords[:5])
            if len(matched_keywords) > 5:
                keywords_str += f" (and {len(matched_keywords) - 5} more)"
            return f"{strength} on keywords: {keywords_str}"
        else:
            return strength

    async def search_by_organization(
        self,
        organization: str,
        max_results: int = 20
    ) -> list[SearchResult]:
        """Search all datasets from a specific organization.

        Args:
            organization: Organization name (partial match OK)
            max_results: Maximum results to return

        Returns:
            List of datasets from the organization
        """
        org_lower = organization.lower()
        results: list[SearchResult] = []

        for dataset in self.catalog.get_all():
            if org_lower in dataset.organization.lower():
                result = SearchResult(
                    dataset=dataset,
                    relevance_score=1.0,  # Exact organization match
                    matched_keywords=[organization],
                    match_reason=f"from organization: {dataset.organization}"
                )
                results.append(result)

        return results[:max_results]
