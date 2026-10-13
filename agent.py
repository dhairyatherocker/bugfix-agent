"""Autonomous bug-fixing agent built with LangGraph.

Graph:  run_tests -> (pass -> END | fail -> propose_patch -> apply_patch -> run_tests ...)
The tests are the judge. The agent may never edit test files.
"""
import json, os, re, shutil, subprocess, sys, tempfile
from pathlib import Path
from typing import TypedDict, List, Optional

try:
    from dotenv import load_dotenv; load_dotenv()  # reads GROQ_API_KEY from .env
except ImportError:
    pass
from langgraph.graph import StateGraph, END
from langchain.chat_models import init_chat_model

MAX_ATTEMPTS = int(os.getenv("MAX_ATTEMPTS", 4))
MODEL = os.getenv("MODEL", "groq:openai/gpt-oss-120b")  # e.g. "groq:llama-3.3-70b-versatile", "google_genai:gemini-2.5-flash"


class State(TypedDict):
    repo: str
    passed: bool
    test_output: str
    attempts: int
    patch: Optional[dict]
    history: List[str]  # what was tried and what happened (fed back to the LLM)


# ---------- helpers ----------
def is_test_file(p: Path) -> bool:
    return p.name.startswith("test_") or p.name.endswith("_test.py") or "tests" in p.parts


def read_sources(repo: str) -> str:
    out = []
    for p in sorted(Path(repo).rglob("*.py")):
        if is_test_file(p.relative_to(repo)):
            continue
        out.append(f"### FILE: {p.relative_to(repo)}\n{p.read_text(encoding='utf-8', errors='replace')}")
    return "\n\n".join(out)


def extract_json(text: str) -> dict:
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    return json.loads(text)


# ---------- nodes ----------
def run_tests(state: State) -> dict:
    try:
        r = subprocess.run([sys.executable, "-m", "pytest", "-x", "-q", "--tb=short"],
                           cwd=state["repo"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
        passed, output = r.returncode == 0, (r.stdout + r.stderr)[-3000:]
    except subprocess.TimeoutExpired:
        passed, output = False, "Tests timed out after 60s (possible infinite loop)."
    print(f"[run_tests] attempt={state['attempts']} passed={passed}")
    return {"passed": passed, "test_output": output}


def propose_patch(state: State) -> dict:
    llm = init_chat_model(MODEL, temperature=0, max_retries=5)
    prompt = f"""You are fixing a bug in a Python project. Tests are failing.

SOURCE FILES (non-test):
{read_sources(state['repo'])}

FAILING TEST OUTPUT:
{state['test_output']}

PREVIOUS ATTEMPTS THAT DID NOT WORK:
{chr(10).join(state['history']) or 'none'}

Fix the bug by rewriting ONE source file. Never modify tests.
Reply with ONLY JSON: {{"file": "<relative path>", "content": "<full new file content>", "reason": "<one line>"}}"""
    try:
        patch = extract_json(llm.invoke(prompt).content)
    except Exception as e:  # bad JSON, API error, etc.
        patch = {"error": f"could not get a valid patch: {e}"}
    return {"patch": patch, "attempts": state["attempts"] + 1}


def apply_patch(state: State) -> dict:
    patch, repo = state["patch"] or {}, Path(state["repo"]).resolve()
    note = ""
    if "error" in patch:
        note = patch["error"]
    else:
        target = (repo / patch.get("file", "")).resolve()
        if repo not in target.parents:
            note = "rejected: path outside repo"
        elif is_test_file(target.relative_to(repo)):
            note = "rejected: agent may not edit tests"
        elif not target.exists():
            note = "rejected: file does not exist"
        else:
            target.write_text(patch["content"], encoding="utf-8")
            note = f"edited {patch['file']}: {patch.get('reason', '')}"
    print(f"[apply_patch] {note}")
    return {"history": state["history"] + [f"Attempt {state['attempts']}: {note} -> tests still failed"]}


# ---------- routing ----------
def route(state: State) -> str:
    if state["passed"]:
        return "done"
    if state["attempts"] >= MAX_ATTEMPTS:
        return "give_up"
    return "retry"


def build_graph():
    g = StateGraph(State)
    g.add_node("run_tests", run_tests)
    g.add_node("propose_patch", propose_patch)
    g.add_node("apply_patch", apply_patch)
    g.set_entry_point("run_tests")
    g.add_conditional_edges("run_tests", route,
                            {"done": END, "give_up": END, "retry": "propose_patch"})
    g.add_edge("propose_patch", "apply_patch")
    g.add_edge("apply_patch", "run_tests")
    return g.compile()


def fix_repo(repo_path: str) -> State:
    """Copy the repo to a temp dir (original stays untouched) and run the agent."""
    work = tempfile.mkdtemp(prefix="bugfix_")
    work_repo = shutil.copytree(repo_path, os.path.join(work, "repo"))
    init: State = {"repo": work_repo, "passed": False, "test_output": "",
                   "attempts": 0, "patch": None, "history": []}
    final = build_graph().invoke(init)
    print("RESULT:", "FIXED" if final["passed"] else "FAILED", f"in {final['attempts']} attempt(s)")
    print("Fixed copy at:", work_repo)
    return final


if __name__ == "__main__":
    fix_repo(sys.argv[1] if len(sys.argv) > 1 else "demo_repo")
