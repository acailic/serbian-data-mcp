"""Unit tests for query expander."""

import pytest
from serbian_data_mcp.intelligence.query_expander import QueryExpander


@pytest.fixture
def expander():
    """Create query expander instance."""
    return QueryExpander()


@pytest.mark.asyncio
async def test_expand_basic(expander):
    """Test basic query expansion."""
    terms = await expander.expand("age")

    assert "age" in terms
    assert any("staros" in term or "godine" in term for term in terms)
    assert isinstance(terms, list)


@pytest.mark.asyncio
async def test_expand_population(expander):
    """Test population query expansion."""
    terms = await expander.expand("population")

    assert "population" in terms
    assert "stanovništvo" in terms or any("stanovništvo" in term for term in terms)
    assert len(terms) >= 3


@pytest.mark.asyncio
async def test_expand_serbian(expander):
    """Test Serbian query expansion."""
    terms = await expander.expand("stanovništvo")

    assert "stanovništvo" in terms
    assert "population" in terms


@pytest.mark.asyncio
async def test_expand_multiple_terms(expander):
    """Test expansion of multi-word query."""
    terms = await expander.expand("age population")

    # Should include expanded terms from both words
    assert "age" in terms or "staros" in terms
    assert "population" in terms or "stanovništvo" in terms


def test_detect_language_english(expander):
    """Test language detection for English."""
    assert expander.detect_language("population") == "english"
    assert expander.detect_language("budget") == "english"


def test_detect_language_serbian(expander):
    """Test language detection for Serbian."""
    assert expander.detect_language("stanovništvo") == "serbian"
    assert expander.detect_language("budžet") == "serbian"


def test_detect_language_serbian_chars(expander):
    """Test language detection with Serbian characters."""
    assert expander.detect_language("čćžšđ") == "serbian"


def test_fuzzy_match(expander):
    """Test fuzzy matching."""
    vocabulary = {"population", "stanovništvo", "age", "budget"}

    # One character difference
    matches = expander.fuzzy_match("populaton", vocabulary, max_distance=2)
    assert "population" in matches

    # Two character difference
    matches = expander.fuzzy_match("stanovništo", vocabulary, max_distance=3)
    assert "stanovništvo" in matches


def test_levenshtein_distance(expander):
    """Test Levenshtein distance calculation."""
    # Identical strings
    assert expander._levenshtein_distance("test", "test") == 0

    # One substitution
    assert expander._levenshtein_distance("test", "tast") == 1

    # One insertion
    assert expander._levenshtein_distance("test", "tests") == 1

    # One deletion
    assert expander._levenshtein_distance("tests", "test") == 1
