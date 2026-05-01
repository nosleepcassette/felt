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


def get_firebase_api_key() -> str | None:
    """Return Firebase API key if available, None otherwise.
    Does NOT raise — allows interactive flows to prompt for it."""
    return os.environ.get("FEELD_FIREBASE_API_KEY", "") or None


def require_firebase_api_key() -> str:
    """Return Firebase API key or raise. Use when key is required with no fallback."""
    key = get_firebase_api_key()
    if not key:
        raise RuntimeError(
            "FEELD_FIREBASE_API_KEY not set. Add it to ~/dev/feeld-local/.env\n"
            "Get it from the magic link URL (apiKey= parameter)."
        )
    return key


def get_email() -> str | None:
    """Return email if available, None otherwise."""
    return os.environ.get("FEELD_EMAIL", "") or None


def require_email() -> str:
    """Return email or raise."""
    email = get_email()
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
    data = {}
    if CONFIG_FILE.exists():
        data = json.loads(CONFIG_FILE.read_text())
    data["graphql_endpoint"] = endpoint
    data["extra_headers"] = extra_headers or {}
    CONFIG_FILE.write_text(json.dumps(data, indent=2))
    print(f"Config saved to {CONFIG_FILE}")


def save_api_key(api_key: str):
    """Persist the Firebase API key to .env (appends if file exists)."""
    env_path = Path(__file__).parent.parent / ".env"
    lines = []
    if env_path.exists():
        lines = env_path.read_text().splitlines()

    # Update existing or append
    found = False
    for i, line in enumerate(lines):
        if line.startswith("FEELD_FIREBASE_API_KEY="):
            lines[i] = f"FEELD_FIREBASE_API_KEY={api_key}"
            found = True
            break
    if not found:
        lines.append(f"FEELD_FIREBASE_API_KEY={api_key}")

    env_path.write_text("\n".join(lines) + "\n")
    # Also set in current process env so it's available immediately
    os.environ["FEELD_FIREBASE_API_KEY"] = api_key


def save_email(email: str):
    """Persist email to .env."""
    env_path = Path(__file__).parent.parent / ".env"
    lines = []
    if env_path.exists():
        lines = env_path.read_text().splitlines()

    found = False
    for i, line in enumerate(lines):
        if line.startswith("FEELD_EMAIL="):
            lines[i] = f"FEELD_EMAIL={email}"
            found = True
            break
    if not found:
        lines.append(f"FEELD_EMAIL={email}")

    env_path.write_text("\n".join(lines) + "\n")
    os.environ["FEELD_EMAIL"] = email
