---
name: fable-orchestration
description: "Delegation policy for a multi-model agent stack where the main loop runs on a strong but expensive model (e.g. Claude Fable 5.2). The main loop orchestrates, writes briefs and synthesizes; the work is routed by difficulty. Medium-high difficulty goes to Opus with a fairly loose brief; simple-medium goes to Sonnet with a tighter brief. GPT-side execution goes to gpt-6.1-sol with a detailed step-by-step brief; second opinions and out-of-the-box thinking go to gpt-6-astra. Very large data cleanup goes to Claude Haiku 5.5 or gpt-6-luna. Load whenever spawning sub-agents (Agent tool, Workflow agent() calls, codex fleets) or planning any delegation."
---

# Orchestration & delegation policy (expensive-main-loop stack)

A routing policy for stacks with **one strong, expensive main-loop model** and
**cheaper delegate tiers**. Written against a Claude Fable 5.2 main loop with
Opus, Sonnet and Haiku sub-agents and Codex lanes, but the shape transfers to
any stack with the same economics.

Core law: **the expensive model's tokens buy judgment, not throughput.** It
writes the plan, the briefs, the hard calls and the final synthesis.
Everything else goes to the cheapest tier that can carry it.

## The routing table

| Work | Goes to | How to call it | Brief style |
|---|---|---|---|
| Architecture, specs, hard judgment, integration, final synthesis | **Main loop** (Fable) | itself | n/a |
| Medium-high difficulty: multi-file implementation, real debugging, research that needs judgment, review and verification | **Opus** | `model: 'opus'` | Fairly loose: goal, context, constraints, what done looks like |
| Simple-medium: scoped edits, pattern clones, lookups, templated work, straightforward reading and summarizing | **Sonnet** | `model: 'sonnet'` | A notch tighter: named files, steps, output shape, boundaries |
| GPT-side execution, when the operator asks to send work to GPT | **gpt-6.1-sol** | `codex exec -m gpt-6.1-sol` | Detailed and step by step, nothing left implicit |
| Second opinion, out-of-the-box thinking, an angle the main loop may be missing | **gpt-6-astra** | `codex exec -m gpt-6-astra` | The open question plus the evidence, as to a peer |
| Very large data cleanup: thousands of rows or files, normalizing, deduplicating, classifying, extracting | **Claude Haiku 5.5** or **gpt-6-luna** | `model: 'haiku'` / `codex exec -m gpt-6-luna` | Exact rule set with input and output examples, small batches, spot checks |

## The hard rules

1. **Always pass an explicit `model:`** on every Agent tool call, Workflow
   `agent()` call and `meta.phases` entry. Omitting it inherits the main-loop
   model and silently fans out your most expensive tier.
2. **The main-loop model is not a sub-agent tier.** Spawn it as a sub-agent
   only when the operator names it for that task, or when a rare
   judgment-heavy piece genuinely fails on Opus.
3. **Route by difficulty, then pick the cheapest tier that can carry it.**
   When unsure between two tiers, take the cheaper one and verify the result;
   escalate one tier on failure rather than starting high.
4. **Claude tiers are the default.** The GPT side is used when the operator
   asks for it, with two standing exceptions: a second opinion on a hard call
   goes to astra, and bulk cleanup may go to luna.
5. **The main loop keeps its own context lean.** Wide reading, file dumps and
   raw data go to a delegate that returns the conclusion; the main loop reads
   what it must judge. Small things (a handful of tool calls, one known file)
   it does itself, since a delegation costs more than it saves there.
6. **A delegate's report is a claim.** Check the diff, the output or a sample
   before reporting it as done.

## Brief shape per tier

How tightly to write depends on who reads it.

- **Opus (fairly loose).** State the goal and why it matters, the context it
  cannot discover on its own, the constraints, and what done looks like. Leave
  the route to it. Over-specifying an Opus brief costs tokens and removes the
  judgment you are paying for.
- **Sonnet (a notch tighter).** Name the files or area, list the steps in
  order when order matters, give the output format, and say what not to touch.
  Say when to stop and report instead of improvising. One task per agent.
- **gpt-6.1-sol (detailed, complete).** Sol is a soldier: it does exactly
  what the brief says, step by step, with nothing skipped and nothing added.
  That makes the brief the whole quality ceiling. Write numbered steps,
  exact paths and commands, the acceptance check for each step, the edge cases
  and what to do in each, and the things that are out of scope. Anything left
  unsaid will not happen. Do not ask it to "use judgment" on an open design
  question; decide that first, then hand it the decision.
- **gpt-6-astra (peer question).** Give it the problem, the evidence, the
  options you see and where you are unsure, and ask for what you may be
  missing. Do not hand it your conclusion to confirm. Treat the answer as a
  peer review and disagree on evidence. Medium or high effort; `xhigh` or
  `max` only when the question justifies it.
- **Haiku 5.5 / gpt-6-luna (bulk).** One mechanical rule set, stated exactly,
  with two or three input and output examples. Split the data into batches
  small enough that a bad batch is cheap to redo, have each batch write to its
  own output file, and sample the results before merging. Never ask this tier
  to decide what the rules should be.

Long briefs go in a file; the prompt points at the file.

## Codex lanes

GPT lanes run through `codex exec` (recipe in [`codex-fleet`](../codex-fleet/SKILL.md)).
Execution lanes run on `-m gpt-6.1-sol`, that skill's default; pass
`-m gpt-6-astra` for second opinions and `-m gpt-6-luna` for bulk cleanup. Effort: `medium` for
routine lanes, `high` for precision lanes, `xhigh` or `max` only for an
explicitly heavy lane. When assigning fleet lanes, stamp the model per lane in
the spec so the launch is mechanical and no routing decision happens at spawn
time.

## Exceptions

- If the operator explicitly names a model for a scoped task, honor it for that
  task only, then return to this policy.
- The operator can override any of this per session; absent that, this policy
  stands.
