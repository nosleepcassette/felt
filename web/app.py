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
    fetch_passes_received,
    fetch_profile_stats,
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
        profile = fetch_me(get_client())
        return jsonify({
            "id": profile.id,
            "displayName": profile.display_name,
            "age": profile.age,
            "primaryPhotoUrl": profile.primary_photo_url,
        })
    except FeeldAuthError as e:
        return _error(str(e), 401)
    except Exception as e:
        return _error(str(e))


@app.route("/api/stats")
def api_stats():
    try:
        stats = fetch_profile_stats(get_client())
        return jsonify(stats)
    except Exception as e:
        return _error(str(e))


@app.route("/api/likes")
def api_likes():
    limit = min(int(request.args.get("limit", 50)), 200)
    try:
        events = fetch_likes_received(get_client(), limit=limit)
        return jsonify([_swipe_to_dict(e) for e in events])
    except FeeldAuthError as e:
        return _error(str(e), 401)
    except Exception as e:
        return _error(str(e))


@app.route("/api/passes")
def api_passes():
    limit = min(int(request.args.get("limit", 50)), 200)
    try:
        events = fetch_passes_received(get_client(), limit=limit)
        return jsonify([_swipe_to_dict(e) for e in events])
    except FeeldAuthError as e:
        return _error(str(e), 401)
    except Exception as e:
        return _error(str(e))


@app.route("/api/matches")
def api_matches():
    limit = min(int(request.args.get("limit", 50)), 200)
    try:
        matches = fetch_matches(get_client(), limit=limit)
        return jsonify([_match_to_dict(m) for m in matches])
    except FeeldAuthError as e:
        return _error(str(e), 401)
    except Exception as e:
        return _error(str(e))


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------

def _swipe_to_dict(event) -> dict:
    p = event.profile
    return {
        "id": event.id,
        "action": event.action,
        "timeAgo": event.time_ago,
        "profile": {
            "id": p.id,
            "displayName": p.display_name,
            "age": p.age,
            "gender": p.gender,
            "bio": p.bio,
            "desires": p.desires,
            "primaryPhotoUrl": p.primary_photo_url,
            "photos": [{"url": ph.url} for ph in p.photos],
        },
    }


def _match_to_dict(match) -> dict:
    p = match.profile
    return {
        "id": match.id,
        "matchedAt": match.matched_at.isoformat() if match.matched_at else None,
        "unreadCount": match.unread_count,
        "lastMessage": match.last_message,
        "profile": {
            "id": p.id,
            "displayName": p.display_name,
            "age": p.age,
            "primaryPhotoUrl": p.primary_photo_url,
        },
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
