"""Streamlit UI for the bug-fixing agent.  Run:  streamlit run app.py"""
import difflib, io, os, shutil, sys, tempfile, zipfile
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))
import agent  # noqa: E402

st.set_page_config(page_title="Autonomous Bug-Fixing Agent", page_icon="🛠️", layout="wide")

SKIP_DIRS = {"__pycache__", ".pytest_cache", ".venv", "venv", ".git", "node_modules"}


# ---------- helpers ----------
def builtin_repos() -> dict:
    repos = {}
    if (ROOT / "demo_repo").is_dir():
        repos["demo_repo"] = ROOT / "demo_repo"
    for group in ("dev", "heldout"):
        d = ROOT / "evals" / group
        if d.is_dir():
            for p in sorted(d.iterdir()):
                if p.is_dir():
                    repos[f"{group}/{p.name}"] = p
    return repos


def copy_to_workdir(source: Path) -> Path:
    work = Path(tempfile.mkdtemp(prefix="bugfix_ui_"))
    return Path(shutil.copytree(source, work / "repo", ignore=shutil.ignore_patterns(*SKIP_DIRS)))


def extract_zip(data: bytes) -> Path:
    dest = Path(tempfile.mkdtemp(prefix="bugfix_ui_")) / "repo"
    dest.mkdir()
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        z.extractall(dest)
    entries = [p for p in dest.iterdir() if p.name != "__MACOSX"]
    return entries[0] if len(entries) == 1 and entries[0].is_dir() else dest


def py_files(repo: Path):
    for p in sorted(repo.rglob("*.py")):
        if not any(part in SKIP_DIRS for part in p.relative_to(repo).parts):
            yield p


def snapshot(repo: Path) -> dict:
    return {p.relative_to(repo).as_posix(): p.read_text(encoding="utf-8", errors="replace") for p in py_files(repo)}


def make_diff(old: str, new: str, name: str) -> str:
    return "\n".join(difflib.unified_diff(old.splitlines(), new.splitlines(), f"a/{name}", f"b/{name}", lineterm=""))


def zip_dir(repo: Path) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for p in repo.rglob("*"):
            if p.is_file() and not any(part in SKIP_DIRS for part in p.relative_to(repo).parts):
                z.write(p, p.relative_to(repo))
    return buf.getvalue()


def render(events: list):
    for e in events:
        if e["kind"] == "tests":
            title = "Initial test run" if e["attempt"] == 0 else f"Tests after patch {e['attempt']}"
            icon = "✅" if e["passed"] else "❌"
            with st.expander(f"{icon} {title}: {'passed' if e['passed'] else 'failed'}", expanded=not e["passed"]):
                st.code(e["output"] or "(no output)", language="text")
        elif e["kind"] == "patch":
            with st.expander(f"🔧 Patch {e['attempt']}: {e['file']}", expanded=True):
                st.write(e["reason"] or e["note"])
                if e["diff"]:
                    st.code(e["diff"], language="diff")
                else:
                    st.warning(e["note"])


# ---------- the agent run (streams each graph step to the UI) ----------
def run_agent(repo: Path, events: list, show):
    snap, pending, attempts = snapshot(repo), None, 0
    init = {"repo": str(repo), "passed": False, "test_output": "", "attempts": 0, "patch": None, "history": []}
    for update in agent.build_graph().stream(init, stream_mode="updates"):
        for node, data in update.items():
            if node == "run_tests":
                events.append({"kind": "tests", "attempt": attempts, "passed": data["passed"], "output": data["test_output"]})
            elif node == "propose_patch":
                pending, attempts = data["patch"] or {}, data["attempts"]
            elif node == "apply_patch":
                note = data["history"][-1]
                name = (pending or {}).get("file", "").replace("\\", "/")
                diff = ""
                if "edited" in note and name in snap:
                    new = pending["content"]
                    diff = make_diff(snap[name], new, name)
                    snap[name] = new
                events.append({"kind": "patch", "attempt": attempts, "file": name or "(none)",
                               "reason": (pending or {}).get("reason", ""), "note": note, "diff": diff})
            show()
    return events


# ---------- UI ----------
st.title("🛠️ Autonomous Bug-Fixing Agent")
st.caption("Give it a Python repo with failing tests. It reads the code, patches the bug, re-runs the tests, "
           "and retries until they pass or the attempt limit is reached. It never edits the tests.")

with st.sidebar:
    st.header("Settings")
    model = st.text_input("Model (provider:name)", value=agent.MODEL)
    max_attempts = st.slider("Max fix attempts", 1, 6, agent.MAX_ATTEMPTS)
    if model.startswith("groq") and not os.getenv("GROQ_API_KEY"):
        st.warning("GROQ_API_KEY not found. Add it to your .env file.")
    with st.expander("How it works"):
        st.graphviz_chart('digraph { rankdir=LR; node [shape=box, style=rounded]; '
                          'run_tests -> propose_patch [label="fail"]; propose_patch -> apply_patch; '
                          'apply_patch -> run_tests; run_tests -> END [label="pass or limit"]; }')

mode = st.radio("Repo to fix", ["Built-in example", "Upload a repo (.zip)"], horizontal=True)
source, upload = None, None
if mode == "Built-in example":
    repos = builtin_repos()
    choice = st.selectbox("Choose a buggy repo", list(repos)) if repos else None
    if choice:
        source = repos[choice]
        with st.expander("Show code and tests"):
            for p in py_files(source):
                st.markdown(f"**{p.relative_to(source).as_posix()}**")
                st.code(p.read_text(encoding="utf-8", errors="replace"), language="python")
else:
    upload = st.file_uploader("Zip of a Python project with pytest tests", type="zip")

clicked = st.button("Fix it", type="primary", disabled=(source is None and upload is None))
area = st.empty()

if clicked:
    agent.MODEL, agent.MAX_ATTEMPTS = model, max_attempts
    events = []
    st.session_state["events"], st.session_state["outcome"] = events, None

    def show():
        with area.container():
            render(events)

    try:
        repo = copy_to_workdir(source) if source else extract_zip(upload.getvalue())
        if not any(py_files(repo)):
            raise ValueError("No Python files found in that repo.")
        with st.spinner("Agent is working..."):
            run_agent(repo, events, show)
        tests = [e for e in events if e["kind"] == "tests"]
        st.session_state["outcome"] = {"fixed": bool(tests and tests[-1]["passed"]),
                                       "attempts": sum(e["kind"] == "patch" for e in events),
                                       "zip": zip_dir(repo), "error": ""}
    except Exception as ex:
        st.session_state["outcome"] = {"fixed": False, "attempts": 0, "zip": None, "error": str(ex)}
elif st.session_state.get("events"):
    with area.container():
        render(st.session_state["events"])

out = st.session_state.get("outcome")
if out:
    if out["error"]:
        st.error(f"Run failed: {out['error']}")
    elif out["fixed"]:
        st.success(f"Fixed! All tests pass after {out['attempts']} patch(es).")
    else:
        st.error(f"Not fixed within {out['attempts']} attempt(s). The last test output is shown above.")
    if out["zip"]:
        st.download_button("Download fixed code (.zip)", out["zip"], file_name="fixed_repo.zip", mime="application/zip")
