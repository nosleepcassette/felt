# felt

Personal Feeld client. CLI, TUI, and web interface for your own dating data.

```
feeld auth "https://feeld.onelink.me/..."   # paste magic link from email
feeld status                                 # check auth
feeld likes                                  # who likes you (JSON)
feeld matches                                # your matches (JSON)
feeld tui                                    # terminal UI
feeld web                                    # http://localhost:5000
```

## What this does

Feeld's iOS app doesn't show you everything. This tool talks directly to Feeld's GraphQL API and gives you:

- **whoLikesMe** — everyone who's liked you, not just the ones the app surfaces
- **whoPingsMe** — pings you've received
- **matches** — all your chat summaries
- **discovery** — the raw discovery feed (who you could swipe on)
- **mutations** — like, dislike, ping, block (yes, from the terminal)

All queries are the real confirmed ones from the iOS app's GraphQL schema — no guessing.

## Auth

Feeld uses Firebase magic link auth (no password). Two ways to log in:

```bash
# Option 1: Paste a magic link URL directly (easiest)
# Log out of the Feeld app → it emails you a login link → copy that URL
feeld auth "https://feeld.onelink.me/TRZt/...?link=...%26oobCode%3D..."

# Option 2: Interactive flow (tries to send a magic link, then prompts for it)
feeld auth
```

Your refresh token is stored at `~/.feeld-local/tokens.json`. Once authenticated, you stay authenticated — tokens auto-refresh.

## Install

```bash
cd ~/dev/feeld-local
pip install -e .
```

Requires Python 3.11+. Dependencies: httpx, flask, urwid, python-dotenv.

## Architecture

```
feeld/
  auth.py      — Firebase magic link auth (send, exchange, refresh)
  client.py    — GraphQL client with rate limiting and auto-refresh
  config.py    — API keys, endpoints, config persistence
  models.py    — data models (currently minimal, API returns dicts)
  queries.py   — all confirmed GraphQL queries + mutations + fetch helpers
  cli.py       — argparse CLI entry point
tui/
  app.py       — urwid TUI (likes, pings, matches, discovery tabs)
web/
  app.py       — Flask web app (JSON API + frontend)
  templates/   — HTML
  static/      — JS, CSS
scripts/
  introspect.py — dump the GraphQL schema for debugging
```

## Firebase details

- **API key**: `FEELD_FIREBASE_API_KEY` (public, embedded in every magic link)
- **Project**: `f2-prod-53475`
- **Bundle ID**: `com.3nder.threender` (legacy from when Feeld was "3nder")
- **GraphQL endpoint**: `https://core.api.fldcore.com/graphql`

## Reference

The confirmed queries and auth flow were sourced from [niewiemczego/Feeld](https://github.com/niewiemczego/Feeld), a community reverse-engineered Python wrapper for the Feeld API. That repo's refresh token endpoint and API key were for a different Firebase project — the correct key was extracted from a real magic link URL.

## Disclaimer

This is an independent, personal tool. Not affiliated with or endorsed by Feeld/Feeld Ltd. Use responsibly. Don't be a creep.

---

## support this work

maps is currently navigating severe financial precarity and is at real risk of losing her housing. if this project has been useful to you — or you just think what she's building is worth keeping alive — please consider throwing a few dollars her way. it goes directly toward keeping the lights on.

[ko-fi.com/nosleepcassette](https://ko-fi.com/nosleepcassette) · venmo: **@keaghoul** · cashapp: **$keaghoul** · [cassette.help](https://cassette.help)

<!-- cassette.help/donate -->
