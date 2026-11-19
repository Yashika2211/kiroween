---
inclusion: fileMatch
fileMatchPattern: "frontend/**"
---

# Theme and tone

The UI is a graveyard. It should feel spooky and crafted, never cheesy, and always readable.

## Vocabulary
| Concept          | Word in the UI     |
|------------------|--------------------|
| Submit a repo    | Summon             |
| Analysis report  | Death Certificate  |
| Plan generation  | Ritual             |
| Applying fixes   | Resurrection       |
| PR opened        | Rise               |
| Job list         | Graveyard          |

## Visual rules
- Dark background (`#0b0a10`), bone-white text (`#ece6d9`), ectoplasm green accent
  (`#7cf5a5`) for life/success, blood red (`#e5484d`) only for errors and CVEs.
- Headings: gothic display font (`UnifrakturCook` / `Pirata One`). Body: `Inter`.
  Never use the display font for paragraphs, numbers or code.
- Fog and particles sit behind content at low opacity and never reduce text contrast
  below WCAG AA (4.5:1 for body text).

## Accessibility
- Every animation respects `prefers-reduced-motion` (Framer Motion `useReducedMotion`).
- All interactive elements are reachable by keyboard and have a visible focus ring.
- Decay score is never conveyed by colour alone: always show the number and a label.
