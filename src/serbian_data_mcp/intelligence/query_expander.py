"""Query expansion with synonyms and multilingual support."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class QueryExpander:
    """Expand search queries with synonyms and translations.

    This class provides:
    - Synonym expansion (age → years, staros, godine)
    - Serbian↔English translation
    - Fuzzy matching for typos

    Example:
        expander = QueryExpander()
        terms = await expander.expand("stanovništvo")
        # Returns: ["stanovništvo", "population", "ljudi", "broj stanovnika"]
    """

    # Synonym dictionary (English → Serbian equivalents)
    SYNONYMS: dict[str, list[str]] = {
        "age": ["age", "years", "staros", "godine", "starost"],
        "population": ["population", "stanovništvo", "ljudi", "broj stanovnika", "populacija"],
        "demographics": ["demographics", "demografija", "popis", "census", "registrovi"],
        "budget": ["budget", "budžet", "finansije", "finansije", "novac"],
        "finance": ["finance", "finansije", "finansijski", "ekonomija"],
        "health": ["health", "zdravlje", "zdravstvo", "medicinski"],
        "education": ["education", "obrazovanje", "škole", "školstvo", "učenje"],
        "air": ["air", " vazduh", "zagađenje", "kvalitet vazduha"],
        "quality": ["quality", "kvalitet", "standards", "standard"],
        "transport": ["transport", "saobraćaj", "promet"],
        "municipal": ["municipal", "opštinski", "lokalni", "komunalni"],
        "real estate": ["real estate", "nekretnine", "imovina", "parcela"],
        "registry": ["registry", "registar", "evidencija", "baza podataka"],
        "statistics": ["statistics", "statistika", "statistički podaci", "podaci"],
        "data": ["data", "podaci", "informacije"],
    }

    # Serbian character detection
    SERBIAN_CHARS = set("čćžšđČĆŽŠĐ")

    def __init__(self) -> None:
        """Initialize query expander."""
        # Build reverse synonym mapping (Serbian → English)
        self._reverse_synonyms: dict[str, list[str]] = {}
        for eng_term, alternatives in self.SYNONYMS.items():
            for alt in alternatives:
                if alt not in self._reverse_synonyms:
                    self._reverse_synonyms[alt] = []
                self._reverse_synonyms[alt].append(eng_term)

    async def expand(self, query: str) -> list[str]:
        """Expand query with synonyms and translations.

        Args:
            query: Original search query

        Returns:
            List of expanded search terms

        Example:
            >>> await expander.expand("age data")
            ["age", "years", "staros", "godine", "starost", "data", "podaci", "informacije"]
        """
        # Tokenize query into terms
        terms = self._tokenize(query)

        # Expand each term
        expanded: set[str] = set()
        for term in terms:
            expanded.add(term)

            # Add synonyms (English → Serbian)
            if term.lower() in self.SYNONYMS:
                for synonym in self.SYNONYMS[term.lower()]:
                    expanded.add(synonym)

            # Add reverse synonyms (Serbian → English)
            if term.lower() in self._reverse_synonyms:
                for eng_term in self._reverse_synonyms[term.lower()]:
                    expanded.add(eng_term)
                    # Add all English synonyms for this term
                    if eng_term in self.SYNONYMS:
                        for synonym in self.SYNONYMS[eng_term]:
                            expanded.add(synonym)

        # Remove duplicates and return as list
        return list(expanded)

    def _tokenize(self, query: str) -> list[str]:
        """Tokenize query into individual terms.

        Args:
            query: Search query

        Returns:
            List of terms (lowercased)

        Example:
            >>> self._tokenize("Age and Population")
            ["age", "population"]
        """
        # Simple tokenization: split on whitespace and punctuation
        import re

        terms = re.findall(r"\w+", query.lower())
        return terms

    def detect_language(self, query: str) -> str:
        """Detect if query is in Serbian or English.

        Args:
            query: Search query

        Returns:
            "serbian", "english", or "unknown"

        Example:
            >>> detect_language("stanovništvo")
            "serbian"
            >>> detect_language("population")
            "english"
        """
        has_serbian_chars = any(char in self.SERBIAN_CHARS for char in query)

        if has_serbian_chars:
            return "serbian"

        # Check for Serbian words
        query_lower = query.lower()
        serbian_indicators = ["stanovništva", "godina", "opština", "budžet", "zdravlje"]

        if any(indicator in query_lower for indicator in serbian_indicators):
            return "serbian"

        return "english"

    def fuzzy_match(self, term: str, vocabulary: set[str], max_distance: int = 2) -> list[str]:
        """Find fuzzy matches for term in vocabulary.

        Args:
            term: Term to match
            vocabulary: Set of valid terms
            max_distance: Maximum Levenshtein distance

        Returns:
            List of matching terms from vocabulary

        Example:
            >>> fuzzy_match("populaton", {"population", "stanovništvo"})
            ["population"]
        """
        matches: list[str] = []

        for vocab_term in vocabulary:
            distance = self._levenshtein_distance(term, vocab_term)
            if distance <= max_distance:
                matches.append(vocab_term)

        return matches

    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """Calculate Levenshtein distance between two strings.

        Args:
            s1: First string
            s2: Second string

        Returns:
            Edit distance (number of insertions, deletions, substitutions)

        Example:
            >>> _levenshtein_distance("kitten", "sitting")
            3
        """
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)

        if len(s2) == 0:
            return len(s1)

        previous_row = list(range(len(s2) + 1))

        for i, c1 in enumerate(s1):
            current_row = [i + 1]

            for j, c2 in enumerate(s2):
                # Calculate costs
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)

                current_row.append(min(insertions, deletions, substitutions))

            previous_row = current_row

        return previous_row[-1]
