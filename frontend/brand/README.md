# Bunyan brand assets

The approved identity as files. Colours follow the Riyadh visual theme (PR #13); the logo
keeps its approved shape and colours. This folder is the source the code uses.

## Files

| Path | What |
|---|---|
| `logo/bunyan-logo-ar.svg`, `logo/bunyan-logo-en.svg` | Full logo, light backgrounds |
| `logo/*-dark.svg` | Same, for dark backgrounds |
| `logo/bunyan-mark*.svg` | The mark alone (Arabic, English, dark, single colour) |
| `logo/bunyan-app-icon*.svg` | App icon, 512 px |
| `../public/favicon.svg` | Browser icon, follows the device theme |
| `tokens.json` | Riyadh palette, colours (light and dark), type scale, spacing, radii, logo rules |
| `../src/styles/tokens.css` | The same tokens as CSS variables, used by every screen |

## Logo rules

- Three blocks of 10 units with a 2-unit joint on a 22 × 22 grid, corner radius 1.6.
- The green block (`--bn-brand`) sits on the base, on the side that faces the wordmark: left in Arabic, right in English. The other two use `--bn-brand-ink`.
- Mark first, then the word: right of «بُنيان», left of «Bunyan AI».
- Clear space: one block on every side. Minimum size: 16 px for the mark, 88 px wide for the full logo.
- No gradients, shadows, outlines, rotation or extra blocks.
- The wordmark uses IBM Plex Sans Arabic 600. The SVG files reference the font by name, so convert the text to outlines before print or before sending to anyone without the font.

## Colour rules

- One palette for the whole product: `--bn-riyadh-*` in `tokens.css`. Screens use the semantic tokens (`--bn-bg`, `--bn-text`, `--bn-accent`…), never the raw palette; the landing page (`landing.css`) maps its own names to the same raw values.
- Light theme: white and lavender-tinted surfaces, Riyadh ink text, deep purple accent. Dark theme: the landing page's night palette (midnight, navy, indigo, lavender accent).
- `--bn-highlight` (champagne gold) is for small details only: numbers, coordinates, thin rules. Never for text blocks or buttons.
- `--bn-accent` is for the primary action and links only.
- `--bn-brand` and `--bn-brand-ink` are for the logo only.
- Status is coloured text with a dot, always with a word.
- Shadows only on floating windows (dialog, toast).

Change a value in `tokens.json` and `src/styles/tokens.css` together.
