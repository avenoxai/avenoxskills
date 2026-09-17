---
name: limit
description: Show Claude and Codex subscription usage windows in one colored screen, live where possible. Use when the user asks "limit", "quota", "how much usage is left", or before choosing which model/pool to delegate a task to.
---

# Limit

Run the script that ships next to this file (`python` instead of `python3` on Windows;
adjust the path if you installed the skill somewhere else):

```bash
python3 ~/.claude/skills/limit/scripts/limit.py --color always
```

Show the output verbatim before summarising it — do not paraphrase the numbers.

A window whose warnings include `stale`, `window expired`, or `live fetch failed`
is **unknown, not empty**. Don't treat its percentage as current.

## Acting on it

Each window has its own wall, and the reset time matters as much as the percentage:

| Reading | Do |
|---|---|
| Both windows of a pool clear | Use the pool normally. Don't hedge or narrate the number. |
| A window within ~5 points of full | Narrow the work: fewer parallel jobs, cheapest model that can carry it, sequential. Say the number once. |
| 5-hour window at the wall **and resets within ~30 min** | Wait for the reset. Don't hand off to the other pool or start a long run that will be cut in half. |
| Weekly window at the wall | It won't come back for days: hand the work to the other pool if *both* of its windows are clear, otherwise keep it in the main loop or queue it. |
| Both pools at a wall, or a window unknown | Delegate nothing. Report both numbers and ask. |

The fullest *valid* window in each pool is binding — a 12% 5-hour window next to
an exhausted weekly window means the pool is exhausted. Keep a few percent in
reserve for whatever must run at the end of a session (handoff notes, summaries):
a job that dies mid-flight costs more than one that never started.

## Sources, in order

- **Claude**: live `https://api.anthropic.com/api/oauth/usage` call using the token
  in `~/.claude/.credentials.json` → optional `--claude-observation PATH` file →
  `~/.claude.json` cache (`cachedUsageUtilization`, only refreshed by an interactive
  `/usage` call, can be hours stale).
- **Codex**: CodexBar's live snapshot (`%APPDATA%/CodexBar/codex-accounts/snapshots.json`
  on Windows, `~/Library/Application Support/CodexBar/...` on macOS,
  `~/.config/CodexBar/...` on Linux) → newest `rate_limits` record under
  `~/.codex/sessions/**/*.jsonl`.

## `--claude-observation` file schema

Wire your own statusline/hook to write a small JSON snapshot more often than the
`/usage` cache refreshes, then pass its path with `--claude-observation`:

```json
{"epoch": 1758100000, "five": 18.0, "seven": 92.0, "five_reset": 1758113500, "seven_reset": 1758350000}
```

`epoch` (unix seconds), `five`/`seven` (0–100, the 5-hour/7-day window percentages)
are required; `five_reset`/`seven_reset` (unix seconds) are optional. Older than 45
minutes is ignored. All-zero values are treated as **unreadable**, not an empty pool
— an upstream HTTP 429 can write `0` where it means "could not measure".

## Limits

- No per-model weekly windows for Claude (e.g. a Max-plan Opus-specific window) —
  whatever extra windows the live endpoint returns are shown, but nothing is
  synthesized if it doesn't return them.
- CodexBar is optional; without it the script falls back to session rollout files,
  which are only written while `codex` is running and can be stale for days.
- These are subscription usage windows (percent of a rolling quota), not token counts.
