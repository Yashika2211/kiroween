# Design: Ritual

`backend/necromancer/ritual/planner.py` exposes `build_plan(cert) -> ResurrectionPlan`.

```
DeathCertificate
   │
   ├─ classify findings ──▶ ProblemClass[]  (syntax, stdlib, deps, vulns, tests)
   │
   ├─ render_requirements(classes)  ──▶ requirements.md
   ├─ render_design(classes)        ──▶ design.md
   └─ plan_tasks(classes)           ──▶ PlanTask[] ──▶ tasks.md
```

`PlanTask` has `id`, `title`, `kind` (`rewrite` | `deps` | `vulns` | `llm` | `tests` | `verify`),
`files`, `requirement_ids` and `status` (`pending` → `running` → `done` | `failed` | `skipped`).
The resurrection loop consumes the same `PlanTask` list and updates statuses, which the UI
renders as candles: unlit (pending), flickering (running), lit (done), snuffed (failed).

Rendering is plain string templates so the output is stable and easy to snapshot-test.
