# Logo library & fetch recipe

This repo ships **no logo files** — third-party marks are trademarks and
redistributing them isn't ours to do. Fetch what you need into
`assets/logos/`, and check the brand's trademark policy before publishing.

Pass logos as extra `-i` references and name each one in the prompt
("Reference 2 is the CLAUDE logo…"). For a two-logo "combo" cover, put them in
a tidy row above the headline; for a "vs" cover, one per side.

## Fetching a brand logo

If you have no `libcairo`/`rsvg`/`cairosvg` installed, rasterize SVGs on macOS
with **`qlmanage`** (Quick Look), which renders SVG via WebKit.

```bash
cd <skill>/assets/logos

# 1) colored SVG from Simple Icons (slug + hex, no leading #):
curl -sL "https://cdn.simpleicons.org/<slug>/<HEX>" -o <name>.svg

# 2) rasterize to PNG:
qlmanage -t -s 512 -o . <name>.svg     # -> <name>.svg.png
mv <name>.svg.png <name>.png
```

**Verify the PNG by looking at it** before using — `qlmanage` silently renders
an error page if the SVG was empty or a 404, and you won't notice until it's
baked into a thumbnail.

## Gotchas

- **Some brands are removed from Simple Icons** on trademark grounds (OpenAI /
  ChatGPT among them) — the slug returns empty. Get those from Wikimedia:
  ```bash
  curl -sL -A "Mozilla/5.0" "https://commons.wikimedia.org/w/api.php?action=query&titles=File:<FILE>.svg&prop=imageinfo&iiprop=url&iiurlwidth=512&format=json"
  # take .query.pages[].imageinfo[0].thumburl, then curl -A "Mozilla/5.0" that URL -> png
  ```
- Wikimedia requires a non-empty User-Agent (`-A "Mozilla/5.0"`) or it returns
  403 / an HTML error page.
- `cdn.simpleicons.org/<slug>` with no hex sometimes rate-limits — retry, or
  always pass a hex.
- **Monochrome marks need a plate.** A white logo on a light background
  disappears; drop it into a filled circle in the brand's own color so it reads
  at sidebar size.
