"""Datawrapper cloud export integration.

Creates professional charts via the Datawrapper API and returns embed URLs.
Requires DATAWRAPPER_ACCESS_TOKEN environment variable.

Optional dependency — works without Datawrapper but returns helpful error.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

_DATAWRAPPER_API = "https://api.datawrapper.de/v3"
_DATAWRAPPER_TOKEN_ENV = "DATAWRAPPER_ACCESS_TOKEN"


class DatawrapperExporter:
    """Export charts to Datawrapper for professional rendering and embedding.

    Usage:
        exporter = DatawrapperExporter()
        if exporter.available():
            url = exporter.create_and_publish(data, chart_type="d3-bars-vertical")
    """

    def __init__(self, token: Optional[str] = None):
        self.token = token or os.environ.get(_DATAWRAPPER_TOKEN_ENV)
        self._client: Optional[httpx.Client] = None

    @property
    def available(self) -> bool:
        """Check if Datawrapper integration is configured."""
        return bool(self.token)

    def _get_client(self) -> httpx.Client:
        if not self.token:
            raise RuntimeError(
                "Datawrapper integration requires an API token. "
                f"Set {_DATAWRAPPER_TOKEN_ENV} environment variable or pass token to constructor.\n"
                "Get a free token at https://app.datawrapper.de/account/api-tokens"
            )
        if self._client is None or self._client.is_closed:
            self._client = httpx.Client(
                base_url=_DATAWRAPPER_API,
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=30.0,
            )
        return self._client

    def create_chart(
        self,
        data: list[dict[str, Any]],
        title: str,
        chart_type: str = "d3-bars-vertical",
        labels: Optional[dict[str, str]] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Create a Datawrapper chart from data.

        Args:
            data: List of row dicts
            title: Chart title
            chart_type: Datawrapper chart type id:
                - d3-bars-vertical, d3-bars-horizontal
                - d3-lines, d3-area
                - d3-pies, d3-pie-donut
                - d3-scatter
                - d3-table
            labels: Column name → display label mapping
            metadata: Additional chart metadata (axes, colors, etc.)

        Returns:
            API response dict with chart id and URL
        """
        client = self._get_client()

        # Prepare chart creation payload
        chart_config: dict[str, Any] = {
            "title": title,
            "type": chart_type,
            "metadata": {
                "data": {
                    "upload": True,
                },
                "visualize": {
                    "basemaps": "datamaps",
                },
                "publish": {
                    "display-filename": True,
                    "embed-width": 600,
                    "embed-height": 450,
                },
            },
        }

        if labels:
            col_names = list(data[0].keys()) if data else []
            chart_config["metadata"]["describe"] = {
                name: {"name": labels.get(name, name), "type": "text" if i == 0 else "number"}
                for i, name in enumerate(col_names)
            }

        if metadata:
            chart_config["metadata"].update(metadata)

        # Create chart
        resp = client.post("/charts", json=chart_config)
        resp.raise_for_status()
        chart_data = resp.json()
        chart_id = chart_data["id"]
        logger.info("Created Datawrapper chart %s: %s", chart_id, chart_data.get("url", ""))

        # Upload data
        self._upload_data(chart_id, data)

        return chart_data

    def _upload_data(self, chart_id: str, data: list[dict[str, Any]]) -> None:
        """Upload data to an existing Datawrapper chart as CSV."""
        client = self._get_client()

        if not data:
            logger.warning("No data to upload for chart %s", chart_id)
            return

        headers = list(data[0].keys())
        rows = [",".join(str(row.get(h, "")) for h in headers) for row in data]
        csv_content = "\n".join([",".join(headers)] + rows)

        resp = client.put(
            f"/charts/{chart_id}/data",
            content=csv_content.encode("utf-8"),
            headers={"Content-Type": "text/csv"},
        )
        resp.raise_for_status()
        logger.debug("Uploaded %d rows to chart %s", len(data), chart_id)

    def publish_chart(self, chart_id: str) -> dict[str, str]:
        """Publish a Datawrapper chart and get embed URLs.

        Returns:
            Dict with 'id', 'url', 'embed_url', 'embed_code'
        """
        client = self._get_client()

        # First, introduce data (process it)
        client.post(f"/charts/{chart_id}/data/introduce").raise_for_status()

        # Then publish
        resp = client.post(f"/charts/{chart_id}/publish")
        resp.raise_for_status()
        publish_data = resp.json()

        chart_url = publish_data.get("url", f"https://datawrapper.de/_/{chart_id}")

        # Generate embed code
        embed_url = f"https://datawrapper.de/_/{chart_id}/embed/"
        embed_code = (
            f'<iframe title="{chart_id}" aria-label="Chart" '
            f'src="{embed_url}" '
            f'frameborder="0" scrolling="no" '
            f'width="600" height="450"></iframe>'
        )

        return {
            "id": chart_id,
            "url": chart_url,
            "embed_url": embed_url,
            "embed_code": embed_code,
        }

    def create_and_publish(
        self,
        data: list[dict[str, Any]],
        title: str,
        chart_type: str = "d3-bars-vertical",
        labels: Optional[dict[str, str]] = None,
    ) -> dict[str, str]:
        """Create, upload data, and publish a Datawrapper chart in one call.

        Returns:
            Dict with 'id', 'url', 'embed_url', 'embed_code'
        """
        if not self.available:
            return {
                "id": "",
                "url": "",
                "embed_url": "",
                "embed_code": f"<!-- Set {_DATAWRAPPER_TOKEN_ENV} to enable Datawrapper export -->",
                "error": (
                    f"Datawrapper requires an API token. "
                    f"Set {_DATAWRAPPER_TOKEN_ENV} environment variable. "
                    "Get one at https://app.datawrapper.de/account/api-tokens"
                ),
            }

        chart = self.create_chart(data, title, chart_type, labels)
        chart_id = chart["id"]
        return self.publish_chart(chart_id)

    def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            self._client.close()

    def __enter__(self) -> DatawrapperExporter:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
