"""Custom exceptions for Serbian Data MCP Server.

These exceptions provide helpful error messages for common issues
that users may encounter when using the server.
"""


class SerbianDataError(Exception):
    """Base exception for Serbian Data MCP errors."""

    def __init__(self, message: str, details: str = ""):
        """Initialize exception with user-friendly message.

        Args:
            message: Main error message
            details: Additional details or suggestions
        """
        self.message = message
        self.details = details
        super().__init__(self.format_message())

    def format_message(self) -> str:
        """Format the complete error message."""
        msg = f"❌ {self.message}"
        if self.details:
            msg += f"\n   {self.details}"
        return msg


class ConfigurationError(SerbianDataError):
    """Exception raised for configuration errors."""

    def __init__(self, setting: str, problem: str, suggestion: str = ""):
        """Initialize configuration error.

        Args:
            setting: The configuration setting that caused the error
            problem: What went wrong
            suggestion: How to fix it
        """
        message = f"Configuration error: {setting}"
        details = f"{problem}"
        if suggestion:
            details += f"\n   💡 Suggestion: {suggestion}"
        super().__init__(message, details)


class ConnectionError(SerbianDataError):
    """Exception raised when connection to API fails."""

    def __init__(self, url: str, reason: str = ""):
        """Initialize connection error.

        Args:
            url: The URL that couldn't be reached
            reason: Why the connection failed
        """
        message = f"Cannot connect to {url}"
        details = reason if reason else "Please check your internet connection"
        super().__init__(message, details)


class DatasetNotFoundError(SerbianDataError):
    """Exception raised when a dataset is not found."""

    def __init__(self, dataset_id: str):
        """Initialize dataset not found error.

        Args:
            dataset_id: The dataset ID that wasn't found
        """
        message = f"Dataset not found: {dataset_id}"
        details = "Check the dataset ID or search for available datasets"
        super().__init__(message, details)


class ResourceNotFoundError(SerbianDataError):
    """Exception raised when a resource is not found."""

    def __init__(self, resource_id: str):
        """Initialize resource not found error.

        Args:
            resource_id: The resource ID that wasn't found
        """
        message = f"Resource not found: {resource_id}"
        details = "The resource may have been removed or the ID is incorrect"
        super().__init__(message, details)


class DataParsingError(SerbianDataError):
    """Exception raised when data parsing fails."""

    def __init__(self, format_type: str, reason: str = ""):
        """Initialize data parsing error.

        Args:
            format_type: The data format that couldn't be parsed
            reason: Why parsing failed
        """
        message = f"Failed to parse {format_type} data"
        details = reason if reason else "The data may be corrupted or in an unexpected format"
        super().__init__(message, details)


class VisualizationError(SerbianDataError):
    """Exception raised when visualization creation fails."""

    def __init__(self, chart_type: str, reason: str = ""):
        """Initialize visualization error.

        Args:
            chart_type: The type of chart that couldn't be created
            reason: Why creation failed
        """
        message = f"Failed to create {chart_type} chart"
        details = reason if reason else "Check that data contains the required columns"
        super().__init__(message, details)


class RateLimitError(SerbianDataError):
    """Exception raised when rate limit is exceeded."""

    def __init__(self, limit: float, wait_time: float):
        """Initialize rate limit error.

        Args:
            limit: The rate limit in seconds
            wait_time: How long to wait before retrying
        """
        message = f"Rate limit exceeded ({limit}s between requests)"
        details = f"Please wait {wait_time:.1f} seconds before trying again"
        super().__init__(message, details)


class ValidationError(SerbianDataError):
    """Exception raised when input validation fails."""

    def __init__(self, field: str, value: any, expected: str):
        """Initialize validation error.

        Args:
            field: The field that failed validation
            value: The invalid value
            expected: What was expected
        """
        message = f"Invalid value for '{field}': {value}"
        details = f"Expected: {expected}"
        super().__init__(message, details)
