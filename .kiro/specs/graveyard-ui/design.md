# Design: Graveyard UI

## Routes (Next.js App Router)
| Route | Purpose |
|---|---|
| `/` | Summon form + graveyard grid |
| `/jobs/[id]` | Death Certificate (live during autopsy) |
| `/jobs/[id]/ritual` | Candles, live log, diffs, then the Rise |

## Data flow
`lib/api.ts` wraps REST calls; `lib/useJobStream.ts` opens an `EventSource` on
`/api/jobs/{id}/events` and reduces events into a `JobView` with `useReducer`.

## Components
- `Fog` (canvas particles, paused when reduced motion)
- `Tombstone`, `GraveyardGrid`, `SummonForm`
- `DeathCertificate`, `DecayMeter`, `FindingsTable`, `VulnList`
- `CandleRow`, `RitualLog`, `DiffViewer`
- `RiseScene`

## Fonts
`next/font/google`: `Pirata_One` for display, `Inter` for body, `JetBrains_Mono` for code.
