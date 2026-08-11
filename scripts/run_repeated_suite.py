import argparse
import json
import random
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent.loop import run_agent
from evaluation.checks import (
    programmatic_check,
    trajectory_check,
    graceful_error_check,
)
from evaluation.judge import HeuristicJudge
from tracing.tracer import save_trace


def load_tasks(path):
    tasks = []

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if line:
                tasks.append(json.loads(line))

    return tasks


def get_llm(name):
    if name == "mock":
        from agent.llm import MockLLM

        return MockLLM()

    if name == "mockv2":
        from agent.mock_llm_v2 import MockLLMv2

        return MockLLMv2()

    if name == "broken":
        from agent.broken_llm import BrokenMockLLM

        return BrokenMockLLM()

    if name == "flaky":
        from agent.flaky_llm import FlakyMockLLM

        return FlakyMockLLM()

    raise ValueError("Unknown LLM. Use mock, mockv2, broken, or flaky.")


def get_judge(name):
    if name == "heuristic":
        return HeuristicJudge()

    raise ValueError("Unknown judge. Use heuristic.")


def build_failure_reasons(run, programmatic, trajectory):
    reasons = []

    if run["error"]:
        reasons.append(f"run_error:{run['error']}")

    if not programmatic["passed"]:
        reasons.append("programmatic_check_failed")

    if not trajectory["passed"]:
        if trajectory["missing_tools"]:
            reasons.append("missing_tools")

        if trajectory["used_forbidden_tools"]:
            reasons.append("used_forbidden_tools")

        if trajectory["looping_tools"]:
            reasons.append("looping")

    return reasons


def evaluate_single_run(task, run, judge):
    expected_behavior = task.get("expected_behavior", "answer")

    if expected_behavior == "graceful_error":
        programmatic = {
            "passed": graceful_error_check(run["final_answer"]),
            "predicted": run["final_answer"],
            "expected": "graceful_error",
        }
    else:
        programmatic = programmatic_check(
            predicted=run["final_answer"],
            expected=task["expected_answer"],
        )

    trajectory = trajectory_check(
        trace=run["trace"],
        task=task,
    )

    judge_result = judge.score(
        task=task,
        run=run,
        programmatic=programmatic,
        trajectory=trajectory,
    )

    passed = (
        programmatic["passed"]
        and trajectory["passed"]
        and run["error"] is None
    )

    failure_reasons = []

    if not passed:
        failure_reasons = build_failure_reasons(
            run=run,
            programmatic=programmatic,
            trajectory=trajectory,
        )

    return {
        "passed": passed,
        "programmatic_passed": programmatic["passed"],
        "trajectory_passed": trajectory["passed"],
        "judge_score": judge_result["judge_score"],
        "judge_reason": judge_result["judge_reason"],
        "error": run["error"],
        "failure_reasons": failure_reasons,
        "final_answer_preview": str(run["final_answer"])[:120],
        "total_tokens": run["trace"]["total_tokens"],
        "total_latency_ms": run["trace"]["total_latency_ms"],
        "total_cost": run["trace"].get("total_cost", 0.0),
    }


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--suite",
        default=str(ROOT / "tasks" / "suite.jsonl"),
    )

    parser.add_argument(
        "--agent-version",
        default="repeated",
    )

    parser.add_argument(
        "--llm",
        default="mockv2",
    )

    parser.add_argument(
        "--judge",
        default="heuristic",
    )

    parser.add_argument(
        "--runs",
        type=int,
        default=3,
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=42,
    )

    parser.add_argument(
        "--save-traces",
        action="store_true",
    )

    args = parser.parse_args()

    random.seed(args.seed)

    tasks = load_tasks(args.suite)
    llm = get_llm(args.llm)
    judge = get_judge(args.judge)

    task_summaries = []

    total_runs = 0
    total_passed_runs = 0

    all_judge_scores = []
    all_costs = []
    all_latencies = []

    global_failure_reason_counts = Counter()
    global_judge_reason_counts = Counter()

    trace_dir = ROOT / "reports" / "traces" / f"{args.agent_version}_repeated"

    for task in tasks:
        task_runs = []

        pass_count = 0

        task_judge_scores = []
        task_costs = []
        task_latencies = []

        task_failure_reason_counts = Counter()
        task_judge_reason_counts = Counter()

        for run_index in range(args.runs):
            run = run_agent(
                task=task,
                llm=llm,
                agent_version=args.agent_version,
            )

            if args.save_traces:
                save_trace(run["trace"], outdir=trace_dir)

            evaluation = evaluate_single_run(
                task=task,
                run=run,
                judge=judge,
            )

            evaluation["run_index"] = run_index

            task_runs.append(evaluation)

            total_runs += 1

            if evaluation["passed"]:
                pass_count += 1
                total_passed_runs += 1

            task_judge_scores.append(evaluation["judge_score"])
            task_costs.append(evaluation["total_cost"])
            task_latencies.append(evaluation["total_latency_ms"])

            all_judge_scores.append(evaluation["judge_score"])
            all_costs.append(evaluation["total_cost"])
            all_latencies.append(evaluation["total_latency_ms"])

            for reason in evaluation["failure_reasons"]:
                task_failure_reason_counts[reason] += 1
                global_failure_reason_counts[reason] += 1

            task_judge_reason_counts[evaluation["judge_reason"]] += 1
            global_judge_reason_counts[evaluation["judge_reason"]] += 1

        run_pass_rate = pass_count / args.runs if args.runs else 0.0

        flaky = pass_count > 0 and pass_count < args.runs

        task_summaries.append(
            {
                "task_id": task["task_id"],
                "difficulty": task.get("difficulty"),
                "expected_behavior": task.get("expected_behavior", "answer"),
                "runs": args.runs,
                "pass_count": pass_count,
                "pass_rate": run_pass_rate,
                "flaky": flaky,
                "average_judge_score": (
                    sum(task_judge_scores) / len(task_judge_scores)
                    if task_judge_scores
                    else 0.0
                ),
                "total_cost": sum(task_costs),
                "average_latency_ms": (
                    sum(task_latencies) / len(task_latencies)
                    if task_latencies
                    else 0.0
                ),
                "failure_reason_counts": dict(task_failure_reason_counts),
                "judge_reason_counts": dict(task_judge_reason_counts),
                "runs_detail": task_runs,
            }
        )

    total_tasks = len(task_summaries)

    flaky_tasks = [
        task_summary
        for task_summary in task_summaries
        if task_summary["flaky"]
    ]

    run_pass_rate = (
        total_passed_runs / total_runs
        if total_runs
        else 0.0
    )

    average_task_pass_rate = (
        sum(task_summary["pass_rate"] for task_summary in task_summaries)
        / total_tasks
        if total_tasks
        else 0.0
    )

    flaky_rate = (
        len(flaky_tasks) / total_tasks
        if total_tasks
        else 0.0
    )

    average_judge_score = (
        sum(all_judge_scores) / len(all_judge_scores)
        if all_judge_scores
        else 0.0
    )

    total_cost = sum(all_costs)

    average_latency = (
        sum(all_latencies) / len(all_latencies)
        if all_latencies
        else 0.0
    )

    summary = {
        "summary": {
            "agent_version": args.agent_version,
            "llm": llm.name,
            "judge": judge.name,
            "runs_per_task": args.runs,
            "seed": args.seed,
            "total_tasks": total_tasks,
            "total_runs": total_runs,
            "total_passed_runs": total_passed_runs,
            "run_pass_rate": run_pass_rate,
            "average_task_pass_rate": average_task_pass_rate,
            "flaky_tasks_count": len(flaky_tasks),
            "flaky_rate": flaky_rate,
            "average_judge_score": average_judge_score,
            "total_cost": total_cost,
            "average_latency_ms": average_latency,
            "failure_reason_counts": dict(global_failure_reason_counts),
            "judge_reason_counts": dict(global_judge_reason_counts),
        },
        "tasks": task_summaries,
    }

    reports_dir = ROOT / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    json_path = reports_dir / f"{args.agent_version}_repeated_results.json"
    json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    markdown = []

    markdown.append(f"# Repeated Run Report: {args.agent_version}")
    markdown.append("")
    markdown.append(f"- LLM: `{llm.name}`")
    markdown.append(f"- Judge: `{judge.name}`")
    markdown.append(f"- Runs per task: `{args.runs}`")
    markdown.append(f"- Seed: `{args.seed}`")
    markdown.append(f"- Total tasks: `{total_tasks}`")
    markdown.append(f"- Total runs: `{total_runs}`")
    markdown.append(f"- Passed runs: `{total_passed_runs}`")
    markdown.append(f"- Run pass rate: `{run_pass_rate:.2%}`")
    markdown.append(f"- Average task pass rate: `{average_task_pass_rate:.2%}`")
    markdown.append(f"- Flaky tasks: `{len(flaky_tasks)}`")
    markdown.append(f"- Flaky rate: `{flaky_rate:.2%}`")
    markdown.append(f"- Average judge score: `{average_judge_score:.2f} / 3`")
    markdown.append(f"- Total cost: `{total_cost:.6f}`")
    markdown.append(f"- Average latency: `{average_latency:.2f} ms`")
    markdown.append("")

    markdown.append("## Flaky Tasks")
    markdown.append("")

    if flaky_tasks:
        markdown.append("| Task | Difficulty | Runs | Pass Count | Pass Rate | Avg Judge |")
        markdown.append("|---|---|---:|---:|---:|---:|")

        for task_summary in flaky_tasks:
            markdown.append(
                "| {task_id} | {difficulty} | {runs} | {pass_count} | {pass_rate:.2%} | {avg_judge:.2f} |".format(
                    task_id=task_summary["task_id"],
                    difficulty=task_summary.get("difficulty", ""),
                    runs=task_summary["runs"],
                    pass_count=task_summary["pass_count"],
                    pass_rate=task_summary["pass_rate"],
                    avg_judge=task_summary["average_judge_score"],
                )
            )
    else:
        markdown.append("No flaky tasks detected.")

    markdown.append("")

    markdown.append("## Task Stability")
    markdown.append("")
    markdown.append("| Task | Difficulty | Runs | Pass Count | Pass Rate | Flaky | Avg Judge |")
    markdown.append("|---|---|---:|---:|---:|---:|---:|")

    for task_summary in task_summaries:
        markdown.append(
            "| {task_id} | {difficulty} | {runs} | {pass_count} | {pass_rate:.2%} | {flaky} | {avg_judge:.2f} |".format(
                task_id=task_summary["task_id"],
                difficulty=task_summary.get("difficulty", ""),
                runs=task_summary["runs"],
                pass_count=task_summary["pass_count"],
                pass_rate=task_summary["pass_rate"],
                flaky=task_summary["flaky"],
                avg_judge=task_summary["average_judge_score"],
            )
        )

    markdown.append("")

    markdown.append("## Failure Reasons")
    markdown.append("")

    if global_failure_reason_counts:
        markdown.append("| Failure Reason | Count |")
        markdown.append("|---|---:|")

        for reason, count in global_failure_reason_counts.most_common():
            markdown.append(f"| {reason} | {count} |")
    else:
        markdown.append("No failures detected.")

    markdown_path = reports_dir / f"{args.agent_version}_repeated_report.md"
    markdown_path.write_text("\n".join(markdown), encoding="utf-8")

    print(json.dumps(summary["summary"], indent=2))
    print(f"Repeated results JSON saved to: {json_path}")
    print(f"Repeated report Markdown saved to: {markdown_path}")


if __name__ == "__main__":
    main()