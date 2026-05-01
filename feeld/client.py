# maps · cassette.help · MIT
"""
GraphQL client for Feeld's API.

Thin wrapper around httpx. Handles:
- Auth header injection (auto-refreshes token)
- Rate limiting (1 req/sec default — be polite)
- Error parsing (GraphQL errors vs HTTP errors)
- Pagination cursor helpers

Usage:
 from feeld.client import FeeldClient

 client = FeeldClient()
 result = client.query("{ me { id displayName } }")
 # Or with variables:
 result = client.query(MY_QUERY, variables={"first": 20})
"""

import time
from typing import Any

import httpx

from feeld.auth import get_valid_token
from feeld.config import get_extra_headers, get_graphql_endpoint

# Polite rate limit — 1 request per second
# Feeld's backend is apparently already stressed (10 requests on every app open)
_RATE_LIMIT_SECONDS = 1.0
_last_request_time: float = 0.0


class FeeldClient:
    """
    GraphQL client for Feeld's API.

    Instantiate once and reuse. Handles token refresh automatically.
    """

    def __init__(self, rate_limit: float = _RATE_LIMIT_SECONDS):
        self.endpoint = get_graphql_endpoint()
        self.extra_headers = get_extra_headers()
        self.rate_limit = rate_limit
        self._last_request = 0.0

    def _headers(self) -> dict:
        """Build request headers, fetching a fresh token if needed."""
        token = get_valid_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        headers.update(self.extra_headers)
        return headers

    def _rate_limit(self):
        """Enforce rate limit between requests."""
        elapsed = time.time() - self._last_request
        if elapsed < self.rate_limit:
            time.sleep(self.rate_limit - elapsed)
        self._last_request = time.time()

    def query(
        self,
        query: str,
        variables: dict[str, Any] | None = None,
        operation_name: str | None = None,
    ) -> dict:
        """
        Execute a GraphQL query.

        Args:
            query: GraphQL query string
            variables: Optional query variables
            operation_name: Optional operation name

        Returns:
            The `data` dict from the GraphQL response

        Raises:
            FeeldAPIError: if the API returns GraphQL errors
            httpx.HTTPError: on network/HTTP failures
        """
        self._rate_limit()

        payload: dict[str, Any] = {"query": query}
        if variables:
            payload["variables"] = variables
        if operation_name:
            payload["operationName"] = operation_name

        r = httpx.post(
            self.endpoint,
            json=payload,
            headers=self._headers(),
            timeout=20,
        )
        r.raise_for_status()

        body = r.json()

        if "errors" in body and body["errors"]:
            errors = body["errors"]
            # Check for auth errors specifically
            for err in errors:
                msg = str(err.get("message", "")).lower()
                if any(kw in msg for kw in ("unauthorized", "unauthenticated", "token", "forbidden")):
                    raise FeeldAuthError(
                        f"Auth error from Feeld API: {err['message']}\n"
                        "Try: feeld auth --fresh"
                    )
            raise FeeldAPIError(errors)

        return body.get("data", {})

    def paginate(
        self,
        query: str,
        variables: dict[str, Any],
        data_path: list[str],
        max_pages: int = 10,
    ) -> list[dict]:
        """
        Paginate through a cursor-based connection.

        Args:
            query: GraphQL query with $after variable
            variables: Initial variables (will add/update `after` cursor)
            data_path: List of keys to drill into the response to find
                the connection node. E.g. ["likesReceived"]
            max_pages: Safety cap on pages fetched

        Returns:
            Flat list of all edge nodes across all pages

        Example:
            results = client.paginate(
                LIKES_RECEIVED_QUERY,
                {"first": 20},
                data_path=["likesReceived"],
            )
        """
        results = []
        cursor = None
        page = 0

        while page < max_pages:
            if cursor:
                variables = {**variables, "after": cursor}

            data = self.query(query, variables)

            # Drill into data_path
            node = data
            for key in data_path:
                node = node.get(key, {})
                if not node:
                    return results

            edges = node.get("edges", [])
            for edge in edges:
                if edge.get("node"):
                    results.append(edge["node"])

            page_info = node.get("pageInfo", {})
            if not page_info.get("hasNextPage"):
                break

            cursor = page_info.get("endCursor")
            if not cursor:
                break

            page += 1

        return results


class FeeldAPIError(Exception):
    """GraphQL-level error from Feeld's API."""

    def __init__(self, errors: list[dict]):
        self.errors = errors
        messages = "; ".join(e.get("message", "Unknown") for e in errors)
        super().__init__(f"Feeld API errors: {messages}")


class FeeldAuthError(FeeldAPIError):
    """Auth-specific API error."""
    pass
