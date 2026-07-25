# Deep-model prompt house style

Frontier reasoning models on a chat front end are prompt-sensitive and highly
steerable: they follow instructions literally, build scaffolding by default,
run lower verbosity than predecessors, stay conservatively grounded (favoring
correctness over speculation), and are excellent at internal self-critique.

Vague prompts fail; explicit ones excel — but "explicit" means a clear problem
and clear constraints, **not** a narrow leash on everything. Because the model
follows instructions so literally, **match prompt tightness to intent**: tight
for verification, loose for research (see SKILL.md, "Calibrate the leash to the
intent").

Do NOT set a reasoning level in the prompt — the operator picks the tier in the
UI at send time, so any reasoning-effort text is dead weight.

## XML structure

These models parse XML-tagged sections with high fidelity. Standard skeleton
for a research/audit handoff:

```xml
<ROLE>
A specific senior expert (e.g. "principal distributed-systems engineer who has
shipped production sync engines"). The role shapes the lens — be concrete, and
push it toward "answers from THIS code, not generic folklore."
</ROLE>

<TASK>
The decision the model must produce. Number the objectives if there's more than
one. Be explicit about what the deliverable is.
</TASK>

<CONTEXT>
The real architecture, in enough detail to reason from. Point at the
authoritative doc(s) ("READ X FIRST"). Give the file anchors to inspect.
Include EMPIRICAL SIGNALS (sizes, counts, timings) as leads to verify, not as
conclusions. List YOUR HYPOTHESES and tag each "confirm, refute, or extend
against the actual code" so the model verifies instead of agreeing. State the
hard INVARIANTS it must respect.
</CONTEXT>

<self_reflection>
Before answering, build an internal rubric (6–8 categories) for a world-class
answer to THIS task — grounded-in-code, separates verified from hypothesis,
quantifies cost, names specific industrial techniques mapped to our
constraints, respects the invariants, prioritizes by impact-vs-effort,
implementable incrementally. Iterate internally until top marks across all.
Show only the final answer.
</self_reflection>

<long_context_handling>
First produce an internal outline from the code + docs. Re-state the
load-bearing constraints before recommending. Anchor every claim to a
file/section; quote the specific mechanism (function, file:line, config knob)
rather than describing it abstractly.
</long_context_handling>

<uncertainty_handling>
Label each finding VERIFIED (confirmed in the attached source) or HYPOTHESIS
(plausible, unconfirmed). Never fabricate line numbers, sizes, or APIs. State
assumptions explicitly. Where our hypotheses are wrong, say so and show the
code that refutes them.
</uncertainty_handling>

<OUTPUT_FORMAT>
Lead with a short executive summary (highest-impact only), then the structured
body, then a PRIORITIZED ROADMAP table (Change | Objective | Impact | Effort |
Risk | Rank) with a DO-NOT row for anything that would cross an invariant, then
≤5 open questions for the operator. Specify exactly what each section contains.
</OUTPUT_FORMAT>

<CONSTRAINTS>
Ground everything in the attached codebase + docs; flag drift between what the
code does and what the docs claim. No from-scratch rewrites unless provably the
only fix. Never weaken a stated governance/consistency invariant. Industrial
references must name the system AND the borrowable technique — no vague "use
CRDTs." No filler.
</CONSTRAINTS>
```

No `<REASONING>` block: the operator sets the tier in the UI, so putting it in
the prompt is dead weight. For a research/theory prompt, add an `<exploration>`
block instead (see below).

## The rules that matter most

1. **Match the leash to the intent.** Tight for audit, loose for research. The
   model follows instructions so literally that an over-constrained research
   prompt tunnels on your seeds and never surfaces the ideas you couldn't
   pre-specify — the one thing it's best at. Rules 2 and 5 are the audit-mode
   toolkit: apply them in full for verification, relax them for exploration.
2. **VERIFIED vs HYPOTHESIS labeling** is the load-bearing instruction for
   audits. It makes the report triageable and stops the model laundering your
   own guesses back to you as facts. Relax it for pure-theory prompts.
3. **Seed, don't spoon-feed.** Give your hypotheses and empirical signals, but
   always framed as "verify against the code — and go beyond it." You want it
   to find what you missed and kill what you got wrong, not agree with you.
4. **State invariants as hard constraints — even on a loose leash.** The model
   is helpful to a fault; if you don't say the consistency gate must hold, it
   may cheerfully propose making it local-first. Free on ideas, fixed on
   constraints.
5. **Demand the prioritized DO-NOT roadmap** for audit/roadmap prompts. That
   table is the direct input to the implement step — it gives you sequence and
   flags the traps. A pure-theory prompt may want an open synthesis instead.

## Optional blocks to add per task

| Block | Use when |
|---|---|
| `<scope_constraints>` | you need to prevent feature creep / over-engineering |
| `<persistence>` | a long autonomous deliverable the model should fully complete |
| `<high_risk_self_check>` | security, financial, or compliance-sensitive analysis |
| `<extraction_spec>` | you want structured/JSON output with a fixed schema |
| `<exploration>` | research/theory prompts — explicitly grant freedom to go beyond the seeded hypotheses, challenge your framing, and surface directions you didn't ask about |

Use `<exploration>` to loosen the leash, often *instead of* a rigid
`<OUTPUT_FORMAT>`, when you want ideas you couldn't pre-specify. Keep
`<CONSTRAINTS>` hard even there. In a blended prompt, scope it to the research
objectives and leave the audit objectives tightly formatted.

## Keep a worked example

Once you've authored a prompt that produced a genuinely good report, keep it as
your house reference (`gptpro/issue-01-<slug>.md`) and read it before writing a
new one. A concrete example of your own architecture, invariants, and voice
teaches the pattern faster than any style guide — including this one.
