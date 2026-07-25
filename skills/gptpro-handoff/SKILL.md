---
name: gptpro-handoff
description: >-
  Run the research/audit handoff loop between an agentic coding harness and a slow,
  non-agentic frontier reasoning model (GPT Pro on the ChatGPT web UI, or equivalent)
  with the codebase pre-loaded as split zip bundles. Author a high-signal prompt, then
  later take the returned report, verify every finding against the LIVE codebase, and
  implement what holds up. Use whenever the operator wants to send something to a deep
  external model, prep a prompt or report, scope an issue for deep research, bug-hunting,
  or optimization analysis, OR when a report comes back and needs checking against the
  code before anything is implemented. This is the WORKFLOW skill — to build or refresh
  the zip bundles themselves, use the separate `gptpro` export skill.
---

# Deep-model handoff loop

A **slow, non-agentic frontier reasoning model** is a different tool from your
coding agent, and it needs a different workflow. This skill is that workflow.

Written against GPT Pro on the ChatGPT web UI, with the codebase loaded into a
Project as split zip bundles (produced by the `gptpro` export skill). It
transfers to any deep model you reach through a chat UI rather than a harness.

The defining fact: **the model is non-agentic** — no shell, no live filesystem,
bounded context. It reasons over a static snapshot.

That drives the entire discipline: **it proposes, you verify, then you
implement.** Its report is the strongest kind of input, but it is read against a
snapshot that may lag the live tree, and it cannot run a test. Nothing ships
unchecked. In practice the large majority of findings hold up — the job is to
catch the ones that don't before they cost you.

## What this model is (and how it behaves)

Internalize the model before writing for it. Its constraints and its
personality both shape the prompt.

- **No harness, no live repo.** It runs in the chat provider's own container:
  no shell, no tools, no filesystem. It sees only the **bundled snapshot** you
  upload. On the harness axis it is strictly disadvantaged; its reasoning depth
  is what makes up for that. **You give up "can run a test" to buy "can
  out-think the problem."**
- **Slow, deep, one-shot.** A single answer can take **~50–60 minutes**. You do
  not iterate cheaply. The prompt must be complete and self-contained, because
  there is no follow-up channel mid-run.
- **The prompt is the entire interface.** The agent authors it; the operator
  copies it verbatim into the web UI. No tool call, no back-channel. What you
  write is exactly and only what the model gets.
- **The operator sets the reasoning tier at send time.** NEVER put
  reasoning-effort instructions in the prompt (no "use xhigh", no `<REASONING>`
  block) — that's a UI control, so any such text is dead weight crowding the
  real instructions.
- **Obsessively literal.** It follows instructions to the letter and
  hyper-focuses on exactly what you specify. A superpower for audits, and a
  trap for research: over-constrain a prompt meant to surface theories and it
  will tunnel on your seeds and never bring you the ideas you couldn't think of
  yourself.

### Calibrate the leash to the intent

Because the model is so literal, prompt tightness is a dial you set
deliberately:

- **Audit / verification → tight leash.** When the job is "check THIS against
  the code," constrain hard: VERIFIED/HYPOTHESIS labeling, confirm-or-refute
  each seeded hypothesis, fixed output format, DO-NOT roadmap. The rigid
  structure is what makes verification fast and the report triageable.
- **Research / theory / exploration → loose leash.** When the job is "tell us
  what we're missing," do the opposite: state the problem and the constraints,
  then **explicitly grant freedom to reason independently, challenge your
  framing, and surface directions you didn't ask about.** Seeds are a floor,
  not a fence — say so ("our hypotheses are a starting point; go beyond them,
  and tell us where we're wrong"). Leash a research prompt like an audit and
  you waste the one thing this model is best at.
- **Blended (most real prompts) → label the halves.** Mark which objectives are
  "verify tightly" and which are "run free."

Keep the invariants hard even on a loose leash. **Free on ideas, fixed on
constraints.**

## The loop

```
1. SCOPE      — pin one well-framed problem with the operator (not "review everything").
2. AUTHOR     — write the prompt together; save to gptpro/issue-NN-<slug>.md.
3. FRESHEN    — if code changed materially since the last export, re-run `gptpro`.
4. HAND OFF   — operator pastes the prompt into the web UI.
5. RECEIVE    — operator brings the report back; save to gptpro/issue-NN-<slug>.report.md.
6. VERIFY     — re-check every finding against the LIVE codebase (this is the gate).
7. IMPLEMENT  — apply what holds up; record what didn't and why.
```

Steps 1–3 are one session's work. Steps 5–7 usually happen in a later session,
when the report lands.

## 1–2. Scope and author

A good payload is **one hard problem, deeply framed** — not a grab-bag. Pin
three things with the operator first:

- **The decision** — what the model should produce (a critique? a chosen
  design? a prioritized fix list? a teardown of an approach you doubt?).
- **The frame** — the minimal context that makes it answerable: constraints,
  what's already decided and won't be relitigated, invariants it must respect.
- **Focus + anti-focus** — the surfaces and files to attend to, and what's
  explicitly out of scope so it doesn't wander.

Then write in the house style — see
[references/prompt-style.md](references/prompt-style.md) for the XML structure,
the VERIFIED-vs-HYPOTHESIS rule, and a ready skeleton. Non-negotiables:

- **Ground it in your code.** Give the real architecture and file anchors. Seed
  your hypotheses, but tag each "confirm, refute, or extend against the actual
  code" so it verifies rather than parrots.
- **Set the leash to the intent** (above).
- **State invariants as hard constraints — always.** The model is helpful to a
  fault; if you don't say a consistency boundary must hold, it may cheerfully
  propose moving it.
- **Demand a prioritized, incremental roadmap** with impact × effort ranking and
  a DO-NOT column — that roadmap is the direct input to step 7. (A pure-theory
  prompt may want an open synthesis instead.)
- **Never put a reasoning level in the prompt.**

## Where prompts and reports live

Everything goes in a **gitignored `gptpro/`** folder at the repo root — these
are local handoff artifacts, never committed:

- `gptpro/issue-NN-<slug>.md` — the prompt you author.
- `gptpro/issue-NN-<slug>.report.md` — the returned report, pasted back.

Number issues sequentially so a session can carry several handoffs and you can
refer to them unambiguously.

## 3. Keep the bundles fresh

The model reasons over the last-exported zips. If you've shipped changes since
the last export and the new prompt depends on that code, the snapshot is stale
— re-run the `gptpro` export and have the operator re-upload the changed
bundles. When in doubt, **name the export date in the prompt** so the model
knows the snapshot's age and can flag drift itself.

## Standing project instructions

If your chat provider supports a persistent Project or custom-instructions
blurb, put the "what this system is + answer like a senior engineer, ground in
the attached code, label uncertainty" context there once. Individual prompts
then focus on the specific issue instead of re-explaining the project every
time. If the operator is setting up a fresh Project, offer that blurb first.

## 5–6. Receive and verify (the gate)

This is where the value is captured or lost. For each finding, before treating
it as actionable:

- **Re-anchor it.** Open the `file:line` it cited in the LIVE tree. Bundles lag
  — the line may have moved, the code may already be fixed, or the symbol may
  be gone. Confirm the finding still describes reality.
- **Reproduce the claim.** It couldn't run anything. If it claims a bug, trace
  the code path or write the failing test. If it claims a cost, sanity-check
  the mechanism. A VERIFIED tag means "I found it in the snapshot," not "I
  proved it at runtime."
- **Check it against your invariants.** Reject anything that weakens a
  governance gate, crosses a consistency boundary, or contradicts a decision
  already made — even if the model is confident. **Confident-and-wrong is the
  failure mode that matters.**
- **Triage** into: implement now, needs-a-decision (back to the operator), and
  discard — with a one-line reason so it isn't re-litigated later.

Spawn parallel verification sub-agents when a report has many findings, one per
finding or cluster — but **the conclusion is yours to make**, grounded in the
live code, not the sub-agent's say-so.

## 7. Implement

Implement what survived verification, following the repo's normal discipline
(tests with every change; typecheck and build green before claiming done). Work
the prioritized roadmap top-down. When a finding is implemented or rejected,
note it in the `.report.md` so the next session knows what's been actioned. The
operator can then take a follow-up question back for the next round.

## Anti-patterns

- **Don't rubber-stamp.** "The model said so" is not a reason to merge. The high
  hit rate is *earned by verifying*, not a license to skip it.
- **Don't hand it a vague brief.** "Review the codebase" wastes a 60-minute run.
  One framed problem per prompt.
- **Don't let bundles rot silently.** A confident report against month-old code
  is worse than no report. Freshen, or flag the snapshot age.
- **Don't fragment a coherent problem** into many thin prompts when one deep,
  well-scoped prompt would let the model see the whole shape. Genuinely separate
  concerns do get separate, sequential prompts.
