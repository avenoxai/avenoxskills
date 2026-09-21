#!/usr/bin/env python3
"""Show Claude and Codex subscription usage windows on one screen.

  Claude : LIVE -> https://api.anthropic.com/api/oauth/usage
           Same endpoint the CLI's own `/usage` command calls; token comes
           from ~/.claude/.credentials.json.
           Fallback 1: an optional --claude-observation file (see below).
           Fallback 2: ~/.claude.json -> cachedUsageUtilization. That cache
           is only refreshed by an interactive `/usage` call, so it can be
           stale for hours -- this is SILENT unless we check the age and the
           window-expiry ourselves and say so out loud.

  Codex  : CodexBar's local snapshot cache, then dated core rate-limit
           events under $CODEX_HOME/sessions (default ~/.codex/sessions).
           macOS uses codex-account-snapshots.json; the Windows variant
           uses codex-accounts/snapshots.json. Multiple cached accounts
           require --codex-account; measurements are never combined.
           Cache age is checked, not assumed fresh because the app exists.

Usage: python limit.py [--json] [--color auto|always|never] [--claude-observation PATH]
"""

from __future__ import annotations

import argparse
import glob
import json
import math
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

# Windows consoles default to an OEM code page; force UTF-8 output.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Claude's cache is considered "untrustworthy" after this age.
CLAUDE_MAX_AGE_MIN = 45
CODEX_MAX_AGE_MIN = 45
# Optional --claude-observation file: same staleness threshold.
OBSERVATION_MAX_AGE_MIN = 45


def _now() -> float:
    return time.time()


def _fmt_delta(seconds: float) -> str:
    """Format seconds as a short duration like '3d 4h' / '2h 15m'."""
    seconds = int(abs(seconds))
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes = rem // 60
    if days:
        return f"{days}d {hours}h" if hours else f"{days}d"
    if hours and minutes:
        return f"{hours}h {minutes}m"
    if hours:
        return f"{hours}h"
    return f"{minutes}m"


def _number(value):
    if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value):
        return float(value)
    return None


def _percent(value):
    value = _number(value)
    return value if value is not None and 0 <= value <= 100 else None


def _parse_iso(value: str | None) -> float | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.timestamp() if parsed.tzinfo is not None else None
    except (ValueError, OverflowError, OSError):
        return None


def _iso_timestamp(value):
    value = _number(value)
    if value is None:
        return None
    try:
        return datetime.fromtimestamp(value, timezone.utc).isoformat()
    except (ValueError, OverflowError, OSError):
        return None


def _warn_age(out, stamp, label):
    age = _now() - stamp if stamp is not None else None
    out["age_minutes"] = round(age / 60) if age is not None else None
    out["stale"] = age is None or age < 0 or age > CODEX_MAX_AGE_MIN * 60
    if out["stale"]:
        out["warnings"].append(f"{label} timestamp stale/invalid -- current quota is unknown")


def read_claude_observation(path: str | None,
                             max_age_min: float = OBSERVATION_MAX_AGE_MIN) -> dict | None:
    """Read an optional user-supplied observation file for Claude usage.

    This is a second source ahead of the local cache, meant for anyone who
    wires their own statusline/hook to sample usage percentages more often
    than the interactive `/usage` cache refreshes. See SKILL.md for the
    3-field JSON schema this expects.

    ALL-ZERO MEANS UNREADABLE, NOT EMPTY: if the upstream sampler saw an
    HTTP 429 when it captured this snapshot, it may have written
    `used_percentage: 0`, which looks like an empty pool but is not one.
    """
    if not path:
        return None
    try:
        with open(path, encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, ValueError):
        return None
    if not isinstance(payload, dict):
        return None
    epoch = payload.get("epoch")
    if _number(epoch) is None:
        return None
    age = _now() - float(epoch)
    if age < 0 or age > max_age_min * 60:
        return None
    values = {
        key: float(payload[key])
        for key in ("five", "seven")
        if isinstance(payload.get(key), (int, float))
        and not isinstance(payload[key], bool)
        and 0 <= payload[key] <= 100
    }
    if len(values) != 2 or max(values.values()) <= 0:
        return None
    resets = {
        f"{key}_reset": float(payload[f"{key}_reset"])
        for key in ("five", "seven")
        if isinstance(payload.get(f"{key}_reset"), (int, float))
        and not isinstance(payload[f"{key}_reset"], bool)
        and math.isfinite(payload[f"{key}_reset"])
    }
    return {"epoch": float(epoch), **values, **resets}


CLAUDE_USAGE_URL = "https://api.anthropic.com/api/oauth/usage"


def _claude_oauth() -> dict:
    """Read the `claudeAiOauth` block of ~/.claude/.credentials.json ({} if unreadable)."""
    try:
        with open(
            os.path.expanduser("~/.claude/.credentials.json"), encoding="utf-8"
        ) as handle:
            data = json.load(handle)
            oauth = data.get("claudeAiOauth") if isinstance(data, dict) else None
            return oauth if isinstance(oauth, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _claude_token() -> str | None:
    """Return the OAuth access token, or None if missing or expired.

    The token is NEVER written to disk or logged; it only goes out as the
    Authorization header of Anthropic's own usage endpoint -- the same call
    the CLI itself makes.
    """
    oauth = _claude_oauth()
    expires_at = oauth.get("expiresAt")
    if isinstance(expires_at, (int, float)) and expires_at / 1000 < _now():
        return None
    token = oauth.get("accessToken")
    return token if isinstance(token, str) and token else None


def _claude_plan() -> str | None:
    """Return the subscription plan the token carries (`pro`, `max`, ...)."""
    plan = _claude_oauth().get("subscriptionType")
    return plan if isinstance(plan, str) and plan else None


def _fetch_claude_live_detailed() -> tuple[dict | None, str | None]:
    """Fetch usage LIVE from the API; on failure, return the reason too.

    The local cache (~/.claude.json -> cachedUsageUtilization) only refreshes
    on an interactive `/usage` call and can be stale for hours; this path
    returns the current numbers on every call. On network/token trouble it
    returns (None, reason) and the caller falls back -- better to say "stale"
    than to print a wrong number.
    """
    token = _claude_token()
    if not token:
        return None, "token missing or expired: run `claude auth login`"
    # Never forward an OAuth Authorization header to a redirected origin.
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None

    request = urllib.request.Request(
        CLAUDE_USAGE_URL,
        headers={
            "Authorization": f"Bearer {token}",
            "anthropic-beta": "oauth-2025-04-20",
            "User-Agent": "limit-skill/1.0",
        },
    )
    try:
        with urllib.request.build_opener(NoRedirect()).open(request, timeout=15) as response:
            if response.status != 200:
                return None, f"endpoint returned HTTP {response.status}"
            data = json.loads(response.read().decode("utf-8"))
            return (data, None) if isinstance(data, dict) else (None, "invalid usage response")
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403):
            return None, f"token rejected (HTTP {exc.code}): run `claude auth login`"
        if exc.code == 429:
            # This is a RATE LIMIT on the endpoint, not a quota reading.
            # "429" here does not mean "your window is full" -- it means
            # "could not read the number right now".
            return None, (
                "endpoint returned HTTP 429 -- this is NOT a quota reading, "
                "it is the endpoint's own rate limit. Run /usage in an "
                "interactive session; if it persists, refresh the token "
                "with `claude auth login`"
            )
        return None, f"endpoint returned HTTP {exc.code}"
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return None, (
            f"network unreachable ({exc.__class__.__name__}) -- this is a "
            "network problem, not a token problem. If you're running inside "
            "a sandbox with network access disabled, Claude usage cannot be "
            "read live from there"
        )
    except (ValueError, UnicodeError):
        return None, "endpoint did not return valid JSON"


def _append_windows(out: dict, utilization: dict) -> None:
    if not isinstance(utilization, dict):
        return
    # Known windows first in a fixed order, then any EXTRA window the
    # endpoint returns. Some plans add model-specific windows (e.g. a
    # weekly Opus window) and a fixed key list would silently swallow it --
    # an invisible wall is the worst kind of wall.
    known = (("five_hour", "5-hour"), ("seven_day", "7-day"))
    extra = tuple(
        (key, key.replace("_", " "))
        for key in utilization
        if key not in {name for name, _ in known}
    )
    for key, label in known + extra:
        window = utilization.get(key)
        if not isinstance(window, dict) or window.get("utilization") is None:
            continue
        resets_ts = _parse_iso(window.get("resets_at"))
        expired = resets_ts is not None and resets_ts < _now()
        if expired:
            out["warnings"].append(
                f"{label} window expired {_fmt_delta(_now() - resets_ts)} ago -- "
                "the percentage below is for that old window, not the current state"
            )
        out["windows"].append(
            {
                "name": label,
                "used_percent": _percent(window["utilization"]),
                "resets_at": window.get("resets_at"),
                "resets_in": _fmt_delta(resets_ts - _now()) if resets_ts and not expired else None,
                "expired": expired,
            }
        )


def read_claude(observation_path: str | None = None) -> dict:
    """Read Claude usage: live API first, then observation file, then cache."""
    live, reason = _fetch_claude_live_detailed()
    plan = _claude_plan()
    if live:
        out: dict = {"source": CLAUDE_USAGE_URL, "windows": [], "warnings": []}
        out["plan"] = plan
        out["age_minutes"] = 0
        _append_windows(out, live)
        if out["windows"]:
            return out

    # Second source: the caller's own observation file, if given. It comes
    # BEFORE ~/.claude.json because that cache only refreshes on an
    # interactive `/usage` call and can be stale for hours.
    observation = read_claude_observation(observation_path)
    if observation:
        out = {"source": observation_path, "windows": [], "warnings": []}
        out["plan"] = plan
        out["age_minutes"] = round((_now() - observation["epoch"]) / 60)
        utilization = {}
        for key, name in (("five", "five_hour"), ("seven", "seven_day")):
            if key not in observation:
                continue
            window = {"utilization": observation[key]}
            reset = observation.get(f"{key}_reset")
            if reset is not None:
                try:
                    window["resets_at"] = datetime.fromtimestamp(
                        reset, timezone.utc).isoformat()
                except (OSError, OverflowError, ValueError):
                    pass
            utilization[name] = window
        # The tail of `reason` ("run /usage to refresh") is WRONG on this
        # branch: the number WAS read. Only its first sentence applies here,
        # the rest belongs to the live-API branch.
        short_reason = (reason or "unknown reason").split(". ", 1)[0]
        reset_note = (
            "reset times come from the observation file"
            if any("resets_at" in window for window in utilization.values())
            else "reset times are not available from this source"
        )
        out["warnings"].append(
            f"live fetch failed ({short_reason}); numbers are from the "
            f"OBSERVATION FILE -- local and fresh, but {reset_note}"
        )
        _append_windows(out, utilization)
        if out["windows"]:
            return out

    path = os.path.expanduser("~/.claude.json")
    out = {"source": path, "windows": [], "warnings": []}
    out["plan"] = plan
    out["warnings"].append(
        f"live fetch failed -- {reason or 'unknown reason'}. "
        "Numbers below are from the LOCAL CACHE and may be stale"
    )
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        out["warnings"].append(f"could not read cache: {exc}")
        return out

    cached = data.get("cachedUsageUtilization") if isinstance(data, dict) else None
    if not isinstance(cached, dict) or not cached:
        out["warnings"].append("no cachedUsageUtilization -- /usage may never have run")
        return out

    fetched_ms = _number(cached.get("fetchedAtMs"))
    _warn_age(out, fetched_ms / 1000 if fetched_ms is not None else None, "Claude cache")

    _append_windows(out, cached.get("utilization") or {})
    return out


def _codexbar_snapshot_paths() -> list[str]:
    candidates = []
    if os.environ.get("APPDATA"):
        candidates.append(os.path.join(os.environ["APPDATA"], "CodexBar", "codex-accounts", "snapshots.json"))
    candidates.extend([
        os.path.expanduser("~/Library/Application Support/CodexBar/codex-account-snapshots.json"),
        os.path.expanduser("~/Library/Application Support/CodexBar/codex-accounts/snapshots.json"),
        os.path.join(os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config")),
                     "CodexBar", "codex-accounts", "snapshots.json"),
    ])
    return candidates


def read_codexbar(account: str | None = None) -> dict | None:
    """Read supported CodexBar caches without combining account measurements.

    The macOS Swift Codable format uses seconds since 2001-01-01; the
    Windows snapshots map uses ISO dates. Neither file is a live API call.
    """
    for path in _codexbar_snapshot_paths():
        try:
            with open(path, encoding="utf-8") as handle:
                payload = json.load(handle)
        except (OSError, ValueError):
            continue
        if not isinstance(payload, dict):
            continue
        swift = isinstance(payload.get("records"), list) and payload.get("version") == 1
        if swift:
            records = {r["id"]: r for r in payload["records"]
                       if isinstance(r, dict) and isinstance(r.get("id"), str)}
        else:
            records = payload.get("snapshots")
        if not isinstance(records, dict) or not records:
            continue
        out = {"source": path, "windows": [], "warnings": []}
        if account is None and len(records) > 1:
            out["warnings"].append("multiple CodexBar accounts -- select --codex-account ID; current quota is unknown")
            return out
        record = records.get(account) if account is not None else next(iter(records.values()))
        if not isinstance(record, dict):
            continue
        if record.get("limitReached"):
            out["warnings"].append("limitReached sentinel is not a measured percentage; current windows are unknown")
            return out
        if record.get("error"):
            out["warnings"].append("CodexBar fetch failed; current quota is unknown")
            return out
        source = record.get("snapshot") if swift else record
        if not isinstance(source, dict):
            continue
        stamp = source.get("updatedAt")
        stamp = (_number(stamp) + 978307200 if _number(stamp) is not None else None) if swift else _parse_iso(stamp)
        _warn_age(out, stamp, "CodexBar snapshot")
        out["plan"] = None if swift else source.get("plan")
        for key, label in (("primary" if swift else "primaryWindow", "primary"),
                           ("secondary" if swift else "secondaryWindow", "weekly")):
            window = source.get(key)
            if not isinstance(window, dict):
                continue
            reset = window.get("resetsAt" if swift else "resetAt")
            reset = (_number(reset) + 978307200 if _number(reset) is not None else None) if swift else _parse_iso(reset)
            minutes = _number(window.get("windowMinutes")) if swift else _number(window.get("limitWindowSeconds"))
            if minutes is not None and not swift:
                minutes /= 60
            _add_codex_window(out, label, window.get("usedPercent"), reset, minutes)
        if out["windows"]:
            if len(out["windows"]) < 2:
                out["warnings"].append("one core window is missing -- full pool availability is unknown")
            return out
    return None


def read_codex(scan_limit: int = 40, account: str | None = None) -> dict:
    """Read cache first, then the latest dated core-quota event in bounded rollouts."""
    cached = read_codexbar(account)
    if cached is not None:
        return cached
    root = os.path.join(os.environ.get("CODEX_HOME", os.path.expanduser("~/.codex")), "sessions")
    out = {"source": root, "windows": [], "warnings": []}
    if account is not None:
        out["warnings"].append("selected CodexBar account unavailable; unscoped session fallback disabled")
        return out
    out["warnings"].append("CodexBar snapshot unreadable; using session measurements (active account not verified)")
    files = glob.glob(os.path.join(root, "**", "*.jsonl"), recursive=True)
    # mtime bounds the search only; it must never determine measurement freshness.
    def mtime(path):
        try:
            return os.path.getmtime(path)
        except OSError:
            return 0
    files.sort(key=mtime, reverse=True)
    newest = None
    undated = None
    for path in files[:scan_limit]:
        try:
            with open(path, encoding="utf-8") as handle:
                for line in handle:
                    if '"rate_limits"' not in line:
                        continue
                    try:
                        event = json.loads(line)
                    except ValueError:
                        continue
                    if not isinstance(event, dict) or event.get("type") != "event_msg":
                        continue
                    payload = event.get("payload")
                    if not isinstance(payload, dict) or payload.get("type") != "token_count":
                        continue
                    limits = payload.get("rate_limits")
                    if not isinstance(limits, dict) or limits.get("limit_id") not in (None, "codex"):
                        continue
                    stamp = _parse_iso(event.get("timestamp"))
                    if stamp is None:
                        undated = (limits, None, path)
                    elif newest is None or stamp >= newest[1]:
                        newest = (limits, stamp, path)
        except (OSError, UnicodeError):
            continue
    measurement = newest or undated
    if measurement is None:
        out["warnings"].append("no core rate_limits measurement found in scanned session files")
        return out
    limits, stamp, out["source"] = measurement
    _warn_age(out, stamp, "Codex measurement")
    _fill_codex(out, limits)
    if len(out["windows"]) < 2:
        out["warnings"].append("latest core rate_limits fields are missing/empty -- full pool availability is unknown")
    return out


def _add_codex_window(out, label, used, reset, minutes):
    iso = _iso_timestamp(reset)
    reset = reset if iso is not None else None
    minutes = _number(minutes)
    if minutes is not None and minutes > 0:
        label += f" ({minutes / 1440:g}-day)" if minutes >= 1440 else f" ({minutes / 60:g}-hour)"
    expired = reset is not None and reset <= _now()
    if expired:
        out["warnings"].append(f"{label} window expired -- current quota is unknown")
    out["windows"].append({
        "name": label, "used_percent": _percent(used), "resets_at": iso,
        "resets_in": _fmt_delta(reset - _now()) if reset is not None and not expired else None,
        "expired": expired,
    })


def _fill_codex(out: dict, limits: dict) -> None:
    out["plan"] = limits.get("plan_type")
    for key, label in (("primary", "primary"), ("secondary", "weekly")):
        window = limits.get(key)
        if isinstance(window, dict):
            _add_codex_window(out, label, window.get("used_percent"),
                              _number(window.get("resets_at")), window.get("window_minutes"))


def _bar(percent: float | None, width: int = 20) -> str:
    if percent is None:
        return "?" * width
    filled = int(round(min(max(percent, 0), 100) / 100 * width))
    return "#" * filled + "." * (width - filled)


RESET = "\033[0m"
DIM = "\033[2m"
BOLD = "\033[1m"
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"


def _usage_color(percent: float | None, invalid: bool = False) -> str:
    """Same usage-based color scheme for both providers."""
    if invalid or percent is None or percent >= 90:
        return RED
    if percent >= 70:
        return YELLOW
    return GREEN


def _paint(text: str, color: str, enabled: bool) -> str:
    return f"{color}{text}{RESET}" if enabled else text


def render(claude: dict, codex: dict, color: bool = False) -> str:
    lines = []
    for title, block in (("CLAUDE", claude), ("CODEX / GPT", codex)):
        head = title
        if block.get("plan"):
            head += f"  (plan: {block['plan']})"
        if block.get("age_minutes") is not None:
            head += f"  [data {_fmt_delta(block['age_minutes'] * 60)} old]"
        lines.append(_paint(head, BOLD + CYAN, color))

        if not block["windows"]:
            lines.append(_paint("  no data", RED, color))
        for window in block["windows"]:
            percent = window["used_percent"]
            shown = f"{percent:>3.0f}%" if percent is not None else "  ?"
            tail = f"resets in: {window['resets_in']}" if window["resets_in"] else ""
            if window["expired"]:
                tail = "WINDOW EXPIRED -- this number is not current"
            band = _usage_color(percent, window["expired"] or block.get("stale", False))
            value = f"{shown}  [{_bar(percent)}]"
            lines.append(
                f"  {window['name']:<22} {_paint(value, band, color)} "
                f"{_paint(tail, RED if window['expired'] else DIM, color)}".rstrip()
            )

        for warning in block["warnings"]:
            lines.append(_paint(f"  ! {warning}", YELLOW, color))
        lines.append("")
    return "\n".join(lines).rstrip()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="limit.py",
        description="Show Claude and Codex subscription usage windows on one screen.",
    )
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument(
        "--color", choices=("auto", "always", "never"), default="auto",
        help="ANSI colors (default: auto = only on a TTY, and never when NO_COLOR is set)",
    )
    parser.add_argument(
        "--claude-observation", metavar="PATH", default=None,
        help="optional JSON snapshot of Claude usage written by your own statusline/hook "
             "(see SKILL.md for the schema); used when the live endpoint is unavailable",
    )
    parser.add_argument("--codex-account", metavar="ID", help="select a CodexBar snapshot account ID when several exist")
    args = parser.parse_args(argv)

    claude, codex = read_claude(args.claude_observation), read_codex(account=args.codex_account)
    if args.json:
        print(json.dumps({"claude": claude, "codex": codex}, indent=2, ensure_ascii=False))
        return 0
    use_color = args.color == "always" or (
        args.color == "auto" and sys.stdout.isatty() and "NO_COLOR" not in os.environ
    )
    print(render(claude, codex, color=use_color))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
