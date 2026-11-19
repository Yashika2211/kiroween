# Design: Rise

`backend/necromancer/rise/`

- `pr_body.py`: pure renderer `render_pr_body(cert, plan, result) -> str`.
- `publisher.py`:
  1. `POST /repos/{owner}/{repo}/forks` and poll `GET /repos/{me}/{repo}` until it exists.
  2. In `workspace/<job>/after`: `git checkout -b necromancer/resurrect-<id>`, commit with the
     configured author, `git push` to the fork using `GIT_ASKPASS` pointing at a tiny script
     that echoes `$NECRO_GIT_TOKEN` from the subprocess environment.
  3. `POST /repos/{me}/{repo}/pulls` with `head=<branch>`, `base=<default branch>`.
- `patch.py`: `git diff` of before/after as a patch for the no-token path.
