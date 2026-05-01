# maps · cassette.help · MIT
"""
Configuration loader.
Reads from ~/.feeld-local/config.json and .env in project root.
"""

import json
import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root (wherever this package is installed from)
_env_path = Path(__file__).parent.parent / ".env"
if _env_path.exists():
    load_dotenv(_env_path)

CONFIG_DIR = Path.home() / ".feeld-local"
CONFIG_FILE = CONFIG_DIR / "config.json"
TOKEN_FILE = CONFIG_DIR / "tokens.json"


def get_firebase_api_key() -> str:
    key = os.environ.get("FEELD_FIREBASE_API_KEY", "")
    if not key:
        raise RuntimeError(
            "FEELD_FIREBASE_API_KEY not set. Add it to ~/dev/feeld-local/.env\n"
            "Get it from the magic link URL (apiKey= parameter)."
        )
    return key


def get_email() -> str:
    email = os.environ.get("FEELD_EMAIL", "")
    if not email:
        raise RuntimeError("FEELD_EMAIL not set. Add it to ~/dev/feeld-local/.env")
    return email


def get_graphql_endpoint() -> str:
    """Return GraphQL endpoint. Reads from config or env."""
    endpoint = os.environ.get("FEELD_GRAPHQL_ENDPOINT", "")
    if endpoint:
        return endpoint
    if CONFIG_FILE.exists():
        data = json.loads(CONFIG_FILE.read_text())
        if data.get("graphql_endpoint"):
            return data["graphql_endpoint"]
    # Default to most likely endpoint — override if wrong
    return "https://api.feeld.co/graphql"


def get_extra_headers() -> dict:
    """Return extra headers discovered during recon (if any)."""
    if CONFIG_FILE.exists():
        data = json.loads(CONFIG_FILE.read_text())
        return data.get("extra_headers", {})
    return {}


def save_config(endpoint: str, extra_headers: dict = None):
    """Persist discovered config."""
    CONFIG_DIR.mkdir(exist_ok=True)
    data = {
        "graphql_endpoint": endpoint,
        "extra_headers": extra_headers or {},
    }
    CONFIG_FILE.write_text(json.dumps(data, indent=2))
    print(f"Config saved to {CONFIG_FILE}")
