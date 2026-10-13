"""Run the bug-fixing agent on every repo in evals/ and report the pass rate.

Usage:  python run_evals.py
Writes: logs/eval_<timestamp>.log (full trace) and evals/results.json
"""
import json, sys, time
from contextlib import redirect_stdout
from datetime import datetime
from pathlib import Path

import agent

ROOT = Path(__file__).parent
GROUPS = ["dev", "heldout"]


class Tee:
    """Write to the terminal and a log file at the same time."""
    def __init__(self, *streams): self.streams = streams
    def write(self, s):
        for st in self.streams: st.write(s)
    def flush(self):
        for st in self.streams: st.flush()


def run_all():
    results = []
    for group in GROUPS:
        for repo in sorted((ROOT / "evals" / group).iterdir()):
            if not repo.is_dir():
                continue
            print(f"\n===== {group}/{repo.name} =====")
            start = time.time()
            try:
                final = agent.fix_repo(str(repo))
                passed, attempts, error = final["passed"], final["attempts"], ""
            except Exception as e:  # an agent crash counts as a failure, not a stop
                passed, attempts, error = False, 0, repr(e)
                print("CRASH:", error)
            results.append({"group": group, "task": repo.name, "passed": passed,
                            "attempts": attempts, "seconds": round(time.time() - start, 1),
                            "error": error})
            time.sleep(3)  # be gentle with free-tier rate limits
    return results


def summarize(results):
    print("\n\n================ SUMMARY ================")
    print(f"{'group':<9}{'task':<22}{'result':<8}{'attempts':<10}{'secs'}")
    for r in results:
        print(f"{r['group']:<9}{r['task']:<22}{'PASS' if r['passed'] else 'FAIL':<8}{r['attempts']:<10}{r['seconds']}")
    for group in GROUPS:
        rs = [r for r in results if r["group"] == group]
        if rs:
            ok = sum(r["passed"] for r in rs)
            print(f"{group}: {ok}/{len(rs)} fixed ({100 * ok / len(rs):.0f}%)")
    ok = sum(r["passed"] for r in results)
    print(f"OVERALL: {ok}/{len(results)} fixed ({100 * ok / max(len(results), 1):.0f}%)")


if __name__ == "__main__":
    (ROOT / "logs").mkdir(exist_ok=True)
    log_path = ROOT / "logs" / f"eval_{datetime.now():%Y%m%d_%H%M%S}.log"
    with open(log_path, "w", encoding="utf-8") as log:
        with redirect_stdout(Tee(sys.stdout, log)):
            results = run_all()
            summarize(results)
    (ROOT / "evals" / "results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nLog saved to {log_path}")
