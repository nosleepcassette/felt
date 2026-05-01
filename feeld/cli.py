# maps · cassette.help · MIT
"""
feeld CLI entry point.

Commands:
 feeld auth — authenticate (sends magic link, exchanges for tokens)
 feeld auth --fresh — force re-auth (clear existing tokens first)
 feeld introspect — map Feeld's GraphQL schema (run after auth)
 feeld web — start web UI at localhost:5000
 feeld tui — launch urwid TUI
 feeld likes — print likes to stdout (JSON)
 feeld passes — print passes to stdout (JSON)
 feeld matches — print matches to stdout (JSON)
 feeld status — show auth status + token expiry
"""

import argparse
import json
import sys


def cmd_auth(args):
    from feeld.auth import do_auth_flow, do_link_auth, load_tokens
    if args.fresh:
        from feeld.config import TOKEN_FILE
        if TOKEN_FILE.exists():
            TOKEN_FILE.unlink()
        print("Cleared existing tokens.")
    if args.link:
        # Direct magic link exchange — skip the send step
        do_link_auth(args.link)
    else:
        do_auth_flow()


def cmd_status(args):
    from feeld.auth import load_tokens
    import time, datetime
    tokens = load_tokens()
    if not tokens:
        print("Not authenticated. Run: feeld auth")
        sys.exit(1)
    exp = tokens.get("expires_at", 0)
    remaining = exp - time.time()
    if remaining > 0:
        print(f"Authenticated: {tokens.get('email', 'unknown')}")
        print(f"Token expires: {datetime.datetime.fromtimestamp(exp)} ({int(remaining)}s remaining)")
        print("Refresh token: present (auto-refresh on next request)")
    else:
        print(f"Authenticated: {tokens.get('email', 'unknown')}")
        print("Token: expired (will auto-refresh on next request)")


def cmd_introspect(args):
    import subprocess, sys
    from pathlib import Path
    script = Path(__file__).parent.parent / "scripts" / "introspect.py"
    subprocess.run([sys.executable, str(script)], check=True)


def cmd_web(args):
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from web.app import run_web
    run_web()


def cmd_tui(args):
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from tui.app import run_tui
    run_tui()


def cmd_json_output(fetch_fn, args):
    """Generic JSON output command."""
    from feeld.client import FeeldClient
    client = FeeldClient()
    items = fetch_fn(client)
    # Serialize using dataclass __dict__ with custom datetime handling
    output = []
    for item in items:
        d = {}
        for k, v in item.__dict__.items():
            if k == "raw":
                continue  # Skip raw API response
            if hasattr(v, "isoformat"):
                d[k] = v.isoformat()
            elif hasattr(v, "__dict__"):
                d[k] = {
                    kk: vv for kk, vv in v.__dict__.items()
                    if not hasattr(vv, "__dict__")
                }
            else:
                d[k] = v
        output.append(d)
    print(json.dumps(output, indent=2))


def main():
    parser = argparse.ArgumentParser(
        prog="feeld",
        description="feeld-local — personal Feeld client",
    )
    sub = parser.add_subparsers(dest="command")

    # auth
    p_auth = sub.add_parser("auth", help="Authenticate via Firebase magic link")
    p_auth.add_argument("--fresh", action="store_true", help="Clear existing tokens and re-auth")
    p_auth.add_argument("link", nargs="?", default=None, help="Magic link URL (from email) — skips the send step")

    # status
    sub.add_parser("status", help="Show auth status")

    # introspect
    sub.add_parser("introspect", help="Map Feeld's GraphQL API schema")

    # web
    sub.add_parser("web", help="Start web UI at http://localhost:5000")

    # tui
    sub.add_parser("tui", help="Launch terminal UI")

    # data commands
    p_likes = sub.add_parser("likes", help="Print received likes as JSON")
    p_likes.add_argument("--limit", type=int, default=50)

    p_passes = sub.add_parser("passes", help="Print received passes as JSON")
    p_passes.add_argument("--limit", type=int, default=50)

    p_matches = sub.add_parser("matches", help="Print matches as JSON")
    p_matches.add_argument("--limit", type=int, default=50)

    args = parser.parse_args()

    if args.command == "auth":
        cmd_auth(args)
    elif args.command == "status":
        cmd_status(args)
    elif args.command == "introspect":
        cmd_introspect(args)
    elif args.command == "web":
        cmd_web(args)
    elif args.command == "tui":
        cmd_tui(args)
    elif args.command == "likes":
        from feeld.queries import fetch_likes_received
        cmd_json_output(lambda c: fetch_likes_received(c, limit=args.limit), args)
    elif args.command == "passes":
        from feeld.queries import fetch_passes_received
        cmd_json_output(lambda c: fetch_passes_received(c, limit=args.limit), args)
    elif args.command == "matches":
        from feeld.queries import fetch_matches
        cmd_json_output(lambda c: fetch_matches(c, limit=args.limit), args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
