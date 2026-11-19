# Tasks: Resurrect someone/deadrepo

- [ ] 1. Rewrite Python 2 syntax with 2to3 fixers (_Req 1_)
  - files: `deadrepo/__init__.py`, `deadrepo/core.py`, `tests/test_core.py`
- [ ] 2. Modernise idioms with pyupgrade --py312-plus (_Req 2_)
  - files: `deadrepo/core.py`
- [ ] 3. Replace removed stdlib modules and APIs (_Req 3_)
  - files: `deadrepo/core.py`, `tests/test_core.py`
- [ ] 4. Bump and replace dependencies (_Req 4_)
  - files: `requirements.txt`
- [ ] 5. Raise vulnerable pins to fixed versions (_Req 5_)
  - files: `requirements.txt`
- [ ] 6. Add smoke tests and property tests (_Req 6_)
- [ ] 7. Install on Python 3.12 and run tests in the sandbox (_Req 6_)
- [ ] 8. Repair remaining failures with the LLM, one file at a time (_Req 6_)
