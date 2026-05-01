# maps · cassette.help · MIT
"""
Flask web app for feeld-local.
Runs on http://localhost:5000
All API calls go through this server to avoid CORS issues.
"""

import json
from flask import Flask, jsonify, render_template, request

from feeld.client import FeeldClient, FeeldAPIError, FeeldAuthError
from feeld.queries import (
    fetch_likes_received,
    fetch_matches,
    fetch_me,
    fetch_discovery,
    fetch_pings_received,
)

app = Flask(__name__, template_folder="templates", static_folder="static")

_client: FeeldClient | None = None


def get_client() -> FeeldClient:
    global _client
    if _client is None:
        _client = FeeldClient()
    return _client


def _error(message: str, status: int = 500):
    return jsonify({"error": message}), status


# ---------------------------------------------------------------------------
# API routes — called by the frontend via fetch()
# ---------------------------------------------------------------------------

@app.route("/api/me")
def api_me():
    try:
        account = fetch_me(get_client())
        # Account has profiles array — grab the first one
        profiles = account.get("profiles", [])
        profile = profiles[0] if profiles else {}
        return jsonify({
            "id": profile.get("id", ""),
            "displayName": profile.get("imaginaryName", ""),
            "age": profile.get("age", ""),
            "gender": profile.get("gender", ""),
            "bio": profile.get("bio", ""),
            "isMajestic": profile.get("isMajestic", False),
            "isVerified": profile.get("isVerified", False),
            "primaryPhotoUrl": (
                profile.get("photos", [{}])[0].get("pictureUrl", "")
                if profile.get("photos") else ""
            ),
        })
    except FeeldAuthError as e:
        return _error(str(e), 401)
    except Exception as e:
        return _error(str(e))


@app.route("/api/likes")
def api_likes():
    limit = min(int(request.args.get("limit", 50)), 200)
    try:
        nodes = fetch_likes_received(get_client())
        return jsonify([_profile_to_dict(n) for n in nodes[:limit]])
    except FeeldAuthError as e:
        return _error(str(e), 401)
    except Exception as e:
        return _error(str(e))


@app.route("/api/pings")
def api_pings():
    limit = min(int(request.args.get("limit", 50)), 200)
    try:
        nodes = fetch_pings_received(get_client(), limit=limit)
        return jsonify([_profile_to_dict(n) for n in nodes])
    except FeeldAuthError as e:
        return _error(str(e), 401)
    except Exception as e:
        return _error(str(e))


@app.route("/api/matches")
def api_matches():
    limit = min(int(request.args.get("limit", 50)), 200)
    try:
        nodes = fetch_matches(get_client(), limit=limit)
        return jsonify([_match_to_dict(n) for n in nodes])
    except FeeldAuthError as e:
        return _error(str(e), 401)
    except Exception as e:
        return _error(str(e))


@app.route("/api/discovery")
def api_discovery():
    try:
        nodes = fetch_discovery(get_client())
        return jsonify([_profile_to_dict(n) for n in nodes])
    except FeeldAuthError as e:
        return _error(str(e), 401)
    except Exception as e:
        return _error(str(e))


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------

def _profile_to_dict(p: dict) -> dict:
    """Convert a raw Feeld profile dict to frontend-friendly JSON."""
    interaction = p.get("interactionStatus", {})
    distance = p.get("distance", {})
    return {
        "id": p.get("id", ""),
        "displayName": p.get("imaginaryName", ""),
        "age": p.get("age", ""),
        "gender": p.get("gender", ""),
        "sexuality": p.get("sexuality", ""),
        "bio": p.get("bio", ""),
        "desires": p.get("desires", []),
        "interests": p.get("interests", []),
        "isMajestic": p.get("isMajestic", False),
        "isVerified": p.get("isVerified", False),
        "isUplift": p.get("isUplift", False),
        "lastSeen": p.get("lastSeen", ""),
        "distanceKm": distance.get("km"),
        "interactionStatus": {
            "mine": interaction.get("mine", ""),
            "theirs": interaction.get("theirs", ""),
            "message": interaction.get("message", ""),
        },
        "primaryPhotoUrl": (
            p.get("photos", [{}])[0].get("pictureUrl", "")
            if p.get("photos") else ""
        ),
        "photos": [
            {"url": ph.get("pictureUrl", ""), "id": ph.get("id", "")}
            for ph in (p.get("photos") or [])
        ],
    }


def _match_to_dict(m: dict) -> dict:
    """Convert a raw chat summary dict to frontend-friendly JSON."""
    return {
        "id": m.get("id", ""),
        "name": m.get("name", ""),
        "type": m.get("type", ""),
        "status": m.get("status", ""),
        "latestMessage": m.get("latestMessage", ""),
        "streamChannelId": m.get("streamChannelId", ""),
        "targetProfileId": m.get("targetProfileId", ""),
    }


# ---------------------------------------------------------------------------
# Frontend route
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


def run_web():
    """Entry point called by CLI."""
    print("feeld-local web UI: http://localhost:5000")
    app.run(host="127.0.0.1", port=5000, debug=False)
