# Mascot contract, expressions & safety

## On-model contract (fill this in, then never break it)

Write your mascot's contract here as a single sentence you can paste verbatim
into every prompt. Be specific about **shape, outline weight, shading style,
and face** — those four are what drift first.

```
The mascot is: a <body shape/color>, <outline weight> outline,
<shading style>, <distinguishing feature 1>, <distinguishing feature 2>,
<limb style>.
```

*Worked example (a deadpan yellow lemon character): "a tall rounded YELLOW
lemon body, thick black ink outline, halftone-dot shading, a big long nose,
heavy-lidded deadpan eyes, thin simple arms and legs."*

Rules:

- Always pass `assets/mascot-ref.png` as an `-i` reference and say **"keep
  EXACTLY on-model"** in the prompt. Text description alone is not enough.
- Same colors, same outline weight, same face every time — this is the
  channel's brand recognition, and it compounds. A drifting mascot is worth
  less than no mascot.
- **Costumes and props are fine** (hat + vest as a merchant, engineer hard-hat,
  holding a sword / scroll / hardware) as long as the body and face still read
  as the same character.
- Keep at most one or two variant references (e.g. an angry/shouting version
  for outrage topics). Default to the neutral ref. More variants = more drift.

## Expression menu (match the video's emotion)

deadpan-confident • smug/knowing (temple tap) • suspicious side-eye •
wide-eyed shocked • worried/nervous (sweat drop) • lazy/couldn't-care-less •
over-eager yes-man forced smile • amazed/delighted celebration •
grumpy stubborn elder.

Pick the one that **dramatizes the hook**, not the one that describes the
topic. Examples: hallucination → confident-wrong; sycophancy → forced smile;
memory loss → confused; a ban → worried.

## Pose safety — HARD RULES

1. **NO straight raised outstretched arm / open palm.** Combined with a crowd
   or an army behind the character, this reads as a fascist salute and risks
   the thumbnail being flagged. This is not hypothetical — it happened on an
   "army of agents" cover and had to be re-fired.
2. **Commander / hero / leader poses must keep both arms bent and occupied:**
   holding a banner or sword, hand on hip, fist raised, presenting to the side,
   arms folded, hands behind head. State this explicitly in the prompt:
   *"arms bent, NO straight raised arm/salute."*
3. **Vary poses across a batch.** Three covers with an identical stance looks
   lazy, and for a series it reads as "already watched" — viewers skip it.

Generative image models do not know your channel's risk tolerance. These
constraints have to be in the prompt every single time; they will not be
inferred.

## Composition defaults

- **Text LEFT, mascot RIGHT** (matches scan order), or mascot centered for a
  solo hero shot.
- Keep the **lower-right corner clear** — YouTube stamps the duration there —
  and avoid the far right edge where UI buttons overlay.
- **One clear focal element.** Cut the mascot out with a crisp white or dark
  outline so it separates from the background.
- **Three elements maximum.** Clutter loses the blink test, and the blink test
  is the only test that matters at sidebar size.
