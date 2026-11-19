# Requirements: Graveyard UI

### Requirement 1: Graveyard dashboard
1. The home page SHALL show a summon form and a grid of tombstones, one per job.
2. Each tombstone SHALL show repo name, "born – died" years and cause of death.
3. Resurrected repos SHALL glow green and show "Risen".
4. Tombstones SHALL be links reachable by keyboard.

### Requirement 2: Death Certificate
1. The certificate page SHALL render as an aged-paper document with vital records, decay score
   (number + label + meter), markers, dependencies, vulnerabilities and install probe output.
2. While the autopsy runs, the page SHALL stream progress steps live.
3. The page SHALL offer "Begin the Ritual".

### Requirement 3: Ritual screen
1. The ritual screen SHALL show plan tasks as candles that light up as they complete.
2. It SHALL show a live log and a diff viewer for each changed file.

### Requirement 4: Rise
1. WHEN the job completes THEN the tombstone SHALL crack and the repo rise, revealing the PR link
   (or patch download).
2. IF the user prefers reduced motion THEN the rise SHALL be a simple fade.

### Requirement 5: Accessibility and polish
1. Body text SHALL meet WCAG AA contrast against the background including fog.
2. All animations SHALL respect `prefers-reduced-motion`.
3. Error states SHALL be shown in plain language with a way to retry.
