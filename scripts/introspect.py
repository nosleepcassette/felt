#!/usr/bin/env python3
# maps · cassette.help · MIT
"""
Recon script — run AFTER getting an auth token.
Tries common GraphQL endpoints, dumps schema if introspection is enabled.

Usage:
    python3 scripts/introspect.py

Outputs:
    RECON-schema.json — full schema if introspection enabled
    RECON-queries.txt — list of all query/mutation names
"""

import json
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent.parent))

from feeld.auth import load_tokens
from feeld.config import get_extra_headers

CANDIDATE_ENDPOINTS = [
    "https://api.feeld.co/graphql",
    "https://api.feeld.co/v1/graphql",
    "https://api.feeld.co/v2/graphql",
    "https://feeld.co/api/graphql",
    "https://graph.feeld.co/graphql",
    "https://gateway.feeld.co/graphql",
]

INTROSPECTION_QUERY = """
query IntrospectionQuery {
  __schema {
    queryType {
      fields {
        name
        description
        args { name type { name kind ofType { name kind } } }
      }
    }
    mutationType {
      fields {
        name
        description
      }
    }
    types {
      name
      kind
      fields {
        name
        type { name kind ofType { name kind } }
      }
    }
  }
}
"""

SIMPLE_INTROSPECTION = """
query {
  __schema {
    queryType { fields { name description } }
    mutationType { fields { name } }
  }
}
"""


def try_endpoint(url: str, token: str, extra_headers: dict) -> bool:
    """Try a GraphQL endpoint, return True if it responds to GraphQL."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        **extra_headers,
    }
    try:
        r = httpx.post(
            url,
            json={"query": SIMPLE_INTROSPECTION},
            headers=headers,
            timeout=10,
        )
        if r.status_code in (200, 400):
            body = r.json()
            # 400 with "errors" still means it's GraphQL
            if "data" in body or "errors" in body:
                print(f"  ✓ {url} — HTTP {r.status_code}")
                return True
        print(f"  ✗ {url} — HTTP {r.status_code}")
        return False
    except Exception as e:
        print(f"  ✗ {url} — {e}")
        return False


def dump_schema(url: str, token: str, extra_headers: dict) -> dict | None:
    """Attempt full introspection query. Returns schema dict or None."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        **extra_headers,
    }
    r = httpx.post(
        url,
        json={"query": INTROSPECTION_QUERY},
        headers=headers,
        timeout=30,
    )
    body = r.json()
    if "data" in body and body["data"]:
        return body["data"]
    if "errors" in body:
        for err in body["errors"]:
            if "introspection" in str(err).lower():
                print("  Introspection disabled on this endpoint.")
                return None
    return None


def main():
    tokens = load_tokens()
    if not tokens:
        print("No tokens found. Run `feeld auth` first (Task 2).")
        sys.exit(1)

    token = tokens["id_token"]
    extra_headers = get_extra_headers()

    print("Trying candidate GraphQL endpoints...")
    working_endpoints = []
    for url in CANDIDATE_ENDPOINTS:
        if try_endpoint(url, token, extra_headers):
            working_endpoints.append(url)

    if not working_endpoints:
        print("\nNo endpoints responded. You'll need to run Proxyman.")
        print("See RECON.md → Step B for proxy instructions.")
        sys.exit(1)

    print(f"\nWorking endpoints: {working_endpoints}")
    endpoint = working_endpoints[0]
    print(f"Using: {endpoint}")

    print("\nAttempting schema introspection...")
    schema = dump_schema(endpoint, token, extra_headers)

    out_dir = Path(__file__).parent.parent

    if schema:
        schema_file = out_dir / "RECON-schema.json"
        schema_file.write_text(json.dumps(schema, indent=2))
        print(f"Full schema written to {schema_file}")

        # Extract query/mutation names for easy reading
        queries_file = out_dir / "RECON-queries.txt"
        lines = ["=== QUERIES ===\n"]
        query_type = schema.get("__schema", {}).get("queryType", {})
        for field in query_type.get("fields", []):
            desc = field.get("description", "")
            lines.append(f"  {field['name']}" + (f" — {desc}" if desc else ""))

        lines.append("\n=== MUTATIONS ===\n")
        mutation_type = schema.get("__schema", {}).get("mutationType", {})
        for field in (mutation_type or {}).get("fields", []):
            lines.append(f"  {field['name']}")

        queries_file.write_text("\n".join(lines))
        print(f"Query names written to {queries_file}")
        print("\nLook for: likes, passes, dislikes, swipes, connections, matches")
        print("Those field names go into feeld/queries.py (Task 5).")
    else:
        print("Introspection disabled. Endpoint confirmed working though.")
        print("Run Proxyman to capture query names from live traffic.")
        print(f"Add discovered endpoint to .env as FEELD_GRAPHQL_ENDPOINT={endpoint}")

    # Save the working endpoint to config
    from feeld.config import save_config
    save_config(endpoint, extra_headers)


if __name__ == "__main__":
    main()
