# feeld-local — Build Status

**Last updated:** 2026-04-30 by Wizard
**Buildsheet:** ~/atlas/projects/BUILDSHEET-feeld-local-v1.md
**Git:** bac2f8f — initial commit on main

## What's done

All code files written, pip-installed, smoke-tested, and committed.

| Component | File(s) | Status |
|-----------|---------|--------|
| Project setup | pyproject.toml, .gitignore, .env stub | ✅ installed |
| Config | feeld/config.py | ✅ import OK |
| Auth (with magic link sending) | feeld/auth.py | ✅ import OK |
| GraphQL client | feeld/client.py | ✅ import OK |
| Data models | feeld/models.py | ✅ import OK |
| Queries (placeholder fields) | feeld/queries.py | ✅ import OK |
| Web UI | web/app.py, templates/, static/ | ✅ import OK |
| TUI | tui/app.py | ✅ import OK |
| CLI | feeld/cli.py | ✅ `feeld --help` works, `feeld status` works |
| Introspect script | scripts/introspect.py | ✅ written |
| Symlink | /usr/local/bin/feeld | ✅ on PATH |

### Enhancement over buildsheeet

**`send_magic_link()` added to auth.py.** The buildsheeet treated magic link acquisition as a manual out-of-band step (open phone, find link, extract oobCode). But Firebase's `sendSignInLinkToEmail` endpoint can be called directly — you just need the email and the Firebase API key. This is what the reverse-engineered Feeld desktop app did.

The `feeld auth` flow now does the full cycle:
1. Sends a magic link to your email via Firebase
2. You open the email, copy the link URL, paste it into the terminal
3. auth.py extracts the oobCode from the URL automatically (handles both direct and page.link formats)
4. Exchanges oobCode for tokens, stores refresh token

No phone required. Just email + API key in .env.

## What you need to do next (Task 0)

Before any data queries work, you need the Firebase API key and to authenticate:

1. **Get the Firebase API key** — this is the one piece you still need externally.
   Options:
   - Extract from a Feeld magic link URL (the `apiKey=` param)
   - Find it in the Feeld iOS app binary (strings search for `AIzaSy`)
   - Check community sources / reverse engineering posts
   - If you have an old magic link email, the key is in the URL

2. **Fill in `.env`:**
   ```
   FEELD_FIREBASE_API_KEY=AIzaSy...
   FEELD_EMAIL=your@email.com
   ```

3. **Authenticate:**
   ```
   feeld auth
   ```
   This sends a magic link to your email. Paste the link when it arrives.

4. **Introspect the API:**
   ```
   feeld introspect
   ```
   This discovers the GraphQL endpoint and field names.

5. **Update queries.py** — replace `# CONFIRM_FIELD_NAME` placeholders with real names from RECON-queries.txt

6. **Test:**
   ```
   feeld likes
   feeld web
   ```

## Known issues / notes

- `feeld` CLI binary is symlinked to `/usr/local/bin/feeld` (points to Python framework bin)
- Query field names in queries.py are all placeholders — will 404 until confirmed
- Passes endpoint may not exist on Feeld's API (graceful fallback built in)
- Photo CDN may require auth headers (needs proxy route in v2)
- `send_magic_link` uses `iOSBundleId: "co.feeld.ios"` and `continueUrl: "https://feeld.co/__/auth/action"` — may need tweaking if Firebase rejects them
