#!/usr/bin/env python3
"""Refresh expiring external-service tokens stored in configs/privacy.local.env.

A unified, plugin-style entry point that walks one or more providers, checks
whether each provider's credential is still healthy, and (if not) drives the
provider-specific refresh flow.  All providers read from / write back to the
same ``configs/privacy.local.env`` file at the repo root.

Usage:
    # Check + refresh all known providers (interactive prompts as needed):
    python3 scripts/dev/refresh_tokens.py

    # Scope to one provider:
    python3 scripts/dev/refresh_tokens.py --provider gcalcli
    python3 scripts/dev/refresh_tokens.py --provider zoom
    python3 scripts/dev/refresh_tokens.py --provider ncm

    # Verify-only (no rotation, exits non-zero if any provider is broken):
    python3 scripts/dev/refresh_tokens.py --check-only

    # Don't auto-open a browser; just print the URL (SSH / headless mode):
    python3 scripts/dev/refresh_tokens.py --no-browser

Supported providers (see PROVIDERS dict at bottom of file):

    gcalcli   Google Calendar OAuth.  Fully automated via
              google_auth_oauthlib InstalledAppFlow.  Refresh tokens last
              ~6 months unless revoked.
              Env vars: GCALCLI_CLIENT_ID, GCALCLI_CLIENT_SECRET,
                        GCALCLI_OAUTH_B64.

    zoom      Zoom OAuth2.  Programmatic refresh via the standard
              ``POST /oauth/token?grant_type=refresh_token`` endpoint;
              falls back to printing the authorize URL for interactive
              re-auth if the refresh_token is itself expired.  Zoom
              rotates refresh tokens on every refresh (the new token
              replaces the old in privacy.local.env).
              Env vars: ZOOM_CLIENT_ID, ZOOM_CLIENT_SECRET,
                        ZOOM_REFRESH_TOKEN.

    ncm       NetEase Cloud Music (ncm-cli session token).  Re-auth
              requires scanning a QR code in the NetEase app, so this
              provider currently prints the manual procedure rather
              than driving the flow itself; the plumbing for writing
              the new ``NCM_TOKENS_ENC`` is in place once the manual
              flow finishes.
              Env vars: NCM_APP_ID, NCM_PRIVATE_KEY, NCM_TOKENS_ENC.

Adding a new provider:
    1. Write ``check_<name>(env) -> bool`` and ``refresh_<name>(env, args)
       -> dict[str, str]`` functions following the patterns below.
    2. Register them in the ``PROVIDERS`` dict with display name + env vars.

Maintenance note:
    Keep provider-specific code in this utility small and auditable. It should
    only read from and write to ``configs/privacy.local.env`` and should never
    print raw credential values.
"""
from __future__ import annotations

import argparse
import base64
import importlib
import json
import os
import pickle
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.parse
import webbrowser
from dataclasses import dataclass
from pathlib import Path


# ── runtime deps preflight ──────────────────────────────────────────────────
# Fail fast if a required package is missing, with the exact pip install
# command — better than crashing mid-OAuth-flow after the user has already
# clicked through Google's consent page.
_REQUIRED_PIP = {
    "google.auth": "google-auth",
    "google.auth.transport.requests": "google-auth",
    "google.oauth2.credentials": "google-auth",
    "google_auth_oauthlib.flow": "google-auth-oauthlib",
    "googleapiclient.discovery": "google-api-python-client",
    "requests": "requests",
}


def _check_deps() -> None:
    missing: set[str] = set()
    for module, pkg in _REQUIRED_PIP.items():
        try:
            importlib.import_module(module)
        except ImportError:
            missing.add(pkg)
    if missing:
        pkgs = " ".join(sorted(missing))
        sys.stderr.write(
            f"refresh_tokens.py: missing Python deps: {sorted(missing)}\n"
            f"→ Install with:\n"
            f"    pip3 install {pkgs}\n"
        )
        raise SystemExit(2)


REPO_ROOT = Path(__file__).resolve().parents[2]
PRIVACY_ENV = REPO_ROOT / "configs" / "privacy.local.env"


# ── env-file IO ─────────────────────────────────────────────────────────────


def read_env(path: Path = PRIVACY_ENV) -> dict[str, str]:
    """Parse KEY=VALUE env file (no shell interpolation, no quotes)."""
    if not path.exists():
        raise FileNotFoundError(f"{path} not found")
    out: dict[str, str] = {}
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        k, _, v = line.partition("=")
        out[k.strip()] = v.strip()
    return out


def write_env_keys(updates: dict[str, str], path: Path = PRIVACY_ENV) -> None:
    """Idempotently rewrite each key in *updates* on its own line; preserve
    every other line of *path* verbatim.  Atomic via temp + rename."""
    if not updates:
        return
    lines = path.read_text().splitlines(keepends=True)
    pending = dict(updates)
    out: list[str] = []
    for ln in lines:
        normalized = ln if ln.endswith("\n") else ln + "\n"
        stripped = normalized.split("#", 1)[0].strip()
        replaced = False
        for k in list(pending.keys()):
            if stripped.startswith(f"{k}="):
                out.append(f"{k}={pending[k]}\n")
                pending.pop(k)
                replaced = True
                break
        if not replaced:
            out.append(normalized)
    # Any keys we never saw — append at end.
    if pending:
        if out and not out[-1].endswith("\n"):
            out[-1] += "\n"
        for k, v in pending.items():
            out.append(f"{k}={v}\n")
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text("".join(out))
    os.replace(tmp, path)


# ── gcalcli ─────────────────────────────────────────────────────────────────

GCALCLI_SCOPES = ["https://www.googleapis.com/auth/calendar"]


def _gcalcli_build_creds(token_b64: str, client_id: str, client_secret: str):
    """Re-hydrate a Credentials object from base64-encoded pickle or JSON."""
    from google.oauth2.credentials import Credentials

    raw = base64.b64decode(token_b64, validate=True)
    try:
        return pickle.loads(raw)
    except Exception:
        pass
    import json as _json

    data = _json.loads(raw.decode("utf-8"))
    return Credentials(
        token=data.get("token") or data.get("access_token"),
        refresh_token=data.get("refresh_token"),
        token_uri=data.get("token_uri") or "https://oauth2.googleapis.com/token",
        client_id=data.get("client_id") or client_id,
        client_secret=data.get("client_secret") or client_secret or None,
        scopes=data.get("scopes") or GCALCLI_SCOPES,
    )


def _gcalcli_verify(creds, label: str) -> bool:
    """Issue one trivial Calendar API call."""
    from googleapiclient.discovery import build

    try:
        service = build("calendar", "v3", credentials=creds, cache_discovery=False)
        items = service.calendarList().list(maxResults=1).execute().get("items", [])
        print(f"  ✓ {label}: Calendar API reachable; {len(items)} calendar(s) visible.")
        return True
    except Exception as exc:
        print(f"  ✗ {label}: {exc}", file=sys.stderr)
        return False


def check_gcalcli(env: dict[str, str]) -> bool:
    """Try to refresh the existing GCALCLI_OAUTH_B64."""
    from google.auth.exceptions import RefreshError
    from google.auth.transport.requests import Request

    client_id = env.get("GCALCLI_CLIENT_ID", "")
    client_secret = env.get("GCALCLI_CLIENT_SECRET", "")
    token_b64 = env.get("GCALCLI_OAUTH_B64", "")
    if not (client_id and token_b64):
        print("  ✗ gcalcli: GCALCLI_CLIENT_ID or GCALCLI_OAUTH_B64 missing.", file=sys.stderr)
        return False
    try:
        creds = _gcalcli_build_creds(token_b64, client_id, client_secret)
    except Exception as exc:
        print(f"  ✗ gcalcli: GCALCLI_OAUTH_B64 unparseable: {exc}", file=sys.stderr)
        return False
    try:
        creds.refresh(Request())
    except RefreshError as exc:
        msg = "invalid_grant" if "invalid_grant" in str(exc).lower() else str(exc)
        print(f"  ✗ gcalcli: refresh failed ({msg}).", file=sys.stderr)
        return False
    except Exception as exc:
        print(f"  ✗ gcalcli: refresh raised {exc}.", file=sys.stderr)
        return False
    return _gcalcli_verify(creds, "gcalcli existing token")


def refresh_gcalcli(env: dict[str, str], args) -> dict[str, str]:
    """Run InstalledAppFlow; return {GCALCLI_OAUTH_B64: <new base64>}."""
    from google_auth_oauthlib.flow import InstalledAppFlow

    client_id = env.get("GCALCLI_CLIENT_ID", "")
    client_secret = env.get("GCALCLI_CLIENT_SECRET", "")
    if not (client_id and client_secret):
        raise RuntimeError(
            "gcalcli: GCALCLI_CLIENT_ID or GCALCLI_CLIENT_SECRET missing from privacy.local.env"
        )
    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }
    flow = InstalledAppFlow.from_client_config(client_config, GCALCLI_SCOPES)
    if args.no_browser:
        original = webbrowser.open

        def _noop(url, *a, **kw):
            print(f"\n  → Open this URL in any browser to authorize:\n    {url}\n")
            return False

        webbrowser.open = _noop  # type: ignore[assignment]
        try:
            creds = flow.run_local_server(port=0, open_browser=False)
        finally:
            webbrowser.open = original  # type: ignore[assignment]
    else:
        print("  → Opening Google OAuth consent page in your browser…")
        creds = flow.run_local_server(port=0, open_browser=True)

    if not _gcalcli_verify(creds, "gcalcli freshly issued token"):
        raise RuntimeError("gcalcli: new credential failed verification.")

    new_b64 = base64.b64encode(pickle.dumps(creds)).decode("ascii")
    expiry = getattr(creds, "expiry", None)
    expiry_str = expiry.isoformat() if expiry else "<unknown>"
    print(f"  ✓ gcalcli: new access token valid until {expiry_str}.")
    return {"GCALCLI_OAUTH_B64": new_b64}


# ── zoom ────────────────────────────────────────────────────────────────────

ZOOM_TOKEN_URL = "https://zoom.us/oauth/token"
ZOOM_AUTHORIZE_URL = "https://zoom.us/oauth/authorize"


def _zoom_basic_auth(client_id: str, client_secret: str) -> str:
    raw = f"{client_id}:{client_secret}".encode("utf-8")
    return base64.b64encode(raw).decode("ascii")


def _zoom_token_call(*, client_id: str, client_secret: str, body: dict[str, str]) -> dict:
    """POST to Zoom token endpoint with Basic auth; return parsed JSON.

    Uses ``requests`` (transitive via google-auth) so we pick up
    certifi's CA bundle on macOS Python — the stdlib urllib otherwise
    hits ``CERTIFICATE_VERIFY_FAILED`` because Python.org Python has no
    system trust store.
    """
    import requests

    resp = requests.post(
        ZOOM_TOKEN_URL,
        data=body,
        headers={
            "Authorization": f"Basic {_zoom_basic_auth(client_id, client_secret)}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        timeout=30,
    )
    if resp.status_code >= 400:
        raise RuntimeError(f"Zoom token endpoint HTTP {resp.status_code}: {resp.text}")
    return resp.json()


def check_zoom(env: dict[str, str]) -> bool:
    """Try a refresh_token grant; success means the token is healthy."""
    client_id = env.get("ZOOM_CLIENT_ID", "")
    client_secret = env.get("ZOOM_CLIENT_SECRET", "")
    refresh_token = env.get("ZOOM_REFRESH_TOKEN", "")
    if not (client_id and client_secret and refresh_token):
        print(
            "  ✗ zoom: ZOOM_CLIENT_ID / ZOOM_CLIENT_SECRET / ZOOM_REFRESH_TOKEN incomplete.",
            file=sys.stderr,
        )
        return False
    try:
        _zoom_token_call(
            client_id=client_id,
            client_secret=client_secret,
            body={"grant_type": "refresh_token", "refresh_token": refresh_token},
        )
    except Exception as exc:
        print(f"  ✗ zoom: existing refresh_token rejected: {exc}", file=sys.stderr)
        return False
    print("  ✓ zoom: existing refresh_token still valid (Zoom rotates on every refresh).")
    return True


def refresh_zoom(env: dict[str, str], args) -> dict[str, str]:
    """If refresh_token works, rotate.  Otherwise walk user through OAuth.

    Returns {ZOOM_REFRESH_TOKEN: <new>}.
    """
    client_id = env.get("ZOOM_CLIENT_ID", "")
    client_secret = env.get("ZOOM_CLIENT_SECRET", "")
    refresh_token = env.get("ZOOM_REFRESH_TOKEN", "")
    if not (client_id and client_secret):
        raise RuntimeError(
            "zoom: ZOOM_CLIENT_ID or ZOOM_CLIENT_SECRET missing from privacy.local.env"
        )

    # First try a refresh_token grant.
    if refresh_token:
        try:
            resp = _zoom_token_call(
                client_id=client_id,
                client_secret=client_secret,
                body={"grant_type": "refresh_token", "refresh_token": refresh_token},
            )
            new = resp.get("refresh_token")
            if not new:
                raise RuntimeError(f"zoom: refresh response missing refresh_token: {resp}")
            expires_in = resp.get("expires_in", "<unknown>")
            print(
                f"  ✓ zoom: refresh_token rotated successfully "
                f"(new access_token expires in {expires_in}s)."
            )
            return {"ZOOM_REFRESH_TOKEN": new}
        except Exception as exc:
            print(f"  ✗ zoom: refresh_token rotation failed: {exc}", file=sys.stderr)
            print("  → Falling back to authorization_code flow.")

    # Refresh_token is dead — need full re-auth.  Zoom's authorization_code
    # flow requires the OAuth app's redirect_uri to be registered in Zoom's
    # marketplace dashboard.  We can't intercept arbitrary callbacks here
    # without knowing the redirect_uri, so print the URL and ask the user
    # to paste the resulting code.
    redirect_uri = env.get("ZOOM_REDIRECT_URI", "http://localhost:8765/callback")
    auth_params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
    }
    auth_url = f"{ZOOM_AUTHORIZE_URL}?{urllib.parse.urlencode(auth_params)}"
    print()
    print("  Zoom authorization_code re-auth required.")
    print(f"  redirect_uri assumed: {redirect_uri}")
    print(
        "  (override by setting ZOOM_REDIRECT_URI in privacy.local.env to match the\n"
        "   value registered in your Zoom Marketplace OAuth app)"
    )
    print()
    print(f"  → Open this URL, grant access, then paste the ``code=`` query param:")
    print(f"    {auth_url}")
    if not args.no_browser:
        try:
            webbrowser.open(auth_url)
        except Exception:
            pass
    code = input("  Authorization code: ").strip()
    if not code:
        raise RuntimeError("zoom: empty authorization code; aborting.")
    resp = _zoom_token_call(
        client_id=client_id,
        client_secret=client_secret,
        body={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
        },
    )
    new = resp.get("refresh_token")
    if not new:
        raise RuntimeError(f"zoom: authorization_code response missing refresh_token: {resp}")
    expires_in = resp.get("expires_in", "<unknown>")
    print(
        f"  ✓ zoom: authorization_code flow succeeded "
        f"(new refresh_token + access_token expires in {expires_in}s)."
    )
    return {"ZOOM_REFRESH_TOKEN": new}


# ── ncm (NetEase Cloud Music) ───────────────────────────────────────────────
#
# ncm-cli is a Node.js CLI installed via ``npm install -g @music163/ncm-cli``.
# The login flow returns immediately when invoked with ``--background``,
# printing a JSON payload with ``clickableUrl`` plus a NetEase short URL.
# A background worker polls in the background; once the user logs in via
# NetEase mobile app, the worker writes ``登录成功`` to
# ``$HOME/.config/ncm-cli/bg-worker.log`` and updates ``tokens.enc.json``.
#
# We isolate everything under a temp ``HOME`` so the user's personal
# ncm-cli session (if any) is untouched.


def _ncm_setup_isolated_home(env: dict[str, str]) -> Path:
    """Create a temp HOME-style dir, configure ncm-cli with appId +
    privateKey from privacy.local.env, and restore both the existing
    ``NCM_TOKENS_ENC`` and ``NCM_DEVICE_JSON`` so ``ncm-cli login --check``
    can see them.  Returns the temp directory path.

    ``ncm-cli config set`` writes its own (random) ``.netease_mcp_device.json``
    at HOME root the first time it runs, so we run config-set FIRST and
    then overwrite the device file from ``NCM_DEVICE_JSON`` — otherwise
    the token would be encrypted under a different deviceId than the
    one captured at refresh time and ``--check`` would emit
    ``AuthManager token 文件解密失败``.
    """
    workdir = Path(tempfile.mkdtemp(prefix="ncm-refresh-"))
    config_dir = workdir / ".config" / "ncm-cli"
    config_dir.mkdir(parents=True)

    sub_env = os.environ.copy()
    sub_env["HOME"] = str(workdir)

    # 1. Restore the captured device fingerprint FIRST.  Both
    #    ``credentials.enc.json`` (which ``config set`` writes) and
    #    ``tokens.enc.json`` are symmetrically encrypted under
    #    ``.netease_mcp_device.json``'s deviceId.  If we ran ``config set``
    #    before placing the device file, ncm-cli would mint a fresh
    #    random device.json and encrypt credentials under THAT key — then
    #    overwriting the device file later would leave credentials
    #    undecryptable ("error:1C800064:Provider routines::bad decrypt").
    device_b64 = env.get("NCM_DEVICE_JSON", "")
    if device_b64:
        try:
            (workdir / ".netease_mcp_device.json").write_bytes(base64.b64decode(device_b64))
        except Exception:
            pass

    # 2. Configure ncm-cli identity.  This will read the device.json we
    #    just placed and encrypt credentials.enc.json under it.
    app_id = env.get("NCM_APP_ID", "")
    private_key = env.get("NCM_PRIVATE_KEY", "")
    for key, value in (("appId", app_id), ("privateKey", private_key)):
        if not value:
            continue
        subprocess.run(
            ["ncm-cli", "config", "set", key, value],
            env=sub_env, capture_output=True, text=True, check=False,
        )

    # 3. Restore the encrypted login tokens (also under the same device key).
    token_b64 = env.get("NCM_TOKENS_ENC", "")
    if token_b64:
        try:
            (config_dir / "tokens.enc.json").write_bytes(base64.b64decode(token_b64))
        except Exception:
            pass

    return workdir


def _ncm_check(workdir: Path) -> tuple[bool, str]:
    """Run ``ncm-cli login --check`` inside *workdir* HOME; return
    (success, message)."""
    sub_env = os.environ.copy()
    sub_env["HOME"] = str(workdir)
    r = subprocess.run(
        ["ncm-cli", "login", "--check", "--output", "json"],
        env=sub_env, capture_output=True, text=True, check=False,
    )
    # ncm-cli mixes a "new version" banner into stdout; isolate the JSON.
    raw = r.stdout.strip()
    json_start = raw.rfind("{")
    if json_start < 0:
        return False, raw or r.stderr
    try:
        data = json.loads(raw[json_start:])
    except json.JSONDecodeError:
        return False, raw
    return bool(data.get("success")), str(data.get("message", ""))


def check_ncm(env: dict[str, str]) -> bool:
    """Verify NCM_TOKENS_ENC + NCM_DEVICE_JSON by isolated-HOME ``ncm-cli
    login --check``."""
    for key in ("NCM_APP_ID", "NCM_PRIVATE_KEY", "NCM_TOKENS_ENC", "NCM_DEVICE_JSON"):
        if not env.get(key):
            print(f"  ✗ ncm: {key} missing from privacy.local.env.", file=sys.stderr)
            return False
    if shutil.which("ncm-cli") is None:
        print(
            "  ! ncm: ncm-cli not installed on this host; cannot probe.  "
            "Install with: npm install -g @music163/ncm-cli",
            file=sys.stderr,
        )
        return False
    workdir = _ncm_setup_isolated_home(env)
    try:
        ok, msg = _ncm_check(workdir)
        if ok:
            print(f"  ✓ ncm: existing tokens.enc.json + device.json still valid ({msg or 'logged in'}).")
            return True
        print(f"  ✗ ncm: existing tokens.enc.json invalid ({msg}).", file=sys.stderr)
        return False
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def refresh_ncm(env: dict[str, str], args) -> dict[str, str]:
    """Drive ``ncm-cli login --background``, wait for the user to scan
    the QR / click the URL on NetEase phone app, then base64-encode the
    fresh ``tokens.enc.json``.  Returns ``{NCM_TOKENS_ENC: <b64>}``."""
    if shutil.which("ncm-cli") is None:
        raise RuntimeError(
            "ncm: ncm-cli not installed; run `npm install -g @music163/ncm-cli` first."
        )

    workdir = _ncm_setup_isolated_home(env)
    try:
        sub_env = os.environ.copy()
        sub_env["HOME"] = str(workdir)

        # Kick off background login.
        r = subprocess.run(
            ["ncm-cli", "login", "--background", "--output", "json"],
            env=sub_env, capture_output=True, text=True, check=False,
        )
        raw = r.stdout.strip()
        json_start = raw.rfind("{")
        if json_start < 0:
            raise RuntimeError(f"ncm: login --background unexpected stdout: {raw}")
        data = json.loads(raw[json_start:])
        if not data.get("success"):
            raise RuntimeError(f"ncm: login --background returned: {data}")

        url = data.get("clickableUrl") or data.get("qrCodeUrl")
        print()
        print("  → Open this URL in any browser, log in with the *test* NetEase")
        print("    account (the one whose appId/privateKey are in privacy.local.env),")
        print("    NOT your personal account.")
        print(f"    {url}")
        if not args.no_browser:
            try:
                webbrowser.open(url)
            except Exception:
                pass

        # Poll bg-worker.log for success marker.
        bg_log = workdir / ".config" / "ncm-cli" / "bg-worker.log"
        deadline = time.time() + 300  # 5 minutes
        success_marker = "登录成功"
        while time.time() < deadline:
            if bg_log.exists():
                text = bg_log.read_text(errors="ignore")
                if success_marker in text:
                    last = text.strip().splitlines()[-1]
                    print(f"  ✓ ncm: {last.strip()}")
                    break
            time.sleep(2)
        else:
            raise RuntimeError(
                "ncm: login timeout after 5 min; bg-worker.log never reported success."
            )

        # Read the freshly-written tokens.enc.json AND the device.json
        # they were encrypted under.  Both must be persisted for the
        # container side to reconstruct a working ncm-cli login on a
        # different machine — capturing tokens alone yields
        # "AuthManager token 文件解密失败" on restore.
        tokens_file = workdir / ".config" / "ncm-cli" / "tokens.enc.json"
        device_file = workdir / ".netease_mcp_device.json"
        if not tokens_file.exists():
            raise RuntimeError(
                f"ncm: expected tokens.enc.json at {tokens_file} but it's missing."
            )
        if not device_file.exists():
            raise RuntimeError(
                f"ncm: expected device fingerprint at {device_file} but it's missing."
            )
        new_token_b64 = base64.b64encode(tokens_file.read_bytes()).decode("ascii")
        new_device_b64 = base64.b64encode(device_file.read_bytes()).decode("ascii")
        print(
            f"  ✓ ncm: captured tokens.enc.json ({tokens_file.stat().st_size} bytes) + "
            f"device.json ({device_file.stat().st_size} bytes)."
        )

        # Final --check sanity in same workdir.
        ok, msg = _ncm_check(workdir)
        if not ok:
            raise RuntimeError(f"ncm: post-login --check still failing: {msg}")
        print(f"  ✓ ncm: post-login --check confirmed ({msg or 'logged in'}).")

        # Independent end-to-end sanity: fresh workdir, restore via the
        # exact env-var path the container's install.sh will use, run
        # --check.  Catches any case where the captured bundle isn't
        # self-sufficient.
        verify_env = dict(env)
        verify_env["NCM_TOKENS_ENC"] = new_token_b64
        verify_env["NCM_DEVICE_JSON"] = new_device_b64
        verify_workdir = _ncm_setup_isolated_home(verify_env)
        try:
            ok2, msg2 = _ncm_check(verify_workdir)
        finally:
            shutil.rmtree(verify_workdir, ignore_errors=True)
        if not ok2:
            raise RuntimeError(
                f"ncm: cross-workdir round-trip --check failed: {msg2}.\n"
                "  The captured tokens.enc.json + device.json bundle is not "
                "sufficient to restore login on a different machine."
            )
        print(f"  ✓ ncm: cross-workdir round-trip --check confirmed ({msg2}).")

        return {
            "NCM_TOKENS_ENC": new_token_b64,
            "NCM_DEVICE_JSON": new_device_b64,
        }
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


# ── provider registry ──────────────────────────────────────────────────────


@dataclass
class Provider:
    name: str
    display: str
    env_vars: list[str]
    check: callable
    refresh: callable
    notes: str = ""


PROVIDERS: dict[str, Provider] = {
    "gcalcli": Provider(
        name="gcalcli",
        display="Google Calendar (gcalcli)",
        env_vars=["GCALCLI_CLIENT_ID", "GCALCLI_CLIENT_SECRET", "GCALCLI_OAUTH_B64"],
        check=check_gcalcli,
        refresh=refresh_gcalcli,
        notes="OAuth refresh_token ~6 months; revoked by Google security policy.",
    ),
    "zoom": Provider(
        name="zoom",
        display="Zoom OAuth2",
        env_vars=["ZOOM_CLIENT_ID", "ZOOM_CLIENT_SECRET", "ZOOM_REFRESH_TOKEN"],
        check=check_zoom,
        refresh=refresh_zoom,
        notes="refresh_token rotates on every refresh; original ~90 days.",
    ),
    "ncm": Provider(
        name="ncm",
        display="NetEase Cloud Music (ncm-cli)",
        env_vars=["NCM_APP_ID", "NCM_PRIVATE_KEY", "NCM_TOKENS_ENC"],
        check=check_ncm,
        refresh=refresh_ncm,
        notes="QR / browser-link re-login via `ncm-cli login --background`; "
              "isolated under a temp HOME so personal ncm-cli sessions stay untouched.",
    ),
}


# ── entry point ────────────────────────────────────────────────────────────


def main() -> int:
    _check_deps()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--provider", choices=sorted(PROVIDERS) + ["all"], default="all",
        help="Scope to one provider; default 'all' walks every registered provider.",
    )
    parser.add_argument(
        "--check-only", action="store_true",
        help="Only verify existing credentials; do not run any refresh flow.",
    )
    parser.add_argument(
        "--no-browser", action="store_true",
        help="Don't auto-open the browser; print the URL instead.",
    )
    args = parser.parse_args()

    try:
        env = read_env(PRIVACY_ENV)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"Privacy env: {PRIVACY_ENV}")
    print()

    selected = list(PROVIDERS.values()) if args.provider == "all" else [PROVIDERS[args.provider]]

    any_failure = False
    accumulated_updates: dict[str, str] = {}

    for prov in selected:
        print(f"── {prov.display} ({prov.name}) " + "─" * (50 - len(prov.display) - len(prov.name)))
        if prov.notes:
            print(f"  ({prov.notes})")
        ok = prov.check(env)
        if ok:
            print(f"  ✓ {prov.name}: no rotation needed.")
            print()
            continue
        if args.check_only:
            any_failure = True
            print(f"  --check-only: {prov.name} is broken; skipping rotation.")
            print()
            continue
        try:
            updates = prov.refresh(env, args)
        except KeyboardInterrupt:
            print(f"\n  ↪ {prov.name}: aborted by user.")
            any_failure = True
            print()
            continue
        except Exception as exc:
            print(f"  ✗ {prov.name}: refresh raised {exc}", file=sys.stderr)
            any_failure = True
            print()
            continue
        if updates:
            accumulated_updates.update(updates)
            print(f"  ✓ {prov.name}: queued {len(updates)} env-var update(s).")
        print()

    if accumulated_updates and not args.check_only:
        write_env_keys(accumulated_updates, PRIVACY_ENV)
        print(
            f"✓ Wrote {len(accumulated_updates)} env var(s) back to {PRIVACY_ENV}:\n  "
            + ", ".join(sorted(accumulated_updates))
        )
        return 0 if not any_failure else 1

    if any_failure:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
