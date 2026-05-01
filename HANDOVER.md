# HANDOVER — felt (feeld-local) → Claude Code

**Date:** 2026-05-01
**From:** Wizard (Hermes session)
**To:** Claude Code (next session)
**Repo:** ~/dev/feeld-local/ — remote: https://github.com/nosleepcassette/felt
**Branch:** main
**Last commit:** b54608e

---

## What This Is

A personal Feeld dating app client. CLI + TUI + web. Talks directly to Feeld's GraphQL API using Firebase auth. The goal: see who likes you, who pings you, your matches, and the discovery feed — all from the terminal, without the iOS app's limitations.

## Current State: WORKING AUTH, QUERIES CONFIRMED, NEEDS LIVE TESTING

The code compiles and imports clean. Auth works via `feeld auth "magic_link_url"`. But we haven't done a full end-to-end test with live data yet — that's the next step.

---

## Auth — What Works, What Doesn't

### WORKS: `feeld auth "magic_link_url"`
Paste a full magic link URL and it extracts oobCode, apiKey, and email automatically, then exchanges for Firebase tokens. This is the recommended auth path right now.

The magic link URL format is:
```
https://feeld.onelink.me/TRZt/dkln0wth?isSignUpFlow=false&link=https%3A%2F%2Ff2-prod-53475.firebaseapp.com%2F__%2Fauth%2Faction%3FapiKey%3DFEELD_FIREBASE_API_KEY%26mode%3DsignIn%26oobCode%3DXXXXX%26continueUrl%3D...
```

The parser handles the nested URL encoding (onelink.me → firebaseapp.com) and extracts:
- `oobCode` — one-time auth code
- `apiKey` — `FEELD_FIREBASE_API_KEY`
- `email` — from the continueUrl parameter

### DOESN'T WORK: `feeld auth` (interactive send)
The `sendSignInLinkToEmail` Firebase endpoint returns 404 from this machine. We tried multiple API keys and endpoint URLs — all 404. This might be a network issue, or it might need a different Firebase SDK version header. The reference repo (niewiemczego/Feeld) uses the same endpoint for token *refresh* and that works, so it's specifically the sendSignInLinkToEmail call that's broken. This is a nice-to-have, not blocking — the direct link auth path works fine.

**To get a magic link:** Log out of the Feeld iOS app. It'll email you a login link. Copy the link URL and paste it into `feeld auth "..."`.

### Token Refresh
The refresh token endpoint (`securetoken.googleapis.com/v1/token`) is confirmed working by the reference repo. Once you have tokens, they auto-refresh via `get_valid_token()`.

---

## Firebase Details (CONFIRMED FROM REAL MAGIC LINKS)

| Key | Value | Source |
|-----|-------|--------|
| API Key | `FEELD_FIREBASE_API_KEY` | Real magic link URL |
| Firebase Project | `f2-prod-53475` | Real magic link URL |
| Firebase App Domain | `f2-prod-53475.firebaseapp.com` | Real magic link URL |
| Bundle ID | `com.3nder.threender` | Reference repo + magic link |
| GraphQL Endpoint | `https://core.api.fldcore.com/graphql` | Reference repo (confirmed) |
| Chat API | `https://chat.stream-io-api.com` | Reference repo |
| iOS App Version | `7.25.0` | Reference repo |
| Firebase SDK Version | `iOS/FirebaseSDK/10.20.0/FirebaseCore-iOS` | Reference repo |

**IMPORTANT:** The API key from the reference repo (`FEELD_FIREBASE_API_KEY_ALT`) is for a DIFFERENT Firebase project and does NOT work with Feeld's current auth. The correct key is already embedded in config.py as DEFAULT_FIREBASE_API_KEY.

---

## Reference Repo — WHAT TO USE AND WHAT TO IGNORE

There's a reverse-engineered Feeld API wrapper at `~/bin/feeld/` (source: github.com/niewiemczego/Feeld). I already mined everything useful from it. Here's what I took and what you can skip:

### ALREADY INCORPORATED (do not re-mine):
- **GraphQL endpoint URL** (`core.api.fldcore.com`) — in config.py
- **All query names and field structures** — in queries.py (whoLikesMe, whoPingsMe, DiscoverProfiles, HeaderSummaries, AuthProviderQuery, ProfileLike, ProfileDislike, ProfilePing, ProfileAcceptPing, ProfileBlock, etc.)
- **Auth headers** (x-client-version, x-ios-bundle-identifier, user-agent) — in auth.py
- **Client headers** (x-device-os, x-app-version, user-agent: feeld-mobile) — in client.py
- **Token refresh flow** — in auth.py (uses same endpoint as reference repo)
- **Data model field names** (imaginaryName, pictureUrl, interactionStatus, etc.) — in queries.py, web/app.py, tui/app.py

### STILL USEFUL (check if needed):
- **Chat functionality** — the reference repo has chat message sending (text, image, video) via Stream API. We have the chat summaries query but no message send/receive. If maps wants chat, check `~/bin/feeld/feeld/chat/`.
- **Profile update mutations** — the reference repo has ProfileUpdate, ProfileLocationUpdate, SearchSettingsUpdate. We have the queries but not these mutations wired up.
- **noble_tls** — the reference repo uses TLS fingerprint spoofing (noble_tls) to avoid bot detection. We're using plain httpx. If Feeld starts blocking requests, this may be needed.

### IGNORE:
- The reference repo's API key (wrong project)
- The reference repo's refresh token format (same endpoint, different wrapper)
- The reference repo's proxy manager (not needed for personal use)
- The reference repo's data models (pydantic-style, we use raw dicts)

---

## Known Issues / Next Steps

1. **GraphQL 400 Bad Request on live calls** — After authenticating, API calls to `core.api.fldcore.com/graphql` return 400. Observed from `feeld web` when hitting `/api/likes`, `/api/me`, `/api/matches`. The queries are from the reference repo and *should* be correct, but something in the request format is wrong. Likely causes:
   - Missing or wrong `x-profile-id` header (Feeld requires this on most queries — need to fetch it from the AuthProviderQuery first and set it on the client)
   - The AuthProviderQuery itself might need a profile ID header, creating a chicken-and-egg problem (check how the reference repo handles initial profile fetch)
   - Query format differences (the reference repo sends `operationName` as a top-level key, which our client does — verify)
   - Token format issue (Bearer prefix, expired token, etc.)
   - **This is the blocking issue. Everything else is cosmetic.**

2. **sendSignInLinkToEmail 404** — The interactive "send me a magic link" flow doesn't work. Returns 404 from googleapis on this machine. Low priority since direct link auth works.

3. **Web frontend just updated** — HTML/JS now use the real field names (displayName from the API dict, not event.profile.displayName). Tabs are likes/pings/matches/discovery. Removed /api/stats and /api/passes calls. But can't verify rendering until the 400 is fixed.

4. **Models are raw dicts** — The old models.py had dataclasses (Profile, SwipeEvent, Match) but the real API returns nested dicts with different field names. Currently everything just passes dicts through. Could rebuild proper models if wanted.

5. **No chat** — We can list chat summaries (matches) but can't read or send messages. The reference repo has this if needed.

6. **CLI data commands** — `feeld likes`, `feeld matches` etc. still try to use the old dataclass-based serialization (`cmd_json_output` in cli.py). Need to update to work with raw dicts.

7. **Project rename** — The directory is still `feeld-local`, the CLI is still `feeld`, but the project/repo name is now **felt**. The GitHub remote is set to `nosleepcassette/felt`. A future step could rename the directory to `felt` and the package to `felt`, keeping `feeld` as just the CLI command name.

8. **`.env` has stale oobCode line** — Harmless but messy. Clean up if you want.

9. **Web app 500 errors** — The `/api/me` and `/api/likes` routes return 500 because the underlying GraphQL call fails with 400. Once the GraphQL request format is fixed (issue #1), these should work.

10. **The reference repo's HTTPManager needs study for the x-profile-id flow** — The `niewiemczego/Feeld` code at `~/bin/feeld/feeld/networking/http_manager.py` has a `_set_profile_data()` method that sets the profile ID from the auth response. Our client doesn't do this yet. Feeld's API likely requires `x-profile-id` in the headers for most queries. The flow is: (1) call AuthProviderQuery with just the Bearer token, (2) extract profile ID from response, (3) set it as `x-profile-id` header on all subsequent requests. **This is almost certainly the cause of the 400s.**

---

## File Map

```
~/dev/feeld-local/
├── .env                          # FEELD_EMAIL, FEELD_FIREBASE_API_KEY
├── .gitignore
├── README.md                     # Project overview
├── pyproject.toml                # Package config (feeld-local 0.1.0)
├── feeld/
│   ├── __init__.py
│   ├── auth.py                   # Firebase auth: send_magic_link, exchange_magic_link,
│   │                             #   refresh_id_token, get_valid_token, do_auth_flow,
│   │                             #   do_link_auth (the one that works)
│   ├── cli.py                    # argparse CLI: auth, status, likes, matches, tui, web
│   ├── client.py                 # FeeldClient — GraphQL with rate limit + auto-refresh
│   ├── config.py                 # API keys, endpoints, DEFAULT_FIREBASE_API_KEY
│   ├── models.py                 # Old dataclass models (mostly unused now)
│   └── queries.py                # ALL confirmed queries + mutations + fetch functions
├── tui/
│   └── app.py                    # urwid TUI (4 tabs: likes, pings, matches, discovery)
├── web/
│   ├── app.py                    # Flask web app + JSON API
│   ├── templates/
│   │   └── index.html
│   └── static/
│       ├── style.css
│       └── app.js
├── scripts/
│   └── introspect.py             # GraphQL schema introspection
└── BUILD_STATUS.md               # Build status (may be outdated)
```

---

## Quick Smoke Test Checklist

```bash
cd ~/dev/feeld-local
pip install -e .

# 1. Imports
python3 -c "from feeld.auth import do_link_auth; print('OK')"
python3 -c "from feeld.client import FeeldClient; print('OK')"
python3 -c "from feeld.queries import fetch_me, fetch_likes_received; print('OK')"
python3 -c "from tui.app import FeeldTUI; print('OK')"
python3 -c "from web.app import app; print('OK')"

# 2. CLI
feeld --help
feeld auth --help
feeld status

# 3. Auth with a magic link (get one from the Feeld app)
feeld auth "https://feeld.onelink.me/TRZt/..."

# 4. Check token
feeld status

# 5. Try data commands
feeld likes
feeld matches

# 6. TUI
feeld tui

# 7. Web
feeld web
# → http://localhost:5000
```

---

## Git History (6 commits)

1. `bac2f8f` — Initial build: all modules, TUI, web, CLI
2. `4fad396` — fix: interactive auth flow (prompt for email + API key)
3. `adbee2e` — feat: real API keys + confirmed queries from reference code
4. `3ea1936` — fix: handle non-JSON Firebase error responses
5. `ce34884` — feat: feeld auth [link] + fix Firebase API key (correct one)
6. `b54608e` — fix: TUI + web app updated for real API, README added

Remote: `origin → https://github.com/nosleepcassette/felt.git` (not pushed yet)
