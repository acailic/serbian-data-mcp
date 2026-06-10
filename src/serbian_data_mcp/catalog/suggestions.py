"""Alternative suggestion engine for failed searches."""

from __future__ import annotations

import logging
from typing import Any

from .cache import DatasetCatalog
from .models import CachedDataset, SearchResult, Suggestion
from .search import SearchEngine

logger = logging.getLogger(__name__)


class AlternativeSuggestions:
    """Generate alternative suggestions when no exact match found.

    Example:
        suggestions = AlternativeSuggestions(catalog, search_engine)
        result = await suggestions.suggest("xyz123")
        # Returns alternatives with explanation
    """

    def __init__(self, catalog: DatasetCatalog, search_engine: SearchEngine) -> None:
        """Initialize suggestion engine.

        Args:
            catalog: Dataset catalog
            search_engine: Search engine for finding alternatives
        """
        self.catalog = catalog
        self.search_engine = search_engine

    async def suggest(
        self,
        query: str,
        max_alternatives: int = 5
    ) -> Suggestion:
        """Suggest alternative datasets when no exact match found.

        Args:
            query: Original search query that failed
            max_alternatives: Maximum number of alternatives to suggest

        Returns:
            Suggestion object with alternatives and explanation

        Example:
            >>> result = await suggestions.suggest("xyz123")
            >>> result.explanation
            "No exact match for 'xyz123', but found 5 datasets related to: population, statistics"
        """
        # Try broader search strategies
        alternatives: list[SearchResult] = []

        # Strategy 1: Partial keyword matches (lower score threshold)
        partial_results = await self.search_engine.search(
            query,
            max_results=max_alternatives * 2,
            min_score=0.1  # Lower threshold for partial matches
        )
        alternatives.extend(partial_results)

        # Strategy 2: If no results, try individual terms
        if not alternatives:
            terms = query.split()
            for term in terms:
                term_results = await self.search_engine.search(
                    term,
                    max_results=3,
                    min_score=0.2
                )
                alternatives.extend(term_results)
                if len(alternatives) >= max_alternatives:
                    break

        # Remove duplicates by dataset ID
        unique_alternatives = self._deduplicate(alternatives)

        # Sort by relevance and limit
        unique_alternatives.sort(key=lambda r: r.relevance_score, reverse=True)
        unique_alternatives = unique_alternatives[:max_alternatives]

        # Generate explanation
        explanation = self._explain_suggestion(query, unique_alternatives)

        return Suggestion(
            datasets=unique_alternatives,
            explanation=explanation,
            total_alternatives=len(unique_alternatives)
        )

    def _deduplicate(self, results: list[SearchResult]) -> list[SearchResult]:
        """Remove duplicate datasets by ID.

        Args:
            results: Search results with possible duplicates

        Returns:
            Deduplicated results (keeping highest score)
        """
        seen_ids: dict[str, SearchResult] = {}

        for result in results:
            dataset_id = result.dataset.id
            if dataset_id not in seen_ids:
                seen_ids[dataset_id] = result
            else:
                # Keep result with higher score
                if result.relevance_score > seen_ids[dataset_id].relevance_score:
                    seen_ids[dataset_id] = result

        return list(seen_ids.values())

    def _explain_suggestion(self, query: str, datasets: list[SearchResult]) -> str:
        """Generate explanation for why these datasets were suggested.

        Args:
            query: Original search query
            datasets: Suggested datasets

        Returns:
            Human-readable explanation
        """
        if not datasets:
            return f"No matching datasets found for '{query}'. Try different keywords."

        # Collect all matched keywords
        all_keywords: set[str] = set()
        for ds in datasets:
            all_keywords.update(ds.matched_keywords)

        if all_keywords:
            keywords_str = ", ".join(sorted(all_keywords)[:5])
            if len(all_keywords) > 5:
                keywords_str += f" (and {len(all_keywords) - 5} more)"

            return (
                f"No exact match for '{query}', but found {len(datasets)} "
                f"relevant dataset(s) related to: {keywords_str}"
            )
        else:
            return f"No exact match for '{query}', but found {len(datasets)} potentially relevant datasets."

    async def suggest_by_format(
        self,
        query: str,
        preferred_format: str = "csv"
    ) -> Suggestion:
        """Suggest datasets with specific format priority.

        Args:
            query: Search query
            preferred_format: Preferred data format (csv, json, xlsx, etc.)

        Returns:
            Suggestion with format-prioritized results
        """
        # Get all results
        all_results = await self.search_engine.search(
            query,
            max_results=50,
            min_score=0.1
        )

        # Prioritize by format
        results_with_format = [
            r for r in all_results
            if preferred_format in r.dataset.formats
        ]

        # Fill with other formats if needed
        other_results = [r for r in all_results if preferred_format not in r.dataset.formats]
        results_with_format.extend(other_results[:5])

        explanation = f"Found {len(results_with_format)} datasets"
        if any(preferred_format in r.dataset.formats for r in results_with_format):
            explanation += f" (prioritizing {preferred_format.upper()} format)"

        return Suggestion(
            datasets=results_with_format[:5],
            explanation=explanation,
            total_alternatives=len(results_with_format)
        )
