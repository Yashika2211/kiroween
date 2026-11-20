# Tasks: Resurrection

- [x] 1. Workspace copy and diff utilities (_Req 4.1_)
- [x] 2. fissix-based py2→3 fixer (_Req 1.1_)
- [x] 3. pyupgrade fixer (_Req 1.2_)
- [x] 4. Removed-API replacement table (_Req 1.3_)
- [x] 5. Manifest rewriter for bumps, dead packages and vulns (_Req 1.4_)
- [x] 6. Smoke test generator (_Req 3.1_)
- [x] 7. Hypothesis property test generator (_Req 3.1_)
- [x] 8. LLM single-file fixer with parse validation (_Req 2.1–2.3_)
- [x] 9. Bounded fix loop with sandbox verification (_Req 2.4, 3.2_)
- [x] 10. Stream diffs and task statuses (_Req 4_)

## Added during implementation

- [x] 11. Detect `ModuleNotFoundError` in sandbox output and add the missing package
- [x] 12. Treat Python-2-only builtins as a Python 2 codebase (full 2to3 on every module)
- [x] 13. Report package install failures even when tests pass from source
