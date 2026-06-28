"""Offline unit tests for the exception classes in src/serbian_data_mcp/exceptions.py.

Existing test_api_client/test_api exercise these exceptions only via pytest.raises
through client code paths, so the per-subclass message-formatting bodies and the
optional-arg (suggestion/reason) truthy-vs-empty arms stayed uncovered. These
tests construct each class directly and assert the formatted message/details.
"""

import pytest

from serbian_data_mcp.exceptions import (
    ConfigurationError,
    ConnectionError,
    DataParsingError,
    DatasetNotFoundError,
    RateLimitError,
    ResourceNotFoundError,
    SerbianDataError,
    ValidationError,
    VisualizationError,
)


class TestSerbianDataError:
    """Base class message formatting."""

    def test_with_details_formats_message_and_details(self) -> None:
        err = SerbianDataError("boom", "more context")
        assert err.message == "boom"
        assert err.details == "more context"
        assert err.format_message() == "❌ boom\n   more context"
        # __init__ passes format_message() to super().__init__, so str() carries it
        assert str(err) == "❌ boom\n   more context"

    def test_without_details_omits_detail_line(self) -> None:
        # Covers the format_message partial branch where self.details is falsy.
        err = SerbianDataError("boom")
        assert err.details == ""
        assert err.format_message() == "❌ boom"

    def test_is_exception_subclass(self) -> None:
        assert issubclass(SerbianDataError, Exception)
        with pytest.raises(SerbianDataError):
            raise SerbianDataError("x")


class TestConfigurationError:
    """ConfigurationError: setting/problem/suggestion formatting arms."""

    def test_with_suggestion(self) -> None:
        err = ConfigurationError("RATE_LIMIT", "must be positive", "set a value > 0")
        assert err.message == "Configuration error: RATE_LIMIT"
        assert "must be positive" in err.details
        assert "💡 Suggestion: set a value > 0" in err.details
        assert str(err).startswith("❌ Configuration error: RATE_LIMIT")

    def test_without_suggestion(self) -> None:
        # Covers the `if suggestion:` falsy arm — no suggestion line appended.
        err = ConfigurationError("TIMEOUT", "bad value")
        assert err.details == "bad value"
        assert "💡 Suggestion" not in err.details

    def test_subclass_of_base(self) -> None:
        assert isinstance(ConfigurationError("x", "y"), SerbianDataError)


class TestConnectionError:
    """ConnectionError: url + optional reason fallback."""

    def test_with_reason(self) -> None:
        err = ConnectionError("https://data.gov.rs", "dns failure")
        assert err.message == "Cannot connect to https://data.gov.rs"
        assert err.details == "dns failure"

    def test_without_reason_uses_default(self) -> None:
        err = ConnectionError("https://data.gov.rs")
        assert err.details == "Please check your internet connection"


class TestDatasetNotFoundError:
    """DatasetNotFoundError: fixed details suggestion."""

    def test_message_and_details(self) -> None:
        err = DatasetNotFoundError("ds-123")
        assert err.message == "Dataset not found: ds-123"
        assert err.details == "Check the dataset ID or search for available datasets"
        assert "ds-123" in str(err)


class TestResourceNotFoundError:
    """ResourceNotFoundError: fixed details suggestion (lines 86-88)."""

    def test_message_and_details(self) -> None:
        err = ResourceNotFoundError("res-456")
        assert err.message == "Resource not found: res-456"
        assert err.details == "The resource may have been removed or the ID is incorrect"
        assert "res-456" in str(err)


class TestDataParsingError:
    """DataParsingError: format_type + optional reason fallback."""

    def test_with_reason(self) -> None:
        err = DataParsingError("csv", "malformed header")
        assert err.message == "Failed to parse csv data"
        assert err.details == "malformed header"

    def test_without_reason_uses_default(self) -> None:
        # Covers the `reason if reason else ...` fallback arm.
        err = DataParsingError("xlsx")
        assert err.details == "The data may be corrupted or in an unexpected format"


class TestVisualizationError:
    """VisualizationError: chart_type + optional reason fallback."""

    def test_with_reason(self) -> None:
        err = VisualizationError("bar", "missing x column")
        assert err.message == "Failed to create bar chart"
        assert err.details == "missing x column"

    def test_without_reason_uses_default(self) -> None:
        err = VisualizationError("line")
        assert err.details == "Check that data contains the required columns"


class TestRateLimitError:
    """RateLimitError: limit + wait_time formatting."""

    def test_message_and_details(self) -> None:
        err = RateLimitError(1.0, 2.5)
        assert err.message == "Rate limit exceeded (1.0s between requests)"
        assert err.details == "Please wait 2.5 seconds before trying again"

    def test_wait_time_formatted_to_one_decimal(self) -> None:
        # Covers the f"{wait_time:.1f}" format spec.
        err = RateLimitError(0.5, 3.14159)
        assert "wait 3.1 seconds" in err.details


class TestValidationError:
    """ValidationError: field/value/expected formatting (lines 147-149)."""

    def test_message_and_details(self) -> None:
        err = ValidationError("page_size", -1, "a positive integer")
        assert err.message == "Invalid value for 'page_size': -1"
        assert err.details == "Expected: a positive integer"
        assert "page_size" in str(err)
        assert "-1" in str(err)

    def test_string_value_rendered_in_message(self) -> None:
        err = ValidationError("format", "weird", "one of csv/json/xlsx")
        assert err.message == "Invalid value for 'format': weird"
