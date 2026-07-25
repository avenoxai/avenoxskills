---
name: avenox-thumbnail
description: >-
  Generate high-CTR YouTube thumbnails for a mascot-driven channel using parallel
  gpt-image-2 jobs via the Codex CLI. Use whenever the user asks for a thumbnail,
  cover, or thumbnail alternatives for a video, wants their mascot on a cover, or
  asks to retrofit new thumbnails onto old videos. Produces on-model mascot + a big
  2-4 word hook + tool logos + high-contrast covers, saved 1280x720 ready for
  YouTube A/B testing.
---

# Thumbnail Factory

A systematic pipeline for producing scroll-stopping YouTube thumbnails for a
**mascot-driven channel**. It encodes the formula, the working prompt recipe,
the hook-pattern playbook, and the hard safety rules learned in production.

Built for anonymous / faceless channels: the mascot is the face, so the
covers stay consistent without ever putting a person on screen.

> **Anonymity rule:** never put the creator's real name, personal handle, or
> likeness on a thumbnail. If the channel is anonymous, the mascot *is* the
> identity — breaking that once is not reversible.

## Configure before first use

| Setting | Where | Example |
|---|---|---|
| Mascot reference image | `assets/mascot-ref.png` | see `assets/README.md` |
| Mascot on-model contract | `references/character-and-safety.md` | fill in the contract block |
| Hook language | prompt (`HOOK_LANG`) | `Turkish`, `English`, … |
| Output dir | `$THUMB_OUT` | `~/Desktop/thumbnails` |

## The formula

Every thumbnail = **4 ingredients, nothing more** (3-element rule; blink-test
first — if it doesn't read in a quarter second at sidebar size, it failed):

1. **The mascot** — on-model, expressive pose that fits the video's emotion.
2. **One 2-4 word hook** — MASSIVE bold sans-serif caps, **white + ONE accent
   word**, thick black outline. Never duplicate the video title; open a
   curiosity gap that the title and video close.
3. **Relevant tool logo(s)** — so the topic is legible in one glance.
4. **High-contrast modern background** — dark + one strong accent color
   (red = urgency, green = success, blue = tech, purple = automation,
   gold = money). Bright, saturated, clean.

Design levers (apply, don't just decorate): curiosity gap • negativity/risk •
contrast (before/after, ✓/✗) • tangible number or timeframe • authority • one
clear focal point • lower-right corner kept clear (YouTube stamps the duration
there) • text left / mascot right reads best.

Full hook playbook → `references/hook-patterns.md`.

## Standard workflow

1. **Read the video** — title + description/topic. Identify the single most
   clickable angle.
2. **Propose hooks** (unless told "just fire") — 2-3 distinct concept
   directions: hook words + composition + which logo + which pattern. Let the
   user pick, or fire all as alternatives.
3. **Fire in PARALLEL** — one `codex exec` gpt-image-2 job per concept, all
   `run_in_background: true` in a single message. The user wants alternatives;
   compute isn't the constraint. Recipe → `references/prompt-template.md`.
4. **Save** all outputs to `$THUMB_OUT` with descriptive names
   (`<video>-<letter>-<hook>.png`).
5. **md5-dedupe** after the batch — parallel gpt-image-2 jobs can occasionally
   return duplicate images. Re-fire any duplicate solo.
6. **Show + recommend** — look at each PNG, give an honest verdict, say which
   title it pairs with, and make an A/B recommendation.
7. **Deliver finals** — `sips -z 720 1280 <file>` (exact YouTube 1280×720,
   under 2MB) and copy out with a clear name.

## Mascot contract

The mascot must stay **on-model every time** — same colors, same outline
weight, same face. That consistency *is* the brand recognition; a mascot that
drifts is worth less than no mascot.

Costumes and props are fine (hat, vest, holding an object) as long as the body
and face still read as the same character.

**HARD SAFETY RULE — never violate:** do NOT pose the mascot with a straight
raised outstretched arm / open palm. With a crowd or army behind it, that reads
as a fascist salute and will get the thumbnail flagged. Commander/hero poses
must keep **both arms bent and occupied** (holding a banner or sword, hand on
hip, fist raised, presenting to the side). Vary poses across a batch — don't
reuse an identical stance.

Full contract, expression menu, and safe-pose list →
`references/character-and-safety.md`.

## Series rule

For a numbered series, **never bake the episode number into the thumbnail** —
it makes viewers watch only Part 1. Give each episode a distinct, standalone
hook that fits *that* episode, and vary the accent color and pose so the covers
don't look like copies of each other. Copy-paste covers read as "already
watched".

## References

| File | Read for |
|---|---|
| `references/prompt-template.md` | the exact working `codex exec` gpt-image-2 command + prompt skeleton, non-Latin text handling, sizes, output handling |
| `references/hook-patterns.md` | the hook/title pattern library and how to map a video to hooks |
| `references/character-and-safety.md` | mascot on-model contract, expressions, poses, safety rules |
| `references/logo-library.md` | how to fetch and rasterize brand logos |

Requires the `codex-fleet` skill for the underlying Codex CLI image runner.
