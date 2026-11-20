# Devpost submission kit

Everything needed for the Kiroween 2026 submission (category: **Resurrection**).
Deadline: **Dec 4, 2026, 2:00 PM PT**.

## Checklist

- [x] Public repo with an OSI licence (MIT) and `.kiro/` committed (not in `.gitignore`)
- [x] README lets a judge run it locally in under 5 minutes
- [ ] **Fill in "How I used Kiro" below with your real experience** (judges weigh this)
- [ ] Record the demo video (script below; 3 minutes or less) and upload to YouTube or Vimeo as public/unlisted
- [ ] Deploy to a public URL (see "Deploying") and put it in the Devpost form
- [ ] Add `GITHUB_TOKEN` + `ANTHROPIC_API_KEY` to the deployed backend so judges see a real PR
- [ ] Paste the text below into Devpost

---

## Devpost text

### Inspiration
Every company runs on open-source packages that nobody maintains anymore. They break on
current Python, pin versions with known CVEs, and get kept alive only because rewriting them
is expensive. I wanted to give those projects a proper funeral and then bring them back.

### What it does
Paste the URL of an abandoned Python repository. Necromancer:

1. **Performs an autopsy** in about 10 seconds and issues a **Death Certificate**: when it was born
   and died, Python 2 markers found by a static scanner, dead and outdated dependencies, known
   vulnerabilities from OSV, whether it still installs on Python 3.12, a decay score out of
   100 and a cause of death.
2. **Performs the ritual**: it writes a Kiro-style resurrection spec (requirements in EARS
   format, design and tasks) from those findings.
3. **Resurrects it**: 2to3 fixers, pyupgrade, a removed-API replacement table, dependency
   bumps that clear the CVEs, generated smoke and hypothesis property tests, then the real
   tests inside a network-isolated Docker sandbox. Anything still failing goes to Claude,
   one file at a time, until the tests pass.
4. **Rises**: it opens a pull request on your fork with the autopsy and the plan in the body.

Each step streams live: candles light up as tasks finish, and every rewrite appears as a diff.

### How I built it
- **Backend:** Python 3.12, FastAPI, Server-Sent Events, SQLite; fissix (a maintained
  lib2to3 fork), pyupgrade, the OSV batch API, the GitHub REST API, the Anthropic API.
- **Sandbox:** one Docker container per phase with dropped capabilities, memory/CPU/PID limits,
  a read-only root, a non-root user, and **no network while tests run**. The host never imports or
  executes cloned code; even `setup.py` is read with `ast`.
- **Frontend:** Next.js 14 App Router, TypeScript strict, Tailwind, Framer Motion; canvas fog,
  an aged-paper certificate, SVG candles, a cracking-tombstone rise animation. Every animation
  respects `prefers-reduced-motion`, and scores are always shown as a number plus a label.
- **Custom MCP server** `mcp-osv` exposing `query_vulns` and `get_vuln`.
- 180+ backend tests, including hypothesis property tests showing the rewrites preserve
  Python 2 semantics.

### How I used Kiro
<!-- WRITE THIS YOURSELF. Be specific and honest; judges compare it with the .kiro/ folder.
     Prompts to answer:
     - Spec-driven development: which spec did you start from? Did Kiro's requirements → design → tasks
       flow change your plan (e.g. the decay-score weights, the sandbox two-phase design)?
     - Steering: which steering doc made the biggest difference (sandbox-security.md? theme-and-tone.md)?
     - Hooks: did the run-tests-on-save or rescan-vulns hook catch something real? Give an example.
     - MCP: how did you use the mcp-osv server from inside Kiro?
     - Vibe coding vs specs: where did each work better?
-->

### Challenges I ran into
- **Python 2 semantics hide in code that parses.** PyClojure's tests compared `map(...)` to a
  list, and pyfin compared `dict.keys()` to a list. Both files are valid Python 3 and both are
  wrong in it. The fix was to detect a Python 2 *codebase* (any unparseable file or any
  Python-2-only builtin) and apply full 2to3 semantics everywhere.
- **Docker on macOS only shares `$HOME`.** A workspace under `/tmp` mounted as an empty folder
  and the install probe "passed" with nothing to install. The sandbox now refuses to run on an
  empty mount.
- **Honesty in the UI.** The first version showed every finished job as "Risen". Now a repo
  only glows green when its tests pass; otherwise it is "Stirring".

### Accomplishments that I'm proud of
- `opendoor-labs/pyfin` (13 known CVEs, numpy 1.8.1 pins that can't build on 3.12) goes to
  **8/8 tests passing** with deterministic fixes alone, with no LLM involved.
- The whole pipeline treats repositories as untrusted, and tests prove it: secrets never reach
  the sandbox, `setup.py` is never executed, and the GitHub token never lands in git config.

### What I learned
<!-- your words -->

### What's next for Necromancer
- Batch mode: resurrect every dead dependency in a `requirements.txt`
- JavaScript/Node resurrection with the same pipeline
- A GitHub App that comments a Death Certificate on PRs adding abandoned dependencies

### Built with
python · fastapi · docker · next.js · typescript · tailwindcss · framer-motion · sqlite ·
osv · github-api · anthropic-claude · mcp · kiro · hypothesis · fissix · pyupgrade

---

## Demo video script (about 2:45)

Record at 1440p, browser zoom 110%, with a GitHub token and an Anthropic key configured. Pre-pull
`python:3.12-slim` and run each demo once beforehand so pip caches are warm.

| Time | On screen | Say |
|---|---|---|
| 0:00 | Graveyard home page, fog drifting | "Thousands of Python packages companies depend on are dead. Necromancer brings them back." |
| 0:12 | Click **opendoor-labs/pyfin** | "I'll summon a finance library abandoned in 2014." |
| 0:15 | Autopsy steps lighting up | "It clones the repo, scans every file without running it, checks PyPI and OSV, and tries to install it on Python 3.12 in a sandbox." |
| 0:28 | Death Certificate appears | "Cause of death: dependency rot. numpy 1.8 can't even build today, and there are 13 known vulnerabilities. Decay: 75 out of 100." |
| 0:45 | Scroll through dependencies and CVEs | "Every finding has evidence: the old pins, the CVEs and the versions that fix them." |
| 0:55 | **Begin the Ritual** → candles | "The ritual writes a Kiro-style spec, then runs each task. 2to3, pyupgrade, dependency bumps, generated tests…" |
| 1:15 | Diff viewer | "Every change is a reviewable diff, labelled by which tool made it." |
| 1:25 | Tests pass → tombstone cracks → **It lives!** | "Eight of eight tests pass on Python 3.12, and it opened a pull request." |
| 1:35 | Click the PR on GitHub | "The PR carries the autopsy and the plan, so a reviewer knows exactly what happened." |
| 1:50 | Summon **PyClojure**, fast-forward | "This one has real Python 2 syntax. Deterministic fixes get it most of the way, then Claude repairs the file the traceback blames, one file at a time." |
| 2:15 | `.kiro/` folder in Kiro | "Built with Kiro: specs for every feature, steering for sandbox security and tone, hooks that rerun tests and rescan vulnerabilities, and my own OSV MCP server." |
| 2:35 | Graveyard with risen graves | "Necromancer. Let dead code rest… or don't." |

---

## Deploying

The backend needs a Docker daemon to run sandboxes, so serverless hosts won't work for it.

- **Backend:** a small VM (e.g. a 2 vCPU / 4 GB droplet or EC2 instance) with Docker:
  `git clone … && cp .env.example .env && docker compose up -d --build api`, behind Caddy or nginx for TLS.
  Set `NECRO_CORS_ORIGINS` to the frontend URL.
- **Frontend:** Vercel (root directory `frontend/`) with `NEXT_PUBLIC_API_URL=https://<your-api-host>`,
  or the `web` service in `docker-compose.yml`.
- Pre-populate the graveyard for judges: `scripts/seed_demo.sh https://<your-api-host> --resurrect`.
- `NECRO_RATE_LIMIT_PER_HOUR` (default 20 per client) protects the sandbox host from abuse.
