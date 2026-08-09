import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def save_trace(trace, outdir=None):
    if outdir is None:
        outdir = ROOT / "reports" / "traces"
    else:
        outdir = Path(outdir)

    outdir.mkdir(parents=True, exist_ok=True)

    task_id = trace.get("task_id", "task")
    trace_id = trace.get("trace_id", "trace")

    filename = f"{task_id}_{trace_id}.json"
    path = outdir / filename

    path.write_text(json.dumps(trace, indent=2), encoding="utf-8")

    return str(path)