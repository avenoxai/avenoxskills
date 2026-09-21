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

  Codex  : first CodexBar's live snapshot
           (Windows:  %APPDATA%/CodexBar/codex-accounts/snapshots.json
            macOS:    ~/Library/Application Support/CodexBar/codex-accounts/snapshots.json
            Linux:    ~/.config/CodexBar/codex-accounts/snapshots.json)
           CodexBar polls usage continuously in the background, so this data
           is minute-fresh. The record with the newest `updatedAt` wins.
           Fallback: ~/.codex/sessions/**/*.jsonl -> the newest `rate_limits`
           entry. That path is only written when `codex` actually runs, so it
           can be days old.

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


def _parse_iso(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).timestamp()
    except ValueError:
        return None


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
    if not isinstance(epoch, (int, float)) or isinstance(epoch, bool):
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
    if not values or max(values.values()) <= 0:
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
            return (json.load(handle) or {}).get("claudeAiOauth") or {}
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
    request = urllib.request.Request(
        CLAUDE_USAGE_URL,
        headers={
            "Authorization": f"Bearer {token}",
            "anthropic-beta": "oauth-2025-04-20",
            "User-Agent": "limit-skill/1.0",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            if response.status != 200:
                return None, f"endpoint returned HTTP {response.status}"
            return json.loads(response.read().decode("utf-8")), None
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
    except json.JSONDecodeError:
        return None, "endpoint did not return valid JSON"


def _append_windows(out: dict, utilization: dict) -> None:
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
                "used_percent": window["utilization"],
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

    cached = data.get("cachedUsageUtilization")
    if not cached:
        out["warnings"].append("no cachedUsageUtilization -- /usage may never have run")
        return out

    fetched_ms = cached.get("fetchedAtMs")
    if fetched_ms:
        age_min = (_now() - fetched_ms / 1000) / 60
        out["age_minutes"] = round(age_min)
        if age_min > CLAUDE_MAX_AGE_MIN:
            out["warnings"].append(
                f"cache is {_fmt_delta(age_min * 60)} stale "
                f"(threshold {CLAUDE_MAX_AGE_MIN}m) -- run /usage in an interactive session"
            )

    _append_windows(out, cached.get("utilization") or {})
    return out


def _codexbar_snapshot_paths() -> list[str]:
    """Candidate CodexBar snapshot paths, checked in order, platform-first."""
    appdata = os.environ.get("APPDATA")
    candidates = []
    if appdata:
        candidates.append(os.path.join(appdata, "CodexBar", "codex-accounts", "snapshots.json"))
    candidates.append(os.path.expanduser(
        "~/Library/Application Support/CodexBar/codex-accounts/snapshots.json"
    ))
    candidates.append(os.path.expanduser(
        "~/.config/CodexBar/codex-accounts/snapshots.json"
    ))
    return candidates


def read_codexbar() -> dict | None:
    """Read CodexBar's live snapshot -- the FRESHEST source for Codex.

    CodexBar runs continuously in the tray polling usage and writes every
    poll to `snapshots.json`. That is far fresher than session rollout
    files, which are only written while `codex` is actually running.
    Records are keyed by session id; the newest `updatedAt` wins.
    Returns None if the app is not installed, and the rollout path is
    tried instead.
    """
    data = None
    used_path = None
    for path in _codexbar_snapshot_paths():
        try:
            with open(path, encoding="utf-8") as handle:
                data = (json.load(handle) or {}).get("snapshots") or {}
            used_path = path
            break
        except (OSError, json.JSONDecodeError):
            continue
    if not data:
        return None

    # Two selections are made because CodexBar writes a SENTINEL when a
    # limit is hit: a snapshot with `limitReached: true` reports BOTH
    # windows at exactly 100, even if the weekly window is nowhere near
    # full. The primary 100 is correct (it really is exhausted), but
    # reusing the same record's secondary value would show every full
    # 5-hour window as also killing the week. So the secondary value is
    # read from the newest record that is NOT a sentinel.
    newest, newest_ts = None, None
    newest_ok, newest_ok_ts = None, None
    for record in data.values():
        if not isinstance(record, dict):
            continue
        stamp = _parse_iso((record.get("updatedAt") or "").replace("Z", "+00:00"))
        if stamp is None:
            continue
        if newest_ts is None or stamp > newest_ts:
            newest, newest_ts = record, stamp
        if not record.get("limitReached") and (newest_ok_ts is None or stamp > newest_ok_ts):
            newest_ok, newest_ok_ts = record, stamp
    if newest is None:
        return None

    out: dict = {
        "source": used_path,
        "windows": [],
        "warnings": [],
        "plan": newest.get("plan"),
        "age_minutes": round((_now() - newest_ts) / 60),
    }
    if out["age_minutes"] > CODEX_MAX_AGE_MIN or out["age_minutes"] < 0:
        out["warnings"].append("CodexBar snapshot is stale/invalid -- do not use for a quota decision")
    if newest.get("limitReached"):
        out["warnings"].append("limit FULL -- new requests will be rejected")
    # secondaryWindow (the weekly quota) is shown alongside primaryWindow
    # because primary alone (the fast-resetting window) is misleading on
    # its own: it can read 12% while the week is already exhausted.
    for key, name in (("primaryWindow", "primary"), ("secondaryWindow", "weekly")):
        source = newest
        if key == "secondaryWindow" and newest.get("limitReached") and newest_ok is not None:
            source = newest_ok
            out["warnings"].append(
                "weekly percentage is from the last NON-sentinel measurement "
                f"({_fmt_delta(_now() - newest_ok_ts)} ago) -- a limitReached "
                "record reports both windows as 100, which is not valid for weekly"
            )
        window = source.get(key) or {}
        if not window:
            continue
        resets_ts = _parse_iso((window.get("resetAt") or "").replace("Z", "+00:00"))
        seconds = window.get("limitWindowSeconds") or 0
        if seconds and seconds % 86400 == 0:
            label = f"{name} ({seconds // 86400}-day)"
        elif seconds:
            label = f"{name} ({seconds // 3600}-hour)"
        else:
            label = name
        expired = resets_ts is not None and resets_ts < _now()
        out["windows"].append(
            {
                "name": label,
                "used_percent": window.get("usedPercent"),
                "resets_at": window.get("resetAt"),
                "resets_in": _fmt_delta(resets_ts - _now()) if resets_ts and not expired else None,
                "expired": expired,
            }
        )
    return out if out["windows"] else None


def read_codex(scan_limit: int = 40) -> dict:
    """Read Codex usage: CodexBar snapshot first, then session rollout files."""
    fresh = read_codexbar()
    if fresh is not None:
        return fresh

    root = os.path.expanduser("~/.codex/sessions")
    out: dict = {"source": root, "windows": [], "warnings": []}
    out["warnings"].append(
        "CodexBar snapshot unreadable, fell back to session files (may be older)"
    )

    files = glob.glob(os.path.join(root, "**", "*.jsonl"), recursive=True)
    if not files:
        out["warnings"].append("no session files -- codex has never been run")
        return out
    files.sort(key=os.path.getmtime, reverse=True)

    def dig(node):
        """Find the first `rate_limits` object in a nested structure."""
        if isinstance(node, dict):
            if "rate_limits" in node:
                return node["rate_limits"]
            for value in node.values():
                found = dig(value)
                if found is not None:
                    return found
        elif isinstance(node, list):
            for value in node:
                found = dig(value)
                if found is not None:
                    return found
        return None

    fallback = None
    for path in files[:scan_limit]:
        newest = None
        try:
            with open(path, encoding="utf-8") as handle:
                for line in handle:
                    if "rate_limits" in line:
                        newest = line
        except OSError:
            continue
        if not newest:
            continue
        try:
            limits = dig(json.loads(newest))
        except json.JSONDecodeError:
            continue
        if not limits:
            continue

        age = _now() - os.path.getmtime(path)
        if fallback is None:
            fallback = (limits, age)
        if limits.get("primary"):
            _fill_codex(out, limits, age)
            return out

    # No non-empty record found: report the newest empty one instead of
    # silently leaving a gap.
    if fallback:
        limits, age = fallback
        _fill_codex(out, limits, age)
        out["warnings"].append(
            "limit fields came back empty -- quota exhausted, a free plan, "
            "or no requests have been made yet"
        )
    else:
        out["warnings"].append("no rate_limits entry found in any session file")
    return out


def _fill_codex(out: dict, limits: dict, age_seconds: float) -> None:
    out["plan"] = limits.get("plan_type")
    out["age_minutes"] = round(age_seconds / 60)
    if age_seconds > 24 * 3600:
        out["warnings"].append(
            f"most recent codex session was {_fmt_delta(age_seconds)} ago -- "
            "data is that old, any usage in between is not visible here"
        )
    for key, label in (("primary", "primary"), ("secondary", "weekly")):
        window = limits.get(key)
        if not window:
            continue
        resets_ts = window.get("resets_at")
        minutes = window.get("window_minutes") or 0
        if minutes >= 1440:
            name = f"{label} ({minutes // 1440}-day)"
        else:
            name = f"{label} ({minutes // 60}-hour)"
        expired = bool(resets_ts and resets_ts < _now())
        out["windows"].append(
            {
                "name": name,
                "used_percent": window.get("used_percent"),
                "resets_at": (
                    datetime.fromtimestamp(resets_ts, timezone.utc).isoformat()
                    if resets_ts
                    else None
                ),
                "resets_in": _fmt_delta(resets_ts - _now()) if resets_ts and not expired else None,
                "expired": expired,
            }
        )


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
            band = _usage_color(percent, window["expired"])
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
    args = parser.parse_args(argv)

    claude, codex = read_claude(args.claude_observation), read_codex()
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
