# Autonomous Bug-Fixing Agent (LangGraph)

Given a Python repo with failing tests, the agent locates the bug, patches the source, re-runs the tests, and retries until they pass or the attempt limit is hit.

## Architecture
run_tests -> (pass -> END | fail -> propose_patch -> apply_patch -> run_tests)

TODO: add Mermaid diagram (`build_graph().get_graph().draw_mermaid()`).

## Setup
pip install -r requirements.txt
cp .env.example .env   # then put your GROQ_API_KEY in .env (never commit it)
python agent.py demo_repo

## Design decisions
- Tests are the verifier; the agent cannot edit test files (prevents "cheating").
- Works on a temp copy; the original repo is never modified.
- Retry cap + test timeout for reliability; failed attempts are fed back to the LLM.

## Evaluation
TODO: evals/ with 5-10 buggy repos, and a script that prints the pass rate.

## Limitations / future work
TODO
