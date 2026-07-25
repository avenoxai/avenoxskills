---
name: fable-orchestration
description: "Delegation policy for a multi-model agent stack where the main loop runs on a scarce top-tier model (e.g. Claude Fable) and cheaper/unlimited tiers do the mechanical work. The main loop owns architecture and judgment; sub-agents (Opus) and Codex lanes execute. Load whenever spawning sub-agents (Agent tool, Workflow agent() calls, codex fleets) or planning any delegation."
---

# Orchestration & delegation policy (scarce-top-tier stack)

A routing policy for stacks with **one scarce, expensive main-loop model** and
**cheaper or unlimited delegate tiers**. Written against a Claude Fable main
loop with Opus sub-agents and Codex lanes, but the shape transfers to any
stack with the same economics.

Core law: **the scarce model must not do pleb work, and must not be spawned as
a sub-agent.** Its tokens buy judgment, not throughput.

## The hard rules

1. **Scarce tier as sub-agent: sparingly, never aggressively.** Default to an
   explicit `model: 'opus'` on every Agent tool / Workflow `agent()` call and
   `meta.phases` entry — never omit-and-inherit when the parent is the scarce
   tier, or you silently fan out your most expensive model. A rare
   judgment-heavy delegated task may use it, only when the cheaper tier
   genuinely can't carry the work. Also prefer the main loop doing work
   hands-on over reflexive delegation while limits are healthy — delegation has
   its own overhead.
2. **No mid-tiers.** Pick a small number of delegate tiers and stick to them.
   In this stack: **Opus** (unlimited) and **Codex gpt-5.x** (via `codex exec`).
   Mixing in more tiers makes routing decisions unauditable.
3. **The main loop keeps the big picture.** Architecture, specs,
   contract-sensitive design, subtle state machines, integration and conflict
   resolution, final synthesis, judgment calls — all done in the main loop.
   Mechanical, scoped, parallelizable work gets delegated.

## Choosing the delegate

- **Codex (`gpt-5.x`, xhigh reasoning effort) — the default for most high-level
  tasks**, including substantial implementation lanes. It is an obsessive
  instruction follower: nearly as capable as the scarce tier, but less
  creative. It does not improvise well — it *executes*. Give it a carefully
  written, detailed, explicit spec and it will grind through it relentlessly
  and precisely. Use for: implementation lanes, migrations, refactors,
  test-writing against a defined contract, scenario authoring — anything where
  the spec is complete and deviation is unwanted.
- **Opus — mainly for context gathering.** Exploration, codebase mapping,
  research sweeps, reviews, verification passes — work where the brief can be
  loose and the deliverable is understanding, not a diff. Opus copes well with
  ambiguity: hand it a goal and let it figure out the terrain.

Rule of thumb: **context gathering → Opus; execution (once the main loop has
written the spec) → Codex; judgment / synthesis / spec-writing → the main loop
itself.** The quality of a Codex lane is bounded by the quality of the spec —
invest tokens in the brief, not in doing the lane yourself.

## The difficulty axis

The routing axis is **difficulty**, not just recon-vs-execution.

- **Simple, well-bounded work → Opus agents.** This includes light *execution*:
  templated UI ops, e2e clones of an existing pattern, features that ride an
  existing pipeline end-to-end. Opus is unlimited and copes with looser briefs.
- **Hard or precision work → Codex xhigh lanes with a complete spec.** Core
  evaluator seams, security-critical strengthen-never-relax changes,
  correctness-sensitive paths, the largest surfaces.
- **Gate-reviewer lanes stay on the highest Codex preset** regardless of the
  size of what they're reviewing.

When assigning fleet lanes, stamp the adapter per lane in the spec so the
launch is mechanical and no routing decision happens at spawn time.

## Exceptions

- If the operator explicitly names a model for a scoped task, honor it for that
  task only, then return to this policy.
- The operator can override any of this per session; absent that, this policy
  stands.
