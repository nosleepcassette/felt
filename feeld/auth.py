# maps · cassette.help · MIT
"""
Firebase authentication for Feeld.

Feeld uses Firebase email magic link auth (signInWithEmailLink).
Flow:
 1. Call Firebase sendSignInLinkToEmail to trigger the magic link email
 2. Firebase emails a link with oobCode + apiKey
 3. We exchange oobCode + email + apiKey for idToken + refreshToken
 4. idToken is valid for 1 hour
 5. refreshToken is valid indefinitely — we use it to get new idTokens

Storage:
 ~/.feeld-local/tokens.json (created on first login, never committed)

Usage:
 from feeld.auth import send_magic_link, exchange_magic_link, get_valid_token

 # Step 1: Request the magic link (emails you a login link)
 send_magic_link(email, api_key)

 # Step 2: After clicking the link, extract oobCode and exchange it
 token_data = exchange_magic_link(oob_code, email, api_key)

 # Every subsequent request
 token = get_valid_token()
"""

import json
import os
import time
from pathlib import Path
from urllib.parse import parse_qs, urlparse, unquote

import httpx

from feeld.config import (
    CONFIG_DIR,
    TOKEN_FILE,
    get_email,
    get_firebase_api_key,
    save_api_key,
    save_email,
)

# Firebase endpoints — these are public/documented, not Feeld-specific
FIREBASE_SEND_LINK_URL = "https://identitytoolkit.googleapis.com/v1/accounts:sendSignInLinkToEmail"
FIREBASE_SIGN_IN_URL = "https://identitytoolkit.googleapis.com/v1/accounts:signInWithEmailLink"
FIREBASE_REFRESH_URL = "https://securetoken.googleapis.com/v1/token"

# Feeld's Firebase API key is in every magic link URL as `apiKey=`
# It is NOT secret (it's embedded in the published iOS app).
# Do not confuse with a private API key.


def send_magic_link(email: str, api_key: str) -> None:
    """
    Request a Firebase magic link email for the given address.

    This calls Firebase's sendSignInLinkToEmail endpoint, which sends
    an email with a login link containing the oobCode. The email arrives
    in seconds. You then extract the oobCode from the link URL and
    pass it to exchange_magic_link().

    Args:
        email: The email address associated with your Feeld account
        api_key: Feeld's Firebase Web API Key (from .env or config)

    Raises:
        RuntimeError: if Firebase rejects the request (invalid email, etc.)

    The oobCode will be embedded in the link URL as the `oobCode=` parameter.
    The link format is typically:
      https://feeld.page.link/?link=https%3A%2F%2Ffeeld.co%2F__auth%2Faction%3FapiKey%3D...%26oobCode%3DXXXX...
    or:
      https://feeld.co/__/auth/action?apiKey=...&mode=signIn&oobCode=XXXX...
    """
    r = httpx.post(
        f"{FIREBASE_SEND_LINK_URL}?key={api_key}",
        json={
            "email": email,
            "requestType": "SIGN_IN",
            "continueUrl": "https://feeld.co/__/auth/action",
            "iOSBundleId": "com.3nder.threender",
        },
        headers={
            "Content-Type": "application/json",
            "x-client-version": "iOS/FirebaseSDK/10.20.0/FirebaseCore-iOS",
            "x-ios-bundle-identifier": "com.3nder.threender",
            "user-agent": "FirebaseAuth.iOS/10.20.0 com.3nder.threender/7.18.0 iPhone/17.5.1 hw/iPhone14_5",
        },
        timeout=15,
    )

    if r.status_code != 200:
        # Firebase sometimes returns non-JSON on errors (HTML, empty body, etc.)
        try:
            body = r.json()
            error = body.get("error", {}).get("message", "Unknown Firebase error")
        except Exception:
            error = f"HTTP {r.status_code}: {r.text[:200] or '(empty body)'}"
        raise RuntimeError(
            f"Failed to send magic link: {error}\n"
            f"Full response: {r.status_code} {r.reason_phrase}\n"
            "Common causes:\n"
            " - Email not associated with a Feeld account\n"
            " - Invalid Firebase API key\n"
            " - Rate limited (too many requests — wait a minute)\n"
            "Check FEELD_FIREBASE_API_KEY in .env"
        )

    print(f"✓ Magic link sent to {email}")
    print("Check your inbox (and spam folder). The email should arrive within seconds.")
    print("")
    print("Once you get the email, right-click the login button → Copy Link Address.")
    print("The link contains an `oobCode=` parameter — that's what we need next.")


def exchange_magic_link(oob_code: str, email: str, api_key: str) -> dict:
    """
    Exchange a magic link oobCode for Firebase tokens.

    Args:
        oob_code: The `oobCode` parameter from the magic link URL
        email: The email address you used to request the link
        api_key: The `apiKey` parameter from the magic link URL

    Returns:
        dict with keys: id_token, refresh_token, expires_at, local_id, email

    Raises:
        RuntimeError: if Firebase rejects the exchange (expired code, wrong email, etc.)
    """
    r = httpx.post(
        f"{FIREBASE_SIGN_IN_URL}?key={api_key}",
        json={
            "email": email,
            "oobCode": oob_code,
        },
        headers={"Content-Type": "application/json"},
        timeout=15,
    )

    if r.status_code != 200:
        try:
            body = r.json()
            error = body.get("error", {}).get("message", "Unknown Firebase error")
        except Exception:
            error = f"HTTP {r.status_code}: {r.text[:200] or '(empty body)'}"
        raise RuntimeError(
            f"Firebase auth failed: {error}\n"
            "Common causes:\n"
            " - oobCode already used (each magic link is one-time only)\n"
            " - oobCode expired (they expire quickly — use within a few minutes)\n"
            " - Email mismatch\n"
            "Request a fresh magic link and try again."
        )

    data = r.json()
    expires_in = int(data.get("expiresIn", 3600))

    tokens = {
        "id_token": data["idToken"],
        "refresh_token": data["refreshToken"],
        "local_id": data.get("localId", ""),
        "email": data.get("email", email),
        "expires_at": time.time() + expires_in - 60,  # 60s buffer
        "api_key": api_key,
    }

    _save_tokens(tokens)
    print(f"✓ Auth successful. Token valid until {_format_expiry(tokens['expires_at'])}")
    print(f"✓ Refresh token stored. You will not need to log in again.")
    return tokens


def refresh_id_token(tokens: dict) -> dict:
    """
    Use the refresh token to get a new idToken.
    Called automatically by get_valid_token() when expired.

    Args:
        tokens: Current token dict (must have refresh_token and api_key)

    Returns:
        Updated token dict with new id_token and expires_at
    """
    api_key = tokens.get("api_key") or get_firebase_api_key()

    r = httpx.post(
        f"{FIREBASE_REFRESH_URL}?key={api_key}",
        json={
            "grant_type": "refresh_token",
            "refresh_token": tokens["refresh_token"],
        },
        headers={"Content-Type": "application/json"},
        timeout=15,
    )

    if r.status_code != 200:
        try:
            body = r.json()
            error = body.get("error", {}).get("error_description", "Unknown error")
        except Exception:
            error = f"HTTP {r.status_code}: {r.text[:200] or '(empty body)'}"
        raise RuntimeError(
            f"Token refresh failed: {error}\n"
            "Your refresh token may be revoked (e.g., password change or account action).\n"
            "Run `feeld auth` to re-authenticate with a new magic link."
        )

    data = r.json()
    expires_in = int(data.get("expires_in", 3600))

    tokens["id_token"] = data["id_token"]
    tokens["refresh_token"] = data.get("refresh_token", tokens["refresh_token"])
    tokens["expires_at"] = time.time() + expires_in - 60

    _save_tokens(tokens)
    return tokens


def get_valid_token() -> str:
    """
    Return a valid Firebase ID token, refreshing if expired.
    This is the main function called by the GraphQL client.

    Returns:
        str: A valid Bearer token

    Raises:
        RuntimeError: if no tokens stored (not authenticated yet)
    """
    tokens = load_tokens()
    if not tokens:
        raise RuntimeError(
            "Not authenticated. Run:\n"
            " feeld auth\n"
            "This will send a magic link to your email."
        )

    # Check if expired (with 60s buffer already baked in)
    if time.time() > tokens.get("expires_at", 0):
        print("Token expired, refreshing...")
        tokens = refresh_id_token(tokens)

    return tokens["id_token"]


def load_tokens() -> dict | None:
    """Load stored tokens. Returns None if not authenticated."""
    if not TOKEN_FILE.exists():
        return None
    try:
        return json.loads(TOKEN_FILE.read_text())
    except (json.JSONDecodeError, IOError):
        return None


def _save_tokens(tokens: dict):
    """Persist tokens to disk."""
    CONFIG_DIR.mkdir(exist_ok=True)
    TOKEN_FILE.write_text(json.dumps(tokens, indent=2))
    # Restrict permissions — tokens are sensitive
    TOKEN_FILE.chmod(0o600)


def _format_expiry(ts: float) -> str:
    import datetime
    return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")


def _extract_oob_code_from_url(url: str) -> str | None:
    """
    Extract the oobCode from a magic link URL.

    Handles both formats:
    - https://feeld.co/__/auth/action?apiKey=...&mode=signIn&oobCode=XXXX
    - https://feeld.page.link/?link=https%3A%2F%2Ffeeld.co%2F__auth%2Faction%3FapiKey%3D...%26oobCode%3DXXXX
    """
    # Try direct URL first
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    if "oobCode" in params:
        return params["oobCode"][0]

    # Try extracting from the encoded `link` parameter (page.link format)
    if "link" in params:
        inner_url = unquote(params["link"][0])
        inner_parsed = urlparse(inner_url)
        inner_params = parse_qs(inner_parsed.query)
        if "oobCode" in inner_params:
            return inner_params["oobCode"][0]

    return None


def _extract_api_key_from_url(url: str) -> str | None:
    """
    Extract the Firebase API key from a magic link URL.

    Handles both direct and page.link/onelink.me formats.
    """
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    if "apiKey" in params:
        return params["apiKey"][0]

    if "link" in params:
        inner_url = unquote(params["link"][0])
        inner_parsed = urlparse(inner_url)
        inner_params = parse_qs(inner_parsed.query)
        if "apiKey" in inner_params:
            return inner_params["apiKey"][0]

    return None


def _extract_email_from_url(url: str) -> str | None:
    """
    Extract email from a magic link URL.
    Feeld embeds the email in the continueUrl parameter.
    """
    parsed = urlparse(url)
    params = parse_qs(parsed.query)

    # Check outer params first
    if "email" in params:
        return unquote(params["email"][0])

    # Drill into the 'link' parameter (onelink.me / page.link format)
    if "link" in params:
        inner_url = unquote(params["link"][0])
        inner_parsed = urlparse(inner_url)
        inner_params = parse_qs(inner_parsed.query)

        # Email might be in the continueUrl within the inner URL
        if "continueUrl" in inner_params:
            cont_url = unquote(inner_params["continueUrl"][0])
            cont_parsed = urlparse(cont_url)
            cont_params = parse_qs(cont_parsed.query)
            if "email" in cont_params:
                return unquote(cont_params["email"][0])

        # Or directly in the inner URL params
        if "email" in inner_params:
            return unquote(inner_params["email"][0])

    return None


def _prompt(prompt: str, default: str = "") -> str:
    """Prompt user for input with optional default."""
    if default:
        result = input(f"{prompt} [{default}]: ").strip()
        return result if result else default
    result = input(f"{prompt}: ").strip()
    return result


def do_auth_flow():
    """
    Full interactive auth flow. Handles the complete cycle:

    On first run (no API key or email configured):
      1. Prompt for email
      2. Prompt for Firebase API key (or extract from a pasted magic link)
      3. Send magic link
      4. Accept pasted magic link URL, extract oobCode
      5. Exchange for tokens

    On subsequent runs (already configured):
      1. Check existing tokens
      2. If valid, report status
      3. If expired, send new magic link and re-auth

    Called by `feeld auth` CLI command.
    """
    # --- Step 0: Check existing auth ---
    existing_tokens = load_tokens()
    if existing_tokens:
        exp = existing_tokens.get("expires_at", 0)
        if time.time() < exp:
            print(f"Already authenticated as {existing_tokens.get('email', 'unknown')}")
            print(f"Token valid until {_format_expiry(exp)}")
            print("Use --fresh to re-authenticate.")
            return

    # --- Step 1: Get email ---
    email = get_email()
    if not email:
        print("No email configured. This is the email address for your Feeld account.")
        email = _prompt("Email")
        if not email:
            raise RuntimeError("Email is required.")
        save_email(email)
        print(f"✓ Email saved to .env")
    else:
        print(f"Email: {email}")

    # --- Step 2: Get Firebase API key (embedded default, no manual config needed) ---
    api_key = get_firebase_api_key()
    print(f"✓ Firebase API key: {api_key[:8]}...{api_key[-4:]}")

    # --- Step 3: Send the magic link ---
    print("")
    print(f"Sending magic link to {email}...")
    send_magic_link(email, api_key)

    # --- Step 4: Get the oobCode from the user ---
    print("")
    print("Paste the full magic link URL (or just the oobCode):")
    user_input = _prompt("> ")

    if not user_input:
        raise RuntimeError("No link provided. Run `feeld auth` to try again.")

    # Try to extract oobCode from a URL, or use the input directly if it looks like a code
    oob_code = _extract_oob_code_from_url(user_input)
    if not oob_code:
        # Maybe they pasted just the code (raw oobCode is a long alphanumeric string)
        if len(user_input) > 20 and "/" not in user_input:
            oob_code = user_input
        else:
            raise RuntimeError(
                "Could not extract oobCode from that input.\n"
                "Paste the full URL from the email, or just the oobCode value."
            )

    # --- Step 5: Exchange the oobCode for tokens ---
    print("Exchanging magic link for tokens...")
    exchange_magic_link(oob_code, email, api_key)

    print("")
    print("You're all set. Run `feeld status` to verify, or `feeld introspect` to map the API.")


def do_link_auth(link_url: str):
    """
    Direct magic link auth — skip the send step.
    Use when you already have a magic link URL (e.g. from the Feeld app's login email).

    Usage: feeld auth "https://feeld.onelink.me/TRZt/...?link=...%3FapiKey%3D...%26oobCode%3D..."

    Extracts apiKey, oobCode, and email from the URL and exchanges them for tokens.
    Also works with the inner firebaseapp.com URL directly.
    """
    print("Extracting credentials from magic link...")

    # Extract oobCode
    oob_code = _extract_oob_code_from_url(link_url)
    if not oob_code:
        raise RuntimeError(
            "Could not extract oobCode from that URL.\n"
            "Expected a URL containing 'oobCode=' parameter.\n"
            "Paste the full link from the Feeld login email."
        )
    print(f"✓ oobCode: {oob_code[:12]}...{oob_code[-4:]}")

    # Extract API key
    api_key = _extract_api_key_from_url(link_url)
    if api_key:
        print(f"✓ API key: {api_key[:8]}...{api_key[-4:]}")
        # Save it as the default going forward
        save_api_key(api_key)
    else:
        api_key = get_firebase_api_key()
        print(f"✓ Using embedded API key: {api_key[:8]}...{api_key[-4:]}")

    # Try to extract email from URL (it's in the continueUrl parameter)
    email = _extract_email_from_url(link_url)
    if not email:
        # Fall back to stored email
        email = get_email()
    if not email:
        # Last resort: prompt
        email = _prompt("Email")
        if not email:
            raise RuntimeError("Email is required.")
    print(f"✓ Email: {email}")
    save_email(email)

    # Exchange the oobCode for tokens
    print("")
    print("Exchanging magic link for tokens...")
    exchange_magic_link(oob_code, email, api_key)

    print("")
    print("You're all set. Run `feeld status` to verify, or `feeld likes` to see who's into you.")
