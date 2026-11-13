# Bunyan brand assets

The approved identity (direction C, calm green) as files. The full brand guide lives in the
team's design-system page; this folder is the source the code uses.

## Files

| Path | What |
|---|---|
| `logo/bunyan-logo-ar.svg`, `logo/bunyan-logo-en.svg` | Full logo, light backgrounds |
| `logo/*-dark.svg` | Same, for dark backgrounds |
| `logo/bunyan-mark*.svg` | The mark alone (Arabic, English, dark, single colour) |
| `logo/bunyan-app-icon*.svg` | App icon, 512 px |
| `../public/favicon.svg` | Browser icon, follows the device theme |
| `tokens.json` | Colours (light and dark), type scale, spacing, radii, logo rules |
| `../src/styles/tokens.css` | The same tokens as CSS variables, used by every screen |

## Logo rules

- Three blocks of 10 units with a 2-unit joint on a 22 × 22 grid, corner radius 1.6.
- The green block (`--bn-brand`) sits on the base, on the side that faces the wordmark: left in Arabic, right in English. The other two use `--bn-brand-ink`.
- Mark first, then the word: right of «بُنيان», left of «Bunyan AI».
- Clear space: one block on every side. Minimum size: 16 px for the mark, 88 px wide for the full logo.
- No gradients, shadows, outlines, rotation or extra blocks.
- The wordmark uses IBM Plex Sans Arabic 600. The SVG files reference the font by name, so convert the text to outlines before print or before sending to anyone without the font.

## Colour rules

- `--bn-accent` is for the primary action and links only.
- `--bn-brand` and `--bn-brand-ink` are for the logo only.
- Status is coloured text with a dot, always with a word.
- Shadows only on floating windows (dialog, toast).

Change a value in `tokens.json` and `src/styles/tokens.css` together.
